"""
Firm Applications API endpoints - Complete CRUD operations
"""
from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime
import structlog
import base64
import os
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app.core.auth import get_current_user, require_admin
from app.core.database import get_db
from app.services.auth import UserContext
from app.services.security_firm import SecurityFirmService
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()

router = APIRouter()



async def get_file_content_base64(file_path: str) -> str:
    """
    Get file content as base64 encoded string from S3 bucket.
    Raises HTTPException if file cannot be retrieved.
    """
    try:
        # Get S3 configuration from environment
        aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        aws_region_name = os.getenv("AWS_REGION_NAME", "af-south-1")
        bucket_name = os.getenv("AWS_S3_BUCKET")
        
        # Log configuration status for debugging
        logger.info(f"S3 Config - Bucket: {bucket_name}, Region: {aws_region_name}, "
                   f"Access Key: {'***' if aws_access_key_id else 'None'}, "
                   f"Secret Key: {'***' if aws_secret_access_key else 'None'}")
        
        if not bucket_name:
            logger.error("AWS_S3_BUCKET environment variable not set")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="S3 bucket configuration missing"
            )
            
        if not aws_access_key_id or not aws_secret_access_key:
            logger.error("AWS credentials not properly configured")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="S3 credentials configuration missing"
            )
        
        # Create S3 client
        s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region_name
        )
        
        try:
            logger.info(f"Downloading file from S3: bucket={bucket_name}, key={file_path}")
            response = s3_client.get_object(Bucket=bucket_name, Key=file_path)
            file_content = response['Body'].read()
            base64_content = base64.b64encode(file_content).decode('utf-8')
            logger.info(f"Successfully converted file to base64, size: {len(base64_content)} characters")
            return base64_content
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"S3 ClientError for file {file_path}: {error_code} - {e}")
            
            if error_code == 'NoSuchKey':
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Document file not found in storage"
                )
            elif error_code == 'AccessDenied':
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to document storage"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to retrieve document from storage"
                )
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error reading file {file_path}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process document"
        )


class FirmApplicationCreateRequest(BaseModel):
    """Create firm application request"""
    firm_id: str = Field(..., description="Security firm ID")
    admin_notes: Optional[str] = Field(None, description="Initial admin notes")


class FirmApplicationUpdateRequest(BaseModel):
    """Update firm application request"""
    status: Optional[str] = Field(None, description="Application status")
    rejection_reason: Optional[str] = Field(None, description="Reason for rejection")
    admin_notes: Optional[str] = Field(None, description="Admin notes")


