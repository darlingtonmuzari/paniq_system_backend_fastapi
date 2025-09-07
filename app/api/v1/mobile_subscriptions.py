"""
Mobile subscription management API endpoints with attestation
These endpoints are specifically for mobile apps and require attestation
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, validator
from uuid import UUID

from app.core.database import get_db
from app.services.subscription import SubscriptionService
from app.core.auth import get_current_registered_user
from app.services.auth import UserContext

router = APIRouter()


class SubscriptionPurchaseRequest(BaseModel):
    """Subscription purchase request model"""
    product_id: str
    payment_method: Optional[str] = "credit_card"
    payment_token: Optional[str] = None
    
    @validator('product_id')
    def validate_product_id(cls, v):
        try:
            UUID(v)
        except ValueError:
            raise ValueError('Invalid product ID format')
        return v


class StoredSubscriptionResponse(BaseModel):
    """Stored subscription response model"""
    id: str
    product_id: str
    product_name: str
    product_description: Optional[str]
    product_price: float
    product_max_users: int
    firm_name: str
    is_applied: bool
    applied_to_group_id: Optional[str] = None
    purchased_at: str
    applied_at: Optional[str] = None
    
    class Config:
        from_attributes = True


class SubscriptionApplicationRequest(BaseModel):
    """Subscription application request model"""
    subscription_id: str
    group_id: str
    
    @validator('subscription_id', 'group_id')
    def validate_ids(cls, v):
        try:
            UUID(v)
        except ValueError:
            raise ValueError('Invalid ID format')
        return v


class SubscriptionStatusResponse(BaseModel):
    """Subscription status response model"""
    group_id: str
    is_active: bool
    is_expired: bool
    expires_at: Optional[str] = None
    days_remaining: int
    subscription_id: Optional[str] = None


class ActiveSubscriptionResponse(BaseModel):
    """Active subscription response model"""
    group_id: str
    group_name: str
    group_address: str
    mobile_numbers_count: int
    is_active: bool
    is_expired: bool
    expires_at: Optional[str] = None
    days_remaining: int
    subscription_id: Optional[str] = None


class AlternativeFirmResponse(BaseModel):
    """Alternative firm response model"""
    firm_id: str
    firm_name: str
    coverage_area_name: str


class CoverageValidationRequest(BaseModel):
    """Coverage validation request model"""
    latitude: float
    longitude: float
    
    @validator('latitude')
    def validate_latitude(cls, v):
        if not -90 <= v <= 90:
            raise ValueError('Latitude must be between -90 and 90')
        return v
    
    @validator('longitude')
    def validate_longitude(cls, v):
        if not -180 <= v <= 180:
            raise ValueError('Longitude must be between -180 and 180')
        return v


@router.get("/products", response_model=List[Dict[str, Any]])
async def get_available_products(
    current_user: UserContext = Depends(get_current_registered_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all available subscription products (mobile endpoint with attestation)
    
    Returns all active subscription products from approved security firms
    that users can purchase.
    """
    try:
        subscription_service = SubscriptionService(db)
        products = await subscription_service.get_active_products()
        
        product_list = []
        for product in products:
            product_list.append({
                "id": str(product.id),
                "name": product.name,
                "description": product.description,
                "price": float(product.price),
                "max_users": product.max_users,
                "firm_id": str(product.firm_id),
                "firm_name": product.firm.name if product.firm else "Unknown",
                "created_at": product.created_at.isoformat()
            })
        
        return product_list
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve available products"
        )


