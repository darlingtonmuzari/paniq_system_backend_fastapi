"""
Emergency Provider Types API endpoints for managing provider type configurations
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import require_admin_or_super_admin, get_current_user
from app.services.auth import UserContext
from app.services.emergency_provider_type import EmergencyProviderTypeService

router = APIRouter()


class ProviderTypeCreateRequest(BaseModel):
    """Request model for creating emergency provider type"""
    name: str = Field(..., min_length=1, max_length=100, description="Provider type name")
    code: str = Field(..., min_length=1, max_length=50, description="Provider type code")
    description: Optional[str] = Field(None, max_length=1000, description="Provider type description")
    requires_license: bool = Field(False, description="Whether this provider type requires a license")
    default_coverage_radius_km: float = Field(50.0, gt=0, le=500, description="Default coverage radius in kilometers")
    icon: Optional[str] = Field(None, max_length=100, description="Icon identifier for UI")
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$", description="Hex color code")
    priority_level: str = Field("medium", description="Priority level")
    
    @validator('priority_level')
    def validate_priority_level(cls, v):
        allowed_levels = ["low", "medium", "high", "critical"]
        if v not in allowed_levels:
            raise ValueError(f"Priority level must be one of: {', '.join(allowed_levels)}")
        return v
    
    @validator('code')
    def validate_code(cls, v):
        # Code should be lowercase with underscores
        if not v.replace('_', '').isalnum():
            raise ValueError("Code must contain only letters, numbers, and underscores")
        return v.lower()


class ProviderTypeUpdateRequest(BaseModel):
    """Request model for updating emergency provider type"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    requires_license: Optional[bool] = None
    default_coverage_radius_km: Optional[float] = Field(None, gt=0, le=500)
    icon: Optional[str] = Field(None, max_length=100)
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    priority_level: Optional[str] = None
    is_active: Optional[bool] = None
    
    @validator('priority_level')
    def validate_priority_level(cls, v):
        if v is not None:
            allowed_levels = ["low", "medium", "high", "critical"]
            if v not in allowed_levels:
                raise ValueError(f"Priority level must be one of: {', '.join(allowed_levels)}")
        return v


class ProviderTypeResponse(BaseModel):
    """Response model for emergency provider type"""
    id: str
    name: str
    code: str
    description: Optional[str]
    is_active: bool
    requires_license: bool
    default_coverage_radius_km: float
    icon: Optional[str]
    color: Optional[str]
    priority_level: str
    created_at: str
    updated_at: str


@router.post("/", response_model=ProviderTypeResponse, status_code=201)
async def create_provider_type(
    request: ProviderTypeCreateRequest,
    current_user: UserContext = Depends(require_admin_or_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new emergency provider type
    
    Only accessible by admin and super_admin
    """
    try:
        service = EmergencyProviderTypeService(db)
        provider_type = await service.create_provider_type(
            name=request.name,
            code=request.code,
            description=request.description,
            requires_license=request.requires_license,
            default_coverage_radius_km=request.default_coverage_radius_km,
            icon=request.icon,
            color=request.color,
            priority_level=request.priority_level
        )
        
        return ProviderTypeResponse(
            id=str(provider_type.id),
            name=provider_type.name,
            code=provider_type.code,
            description=provider_type.description,
            is_active=provider_type.is_active,
            requires_license=provider_type.requires_license,
            default_coverage_radius_km=provider_type.default_coverage_radius_km,
            icon=provider_type.icon,
            color=provider_type.color,
            priority_level=provider_type.priority_level,
            created_at=provider_type.created_at.isoformat(),
            updated_at=provider_type.updated_at.isoformat()
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create provider type"
        )


@router.get("/", response_model=List[ProviderTypeResponse])
async def list_provider_types(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List emergency provider types
    
    Accessible by all authenticated users
    """
    try:
        service = EmergencyProviderTypeService(db)
        provider_types = await service.list_provider_types(
            skip=skip,
            limit=limit,
            is_active=is_active
        )
        
        return [
            ProviderTypeResponse(
                id=str(pt.id),
                name=pt.name,
                code=pt.code,
                description=pt.description,
                is_active=pt.is_active,
                requires_license=pt.requires_license,
                default_coverage_radius_km=pt.default_coverage_radius_km,
                icon=pt.icon,
                color=pt.color,
                priority_level=pt.priority_level,
                created_at=pt.created_at.isoformat(),
                updated_at=pt.updated_at.isoformat()
            )
            for pt in provider_types
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list provider types"
        )


@router.get("/{type_id}", response_model=ProviderTypeResponse)
async def get_provider_type(
    type_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get emergency provider type by ID
    
    Accessible by all authenticated users
    """
    try:
        service = EmergencyProviderTypeService(db)
        provider_type = await service.get_provider_type_by_id(UUID(type_id))
        
        if not provider_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Provider type not found"
            )
        
        return ProviderTypeResponse(
            id=str(provider_type.id),
            name=provider_type.name,
            code=provider_type.code,
            description=provider_type.description,
            is_active=provider_type.is_active,
            requires_license=provider_type.requires_license,
            default_coverage_radius_km=provider_type.default_coverage_radius_km,
            icon=provider_type.icon,
            color=provider_type.color,
            priority_level=provider_type.priority_level,
            created_at=provider_type.created_at.isoformat(),
            updated_at=provider_type.updated_at.isoformat()
        )
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid provider type ID"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get provider type"
        )


@router.put("/{type_id}", response_model=ProviderTypeResponse)
async def update_provider_type(
    type_id: str,
    request: ProviderTypeUpdateRequest,
    current_user: UserContext = Depends(require_admin_or_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Update emergency provider type
    
    Only accessible by admin and super_admin
    """
    try:
        service = EmergencyProviderTypeService(db)
        
        # Get current provider type
        provider_type = await service.get_provider_type_by_id(UUID(type_id))
        if not provider_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Provider type not found"
            )
        
        # Update provider type
        updated_provider_type = await service.update_provider_type(
            type_id=UUID(type_id),
            **request.dict(exclude_unset=True)
        )
        
        return ProviderTypeResponse(
            id=str(updated_provider_type.id),
            name=updated_provider_type.name,
            code=updated_provider_type.code,
            description=updated_provider_type.description,
            is_active=updated_provider_type.is_active,
            requires_license=updated_provider_type.requires_license,
            default_coverage_radius_km=updated_provider_type.default_coverage_radius_km,
            icon=updated_provider_type.icon,
            color=updated_provider_type.color,
            priority_level=updated_provider_type.priority_level,
            created_at=updated_provider_type.created_at.isoformat(),
            updated_at=updated_provider_type.updated_at.isoformat()
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update provider type"
        )


@router.delete("/{type_id}")
async def delete_provider_type(
    type_id: str,
    current_user: UserContext = Depends(require_admin_or_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete emergency provider type
    
    Only accessible by admin and super_admin
    Note: Cannot delete provider types that are in use by existing providers
    """
    try:
        service = EmergencyProviderTypeService(db)
        
        # Check if provider type exists
        provider_type = await service.get_provider_type_by_id(UUID(type_id))
        if not provider_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Provider type not found"
            )
        
        # Check if provider type is in use
        is_in_use = await service.is_provider_type_in_use(UUID(type_id))
        if is_in_use:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete provider type that is in use by existing providers"
            )
        
        await service.delete_provider_type(UUID(type_id))
        
        return {"message": "Provider type deleted successfully"}
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid provider type ID"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete provider type"
        )