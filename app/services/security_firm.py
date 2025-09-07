"""
Security firm service for registration and management
"""
import os
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from fastapi import UploadFile
from geoalchemy2.shape import from_shape
from shapely.geometry import Polygon

from app.models.security_firm import SecurityFirm, CoverageArea, FirmApplication, FirmDocument, FirmUser
from app.core.config import settings
from app.services.s3_service import S3Service
# User model not needed for this service


class SecurityFirmService:
    """Service for managing security firm operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def register_firm(
        self,
        name: str,
        registration_number: str,
        email: str,
        phone: str,
        address: str,
        province: str,
        country: str,
        vat_number: Optional[str],
        user_id: str
    ) -> SecurityFirm:
        """
        Register a new security firm for verification
        """
        # Check if registration number or email already exists
        existing_firm = await self.db.execute(
            select(SecurityFirm).where(
                (SecurityFirm.registration_number == registration_number) |
                (SecurityFirm.email == email)
            )
        )
        if existing_firm.scalar_one_or_none():
            raise ValueError("Security firm with this registration number or email already exists")
        
        # Create new security firm
        firm = SecurityFirm(
            name=name,
            registration_number=registration_number,
            email=email,
            phone=phone,
            address=address,
            province=province,
            country=country,
            vat_number=vat_number,
            verification_status="draft",
            credit_balance=0
        )
        
        self.db.add(firm)
        await self.db.flush()  # Get the firm ID
        
        # Create initial application
        from app.models.security_firm import FirmApplication
        application = FirmApplication(
            firm_id=firm.id,
            status="draft"
        )
        self.db.add(application)
        
        # Create firm user relationship with firm_admin role
        from app.models.security_firm import FirmUser
        firm_user = FirmUser(
            user_id=user_id,
            firm_id=firm.id,
            role="firm_admin",
            status="active",
            accepted_at=datetime.utcnow()
        )
        self.db.add(firm_user)
        
        await self.db.commit()
        await self.db.refresh(firm)
        
        return firm
    
    async def get_pending_firms(self) -> List[SecurityFirm]:
        """
        Get all security firms pending verification
        """
        result = await self.db.execute(
            select(SecurityFirm).where(SecurityFirm.verification_status == "pending")
        )
        return result.scalars().all()
    
    async def verify_firm(
        self,
        firm_id: str,
        verification_status: str,
        rejection_reason: Optional[str] = None
    ) -> SecurityFirm:
        """
        Approve or reject a security firm registration
        """
        firm = await self.db.get(SecurityFirm, firm_id)
        if not firm:
            raise ValueError("Security firm not found")
        
        if firm.verification_status != "pending":
            raise ValueError("Security firm has already been processed")
        
        firm.verification_status = verification_status
        
        # If rejected, could store rejection reason in a separate table
        # For now, we'll just update the status
        
        await self.db.commit()
        await self.db.refresh(firm)
        
        return firm
    
    async def create_coverage_area(
        self,
        firm_id: str,
        name: str,
        boundary_coordinates: List[List[float]],
        user_id: str
    ) -> CoverageArea:
        """
        Create a coverage area for an approved security firm
        """
        # Verify firm exists and is approved
        firm = await self.db.get(SecurityFirm, firm_id)
        if not firm:
            raise ValueError("Security firm not found")
        
        if firm.verification_status != "approved":
            raise ValueError("Security firm must be approved to create coverage areas")
        
        # TODO: Add authorization check - user should be associated with the firm
        # For now, we'll allow any authenticated user to create coverage areas
        
        # Create polygon from coordinates
        try:
            polygon = Polygon(boundary_coordinates)
            if not polygon.is_valid:
                raise ValueError("Invalid polygon coordinates")
        except Exception as e:
            raise ValueError(f"Invalid polygon coordinates: {str(e)}")
        
        # Create coverage area
        coverage_area = CoverageArea(
            firm_id=firm_id,
            name=name,
            boundary=from_shape(polygon, srid=4326)
        )
        
        self.db.add(coverage_area)
        await self.db.commit()
        await self.db.refresh(coverage_area)
        
        return coverage_area
    
    async def get_coverage_areas(self, firm_id: str, user_id: str, include_inactive: bool = True) -> List[CoverageArea]:
        """
        Get all coverage areas for a security firm
        
        Args:
            firm_id: Security firm ID
            user_id: User ID for authorization
            include_inactive: Whether to include inactive coverage areas
        """
        # Verify firm exists
        firm = await self.db.get(SecurityFirm, firm_id)
        if not firm:
            raise ValueError("Security firm not found")
        
        # TODO: Add authorization check - user should be associated with the firm
        # For now, we'll allow any authenticated user to view coverage areas
        
        query = select(CoverageArea).where(CoverageArea.firm_id == firm_id)
        
        if not include_inactive:
            query = query.where(CoverageArea.is_active == True)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_coverage_area_by_id(
        self,
        firm_id: str,
        area_id: str,
        user_id: str
    ) -> CoverageArea:
        """
        Get a specific coverage area by ID for a security firm
        
        Args:
            firm_id: Security firm ID
            area_id: Coverage area ID
            user_id: User ID for authorization
        """
        # Verify firm exists
        firm = await self.db.get(SecurityFirm, firm_id)
        if not firm:
            raise ValueError("Security firm not found")
        
        # TODO: Add authorization check - user should be associated with the firm
        # For now, we'll allow any authenticated user to view coverage areas
        
        # Get the coverage area
        coverage_area = await self.db.get(CoverageArea, area_id)
        if not coverage_area:
            raise ValueError("Coverage area not found")
        
        # Verify the coverage area belongs to the specified firm
        if str(coverage_area.firm_id) != firm_id:
            raise ValueError("Coverage area does not belong to this firm")
        
        return coverage_area
    
    async def update_coverage_area(
        self,
        firm_id: str,
        area_id: str,
        name: Optional[str] = None,
        boundary_coordinates: Optional[List[List[float]]] = None,
        is_active: Optional[bool] = None,
        user_id: str = None
    ) -> CoverageArea:
        """
        Update a coverage area for a security firm
        """
        # Verify firm exists and is approved
        firm = await self.db.get(SecurityFirm, firm_id)
        if not firm:
            raise ValueError("Security firm not found")
        
        if firm.verification_status != "approved":
            raise ValueError("Security firm must be approved to update coverage areas")
        
        # Get the existing coverage area
        coverage_area = await self.db.get(CoverageArea, area_id)
        if not coverage_area:
            raise ValueError("Coverage area not found")
        
        # Verify the coverage area belongs to the specified firm
        if str(coverage_area.firm_id) != firm_id:
            raise ValueError("Coverage area does not belong to this firm")
        
        # TODO: Add authorization check - user should be associated with the firm
        
        # Update name if provided
        if name is not None:
            coverage_area.name = name
        
        # Update boundary if provided
        if boundary_coordinates is not None:
            try:
                polygon = Polygon(boundary_coordinates)
                if not polygon.is_valid:
                    raise ValueError("Invalid polygon coordinates")
            except Exception as e:
                raise ValueError(f"Invalid polygon coordinates: {str(e)}")
            
            coverage_area.boundary = from_shape(polygon, srid=4326)
        
        # Update is_active if provided
        if is_active is not None:
            coverage_area.is_active = is_active
        
        await self.db.commit()
        await self.db.refresh(coverage_area)
        
        return coverage_area
    
    async def delete_coverage_area(
        self,
        firm_id: str,
        area_id: str,
        user_id: str
    ) -> bool:
        """
        Delete a coverage area for a security firm
        """
        # Verify firm exists
        firm = await self.db.get(SecurityFirm, firm_id)
        if not firm:
            raise ValueError("Security firm not found")
        
        # Get the existing coverage area
        coverage_area = await self.db.get(CoverageArea, area_id)
        if not coverage_area:
            raise ValueError("Coverage area not found")
        
        # Verify the coverage area belongs to the specified firm
        if str(coverage_area.firm_id) != firm_id:
            raise ValueError("Coverage area does not belong to this firm")
        
        # TODO: Add authorization check - user should be associated with the firm
        
        # Check if there are any teams associated with this coverage area
        from app.models.security_firm import Team
        result = await self.db.execute(
            select(Team).where(Team.coverage_area_id == area_id)
        )
        associated_teams = result.scalars().all()
        
        if associated_teams:
            raise ValueError(
                f"Cannot delete coverage area that has {len(associated_teams)} team(s) associated with it. "
                "Please reassign or remove the teams first."
            )
        
        await self.db.delete(coverage_area)
        await self.db.commit()
        
        return True
    
    async def upload_verification_document(
        self,
        firm_id: str,
        file: UploadFile,
        user_id: str
    ) -> str:
        """
        Upload verification document for a security firm
        """
        # Verify firm exists
        firm = await self.db.get(SecurityFirm, firm_id)
        if not firm:
            raise ValueError("Security firm not found")
        
        # TODO: Add authorization check - user should be associated with the firm
        
        # Create uploads directory if it doesn't exist
        upload_dir = "uploads/security_firms"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate unique filename
        file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'bin'
        unique_filename = f"{firm_id}_{uuid.uuid4()}.{file_extension}"
        file_path = os.path.join(upload_dir, unique_filename)
        
        # Save file
        try:
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
        except Exception as e:
            raise ValueError(f"Failed to save file: {str(e)}")
        
        # TODO: Store document reference in database
        # For now, just return the file path
        return file_path
    
    async def get_firm_by_id(self, firm_id: str, user_id: str) -> SecurityFirm:
        """
        Get security firm by ID with authorization check
        """
        firm = await self.db.get(SecurityFirm, firm_id)
        if not firm:
            raise ValueError("Security firm not found")
        
        # TODO: Add proper authorization check
        # For now, allow any authenticated user to view firm details
        
        return firm
    
    async def get_firm_by_registration_number(self, registration_number: str) -> Optional[SecurityFirm]:
        """
        Get security firm by registration number
        """
        result = await self.db.execute(
            select(SecurityFirm).where(SecurityFirm.registration_number == registration_number)
        )
        return result.scalar_one_or_none()
    
    async def list_firms(
        self, 
        skip: int = 0, 
        limit: int = 100, 
        status: Optional[str] = None
    ) -> List[SecurityFirm]:
        """
        List security firms with optional filtering and pagination
        """
        query = select(SecurityFirm)
        
        if status:
            query = query.where(SecurityFirm.verification_status == status)
        
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_approved_firms(self) -> List[SecurityFirm]:
        """
        Get all approved security firms
        """
        result = await self.db.execute(
            select(SecurityFirm).where(SecurityFirm.verification_status == "approved")
        )
        return result.scalars().all()
    
    async def update_credit_balance(self, firm_id: str, credit_amount: int) -> SecurityFirm:
        """
        Update security firm credit balance
        """
        firm = await self.db.get(SecurityFirm, firm_id)
        if not firm:
            raise ValueError("Security firm not found")
        
        firm.credit_balance += credit_amount
        if firm.credit_balance < 0:
            raise ValueError("Insufficient credits")
        
        await self.db.commit()
        await self.db.refresh(firm)
        
        return firm
    
    async def update_firm(
        self,
        firm_id: str,
        user_id: str,
        **updates
    ) -> SecurityFirm:
        """
        Update security firm details (only allowed in draft status)
        """
        # Check if user has permission to update this firm
        firm_user = await self.db.execute(
            select(FirmUser).where(
                and_(
                    FirmUser.user_id == user_id,
                    FirmUser.firm_id == firm_id,
                    FirmUser.role == "firm_admin",
                    FirmUser.status == "active"
                )
            )
        )
        if not firm_user.scalar_one_or_none():
            raise ValueError("Not authorized to update this firm")
        
        firm = await self.db.get(SecurityFirm, firm_id)
        if not firm:
            raise ValueError("Security firm not found")
        
        if firm.verification_status not in ["draft"]:
            raise ValueError("Cannot update firm after application has been submitted")
        
        # Update allowed fields
        for field, value in updates.items():
            if hasattr(firm, field) and value is not None:
                setattr(firm, field, value)
        
        await self.db.commit()
        await self.db.refresh(firm)
        
        return firm
    
    async def upload_document(
        self,
        firm_id: str,
        document_type: str,
        file: UploadFile,
        user_id: str
    ) -> FirmDocument:
        """
        Upload verification document for a security firm
        """
        # Check if user has permission
        firm_user = await self.db.execute(
            select(FirmUser).where(
                and_(
                    FirmUser.user_id == user_id,
                    FirmUser.firm_id == firm_id,
                    FirmUser.role == "firm_admin",
                    FirmUser.status == "active"
                )
            )
        )
        if not firm_user.scalar_one_or_none():
            raise ValueError("Not authorized to upload documents for this firm")
        
        firm = await self.db.get(SecurityFirm, firm_id)
        if not firm:
            raise ValueError("Security firm not found")
        
        if firm.verification_status not in ["draft", "submitted"]:
            raise ValueError("Cannot upload documents after application has been processed")
        
        # Check if we should use S3 or local storage
        if settings.AWS_S3_BUCKET and settings.AWS_ACCESS_KEY_ID:
            # Use S3 storage
            try:
                s3_service = S3Service()
                key_prefix = f"security_firms/{firm_id}"
                s3_key, file_size = await s3_service.upload_file(file, key_prefix, document_type)
                file_path = s3_key  # Store S3 key as file_path
            except Exception as e:
                raise ValueError(f"Failed to upload file to S3: {str(e)}")
        else:
            # Use local storage (fallback)
            upload_dir = f"uploads/security_firms/{firm_id}"
            os.makedirs(upload_dir, exist_ok=True)
            
            # Generate unique filename
            file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'bin'
            unique_filename = f"{document_type}_{uuid.uuid4()}.{file_extension}"
            file_path = os.path.join(upload_dir, unique_filename)
            
            # Save file locally
            try:
                content = await file.read()
                with open(file_path, "wb") as buffer:
                    buffer.write(content)
                file_size = len(content)
            except Exception as e:
                raise ValueError(f"Failed to save file: {str(e)}")
        
        # Create document record
        document = FirmDocument(
            firm_id=firm_id,
            document_type=document_type,
            file_name=file.filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=file.content_type,
            uploaded_by=user_id
        )
        
        self.db.add(document)
        await self.db.commit()
        await self.db.refresh(document)
        
        return document
    
    async def get_document_by_id(
        self,
        document_id: str,
        firm_id: str,
        user_id: str
    ) -> Optional[FirmDocument]:
        """
        Get a specific document by ID with permission check
        """
        # Check if user has permission to access this firm's documents
        firm_user = await self.db.execute(
            select(FirmUser).where(
                and_(
                    FirmUser.user_id == user_id,
                    FirmUser.firm_id == firm_id,
                    FirmUser.status == "active"
                )
            )
        )
        if not firm_user.scalar_one_or_none():
            raise ValueError("Not authorized to access documents for this firm")
        
        # Get the document
        result = await self.db.execute(
            select(FirmDocument).where(
                and_(
                    FirmDocument.id == document_id,
                    FirmDocument.firm_id == firm_id
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def submit_application(
        self,
        firm_id: str,
        user_id: str
    ) -> FirmApplication:
        """
        Submit security firm application for admin review
        """
        # Check if user has permission
        firm_user = await self.db.execute(
            select(FirmUser).where(
                and_(
                    FirmUser.user_id == user_id,
                    FirmUser.firm_id == firm_id,
                    FirmUser.role == "firm_admin",
                    FirmUser.status == "active"
                )
            )
        )
        if not firm_user.scalar_one_or_none():
            raise ValueError("Not authorized to submit application for this firm")
        
        firm = await self.db.get(SecurityFirm, firm_id)
        if not firm:
            raise ValueError("Security firm not found")
        
        if firm.verification_status != "draft":
            raise ValueError("Application has already been submitted")
        
        # Check if required documents are uploaded using document type service
        from app.services.document_type import DocumentTypeService
        doc_type_service = DocumentTypeService(self.db)
        
        required_doc_types = await doc_type_service.get_required_documents()
        required_codes = [doc_type.code for doc_type in required_doc_types]
        
        uploaded_docs = await self.db.execute(
            select(FirmDocument.document_type).where(FirmDocument.firm_id == firm_id)
        )
        uploaded_types = [doc[0] for doc in uploaded_docs.fetchall()]
        
        missing_docs = [code for code in required_codes if code not in uploaded_types]
        if missing_docs:
            # Get the names for better error message
            missing_names = []
            for code in missing_docs:
                doc_type = await doc_type_service.get_document_type_by_code(code)
                if doc_type:
                    missing_names.append(doc_type.name)
            
            raise ValueError(f"Missing required documents: {', '.join(missing_names)}")
        
        # Update firm status
        firm.verification_status = "submitted"
        
        # Create or update application
        application_result = await self.db.execute(
            select(FirmApplication).where(FirmApplication.firm_id == firm_id)
        )
        application = application_result.scalar_one_or_none()
        
        if not application:
            # Create new application
            application = FirmApplication(
                firm_id=firm_id,
                status="submitted",
                submitted_at=datetime.utcnow()
            )
            self.db.add(application)
        else:
            # Update existing application
            application.status = "submitted"
            application.submitted_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(application)
        
        return application
    
    async def get_pending_applications(self) -> List[FirmApplication]:
        """
        Get all pending firm applications for admin review
        """
        result = await self.db.execute(
            select(FirmApplication).where(
                FirmApplication.status.in_(["submitted", "under_review"])
            ).options(selectinload(FirmApplication.firm))
        )
        return result.scalars().all()
    
    async def review_application(
        self,
        application_id: str,
        status: str,
        rejection_reason: Optional[str],
        admin_notes: Optional[str],
        admin_user_id: str
    ) -> FirmApplication:
        """
        Review and approve/reject a firm application
        """
        application = await self.db.get(FirmApplication, application_id)
        if not application:
            raise ValueError("Application not found")
        
        if application.status not in ["submitted", "under_review"]:
            raise ValueError("Application has already been processed")
        
        # Update application
        application.status = status
        application.reviewed_at = datetime.utcnow()
        application.reviewed_by = admin_user_id
        application.rejection_reason = rejection_reason
        application.admin_notes = admin_notes
        
        # Update firm status
        firm = await self.db.get(SecurityFirm, application.firm_id)
        if status == "approved":
            firm.verification_status = "approved"
            
            # Ensure the application creator has firm_admin role
            await self._ensure_creator_is_firm_admin(application)
        
        elif status == "rejected":
            firm.verification_status = "rejected"
        
        await self.db.commit()
        await self.db.refresh(application)
        
        return application
    
    async def _ensure_creator_is_firm_admin(self, application: FirmApplication) -> None:
        """
        Ensure the application creator has firm_admin role when application is approved.
        This method finds all active users associated with the firm and ensures at least
        one has the firm_admin role, and updates their role in the main user table.
        """
        try:
            # Get all active users associated with this firm
            firm_users_result = await self.db.execute(
                select(FirmUser).where(
                    and_(
                        FirmUser.firm_id == application.firm_id,
                        FirmUser.status == "active"
                    )
                )
            )
            firm_users = firm_users_result.scalars().all()
            
            if not firm_users:
                # No users found - this shouldn't happen in normal flow
                return
            
            # Check if any user already has firm_admin role
            has_admin = any(user.role == "firm_admin" for user in firm_users)
            
            if not has_admin:
                # Promote the first active user to firm_admin
                first_user = firm_users[0]
                first_user.role = "firm_admin"
                
                # Also update their role in the main user table
                from app.models.user import RegisteredUser
                user = await self.db.get(RegisteredUser, first_user.user_id)
                if user:
                    user.role = "firm_admin"
            
            # Ensure all firm_admin users have the role updated in the main user table
            for firm_user in firm_users:
                if firm_user.role == "firm_admin":
                    from app.models.user import RegisteredUser
                    user = await self.db.get(RegisteredUser, firm_user.user_id)
                    if user and user.role != "firm_admin":
                        user.role = "firm_admin"
                        
        except Exception as e:
            # Log error but don't fail the application approval
            # This is a secondary operation that shouldn't block the main process
            pass
    
    async def invite_user(
        self,
        firm_id: str,
        email: str,
        role: str,
        invited_by: str
    ) -> FirmUser:
        """
        Invite a user to join the security firm
        """
        # Check if inviter has permission
        inviter = await self.db.execute(
            select(FirmUser).where(
                and_(
                    FirmUser.user_id == invited_by,
                    FirmUser.firm_id == firm_id,
                    FirmUser.role == "firm_admin",
                    FirmUser.status == "active"
                )
            )
        )
        if not inviter.scalar_one_or_none():
            raise ValueError("Not authorized to invite users to this firm")
        
        firm = await self.db.get(SecurityFirm, firm_id)
        if not firm:
            raise ValueError("Security firm not found")
        
        if firm.verification_status != "approved":
            raise ValueError("Firm must be approved before inviting users")
        
        # Check if user exists
        from app.models.user import RegisteredUser
        user = await self.db.execute(
            select(RegisteredUser).where(RegisteredUser.email == email)
        )
        user = user.scalar_one_or_none()
        
        if not user:
            raise ValueError("User with this email does not exist")
        
        # Check if user is already part of this firm
        existing_membership = await self.db.execute(
            select(FirmUser).where(
                and_(
                    FirmUser.user_id == user.id,
                    FirmUser.firm_id == firm_id
                )
            )
        )
        if existing_membership.scalar_one_or_none():
            raise ValueError("User is already a member of this firm")
        
        # Create invitation
        invitation = FirmUser(
            user_id=user.id,
            firm_id=firm_id,
            role=role,
            status="pending",
            invited_by=invited_by,
            invited_at=datetime.utcnow()
        )
        
        self.db.add(invitation)
        await self.db.commit()
        await self.db.refresh(invitation)
        
        # TODO: Send email invitation
        
        return invitation
    
    async def get_firm_documents(
        self,
        firm_id: str,
        user_id: str
    ) -> List[FirmDocument]:
        """
        Get all documents for a security firm
        """
        # First check if firm exists
        firm = await self.db.get(SecurityFirm, firm_id)
        if not firm:
            raise ValueError("Security firm not found")
        
        # Check if user has permission to view documents
        firm_user = await self.db.execute(
            select(FirmUser).where(
                and_(
                    FirmUser.user_id == user_id,
                    FirmUser.firm_id == firm_id,
                    FirmUser.status == "active"
                )
            )
        )
        
        # Allow both firm_admin and system admin to view documents
        from app.models.user import RegisteredUser
        user = await self.db.get(RegisteredUser, user_id)
        
        if not firm_user.scalar_one_or_none() and (not user or user.role != "admin"):
            raise ValueError("Not authorized to view documents for this firm")
        
        # Get all documents for the firm
        result = await self.db.execute(
            select(FirmDocument).where(FirmDocument.firm_id == firm_id)
        )
        return result.scalars().all()