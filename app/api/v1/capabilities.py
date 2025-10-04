"""
Capabilities API endpoints for managing emergency provider capabilities
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import require_admin_or_super_admin, get_current_user
from app.services.auth import UserContext
from app.services.capability import CapabilityService
from app.models.capability import ProficiencyLevel

router = APIRouter()


class CapabilityCreateRequest(BaseModel):
    """Capability creation request"""
    name: str = Field(..., min_length=1, max_length=100, description="Capability name")
    code: str = Field(..., min_length=1, max_length=50, description="Capability code (unique identifier)")
    description: Optional[str] = Field(None, max_length=1000, description="Capability description")
    category_id: str = Field(..., description="Capability category ID")
    is_active: bool = Field(True, description="Whether capability is active")

    @validator('code')
    def validate_code(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Code must contain only alphanumeric characters, underscores, and hyphens')
        return v.lower()


class CapabilityUpdateRequest(BaseModel):
    """Capability update request"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Capability name")
    description: Optional[str] = Field(None, max_length=1000, description="Capability description")
    category_id: Optional[str] = Field(None, description="Capability category ID")
    is_active: Optional[bool] = Field(None, description="Whether capability is active")


class CapabilityResponse(BaseModel):
    """Capability response"""
    id: str
    name: str
    code: str
    description: Optional[str]
    category_id: str
    category_name: Optional[str] = None
    category_code: Optional[str] = None
    is_active: bool
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class CapabilityListResponse(BaseModel):
    """Capability list response"""
    capabilities: List[CapabilityResponse]
    total_count: int


class ProviderCapabilityCreateRequest(BaseModel):
    """Provider capability assignment request"""
    provider_id: str = Field(..., description="Emergency provider ID")
    capability_id: str = Field(..., description="Capability ID")
    proficiency_level: ProficiencyLevel = Field(ProficiencyLevel.STANDARD, description="Proficiency level")
    certification_level: Optional[str] = Field(None, max_length=50, description="Certification level")


class ProviderCapabilityUpdateRequest(BaseModel):
    """Provider capability update request"""
    proficiency_level: Optional[ProficiencyLevel] = Field(None, description="Proficiency level")
    certification_level: Optional[str] = Field(None, max_length=50, description="Certification level")


class ProviderCapabilityResponse(BaseModel):
    """Provider capability response"""
    id: str
    provider_id: str
    capability_id: str
    capability_name: str
    capability_code: str
    capability_category: str
    proficiency_level: str
    certification_level: Optional[str]
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class ProviderCapabilityListResponse(BaseModel):
    """Provider capability list response"""
    provider_capabilities: List[ProviderCapabilityResponse]
    total_count: int


# Capability CRUD endpoints (Admin/Super Admin only)

