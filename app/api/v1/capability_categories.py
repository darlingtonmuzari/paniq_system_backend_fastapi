"""
Capability Categories API endpoints for managing capability classification
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import require_admin_or_super_admin, get_current_user
from app.services.auth import UserContext
from app.services.capability_category import CapabilityCategoryService

router = APIRouter()


class CapabilityCategoryCreateRequest(BaseModel):
    """Capability category creation request"""
    name: str = Field(..., min_length=1, max_length=100, description="Category name")
    code: str = Field(..., min_length=1, max_length=50, description="Category code (unique identifier)")
    description: Optional[str] = Field(None, max_length=1000, description="Category description")
    icon: Optional[str] = Field(None, max_length=50, description="Icon name for UI")
    color: Optional[str] = Field(None, max_length=7, description="Hex color code")
    is_active: bool = Field(True, description="Whether category is active")

    @validator('code')
    def validate_code(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Code must contain only alphanumeric characters, underscores, and hyphens')
        return v.lower()

    @validator('color')
    def validate_color(cls, v):
        if v and not v.startswith('#'):
            raise ValueError('Color must be a hex color code starting with #')
        if v and len(v) != 7:
            raise ValueError('Color must be a 7-character hex color code (e.g. #FF0000)')
        return v


class CapabilityCategoryUpdateRequest(BaseModel):
    """Capability category update request"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Category name")
    description: Optional[str] = Field(None, max_length=1000, description="Category description")
    icon: Optional[str] = Field(None, max_length=50, description="Icon name for UI")
    color: Optional[str] = Field(None, max_length=7, description="Hex color code")
    is_active: Optional[bool] = Field(None, description="Whether category is active")

    @validator('color')
    def validate_color(cls, v):
        if v and not v.startswith('#'):
            raise ValueError('Color must be a hex color code starting with #')
        if v and len(v) != 7:
            raise ValueError('Color must be a 7-character hex color code (e.g. #FF0000)')
        return v


class CapabilityCategoryResponse(BaseModel):
    """Capability category response"""
    id: str
    name: str
    code: str
    description: Optional[str]
    icon: Optional[str]
    color: Optional[str]
    is_active: bool
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class CapabilityCategoryListResponse(BaseModel):
    """Capability category list response"""
    categories: List[CapabilityCategoryResponse]
    total_count: int


class CapabilityCategoryStatsResponse(BaseModel):
    """Capability category statistics response"""
    total_categories: int
    active_categories: int
    inactive_categories: int
    categories: List[dict]


# Capability category CRUD endpoints (Admin/Super Admin only for CUD, All authenticated for R)

@router.post("/", response_model=CapabilityCategoryResponse)
async def create_capability_category(
    request: CapabilityCategoryCreateRequest,
    current_user: UserContext = Depends(require_admin_or_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new capability category
    
    Only admin and super_admin can create capability categories.
    """
    try:
        service = CapabilityCategoryService(db)
        
        category = await service.create_category(
            name=request.name,
            code=request.code,
            description=request.description,
            icon=request.icon,
            color=request.color,
            is_active=request.is_active
        )
        
        return CapabilityCategoryResponse(
            id=str(category.id),
            name=category.name,
            code=category.code,
            description=category.description,
            icon=category.icon,
            color=category.color,
            is_active=category.is_active,
            created_at=category.created_at.isoformat(),
            updated_at=category.updated_at.isoformat()
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create capability category"
        )


@router.get("/", response_model=CapabilityCategoryListResponse)
async def get_capability_categories(
    include_inactive: bool = Query(True, description="Include inactive categories"),
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all capability categories
    
    All authenticated users can read capability categories.
    """
    try:
        service = CapabilityCategoryService(db)
        
        categories = await service.get_categories(
            include_inactive=include_inactive
        )
        
        category_responses = []
        for category in categories:
            category_responses.append(CapabilityCategoryResponse(
                id=str(category.id),
                name=category.name,
                code=category.code,
                description=category.description,
                icon=category.icon,
                color=category.color,
                is_active=category.is_active,
                created_at=category.created_at.isoformat(),
                updated_at=category.updated_at.isoformat()
            ))
        
        return CapabilityCategoryListResponse(
            categories=category_responses,
            total_count=len(category_responses)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve capability categories"
        )


@router.get("/stats", response_model=CapabilityCategoryStatsResponse)
async def get_capability_category_statistics(
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get capability category statistics
    
    All authenticated users can read capability category statistics.
    """
    try:
        service = CapabilityCategoryService(db)
        stats = await service.get_category_statistics()
        
        return CapabilityCategoryStatsResponse(**stats)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve capability category statistics"
        )


@router.get("/{category_id}", response_model=CapabilityCategoryResponse)
async def get_capability_category(
    category_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get capability category by ID
    
    All authenticated users can read capability categories.
    """
    try:
        service = CapabilityCategoryService(db)
        category = await service.get_category_by_id(UUID(category_id))
        
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Capability category not found"
            )
        
        return CapabilityCategoryResponse(
            id=str(category.id),
            name=category.name,
            code=category.code,
            description=category.description,
            icon=category.icon,
            color=category.color,
            is_active=category.is_active,
            created_at=category.created_at.isoformat(),
            updated_at=category.updated_at.isoformat()
        )
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid category ID"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve capability category"
        )


@router.put("/{category_id}", response_model=CapabilityCategoryResponse)
async def update_capability_category(
    category_id: str,
    request: CapabilityCategoryUpdateRequest,
    current_user: UserContext = Depends(require_admin_or_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Update capability category
    
    Only admin and super_admin can update capability categories.
    """
    try:
        service = CapabilityCategoryService(db)
        
        category = await service.update_category(
            category_id=UUID(category_id),
            name=request.name,
            description=request.description,
            icon=request.icon,
            color=request.color,
            is_active=request.is_active
        )
        
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Capability category not found"
            )
        
        return CapabilityCategoryResponse(
            id=str(category.id),
            name=category.name,
            code=category.code,
            description=category.description,
            icon=category.icon,
            color=category.color,
            is_active=category.is_active,
            created_at=category.created_at.isoformat(),
            updated_at=category.updated_at.isoformat()
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update capability category"
        )


@router.delete("/{category_id}")
async def delete_capability_category(
    category_id: str,
    current_user: UserContext = Depends(require_admin_or_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete capability category
    
    Only admin and super_admin can delete capability categories.
    Soft delete by setting is_active = false.
    """
    try:
        service = CapabilityCategoryService(db)
        
        success = await service.delete_category(UUID(category_id))
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Capability category not found"
            )
        
        return {"message": "Capability category deleted successfully"}
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete capability category"
        )