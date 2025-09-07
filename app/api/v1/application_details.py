"""
Detailed Application View API - Complete application information
"""
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
import structlog

from app.core.auth import get_current_user, require_admin
from app.core.database import get_db
from app.services.auth import UserContext
from app.services.security_firm import SecurityFirmService
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()

router = APIRouter()


class ApplicantDetailsResponse(BaseModel):
    """Applicant (firm admin) details"""
    user_id: str = Field(..., description="User ID")
    email: str = Field(..., description="Email address")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    phone: Optional[str] = Field(None, description="Phone number")
    role: str = Field(..., description="Role in firm")
    joined_at: Optional[str] = Field(None, description="When user joined firm")


class FirmDetailsResponse(BaseModel):
    """Complete firm details"""
    id: str = Field(..., description="Firm ID")
    name: str = Field(..., description="Firm name")
    registration_number: str = Field(..., description="Registration number")
    email: str = Field(..., description="Firm email")
    phone: str = Field(..., description="Firm phone")
    address: str = Field(..., description="Firm address")
    province: str = Field(..., description="Province")
    country: str = Field(..., description="Country")
    vat_number: Optional[str] = Field(None, description="VAT number")
    verification_status: str = Field(..., description="Verification status")
    credit_balance: int = Field(..., description="Credit balance")
    is_locked: bool = Field(..., description="Is firm locked")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


class DocumentDetailsResponse(BaseModel):
    """Document details"""
    id: str = Field(..., description="Document ID")
    document_type: str = Field(..., description="Document type code")
    document_type_name: str = Field(..., description="Document type name")
    file_name: str = Field(..., description="Original file name")
    file_size: int = Field(..., description="File size in bytes")
    mime_type: Optional[str] = Field(None, description="MIME type")
    is_verified: bool = Field(..., description="Is document verified")
    verified_by: Optional[str] = Field(None, description="Verified by user ID")
    verified_at: Optional[str] = Field(None, description="Verification timestamp")
    uploaded_at: str = Field(..., description="Upload timestamp")
    download_url: Optional[str] = Field(None, description="Download URL")


class RequiredDocumentResponse(BaseModel):
    """Required document type info"""
    code: str = Field(..., description="Document type code")
    name: str = Field(..., description="Document type name")
    description: Optional[str] = Field(None, description="Document description")
    is_uploaded: bool = Field(..., description="Is this document uploaded")
    uploaded_document: Optional[DocumentDetailsResponse] = Field(None, description="Uploaded document details")


class FirmUserResponse(BaseModel):
    """Firm user details"""
    user_id: str = Field(..., description="User ID")
    email: str = Field(..., description="Email address")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    phone: Optional[str] = Field(None, description="Phone number")
    role: str = Field(..., description="Role in firm")
    status: str = Field(..., description="User status")
    invited_at: Optional[str] = Field(None, description="Invitation timestamp")
    accepted_at: Optional[str] = Field(None, description="Acceptance timestamp")


class ApplicationDetailsResponse(BaseModel):
    """Complete application details"""
    # Application info
    id: str = Field(..., description="Application ID")
    status: str = Field(..., description="Application status")
    submitted_at: Optional[str] = Field(None, description="Submission timestamp")
    reviewed_at: Optional[str] = Field(None, description="Review timestamp")
    reviewed_by: Optional[str] = Field(None, description="Reviewer user ID")
    reviewer_name: Optional[str] = Field(None, description="Reviewer name")
    rejection_reason: Optional[str] = Field(None, description="Rejection reason")
    admin_notes: Optional[str] = Field(None, description="Admin notes")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    
    # Firm details
    firm: FirmDetailsResponse = Field(..., description="Complete firm details")
    
    # Applicant details (firm admin who submitted)
    applicant: Optional[ApplicantDetailsResponse] = Field(None, description="Applicant details")
    
    # All firm users
    firm_users: List[FirmUserResponse] = Field(default_factory=list, description="All firm users")
    
    # Document requirements and uploads
    required_documents: List[RequiredDocumentResponse] = Field(default_factory=list, description="Required documents status")
    
    # All uploaded documents
    all_documents: List[DocumentDetailsResponse] = Field(default_factory=list, description="All uploaded documents")
    
    # Summary statistics
    summary: Dict[str, Any] = Field(default_factory=dict, description="Application summary")