class DocumentResponse(BaseModel):
    """Document response model"""
    id: str = Field(..., description="Document ID")
    document_type: str = Field(..., description="Document type")
    file_name: Optional[str] = Field(None, description="Original file name")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    mime_type: str = Field(..., description="MIME type")
    uploaded_by: str = Field(..., description="User ID who uploaded")
    is_verified: bool = Field(..., description="Verification status")
    verified_by: Optional[str] = Field(None, description="Admin user ID who verified")
    verified_at: Optional[str] = Field(None, description="Verification timestamp")
    content_base64: str = Field(..., description="Base64 encoded file content")
    created_at: str = Field(..., description="Upload timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


class FirmApplicationListItemResponse(BaseModel):
    """Firm application list item response model (without documents)"""
    id: str = Field(..., description="Application ID")
    firm_id: str = Field(..., description="Security firm ID")
    firm_name: Optional[str] = Field(None, description="Security firm name")
    status: str = Field(..., description="Application status")
    submitted_at: Optional[str] = Field(None, description="Submission timestamp")
    reviewed_at: Optional[str] = Field(None, description="Review timestamp")
    reviewed_by: Optional[str] = Field(None, description="Admin user ID who reviewed")
    rejection_reason: Optional[str] = Field(None, description="Rejection reason")
    admin_notes: Optional[str] = Field(None, description="Admin notes")
    document_count: int = Field(0, description="Number of associated documents")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


class FirmApplicationResponse(BaseModel):
    """Firm application response model (with documents)"""
    id: str = Field(..., description="Application ID")
    firm_id: str = Field(..., description="Security firm ID")
    firm_name: Optional[str] = Field(None, description="Security firm name")
    status: str = Field(..., description="Application status")
    submitted_at: Optional[str] = Field(None, description="Submission timestamp")
    reviewed_at: Optional[str] = Field(None, description="Review timestamp")
    reviewed_by: Optional[str] = Field(None, description="Admin user ID who reviewed")
    rejection_reason: Optional[str] = Field(None, description="Rejection reason")
    admin_notes: Optional[str] = Field(None, description="Admin notes")
    documents: List[DocumentResponse] = Field(default_factory=list, description="Associated documents")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


class FirmApplicationListResponse(BaseModel):
    """Paginated firm applications list response"""
    applications: List[FirmApplicationListItemResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


@router.post("/", response_model=FirmApplicationResponse)
async def create_firm_application(
    request: FirmApplicationCreateRequest,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new firm application
    
    Creates a new application for a security firm. Only firm admins
    can create applications for their firms.
    """
    try:
        service = SecurityFirmService(db)
        
        # Submit application (this creates it if it doesn't exist)
        application = await service.submit_application(
            firm_id=request.firm_id,
            user_id=current_user.user_id
        )
        
        # If admin notes were provided, update them
        if request.admin_notes:
            from app.models.security_firm import FirmApplication
            app_obj = await db.get(FirmApplication, application.id)
            if app_obj:
                app_obj.admin_notes = request.admin_notes
                await db.commit()
                await db.refresh(app_obj)
                application = app_obj
        
        # Get firm with documents for response
        firm = await service.get_firm_by_id(request.firm_id, current_user.user_id)
        
        # Get documents for this firm
        documents = []
        if firm and hasattr(firm, 'documents'):
            for doc in firm.documents:
                # Get base64 content
                content_base64 = await get_file_content_base64(doc.file_path)
                
                documents.append(DocumentResponse(
                    id=str(doc.id),
                    document_type=doc.document_type,
                    file_name=getattr(doc, 'file_name', None),
                    file_size=getattr(doc, 'file_size', None),
                    mime_type=doc.mime_type,
                    uploaded_by=str(doc.uploaded_by),
                    is_verified=doc.is_verified,
                    verified_by=str(doc.verified_by) if doc.verified_by else None,
                    verified_at=doc.verified_at.isoformat() if doc.verified_at else None,
                    content_base64=content_base64,
                    created_at=doc.created_at.isoformat(),
                    updated_at=doc.updated_at.isoformat()
                ))
        
        logger.info(
            "firm_application_created",
            application_id=str(application.id),
            firm_id=request.firm_id,
            user_id=str(current_user.user_id)
        )
        
        return FirmApplicationResponse(
            id=str(application.id),
            firm_id=str(application.firm_id),
            firm_name=firm.name if firm else None,
            status=application.status,
            submitted_at=application.submitted_at.isoformat() if application.submitted_at else None,
            reviewed_at=application.reviewed_at.isoformat() if application.reviewed_at else None,
            reviewed_by=str(application.reviewed_by) if application.reviewed_by else None,
            rejection_reason=application.rejection_reason,
            admin_notes=application.admin_notes,
            documents=documents,
            created_at=application.created_at.isoformat(),
            updated_at=application.updated_at.isoformat()
        )
        
    except ValueError as e:
        logger.warning(
            "firm_application_creation_failed",
            firm_id=request.firm_id,
            user_id=str(current_user.user_id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "firm_application_creation_error",
            firm_id=request.firm_id,
            user_id=str(current_user.user_id),
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create firm application"
        )


@router.get("/", response_model=FirmApplicationListResponse)
async def list_firm_applications(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    firm_id: Optional[str] = Query(None, description="Filter by firm ID"),
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List firm applications with pagination and filtering
    
    Returns paginated list of firm applications. Regular users see only
    their firm's applications, admins see all applications.
    """
    try:
        from app.models.security_firm import FirmApplication, SecurityFirm, FirmUser
        from sqlalchemy import select, func, and_, or_
        from sqlalchemy.orm import selectinload
        
        # Build base query (without loading documents for performance)
        query = select(FirmApplication).options(
            selectinload(FirmApplication.firm)
        )
        
        # Apply authorization filters
        if not current_user.has_permission("admin:all"):
            # Regular users can only see applications for firms they're associated with
            user_firms_query = select(FirmUser.firm_id).where(
                and_(
                    FirmUser.user_id == current_user.user_id,
                    FirmUser.status == "active"
                )
            )
            user_firm_ids = (await db.execute(user_firms_query)).scalars().all()
            
            if not user_firm_ids:
                # User has no firm associations
                return FirmApplicationListResponse(
                    applications=[],
                    total=0,
                    page=page,
                    per_page=per_page,
                    total_pages=0
                )
            
            query = query.where(FirmApplication.firm_id.in_(user_firm_ids))
        
        # Apply filters
        if status_filter:
            query = query.where(FirmApplication.status == status_filter)
        
        if firm_id:
            query = query.where(FirmApplication.firm_id == firm_id)
        
        # Get total count
        count_query = select(func.count(FirmApplication.id))
        if not current_user.has_permission("admin:all"):
            count_query = count_query.where(FirmApplication.firm_id.in_(user_firm_ids))
        if status_filter:
            count_query = count_query.where(FirmApplication.status == status_filter)
        if firm_id:
            count_query = count_query.where(FirmApplication.firm_id == firm_id)
        
        total = (await db.execute(count_query)).scalar()
        
        # Apply pagination
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)
        
        # Order by creation date (newest first)
        query = query.order_by(FirmApplication.created_at.desc())
        
        # Execute query
        result = await db.execute(query)
        applications = result.scalars().all()
        
        # Build response (without loading document content for performance)
        application_responses = []
        for app in applications:
            # Get document count without loading content
            document_count = 0
            if app.firm:
                from sqlalchemy import select, func
                from app.models.security_firm import FirmDocument
                count_query = select(func.count(FirmDocument.id)).where(
                    FirmDocument.firm_id == app.firm_id
                )
                document_count = (await db.execute(count_query)).scalar() or 0
            
            application_responses.append(FirmApplicationListItemResponse(
                id=str(app.id),
                firm_id=str(app.firm_id),
                firm_name=app.firm.name if app.firm else None,
                status=app.status,
                submitted_at=app.submitted_at.isoformat() if app.submitted_at else None,
                reviewed_at=app.reviewed_at.isoformat() if app.reviewed_at else None,
                reviewed_by=str(app.reviewed_by) if app.reviewed_by else None,
                rejection_reason=app.rejection_reason,
                admin_notes=app.admin_notes,
                document_count=document_count,
                created_at=app.created_at.isoformat(),
                updated_at=app.updated_at.isoformat()
            ))
        
        total_pages = (total + per_page - 1) // per_page
        
        return FirmApplicationListResponse(
            applications=application_responses,
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages
        )
        
    except Exception as e:
        logger.error(
            "list_firm_applications_error",
            user_id=str(current_user.user_id),
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list firm applications"
        )


@router.get("/{application_id}", response_model=FirmApplicationResponse)
async def get_firm_application(
    application_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific firm application by ID
    
    Returns detailed information about a firm application.
    Users can only access applications for firms they're associated with.
    """
    try:
        from app.models.security_firm import FirmApplication, FirmUser, SecurityFirm
        from sqlalchemy import select, and_
        from sqlalchemy.orm import selectinload
        
        # Get application with firm details and documents
        query = select(FirmApplication).options(
            selectinload(FirmApplication.firm).selectinload(SecurityFirm.documents)
        ).where(FirmApplication.id == application_id)
        
        result = await db.execute(query)
        application = result.scalar_one_or_none()
        
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Firm application not found"
            )
        
        # Check authorization
        if not current_user.has_permission("admin:all"):
            # Check if user is associated with this firm
            user_firm_query = select(FirmUser).where(
                and_(
                    FirmUser.user_id == current_user.user_id,
                    FirmUser.firm_id == application.firm_id,
                    FirmUser.status == "active"
                )
            )
            user_firm = (await db.execute(user_firm_query)).scalar_one_or_none()
            
            if not user_firm:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to access this application"
                )
        
        # Build documents list
        documents = []
        if application.firm and application.firm.documents:
            for doc in application.firm.documents:
                # Get base64 content
                content_base64 = await get_file_content_base64(doc.file_path)
                
                documents.append(DocumentResponse(
                    id=str(doc.id),
                    document_type=doc.document_type,
                    file_name=getattr(doc, 'file_name', None),
                    file_size=getattr(doc, 'file_size', None),
                    mime_type=doc.mime_type,
                    uploaded_by=str(doc.uploaded_by),
                    is_verified=doc.is_verified,
                    verified_by=str(doc.verified_by) if doc.verified_by else None,
                    verified_at=doc.verified_at.isoformat() if doc.verified_at else None,
                    content_base64=content_base64,
                    created_at=doc.created_at.isoformat(),
                    updated_at=doc.updated_at.isoformat()
                ))
        
        return FirmApplicationResponse(
            id=str(application.id),
            firm_id=str(application.firm_id),
            firm_name=application.firm.name if application.firm else None,
            status=application.status,
            submitted_at=application.submitted_at.isoformat() if application.submitted_at else None,
            reviewed_at=application.reviewed_at.isoformat() if application.reviewed_at else None,
            reviewed_by=str(application.reviewed_by) if application.reviewed_by else None,
            rejection_reason=application.rejection_reason,
            admin_notes=application.admin_notes,
            documents=documents,
            created_at=application.created_at.isoformat(),
            updated_at=application.updated_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "get_firm_application_error",
            application_id=application_id,
            user_id=str(current_user.user_id),
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get firm application"
        )


@router.put("/{application_id}", response_model=FirmApplicationResponse)
async def update_firm_application(
    application_id: str,
    request: FirmApplicationUpdateRequest,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a firm application
    
    Allows updating application status, rejection reason, and admin notes.
    Regular users can only update applications for their firms (limited fields).
    Admins can update any application with full access.
    """
    try:
        from app.models.security_firm import FirmApplication, FirmUser, SecurityFirm
        from sqlalchemy import select, and_
        from sqlalchemy.orm import selectinload
        
        # Get application
        query = select(FirmApplication).options(
            selectinload(FirmApplication.firm).selectinload(SecurityFirm.documents)
        ).where(FirmApplication.id == application_id)
        
        result = await db.execute(query)
        application = result.scalar_one_or_none()
        
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Firm application not found"
            )
        
        # Check authorization and determine allowed updates
        is_admin = current_user.has_permission("admin:all")
        user_can_update = False
        
        if not is_admin:
            # Check if user is associated with this firm
            user_firm_query = select(FirmUser).where(
                and_(
                    FirmUser.user_id == current_user.user_id,
                    FirmUser.firm_id == application.firm_id,
                    FirmUser.status == "active",
                    FirmUser.role == "firm_admin"
                )
            )
            user_firm = (await db.execute(user_firm_query)).scalar_one_or_none()
            user_can_update = bool(user_firm)
        
        if not is_admin and not user_can_update:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this application"
            )
        
        # Apply updates based on permissions
        updated = False
        
        if request.admin_notes is not None:
            application.admin_notes = request.admin_notes
            updated = True
        
        # Only admins can update status and rejection reason
        if is_admin:
            if request.status is not None:
                valid_statuses = ["draft", "submitted", "under_review", "approved", "rejected"]
                if request.status not in valid_statuses:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
                    )
                
                # Use the service method for proper status updates
                if request.status in ["approved", "rejected"]:
                    service = SecurityFirmService(db)
                    application = await service.review_application(
                        application_id=application_id,
                        status=request.status,
                        rejection_reason=request.rejection_reason,
                        admin_notes=request.admin_notes,
                        admin_user_id=current_user.user_id
                    )
                    updated = True
                else:
                    application.status = request.status
                    updated = True
            
            if request.rejection_reason is not None:
                application.rejection_reason = request.rejection_reason
                updated = True
        
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid updates provided"
            )
        
        # Save changes
        await db.commit()
        await db.refresh(application)
        
        # Build documents list
        documents = []
        if application.firm and application.firm.documents:
            for doc in application.firm.documents:
                # Get base64 content
                content_base64 = await get_file_content_base64(doc.file_path)
                
                documents.append(DocumentResponse(
                    id=str(doc.id),
                    document_type=doc.document_type,
                    file_name=getattr(doc, 'file_name', None),
                    file_size=getattr(doc, 'file_size', None),
                    mime_type=doc.mime_type,
                    uploaded_by=str(doc.uploaded_by),
                    is_verified=doc.is_verified,
                    verified_by=str(doc.verified_by) if doc.verified_by else None,
                    verified_at=doc.verified_at.isoformat() if doc.verified_at else None,
                    content_base64=content_base64,
                    created_at=doc.created_at.isoformat(),
                    updated_at=doc.updated_at.isoformat()
                ))
        
        logger.info(
            "firm_application_updated",
            application_id=application_id,
            user_id=str(current_user.user_id),
            is_admin=is_admin,
            status=application.status
        )
        
        return FirmApplicationResponse(
            id=str(application.id),
            firm_id=str(application.firm_id),
            firm_name=application.firm.name if application.firm else None,
            status=application.status,
            submitted_at=application.submitted_at.isoformat() if application.submitted_at else None,
            reviewed_at=application.reviewed_at.isoformat() if application.reviewed_at else None,
            reviewed_by=str(application.reviewed_by) if application.reviewed_by else None,
            rejection_reason=application.rejection_reason,
            admin_notes=application.admin_notes,
            documents=documents,
            created_at=application.created_at.isoformat(),
            updated_at=application.updated_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "update_firm_application_error",
            application_id=application_id,
            user_id=str(current_user.user_id),
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update firm application"
        )


