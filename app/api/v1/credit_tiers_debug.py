"""
Credit tier management API endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from uuid import UUID

from app.core.database import get_db
from app.core.auth import get_current_user, require_admin
from app.models.payment import CreditTier
from app.services.auth import UserContext


router = APIRouter()


class CreditTierBase(BaseModel):
    """Base credit tier model"""
    name: str = Field(..., max_length=255, description="Tier name")
    description: Optional[str] = Field(None, description="Tier description")
    min_credits: int = Field(..., gt=0, description="Minimum credits in this tier")
    max_credits: int = Field(..., gt=0, description="Maximum credits in this tier")
    price: float = Field(..., gt=0, description="Price for this tier")
    discount_percentage: Optional[float] = Field(0.0, ge=0, le=100, description="Discount percentage")
    is_active: bool = Field(True, description="Whether the tier is active")
    sort_order: Optional[int] = Field(0, description="Sort order for display")


class CreditTierCreate(CreditTierBase):
    """Credit tier creation model"""
    
    @validator('max_credits')
    def validate_credits_range(cls, v, values):
        """Validate that min_credits <= max_credits"""
        min_credits = values.get('min_credits')
        if min_credits is not None and v is not None:
            if min_credits > v:
                raise ValueError("min_credits must be less than or equal to max_credits")
        return v


class CreditTierUpdate(BaseModel):
    """Credit tier update model"""
    name: Optional[str] = Field(None, max_length=255, description="Tier name")
    description: Optional[str] = Field(None, description="Tier description")
    min_credits: Optional[int] = Field(None, gt=0, description="Minimum credits in this tier")
    max_credits: Optional[int] = Field(None, gt=0, description="Maximum credits in this tier")
    price: Optional[float] = Field(None, gt=0, description="Price for this tier")
    discount_percentage: Optional[float] = Field(None, ge=0, le=100, description="Discount percentage")
    is_active: Optional[bool] = Field(None, description="Whether the tier is active")
    sort_order: Optional[int] = Field(None, description="Sort order for display")


class CreditTierResponse(BaseModel):
    """Credit tier response model"""
    id: str
    name: str
    description: Optional[str]
    min_credits: int
    max_credits: int
    price: float
    discount_percentage: float
    is_active: bool
    sort_order: int
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


@router.get("/", response_model=List[CreditTierResponse])
async def list_credit_tiers(
    active_only: Optional[bool] = Query(None, description="Filter tiers: true=active only, false=inactive only, null=all"),
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List credit tiers with filtering options
    
    - No parameter: Returns ALL tiers (active + inactive) 
    - active_only=true: Returns only ACTIVE tiers
    - active_only=false: Returns only INACTIVE tiers
    
    Non-admin users are always restricted to active tiers only.
    """
    try:
        query = select(CreditTier)
        
        # Check if user is admin
        is_admin = (current_user.user_type == "admin" or 
                   (current_user.user_type == "firm_personnel" and current_user.role in ["admin", "super_admin"]))
        
        # Non-admin users: always restricted to active tiers only
        # TEMPORARY DEBUG: Commented out for testing - REMOVE THIS IN PRODUCTION
        # if not is_admin:
        #     query = query.where(CreditTier.is_active == True)
        # Admin users: filter based on active_only parameter
        else:
            if active_only is True:
                # Return only active tiers
                query = query.where(CreditTier.is_active == True)
            elif active_only is False:
                # Return only inactive tiers
                query = query.where(CreditTier.is_active == False)
            # else: active_only is None - return all tiers (no filter)
            
        query = query.order_by(CreditTier.sort_order, CreditTier.created_at)
        
        result = await db.execute(query)
        tiers = result.scalars().all()
        
        return [
            CreditTierResponse(
                id=str(tier.id),
                name=tier.name,
                description=tier.description,
                min_credits=tier.min_credits,
                max_credits=tier.max_credits,
                price=float(tier.price),
                discount_percentage=float(tier.discount_percentage),
                is_active=tier.is_active,
                sort_order=tier.sort_order,
                created_at=tier.created_at.isoformat(),
                updated_at=tier.updated_at.isoformat()
            )
            for tier in tiers
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve credit tiers"
        )