@router.get("/{APPLICATION_ID}/details", response_model=ApplicationDetailsResponse)
async def get_application_details(
    APPLICATION_ID: str,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get complete application details including all associated information
    
    Returns comprehensive application information including:
    - Application status and timeline
    - Complete firm details
    - Applicant (firm admin) information
    - All firm users
    - Document requirements and upload status
    - All uploaded documents with download links
    - Summary statistics
    """
    try:
        from app.models.security_firm import (
            FirmApplication, SecurityFirm, FirmUser, FirmDocument
        )
        from app.models.user import RegisteredUser
        from app.models.document_type import DocumentType
        from app.services.document_type import DocumentTypeService
        from app.services.s3_service import S3Service
        from sqlalchemy import select, and_
        from sqlalchemy.orm import selectinload
        
        # Get application with all related data
        query = select(FirmApplication).options(
            selectinload(FirmApplication.firm)
        ).where(FirmApplication.id == APPLICATION_ID)
        
        result = await db.execute(query)
        application = result.scalar_one_or_none()
        
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )
        
        # Check authorization
        is_admin = hasattr(current_user, 'has_permission') and current_user.has_permission("admin:all")
        if not is_admin:
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
        
        firm = application.firm
        
        # Get firm details
        firm_details = FirmDetailsResponse(
            id=str(firm.id),
            name=firm.name,
            registration_number=firm.registration_number,
            email=firm.email,
            phone=firm.phone,
            address=firm.address,
            province=firm.province,
            country=firm.country,
            vat_number=firm.vat_number,
            verification_status=firm.verification_status,
            credit_balance=firm.credit_balance,
            is_locked=firm.is_locked,
            created_at=firm.created_at.isoformat(),
            updated_at=firm.updated_at.isoformat()
        )
        
        # Get firm admin (applicant) details
        applicant_details = None
        firm_admin_query = select(FirmUser, RegisteredUser).join(
            RegisteredUser, FirmUser.user_id == RegisteredUser.id
        ).where(
            and_(
                FirmUser.firm_id == application.firm_id,
                FirmUser.role == "firm_admin",
                FirmUser.status == "active"
            )
        )
        
        firm_admin_result = await db.execute(firm_admin_query)
        firm_admin_data = firm_admin_result.first()
        
        if firm_admin_data:
            firm_user, user = firm_admin_data
            applicant_details = ApplicantDetailsResponse(
                user_id=str(user.id),
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                phone=user.phone,
                role=firm_user.role,
                joined_at=firm_user.accepted_at.isoformat() if firm_user.accepted_at else None
            )
        
        # Get all firm users
        all_users_query = select(FirmUser, RegisteredUser).join(
            RegisteredUser, FirmUser.user_id == RegisteredUser.id
        ).where(FirmUser.firm_id == application.firm_id)
        
        all_users_result = await db.execute(all_users_query)
        firm_users = []
        
        for firm_user, user in all_users_result:
            firm_users.append(FirmUserResponse(
                user_id=str(user.id),
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                phone=user.phone,
                role=firm_user.role,
                status=firm_user.status,
                invited_at=firm_user.invited_at.isoformat() if firm_user.invited_at else None,
                accepted_at=firm_user.accepted_at.isoformat() if firm_user.accepted_at else None
            ))
        
        # Get all uploaded documents
        documents_query = select(FirmDocument).where(
            FirmDocument.firm_id == application.firm_id
        ).order_by(FirmDocument.created_at.desc())
        
        documents_result = await db.execute(documents_query)
        uploaded_documents = documents_result.scalars().all()
        
        # Get document types for mapping
        doc_type_service = DocumentTypeService(db)
        all_doc_types = await doc_type_service.get_all_document_types()
        doc_type_map = {dt.code: dt for dt in all_doc_types}
        
        # Build document details with download URLs
        all_documents = []
        s3_service = S3Service()
        
        for doc in uploaded_documents:
            # Generate download URL
            download_url = None
            try:
                if not doc.file_path.startswith('uploads/'):
                    # S3 storage
                    download_url = s3_service.get_file_url(doc.file_path, expires_in=3600)
                else:
                    # Local storage - would need a separate endpoint
                    download_url = f"/api/v1/security-firms/{application.firm_id}/documents/{doc.id}/download"
            except Exception as e:
                logger.warning(f"Failed to generate download URL for document {doc.id}: {e}")
            
            doc_type = doc_type_map.get(doc.document_type)
            
            all_documents.append(DocumentDetailsResponse(
                id=str(doc.id),
                document_type=doc.document_type,
                document_type_name=doc_type.name if doc_type else doc.document_type,
                file_name=doc.file_name,
                file_size=doc.file_size,
                mime_type=doc.mime_type,
                is_verified=doc.is_verified,
                verified_by=str(doc.verified_by) if doc.verified_by else None,
                verified_at=doc.verified_at.isoformat() if doc.verified_at else None,
                uploaded_at=doc.created_at.isoformat(),
                download_url=download_url
            ))
        
        # Get required documents and their status
        required_doc_types = await doc_type_service.get_required_documents()
        uploaded_by_type = {doc.document_type: doc for doc in uploaded_documents}
        
        required_documents = []
        for req_doc_type in required_doc_types:
            uploaded_doc = uploaded_by_type.get(req_doc_type.code)
            uploaded_doc_details = None
            
            if uploaded_doc:
                # Generate download URL for this document
                download_url = None
                try:
                    if not uploaded_doc.file_path.startswith('uploads/'):
                        download_url = s3_service.get_file_url(uploaded_doc.file_path, expires_in=3600)
                    else:
                        download_url = f"/api/v1/security-firms/{application.firm_id}/documents/{uploaded_doc.id}/download"
                except Exception as e:
                    logger.warning(f"Failed to generate download URL for required document {uploaded_doc.id}: {e}")
                
                uploaded_doc_details = DocumentDetailsResponse(
                    id=str(uploaded_doc.id),
                    document_type=uploaded_doc.document_type,
                    document_type_name=req_doc_type.name,
                    file_name=uploaded_doc.file_name,
                    file_size=uploaded_doc.file_size,
                    mime_type=uploaded_doc.mime_type,
                    is_verified=uploaded_doc.is_verified,
                    verified_by=str(uploaded_doc.verified_by) if uploaded_doc.verified_by else None,
                    verified_at=uploaded_doc.verified_at.isoformat() if uploaded_doc.verified_at else None,
                    uploaded_at=uploaded_doc.created_at.isoformat(),
                    download_url=download_url
                )
            
            required_documents.append(RequiredDocumentResponse(
                code=req_doc_type.code,
                name=req_doc_type.name,
                description=req_doc_type.description,
                is_uploaded=bool(uploaded_doc),
                uploaded_document=uploaded_doc_details
            ))
        
        # Get reviewer details if reviewed
        reviewer_name = None
        if application.reviewed_by:
            reviewer_query = select(RegisteredUser).where(
                RegisteredUser.id == application.reviewed_by
            )
            reviewer_result = await db.execute(reviewer_query)
            reviewer = reviewer_result.scalar_one_or_none()
            if reviewer:
                reviewer_name = f"{reviewer.first_name} {reviewer.last_name}".strip()
                if not reviewer_name:
                    reviewer_name = reviewer.email
        
        # Build summary statistics
        total_required = len(required_doc_types)
        uploaded_required = sum(1 for rd in required_documents if rd.is_uploaded)
        total_documents = len(all_documents)
        verified_documents = sum(1 for doc in all_documents if doc.is_verified)
        
        summary = {
            "total_required_documents": total_required,
            "uploaded_required_documents": uploaded_required,
            "missing_required_documents": total_required - uploaded_required,
            "total_documents": total_documents,
            "verified_documents": verified_documents,
            "unverified_documents": total_documents - verified_documents,
            "completion_percentage": round((uploaded_required / total_required * 100) if total_required > 0 else 100, 1),
            "total_firm_users": len(firm_users),
            "active_firm_users": sum(1 for user in firm_users if user.status == "active"),
            "can_submit": uploaded_required == total_required and application.status == "draft"
        }
        
        return ApplicationDetailsResponse(
            id=str(application.id),
            status=application.status,
            submitted_at=application.submitted_at.isoformat() if application.submitted_at else None,
            reviewed_at=application.reviewed_at.isoformat() if application.reviewed_at else None,
            reviewed_by=str(application.reviewed_by) if application.reviewed_by else None,
            reviewer_name=reviewer_name,
            rejection_reason=application.rejection_reason,
            admin_notes=application.admin_notes,
            created_at=application.created_at.isoformat(),
            updated_at=application.updated_at.isoformat(),
            firm=firm_details,
            applicant=applicant_details,
            firm_users=firm_users,
            required_documents=required_documents,
            all_documents=all_documents,
            summary=summary
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "get_application_details_error",
            application_id=APPLICATION_ID,
            user_id=str(current_user.user_id),
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get application details"
        )


@router.get("/{APPLICATION_ID}/summary")
async def get_application_summary(
    APPLICATION_ID: str,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a quick summary of application status
    
    Returns key metrics and status information for quick overview.
    """
    try:
        from app.models.security_firm import FirmApplication, FirmDocument
        from app.services.document_type import DocumentTypeService
        from sqlalchemy import select, func, and_
        
        # Get application
        application = await db.get(FirmApplication, APPLICATION_ID)
        
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )
        
        # Check authorization (same as detailed view)
        is_admin = hasattr(current_user, 'has_permission') and current_user.has_permission("admin:all")
        if not is_admin:
            from app.models.security_firm import FirmUser
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
        
        # Get document counts
        doc_count_query = select(func.count(FirmDocument.id)).where(
            FirmDocument.firm_id == application.firm_id
        )
        total_documents = (await db.execute(doc_count_query)).scalar()
        
        verified_count_query = select(func.count(FirmDocument.id)).where(
            and_(
                FirmDocument.firm_id == application.firm_id,
                FirmDocument.is_verified == True
            )
        )
        verified_documents = (await db.execute(verified_count_query)).scalar()
        
        # Get required document count
        doc_type_service = DocumentTypeService(db)
        required_doc_types = await doc_type_service.get_required_documents()
        total_required = len(required_doc_types)
        
        # Get uploaded required documents
        if total_required > 0:
            required_codes = [dt.code for dt in required_doc_types]
            uploaded_required_query = select(func.count(func.distinct(FirmDocument.document_type))).where(
                and_(
                    FirmDocument.firm_id == application.firm_id,
                    FirmDocument.document_type.in_(required_codes)
                )
            )
            uploaded_required = (await db.execute(uploaded_required_query)).scalar()
        else:
            uploaded_required = 0
        
        return {
            "application_id": str(application.id),
            "status": application.status,
            "submitted_at": application.submitted_at.isoformat() if application.submitted_at else None,
            "reviewed_at": application.reviewed_at.isoformat() if application.reviewed_at else None,
            "total_documents": total_documents,
            "verified_documents": verified_documents,
            "total_required_documents": total_required,
            "uploaded_required_documents": uploaded_required,
            "missing_required_documents": total_required - uploaded_required,
            "completion_percentage": round((uploaded_required / total_required * 100) if total_required > 0 else 100, 1),
            "can_submit": uploaded_required == total_required and application.status == "draft",
            "is_complete": uploaded_required == total_required
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "get_application_summary_error",
            application_id=APPLICATION_ID,
            user_id=str(current_user.user_id),
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get application summary"
        )