@router.post("/", response_model=CapabilityResponse)
async def create_capability(
    request: CapabilityCreateRequest,
    current_user: UserContext = Depends(require_admin_or_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new capability
    
    Only admin and super_admin can create capabilities.
    """
    try:
        service = CapabilityService(db)
        
        capability = await service.create_capability(
            name=request.name,
            code=request.code,
            description=request.description,
            category_id=UUID(request.category_id),
            is_active=request.is_active
        )
        
        return CapabilityResponse(
            id=str(capability.id),
            name=capability.name,
            code=capability.code,
            description=capability.description,
            category_id=str(capability.category_id),
            category_name=capability.capability_category.name if capability.capability_category else None,
            category_code=capability.capability_category.code if capability.capability_category else None,
            is_active=capability.is_active,
            created_at=capability.created_at.isoformat(),
            updated_at=capability.updated_at.isoformat()
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create capability"
        )


@router.get("/", response_model=CapabilityListResponse)
async def get_capabilities(
    category_id: Optional[str] = Query(None, description="Filter by category ID"),
    include_inactive: bool = Query(True, description="Include inactive capabilities"),
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all capabilities
    
    All authenticated users can read capabilities.
    """
    try:
        service = CapabilityService(db)
        
        capabilities = await service.get_capabilities(
            category_id=UUID(category_id) if category_id else None,
            include_inactive=include_inactive,
            load_category=True
        )
        
        capability_responses = []
        for capability in capabilities:
            capability_responses.append(CapabilityResponse(
                id=str(capability.id),
                name=capability.name,
                code=capability.code,
                description=capability.description,
                category_id=str(capability.category_id),
                category_name=capability.capability_category.name if capability.capability_category else None,
                category_code=capability.capability_category.code if capability.capability_category else None,
                is_active=capability.is_active,
                created_at=capability.created_at.isoformat(),
                updated_at=capability.updated_at.isoformat()
            ))
        
        return CapabilityListResponse(
            capabilities=capability_responses,
            total_count=len(capability_responses)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve capabilities"
        )


@router.get("/{capability_id}", response_model=CapabilityResponse)
async def get_capability(
    capability_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get capability by ID
    
    All authenticated users can read capabilities.
    """
    try:
        service = CapabilityService(db)
        capability = await service.get_capability_by_id(UUID(capability_id), load_category=True)
        
        if not capability:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Capability not found"
            )
        
        return CapabilityResponse(
            id=str(capability.id),
            name=capability.name,
            code=capability.code,
            description=capability.description,
            category_id=str(capability.category_id),
            category_name=capability.capability_category.name if capability.capability_category else None,
            category_code=capability.capability_category.code if capability.capability_category else None,
            is_active=capability.is_active,
            created_at=capability.created_at.isoformat(),
            updated_at=capability.updated_at.isoformat()
        )
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid capability ID"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve capability"
        )


@router.put("/{capability_id}", response_model=CapabilityResponse)
async def update_capability(
    capability_id: str,
    request: CapabilityUpdateRequest,
    current_user: UserContext = Depends(require_admin_or_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Update capability
    
    Only admin and super_admin can update capabilities.
    """
    try:
        service = CapabilityService(db)
        
        capability = await service.update_capability(
            capability_id=UUID(capability_id),
            name=request.name,
            description=request.description,
            category_id=UUID(request.category_id) if request.category_id else None,
            is_active=request.is_active
        )
        
        if not capability:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Capability not found"
            )
        
        return CapabilityResponse(
            id=str(capability.id),
            name=capability.name,
            code=capability.code,
            description=capability.description,
            category_id=str(capability.category_id),
            category_name=capability.capability_category.name if capability.capability_category else None,
            category_code=capability.capability_category.code if capability.capability_category else None,
            is_active=capability.is_active,
            created_at=capability.created_at.isoformat(),
            updated_at=capability.updated_at.isoformat()
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update capability"
        )


@router.delete("/{capability_id}")
async def delete_capability(
    capability_id: str,
    current_user: UserContext = Depends(require_admin_or_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete capability
    
    Only admin and super_admin can delete capabilities.
    Soft delete by setting is_active = false.
    """
    try:
        service = CapabilityService(db)
        
        success = await service.delete_capability(UUID(capability_id))
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Capability not found"
            )
        
        return {"message": "Capability deleted successfully"}
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid capability ID"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete capability"
        )


# Provider capability assignment endpoints

@router.post("/provider-capabilities", response_model=ProviderCapabilityResponse)
async def assign_capability_to_provider(
    request: ProviderCapabilityCreateRequest,
    current_user: UserContext = Depends(require_admin_or_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Assign capability to provider
    
    Only admin and super_admin can manage provider capabilities.
    """
    try:
        service = CapabilityService(db)
        
        provider_capability = await service.assign_capability_to_provider(
            provider_id=UUID(request.provider_id),
            capability_id=UUID(request.capability_id),
            proficiency_level=request.proficiency_level,
            certification_level=request.certification_level
        )
        
        return ProviderCapabilityResponse(
            id=str(provider_capability.id),
            provider_id=str(provider_capability.provider_id),
            capability_id=str(provider_capability.capability_id),
            capability_name=provider_capability.capability.name,
            capability_code=provider_capability.capability.code,
            capability_category=provider_capability.capability.capability_category.name if provider_capability.capability.capability_category else None,
            proficiency_level=provider_capability.proficiency_level.value,
            certification_level=provider_capability.certification_level,
            created_at=provider_capability.created_at.isoformat(),
            updated_at=provider_capability.updated_at.isoformat()
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign capability to provider"
        )


@router.get("/provider-capabilities/{provider_id}", response_model=ProviderCapabilityListResponse)
async def get_provider_capabilities(
    provider_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all capabilities for a provider
    
    All authenticated users can read provider capabilities.
    """
    try:
        service = CapabilityService(db)
        
        provider_capabilities = await service.get_provider_capabilities(UUID(provider_id))
        
        responses = []
        for pc in provider_capabilities:
            responses.append(ProviderCapabilityResponse(
                id=str(pc.id),
                provider_id=str(pc.provider_id),
                capability_id=str(pc.capability_id),
                capability_name=pc.capability.name,
                capability_code=pc.capability.code,
                capability_category=pc.capability.capability_category.name if pc.capability.capability_category else None,
                proficiency_level=pc.proficiency_level.value,
                certification_level=pc.certification_level,
                created_at=pc.created_at.isoformat(),
                updated_at=pc.updated_at.isoformat()
            ))
        
        return ProviderCapabilityListResponse(
            provider_capabilities=responses,
            total_count=len(responses)
        )
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid provider ID"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve provider capabilities"
        )


@router.delete("/provider-capabilities/{provider_capability_id}")
async def remove_capability_from_provider(
    provider_capability_id: str,
    current_user: UserContext = Depends(require_admin_or_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove capability from provider
    
    Only admin and super_admin can manage provider capabilities.
    """
    try:
        service = CapabilityService(db)
        
        success = await service.remove_capability_from_provider(UUID(provider_capability_id))
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Provider capability assignment not found"
            )
        
        return {"message": "Capability removed from provider successfully"}
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid provider capability ID"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove capability from provider"
        )