@router.delete("/{application_id}")
async def delete_firm_application(
    application_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a firm application
    
    Allows deletion of firm applications. Only applications in 'draft' status
    can be deleted. Admins can delete any application, regular users can only
    delete applications for their firms.
    """
    try:
        from app.models.security_firm import FirmApplication, FirmUser
        from sqlalchemy import select, and_
        
        # Get application
        application = await db.get(FirmApplication, application_id)
        
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Firm application not found"
            )
        
        # Check authorization
        is_admin = current_user.has_permission("admin:all")
        user_can_delete = False
        
        if not is_admin:
            # Check if user is associated with this firm
            user_firm_query = select(FirmUser).where(
                and_(
                    FirmUser.user_id == current_user.user_id,
                    FirmUser.firm_id == application.firm_id,
                    FirmUser.status == "active",
                    FirmUser.role == "firm_admin"
                )
            )
            user_firm = (await db.execute(user_firm_query)).scalar_one_or_none()
            user_can_delete = bool(user_firm)
        
        if not is_admin and not user_can_delete:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this application"
            )
        
        # Check if application can be deleted
        if not is_admin and application.status != "draft":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only draft applications can be deleted"
            )
        
        # Delete application
        await db.delete(application)
        await db.commit()
        
        logger.info(
            "firm_application_deleted",
            application_id=application_id,
            user_id=str(current_user.user_id),
            is_admin=is_admin
        )
        
        return {"message": "Firm application deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "delete_firm_application_error",
            application_id=application_id,
            user_id=str(current_user.user_id),
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete firm application"
        )


@router.post("/{application_id}/submit")
async def submit_firm_application(
    application_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit a firm application for review
    
    Changes application status from 'draft' to 'submitted' and sets
    the submission timestamp.
    """
    try:
        from app.models.security_firm import FirmApplication, FirmUser
        from sqlalchemy import select, and_
        
        # Get application
        application = await db.get(FirmApplication, application_id)
        
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Firm application not found"
            )
        
        # Check authorization
        if not current_user.has_permission("admin:all"):
            user_firm_query = select(FirmUser).where(
                and_(
                    FirmUser.user_id == current_user.user_id,
                    FirmUser.firm_id == application.firm_id,
                    FirmUser.status == "active",
                    FirmUser.role == "firm_admin"
                )
            )
            user_firm = (await db.execute(user_firm_query)).scalar_one_or_none()
            
            if not user_firm:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to submit this application"
                )
        
        # Check if application can be submitted
        if application.status != "draft":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only draft applications can be submitted"
            )
        
        # Submit application
        application.status = "submitted"
        application.submitted_at = datetime.utcnow()
        
        await db.commit()
        
        logger.info(
            "firm_application_submitted",
            application_id=application_id,
            user_id=str(current_user.user_id)
        )
        
        return {"message": "Firm application submitted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "submit_firm_application_error",
            application_id=application_id,
            user_id=str(current_user.user_id),
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit firm application"
        )