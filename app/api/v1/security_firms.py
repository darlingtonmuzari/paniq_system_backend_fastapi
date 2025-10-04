"""
Security firm registration and management API endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr, validator
from geoalchemy2.shape import from_shape
from shapely.geometry import Polygon
import json

from app.core.database import get_db
from app.models.security_firm import SecurityFirm, CoverageArea
from app.services.security_firm import SecurityFirmService
from app.core.auth import get_current_user, require_admin
from app.services.auth import UserContext

router = APIRouter()


class SecurityFirmRegistrationRequest(BaseModel):
    """Security firm registration request model"""
    name: str
    registration_number: str
    email: EmailStr
    phone: str
    address: str
    province: str
    country: str = "South Africa"
    vat_number: Optional[str] = None
    
    @validator('name')
    def validate_name(cls, v):
        if len(v.strip()) < 2:
            raise ValueError('Name must be at least 2 characters long')
        return v.strip()
    
    @validator('registration_number')
    def validate_registration_number(cls, v):
        if len(v.strip()) < 3:
            raise ValueError('Registration number must be at least 3 characters long')
        return v.strip()
    
    @validator('phone')
    def validate_phone(cls, v):
        # Basic phone validation - should be digits and common separators
        cleaned = ''.join(c for c in v if c.isdigit() or c in '+()-. ')
        digits_only = ''.join(c for c in cleaned if c.isdigit())
        if len(digits_only) < 10:
            raise ValueError('Phone number must be at least 10 digits')
        return cleaned
    
    @validator('province')
    def validate_province(cls, v):
        if len(v.strip()) < 2:
            raise ValueError('Province must be at least 2 characters long')
        return v.strip()
    
    @validator('vat_number')
    def validate_vat_number(cls, v):
        if v and len(v.strip()) < 5:
            raise ValueError('VAT number must be at least 5 characters long')
        return v.strip() if v else None


class SecurityFirmResponse(BaseModel):
    """Security firm response model"""
    id: str
    name: str
    registration_number: str
    email: str
    phone: str
    address: str
    province: str
    country: str
    vat_number: Optional[str]
    verification_status: str
    credit_balance: int
    is_locked: bool
    created_at: str
    
    class Config:
        from_attributes = True
    
    @classmethod
    def from_orm(cls, obj):
        """Custom from_orm to handle UUID and datetime conversion"""
        return cls(
            id=str(obj.id),
            name=obj.name,
            registration_number=obj.registration_number,
            email=obj.email,
            phone=obj.phone,
            address=obj.address,
            province=obj.province,
            country=obj.country,
            vat_number=obj.vat_number,
            verification_status=obj.verification_status,
            credit_balance=obj.credit_balance,
            is_locked=obj.is_locked,
            created_at=obj.created_at.isoformat()
        )


class CoverageAreaRequest(BaseModel):
    """Coverage area creation request"""
    name: str
    boundary_coordinates: List[List[float]]  # List of [lng, lat] coordinates
    
    @validator('boundary_coordinates')
    def validate_boundary(cls, v):
        if len(v) < 3:
            raise ValueError('Boundary must have at least 3 coordinates')
        # Ensure polygon is closed
        if v[0] != v[-1]:
            v.append(v[0])
        return v


class CoverageAreaUpdateRequest(BaseModel):
    """Coverage area update request"""
    name: Optional[str] = None
    boundary_coordinates: Optional[List[List[float]]] = None  # List of [lng, lat] coordinates
    is_active: Optional[bool] = None
    
    @validator('boundary_coordinates')
    def validate_boundary(cls, v):
        if v is not None:
            if len(v) < 3:
                raise ValueError('Boundary must have at least 3 coordinates')
            # Ensure polygon is closed
            if v[0] != v[-1]:
                v.append(v[0])
        return v


class CoverageAreaResponse(BaseModel):
    """Coverage area response model"""
    id: str
    name: str
    boundary_coordinates: List[List[float]]
    is_active: bool
    created_at: str
    
    class Config:
        from_attributes = True
    
    @classmethod
    def from_orm(cls, obj):
        """Custom from_orm to handle UUID and datetime conversion"""
        return cls(
            id=str(obj.id),
            name=obj.name,
            boundary_coordinates=obj.boundary_coordinates,
            is_active=obj.is_active,
            created_at=obj.created_at.isoformat()
        )


class FirmVerificationRequest(BaseModel):
    """Firm verification request for admin"""
    verification_status: str
    rejection_reason: Optional[str] = None
    admin_notes: Optional[str] = None
    
    @validator('verification_status')
    def validate_status(cls, v):
        if v not in ['approved', 'rejected', 'under_review']:
            raise ValueError('Status must be approved, rejected, or under_review')
        return v


class DocumentUploadResponse(BaseModel):
    """Document upload response model"""
    id: str
    document_type: str
    file_name: str
    file_size: int
    uploaded_at: str
    is_verified: bool


class FirmApplicationResponse(BaseModel):
    """Firm application response model"""
    id: str
    firm_id: str
    status: str
    submitted_at: Optional[str]
    reviewed_at: Optional[str]
    rejection_reason: Optional[str]
    admin_notes: Optional[str]
    created_at: str


class UserInvitationRequest(BaseModel):
    """User invitation request model"""
    email: EmailStr
    user_type: str
    role: str
    
    @validator('user_type')
    def validate_user_type(cls, v):
        valid_user_types = ['firm_user', 'firm_supervisor', 'field_staff']
        if v not in valid_user_types:
            raise ValueError(f'User type must be one of: {", ".join(valid_user_types)}')
        return v
    
    @validator('role')
    def validate_role(cls, v):
        valid_roles = [
            'firm_staff', 'firm_supervisor', 'firm_admin',  # Office personnel
            'firm_field_leader', 'firm_field_security',    # Field personnel
            'super_admin', 'admin'                          # System administrators
        ]
        if v not in valid_roles:
            raise ValueError(f'Role must be one of: {", ".join(valid_roles)}')
        return v
    
    @validator('role')
    def validate_user_type_role_combination(cls, v, values):
        user_type = values.get('user_type')
        if user_type == 'field_staff':
            if v not in ['firm_field_leader', 'firm_field_security']:
                raise ValueError('Field staff can only be assigned firm_field_leader or firm_field_security roles')
        elif user_type in ['firm_user', 'firm_supervisor']:
            if v not in ['firm_staff', 'firm_supervisor', 'firm_admin', 'super_admin', 'admin']:
                raise ValueError('Office staff can only be assigned firm_staff, firm_supervisor, firm_admin, super_admin, or admin roles')
        return v


class FirmUpdateRequest(BaseModel):
    """Security firm update request model"""
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    province: Optional[str] = None
    country: Optional[str] = None
    vat_number: Optional[str] = None


@router.post("/register", response_model=SecurityFirmResponse)
async def register_security_firm(
    request: SecurityFirmRegistrationRequest,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new security firm for verification
    """
    service = SecurityFirmService(db)
    
    try:
        firm = await service.register_firm(
            name=request.name,
            registration_number=request.registration_number,
            email=request.email,
            phone=request.phone,
            address=request.address,
            province=request.province,
            country=request.country,
            vat_number=request.vat_number,
            user_id=current_user.user_id
        )
        return SecurityFirmResponse.from_orm(firm)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/", response_model=List[SecurityFirmResponse])