@router.post("/purchase", response_model=StoredSubscriptionResponse)
async def purchase_subscription(
    request: SubscriptionPurchaseRequest,
    current_user: UserContext = Depends(get_current_registered_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Purchase a subscription product (mobile endpoint with attestation)
    
    Purchases a subscription product and stores it in the user's profile.
    The subscription is not automatically applied to any group.
    """
    try:
        subscription_service = SubscriptionService(db)
        
        # Prepare payment data (for future payment processing)
        payment_data = {
            "method": request.payment_method,
            "token": request.payment_token
        } if request.payment_token else None
        
        stored_subscription = await subscription_service.purchase_subscription(
            user_id=current_user.user_id,
            product_id=request.product_id,
            payment_data=payment_data
        )
        
        # Get product and firm details for response
        product = await subscription_service.get_product_by_id(request.product_id)
        
        return StoredSubscriptionResponse(
            id=str(stored_subscription.id),
            product_id=str(stored_subscription.product_id),
            product_name=product.name,
            product_description=product.description,
            product_price=float(product.price),
            product_max_users=product.max_users,
            firm_name=product.firm.name if product.firm else "Unknown",
            is_applied=stored_subscription.is_applied,
            applied_to_group_id=str(stored_subscription.applied_to_group_id) if stored_subscription.applied_to_group_id else None,
            purchased_at=stored_subscription.purchased_at.isoformat(),
            applied_at=stored_subscription.applied_at.isoformat() if stored_subscription.applied_at else None
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to purchase subscription"
        )


@router.get("/stored", response_model=List[StoredSubscriptionResponse])
async def get_stored_subscriptions(
    include_applied: bool = False,
    current_user: UserContext = Depends(get_current_registered_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's stored subscriptions (mobile endpoint with attestation)
    
    Returns all stored subscriptions for the current user. By default,
    only returns unapplied subscriptions.
    """
    try:
        subscription_service = SubscriptionService(db)
        stored_subscriptions = await subscription_service.get_user_stored_subscriptions(
            user_id=current_user.user_id,
            include_applied=include_applied
        )
        
        result = []
        for stored_subscription in stored_subscriptions:
            product = stored_subscription.product
            result.append(StoredSubscriptionResponse(
                id=str(stored_subscription.id),
                product_id=str(stored_subscription.product_id),
                product_name=product.name,
                product_description=product.description,
                product_price=float(product.price),
                product_max_users=product.max_users,
                firm_name=product.firm.name if product.firm else "Unknown",
                is_applied=stored_subscription.is_applied,
                applied_to_group_id=str(stored_subscription.applied_to_group_id) if stored_subscription.applied_to_group_id else None,
                purchased_at=stored_subscription.purchased_at.isoformat(),
                applied_at=stored_subscription.applied_at.isoformat() if stored_subscription.applied_at else None
            ))
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve stored subscriptions"
        )


@router.post("/apply", response_model=Dict[str, Any])
async def apply_subscription_to_group(
    request: SubscriptionApplicationRequest,
    current_user: UserContext = Depends(get_current_registered_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Apply stored subscription to a group (mobile endpoint with attestation)
    
    Applies a stored subscription to a user group. Validates that the group
    location is within the security firm's coverage area.
    """
    try:
        subscription_service = SubscriptionService(db)
        
        success = await subscription_service.apply_subscription_to_group(
            user_id=current_user.user_id,
            subscription_id=request.subscription_id,
            group_id=request.group_id
        )
        
        if success:
            # Get updated subscription status
            status_info = await subscription_service.validate_subscription_status(request.group_id)
            return {
                "message": "Subscription applied successfully",
                "subscription_status": status_info
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to apply subscription"
            )
        
    except ValueError as e:
        if "coverage area" in str(e).lower():
            # Get alternative firms for better error response
            from app.models.user import UserGroup
            group = await db.get(UserGroup, request.group_id)
            if group:
                alternatives = await subscription_service.get_alternative_firms_for_location(
                    group.latitude, group.longitude
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": str(e),
                        "alternative_firms": alternatives
                    }
                )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to apply subscription to group"
        )


@router.get("/active", response_model=List[ActiveSubscriptionResponse])
async def get_active_subscriptions(
    current_user: UserContext = Depends(get_current_registered_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's active subscriptions (mobile endpoint with attestation)
    
    Returns all groups with active (non-expired) subscriptions for the current user.
    """
    try:
        subscription_service = SubscriptionService(db)
        active_subscriptions = await subscription_service.get_group_active_subscriptions(
            user_id=current_user.user_id
        )
        
        result = []
        for subscription in active_subscriptions:
            result.append(ActiveSubscriptionResponse(**subscription))
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve active subscriptions"
        )


@router.get("/groups/{group_id}/status", response_model=SubscriptionStatusResponse)
async def get_group_subscription_status(
    group_id: str,
    current_user: UserContext = Depends(get_current_registered_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get subscription status for a specific group (mobile endpoint with attestation)
    
    Returns detailed subscription status information for the specified group.
    """
    try:
        # Verify group belongs to user
        from app.models.user import UserGroup
        group = await db.get(UserGroup, group_id)
        if not group or str(group.user_id) != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Group not found or not authorized"
            )
        
        subscription_service = SubscriptionService(db)
        status_info = await subscription_service.validate_subscription_status(group_id)
        
        return SubscriptionStatusResponse(**status_info)
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve subscription status"
        )


@router.post("/validate-coverage", response_model=List[AlternativeFirmResponse])
async def validate_coverage_and_get_alternatives(
    request: CoverageValidationRequest,
    current_user: UserContext = Depends(get_current_registered_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Validate coverage and get alternative firms (mobile endpoint with attestation)
    
    Returns security firms that provide coverage for the specified location.
    Useful for users to check coverage before creating groups or applying subscriptions.
    """
    try:
        subscription_service = SubscriptionService(db)
        alternative_firms = await subscription_service.get_alternative_firms_for_location(
            latitude=request.latitude,
            longitude=request.longitude
        )
        
        result = []
        for firm in alternative_firms:
            result.append(AlternativeFirmResponse(**firm))
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate coverage"
        )