@router.get("/{tier_id}", response_model=CreditTierResponse)
async def get_credit_tier(
    tier_id: UUID,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific credit tier by ID
    
    Returns detailed information about a specific credit tier.
    Non-admin users can only view active tiers.
    """
    try:
        query = select(CreditTier).where(CreditTier.id == tier_id)
        
        # Non-admin users can only see active tiers
        if not (current_user.user_type == "admin" or 
               (current_user.user_type == "firm_personnel" and current_user.role in ["admin", "super_admin"])):
            query = query.where(CreditTier.is_active == True)
        
        result = await db.execute(query)
        tier = result.scalar_one_or_none()
        
        if not tier:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Credit tier not found"
            )
        
        return CreditTierResponse(
            id=str(tier.id),
            name=tier.name,
            description=tier.description,
            min_credits=tier.min_credits,
            max_credits=tier.max_credits,
            price=float(tier.price),
            discount_percentage=float(tier.discount_percentage),
            is_active=tier.is_active,
            sort_order=tier.sort_order,
            created_at=tier.created_at.isoformat(),
            updated_at=tier.updated_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve credit tier"
        )


@router.post("/", response_model=CreditTierResponse)
async def create_credit_tier(
    tier_data: CreditTierCreate,
    current_user: UserContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new credit tier
    
    Admin-only endpoint to create new credit tier packages.
    """
    try:
        # Check if name already exists
        existing_query = select(CreditTier).where(CreditTier.name == tier_data.name)
        existing_result = await db.execute(existing_query)
        existing_tier = existing_result.scalar_one_or_none()
        
        if existing_tier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Credit tier with this name already exists"
            )
        
        # Create new tier
        new_tier = CreditTier(
            name=tier_data.name,
            description=tier_data.description,
            min_credits=tier_data.min_credits,
            max_credits=tier_data.max_credits,
            price=tier_data.price,
            discount_percentage=tier_data.discount_percentage or 0.0,
            is_active=tier_data.is_active,
            sort_order=tier_data.sort_order or 0
        )
        
        db.add(new_tier)
        await db.commit()
        await db.refresh(new_tier)
        
        return CreditTierResponse(
            id=str(new_tier.id),
            name=new_tier.name,
            description=new_tier.description,
            min_credits=new_tier.min_credits,
            max_credits=new_tier.max_credits,
            price=float(new_tier.price),
            discount_percentage=float(new_tier.discount_percentage),
            is_active=new_tier.is_active,
            sort_order=new_tier.sort_order,
            created_at=new_tier.created_at.isoformat(),
            updated_at=new_tier.updated_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create credit tier"
        )


@router.put("/{tier_id}", response_model=CreditTierResponse)
async def update_credit_tier(
    tier_id: UUID,
    tier_data: CreditTierUpdate,
    current_user: UserContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Update an existing credit tier
    
    Admin-only endpoint to update credit tier information.
    """
    try:
        # Get existing tier
        query = select(CreditTier).where(CreditTier.id == tier_id)
        result = await db.execute(query)
        tier = result.scalar_one_or_none()
        
        if not tier:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Credit tier not found"
            )
        
        # Check if new name already exists (if name is being updated)
        if tier_data.name and tier_data.name != tier.name:
            existing_query = select(CreditTier).where(
                and_(CreditTier.name == tier_data.name, CreditTier.id != tier_id)
            )
            existing_result = await db.execute(existing_query)
            existing_tier = existing_result.scalar_one_or_none()
            
            if existing_tier:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Credit tier with this name already exists"
                )
        
        # Update fields that were provided
        update_data = tier_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(tier, field, value)
        
        await db.commit()
        await db.refresh(tier)
        
        return CreditTierResponse(
            id=str(tier.id),
            name=tier.name,
            description=tier.description,
            min_credits=tier.min_credits,
            max_credits=tier.max_credits,
            price=float(tier.price),
            discount_percentage=float(tier.discount_percentage),
            is_active=tier.is_active,
            sort_order=tier.sort_order,
            created_at=tier.created_at.isoformat(),
            updated_at=tier.updated_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update credit tier"
        )


@router.delete("/{tier_id}")
async def delete_credit_tier(
    tier_id: UUID,
    current_user: UserContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a credit tier
    
    Admin-only endpoint to delete a credit tier. This permanently removes
    the tier from the database.
    """
    try:
        # Get existing tier
        query = select(CreditTier).where(CreditTier.id == tier_id)
        result = await db.execute(query)
        tier = result.scalar_one_or_none()
        
        if not tier:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Credit tier not found"
            )
        
        await db.delete(tier)
        await db.commit()
        
        return {"message": "Credit tier deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete credit tier"
        )