async def list_security_firms(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all security firms with optional filtering
    """
    service = SecurityFirmService(db)
    
    # Admin can see all firms, regular users only see approved firms
    if current_user.role == 'admin':
        firms = await service.list_firms(skip=skip, limit=limit, status=status)
    else:
        firms = await service.list_firms(skip=skip, limit=limit, status='approved')
    
    return [SecurityFirmResponse.from_orm(firm) for firm in firms]


@router.get("/pending", response_model=List[SecurityFirmResponse])
async def get_pending_firms(
    current_user: UserContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all pending security firms for admin review
    """
    service = SecurityFirmService(db)
    firms = await service.get_pending_firms()
    return [SecurityFirmResponse.from_orm(firm) for firm in firms]


@router.put("/{firm_id}/verify", response_model=SecurityFirmResponse)
async def verify_security_firm(
    firm_id: str,
    request: FirmVerificationRequest,
    current_user: UserContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Approve or reject a security firm registration
    """
    service = SecurityFirmService(db)
    
    try:
        firm = await service.verify_firm(
            firm_id=firm_id,
            verification_status=request.verification_status,
            rejection_reason=request.rejection_reason
        )
        return SecurityFirmResponse.from_orm(firm)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Security firm not found"
        )


@router.post("/{firm_id}/coverage-areas", response_model=CoverageAreaResponse)
async def create_coverage_area(
    firm_id: str,
    request: CoverageAreaRequest,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a coverage area for an approved security firm
    """
    service = SecurityFirmService(db)
    
    try:
        coverage_area = await service.create_coverage_area(
            firm_id=firm_id,
            name=request.name,
            boundary_coordinates=request.boundary_coordinates,
            user_id=current_user.user_id
        )
        
        # Convert geometry back to coordinates for response
        from geoalchemy2.shape import to_shape
        polygon = to_shape(coverage_area.boundary)
        coordinates = list(polygon.exterior.coords)
        
        return CoverageAreaResponse(
            id=str(coverage_area.id),
            name=coverage_area.name,
            boundary_coordinates=coordinates,
            is_active=coverage_area.is_active,
            created_at=coverage_area.created_at.isoformat()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Security firm not found or not authorized"
        )


@router.get("/{firm_id}/coverage-areas", response_model=List[CoverageAreaResponse])
async def get_coverage_areas(
    firm_id: str,
    include_inactive: bool = True,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all coverage areas for a security firm
    
    Args:
        firm_id: Security firm ID
        include_inactive: Whether to include inactive coverage areas (default: True)
    """
    service = SecurityFirmService(db)
    
    try:
        coverage_areas = await service.get_coverage_areas(firm_id, current_user.user_id, include_inactive)
        
        result = []
        for area in coverage_areas:
            from geoalchemy2.shape import to_shape
            polygon = to_shape(area.boundary)
            coordinates = list(polygon.exterior.coords)
            
            result.append(CoverageAreaResponse(
                id=str(area.id),
                name=area.name,
                boundary_coordinates=coordinates,
                is_active=area.is_active,
                created_at=area.created_at.isoformat()
            ))
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Security firm not found or not authorized"
        )


@router.get("/{firm_id}/coverage-areas/{area_id}", response_model=CoverageAreaResponse)
async def get_coverage_area(
    firm_id: str,
    area_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific coverage area for a security firm
    
    Returns detailed information about a single coverage area including
    its name, boundary coordinates, active status, and creation date.
    """
    service = SecurityFirmService(db)
    
    try:
        coverage_area = await service.get_coverage_area_by_id(
            firm_id=firm_id,
            area_id=area_id,
            user_id=current_user.user_id
        )
        
        # Convert geometry back to coordinates for response
        from geoalchemy2.shape import to_shape
        polygon = to_shape(coverage_area.boundary)
        coordinates = list(polygon.exterior.coords)
        
        return CoverageAreaResponse(
            id=str(coverage_area.id),
            name=coverage_area.name,
            boundary_coordinates=coordinates,
            is_active=coverage_area.is_active,
            created_at=coverage_area.created_at.isoformat()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coverage area not found or not authorized"
        )


@router.put("/{firm_id}/coverage-areas/{area_id}", response_model=CoverageAreaResponse)
async def update_coverage_area(
    firm_id: str,
    area_id: str,
    request: CoverageAreaUpdateRequest,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a coverage area for a security firm
    
    Allows updating the name and/or boundary coordinates of an existing coverage area.
    Only non-null fields in the request will be updated.
    """
    service = SecurityFirmService(db)
    
    try:
        coverage_area = await service.update_coverage_area(
            firm_id=firm_id,
            area_id=area_id,
            name=request.name,
            boundary_coordinates=request.boundary_coordinates,
            is_active=request.is_active,
            user_id=current_user.user_id
        )
        
        # Convert geometry back to coordinates for response
        from geoalchemy2.shape import to_shape
        polygon = to_shape(coverage_area.boundary)
        coordinates = list(polygon.exterior.coords)
        
        return CoverageAreaResponse(
            id=str(coverage_area.id),
            name=coverage_area.name,
            boundary_coordinates=coordinates,
            is_active=coverage_area.is_active,
            created_at=coverage_area.created_at.isoformat()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coverage area not found or not authorized"
        )


@router.delete("/{firm_id}/coverage-areas/{area_id}")
async def delete_coverage_area(
    firm_id: str,
    area_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a coverage area for a security firm
    
    Permanently removes the coverage area. This operation cannot be undone.
    """
    service = SecurityFirmService(db)
    
    try:
        await service.delete_coverage_area(
            firm_id=firm_id,
            area_id=area_id,
            user_id=current_user.user_id
        )
        
        return {"message": "Coverage area deleted successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coverage area not found or not authorized"
        )


@router.put("/{firm_id}/coverage-areas/{area_id}/activate", response_model=CoverageAreaResponse)
async def activate_coverage_area(
    firm_id: str,
    area_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Activate a coverage area for a security firm
    
    Sets the coverage area's is_active status to True.
    """
    service = SecurityFirmService(db)
    
    try:
        coverage_area = await service.update_coverage_area(
            firm_id=firm_id,
            area_id=area_id,
            is_active=True,
            user_id=current_user.user_id
        )
        
        # Convert geometry back to coordinates for response
        from geoalchemy2.shape import to_shape
        polygon = to_shape(coverage_area.boundary)
        coordinates = list(polygon.exterior.coords)
        
        return CoverageAreaResponse(
            id=str(coverage_area.id),
            name=coverage_area.name,
            boundary_coordinates=coordinates,
            is_active=coverage_area.is_active,
            created_at=coverage_area.created_at.isoformat()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coverage area not found or not authorized"
        )


@router.put("/{firm_id}/coverage-areas/{area_id}/deactivate", response_model=CoverageAreaResponse)
async def deactivate_coverage_area(
    firm_id: str,
    area_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Deactivate a coverage area for a security firm
    
    Sets the coverage area's is_active status to False. Inactive areas
    are not considered for subscription validation or team assignments.
    """
    service = SecurityFirmService(db)
    
    try:
        coverage_area = await service.update_coverage_area(
            firm_id=firm_id,
            area_id=area_id,
            is_active=False,
            user_id=current_user.user_id
        )
        
        # Convert geometry back to coordinates for response
        from geoalchemy2.shape import to_shape
        polygon = to_shape(coverage_area.boundary)
        coordinates = list(polygon.exterior.coords)
        
        return CoverageAreaResponse(
            id=str(coverage_area.id),
            name=coverage_area.name,
            boundary_coordinates=coordinates,
            is_active=coverage_area.is_active,
            created_at=coverage_area.created_at.isoformat()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coverage area not found or not authorized"
        )


@router.get("/{firm_id}", response_model=SecurityFirmResponse)
async def get_security_firm(
    firm_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get security firm details
    """
    service = SecurityFirmService(db)
    
    try:
        firm = await service.get_firm_by_id(firm_id, current_user.user_id)
        return SecurityFirmResponse.from_orm(firm)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Security firm not found or not authorized"
        )


@router.put("/{firm_id}", response_model=SecurityFirmResponse)
async def update_security_firm(
    firm_id: str,
    request: FirmUpdateRequest,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update security firm details (only allowed in draft status)
    """
    service = SecurityFirmService(db)
    
    try:
        firm = await service.update_firm(
            firm_id=firm_id,
            user_id=current_user.user_id,
            **request.dict(exclude_unset=True)
        )
        return SecurityFirmResponse.from_orm(firm)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{firm_id}/documents", response_model=DocumentUploadResponse)
async def upload_firm_document(
    firm_id: str,
    document_type: str,
    file: UploadFile = File(...),
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload verification documents for a security firm
    """
    # Validate document type using the document type service
    from app.services.document_type import DocumentTypeService
    doc_type_service = DocumentTypeService(db)
    
    try:
        # Check if document_type is a UUID (ID) or a code
        import uuid
        try:
            # Try to parse as UUID - if successful, it's an ID
            uuid.UUID(document_type)
            doc_type = await doc_type_service.get_document_type_by_id(document_type)
            if not doc_type:
                raise ValueError(f"Document type with ID {document_type} not found")
            document_type_code = doc_type.code
        except ValueError:
            # Not a UUID, treat as code
            doc_type = await doc_type_service.validate_document_type(document_type)
            document_type_code = document_type
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # Use default file validation since we removed MIME type and size restrictions
    allowed_mime_types = ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg']
    max_file_size_mb = 10
    
    # Validate file type
    if file.content_type not in allowed_mime_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file.content_type} not allowed. Allowed types: {', '.join(allowed_mime_types)}"
        )
    
    # Check file size
    max_size_bytes = max_file_size_mb * 1024 * 1024
    if file.size > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size must be less than {max_file_size_mb}MB"
        )
    
    service = SecurityFirmService(db)
    
    try:
        document = await service.upload_document(
            firm_id=firm_id,
            document_type=document_type_code,
            file=file,
            user_id=current_user.user_id
        )
        return DocumentUploadResponse(
            id=str(document.id),
            document_type=document.document_type,
            file_name=document.file_name,
            file_size=document.file_size,
            uploaded_at=document.created_at.isoformat(),
            is_verified=document.is_verified
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{firm_id}/documents", response_model=List[DocumentUploadResponse])
async def get_firm_documents(
    firm_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all documents for a security firm
    """
    service = SecurityFirmService(db)
    
    try:
        documents = await service.get_firm_documents(
            firm_id=firm_id,
            user_id=current_user.user_id
        )
        return [
            DocumentUploadResponse(
                id=str(doc.id),
                document_type=doc.document_type,
                file_name=doc.file_name,
                file_size=doc.file_size,
                uploaded_at=doc.created_at.isoformat(),
                is_verified=doc.is_verified
            )
            for doc in documents
        ]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{firm_id}/submit-application", response_model=FirmApplicationResponse)
async def submit_firm_application(
    firm_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit security firm application for admin review
    """
    service = SecurityFirmService(db)
    
    try:
        application = await service.submit_application(
            firm_id=firm_id,
            user_id=current_user.user_id
        )
        return FirmApplicationResponse(
            id=str(application.id),
            firm_id=str(application.firm_id),
            status=application.status,
            submitted_at=application.submitted_at.isoformat() if application.submitted_at else None,
            reviewed_at=application.reviewed_at.isoformat() if application.reviewed_at else None,
            rejection_reason=application.rejection_reason,
            admin_notes=application.admin_notes,
            created_at=application.created_at.isoformat()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/applications/pending", response_model=List[FirmApplicationResponse])
async def get_pending_applications(
    current_user: UserContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all pending firm applications for admin review
    """
    service = SecurityFirmService(db)
    applications = await service.get_pending_applications()
    
    return [
        FirmApplicationResponse(
            id=str(app.id),
            firm_id=str(app.firm_id),
            status=app.status,
            submitted_at=app.submitted_at.isoformat() if app.submitted_at else None,
            reviewed_at=app.reviewed_at.isoformat() if app.reviewed_at else None,
            rejection_reason=app.rejection_reason,
            admin_notes=app.admin_notes,
            created_at=app.created_at.isoformat()
        )
        for app in applications
    ]


@router.put("/applications/{application_id}/review", response_model=FirmApplicationResponse)
async def review_firm_application(
    application_id: str,
    request: FirmVerificationRequest,
    current_user: UserContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Review and approve/reject a firm application
    """
    service = SecurityFirmService(db)
    
    try:
        application = await service.review_application(
            application_id=application_id,
            status=request.verification_status,
            rejection_reason=request.rejection_reason,
            admin_notes=request.admin_notes,
            admin_user_id=current_user.user_id
        )
        return FirmApplicationResponse(
            id=str(application.id),
            firm_id=str(application.firm_id),
            status=application.status,
            submitted_at=application.submitted_at.isoformat() if application.submitted_at else None,
            reviewed_at=application.reviewed_at.isoformat() if application.reviewed_at else None,
            rejection_reason=application.rejection_reason,
            admin_notes=application.admin_notes,
            created_at=application.created_at.isoformat()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{firm_id}/invite-user")
async def invite_user_to_firm(
    firm_id: str,
    request: UserInvitationRequest,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Invite a user to join the security firm (firm_admin only)
    """
    service = SecurityFirmService(db)
    
    try:
        invitation = await service.invite_user(
            firm_id=firm_id,
            email=request.email,
            role=request.role,
            invited_by=current_user.user_id
        )
        return {"message": f"Invitation sent to {request.email}", "invitation_id": str(invitation.id)}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{firm_id}/documents/{document_id}/download")
async def download_firm_document(
    firm_id: str,
    document_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Download a firm document (returns presigned URL for S3 or file content for local)
    """
    from app.services.s3_service import S3Service
    from app.core.config import settings
    from fastapi.responses import RedirectResponse
    
    service = SecurityFirmService(db)
    
    try:
        # Get the document
        document = await service.get_document_by_id(document_id, firm_id, current_user.user_id)
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Check if file is stored in S3 (S3 keys don't start with 'uploads/')
        if not document.file_path.startswith('uploads/'):
            # S3 storage - return presigned URL
            try:
                s3_service = S3Service()
                presigned_url = s3_service.get_file_url(document.file_path, expires_in=3600)
                return RedirectResponse(url=presigned_url)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to generate download URL: {str(e)}"
                )
        else:
            # Local storage - serve file directly
            from fastapi.responses import FileResponse
            import os
            
            if not os.path.exists(document.file_path):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="File not found on disk"
                )
            
            return FileResponse(
                path=document.file_path,
                filename=document.file_name,
                media_type=document.mime_type or 'application/octet-stream'
            )
            
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )