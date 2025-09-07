"""
Document types API endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, validator

from app.core.database import get_db
from app.services.document_type import DocumentTypeService
from app.core.auth import get_current_user, require_admin
from app.services.auth import UserContext

router = APIRouter()


class DocumentTypeResponse(BaseModel):
    """Document type response model"""
    id: str
    code: str
    name: str
    description: Optional[str]
    is_required: bool
    is_active: bool
    created_by: str
    created_at: str
    
    class Config:
        from_attributes = True


def _create_document_type_response(doc_type) -> DocumentTypeResponse:
    """Helper function to create DocumentTypeResponse from DocumentType model"""
    return DocumentTypeResponse(
        id=str(doc_type.id),
        code=doc_type.code,
        name=doc_type.name,
        description=doc_type.description,
        is_required=doc_type.is_required,
        is_active=doc_type.is_active,
        created_by=str(doc_type.created_by),
        created_at=doc_type.created_at.isoformat()
    )


class DocumentTypeCreateRequest(BaseModel):
    """Document type creation request model"""
    code: str
    name: str
    description: Optional[str] = None
    is_required: bool = False
    
    @validator('code')
    def validate_code(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('Code must be at least 2 characters long')
        # Only allow alphanumeric and underscores
        if not v.replace('_', '').isalnum():
            raise ValueError('Code can only contain letters, numbers, and underscores')
        return v.lower().strip()
    
    @validator('name')
    def validate_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('Name must be at least 2 characters long')
        return v.strip()


class DocumentTypeUpdateRequest(BaseModel):
    """Document type update request model"""
    name: Optional[str] = None
    description: Optional[str] = None
    is_required: Optional[bool] = None
    is_active: Optional[bool] = None
    
    @validator('name')
    def validate_name(cls, v):
        if v is not None and len(v.strip()) < 2:
            raise ValueError('Name must be at least 2 characters long')
        return v.strip() if v else None


@router.get("/all", response_model=List[DocumentTypeResponse])
async def list_all_document_types(
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all document types (both active and inactive)
    """
    service = DocumentTypeService(db)
    
    try:
        document_types = await service.get_all_document_types_including_inactive()
        return [_create_document_type_response(doc_type) for doc_type in document_types]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve document types: {str(e)}"
        )


@router.get("/", response_model=List[DocumentTypeResponse])
async def get_document_types(
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all document types (both active and inactive)
    """
    service = DocumentTypeService(db)
    
    try:
        document_types = await service.get_all_document_types_including_inactive()
        return [_create_document_type_response(doc_type) for doc_type in document_types]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve document types: {str(e)}"
        )


@router.get("/by-id/{document_type_id}", response_model=DocumentTypeResponse)
async def get_document_type_by_id(
    document_type_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific document type by ID
    """
    service = DocumentTypeService(db)
    
    try:
        doc_type = await service.get_document_type_by_id(document_type_id)
        
        if not doc_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document type with ID '{document_type_id}' not found"
            )
        
        return _create_document_type_response(doc_type)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve document type: {str(e)}"
        )


@router.get("/by-code/{code}", response_model=DocumentTypeResponse)
async def get_document_type_by_code(
    code: str,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific document type by code
    """
    service = DocumentTypeService(db)
    
    try:
        doc_type = await service.get_document_type_by_code(code)
        
        if not doc_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document type '{code}' not found"
            )
        
        return _create_document_type_response(doc_type)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve document type: {str(e)}"
        )


@router.get("/required", response_model=List[DocumentTypeResponse])
async def get_required_documents(
    is_active: Optional[bool] = None,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all required document types with optional is_active filter
    
    Query Parameters:
    - is_active: Filter by active status (true/false). If not provided, returns both active and inactive.
    """
    service = DocumentTypeService(db)
    
    try:
        document_types = await service.get_required_documents(is_active=is_active)
        return [_create_document_type_response(doc_type) for doc_type in document_types]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve required documents: {str(e)}"
        )


@router.post("/", response_model=DocumentTypeResponse)
async def create_document_type(
    request: DocumentTypeCreateRequest,
    current_user: UserContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new document type (admin only)
    """
    service = DocumentTypeService(db)
    
    try:
        doc_type = await service.create_document_type(
            code=request.code,
            name=request.name,
            description=request.description,
            created_by=current_user.user_id,
            is_required=request.is_required
        )
        
        return _create_document_type_response(doc_type)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create document type: {str(e)}"
        )


@router.put("/by-id/{document_type_id}", response_model=DocumentTypeResponse)
async def update_document_type_by_id(
    document_type_id: str,
    request: DocumentTypeUpdateRequest,
    current_user: UserContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a document type by ID (admin only)
    """
    service = DocumentTypeService(db)
    
    try:
        # Use dict() instead of dict(exclude_unset=True) to include False values
        updates = request.dict()
        # Remove None values but keep False values
        updates = {k: v for k, v in updates.items() if v is not None}
        
        doc_type = await service.update_document_type_by_id(
            document_type_id=document_type_id,
            **updates
        )
        
        return _create_document_type_response(doc_type)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update document type: {str(e)}"
        )


@router.put("/by-code/{code}", response_model=DocumentTypeResponse)
async def update_document_type_by_code(
    code: str,
    request: DocumentTypeUpdateRequest,
    current_user: UserContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a document type by code (admin only)
    """
    service = DocumentTypeService(db)
    
    try:
        # Use dict() instead of dict(exclude_unset=True) to include False values
        updates = request.dict()
        # Remove None values but keep False values
        updates = {k: v for k, v in updates.items() if v is not None}
        
        doc_type = await service.update_document_type_by_code(
            code=code,
            **updates
        )
        
        return _create_document_type_response(doc_type)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update document type: {str(e)}"
        )


@router.delete("/by-id/{document_type_id}")
async def deactivate_document_type_by_id(
    document_type_id: str,
    current_user: UserContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Deactivate a document type by ID (admin only)
    """
    service = DocumentTypeService(db)
    
    try:
        doc_type = await service.deactivate_document_type_by_id(document_type_id)
        return {"message": f"Document type '{doc_type.code}' has been deactivated"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deactivate document type: {str(e)}"
        )


@router.delete("/by-code/{code}")
async def deactivate_document_type_by_code(
    code: str,
    current_user: UserContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Deactivate a document type by code (admin only)
    """
    service = DocumentTypeService(db)
    
    try:
        await service.deactivate_document_type_by_code(code)
        return {"message": f"Document type '{code}' has been deactivated"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deactivate document type: {str(e)}"
        )


@router.post("/validate/{code}")
async def validate_document_type(
    code: str,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Validate that a document type exists and is active
    """
    service = DocumentTypeService(db)
    
    try:
        doc_type = await service.validate_document_type(code)
        
        return {
            "valid": True,
            "document_type": {
                "code": doc_type.code,
                "name": doc_type.name
            }
        }
    except ValueError as e:
        return {
            "valid": False,
            "error": str(e)
        }