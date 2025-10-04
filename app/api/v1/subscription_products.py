"""
Subscription product management API endpoints
"""
from typing import List, Optional, Dict, Any
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user, require_firm_admin
from app.services.auth import UserContext
from app.services.subscription import SubscriptionService
from app.services.credit import InsufficientCreditsError
from app.models.subscription import SubscriptionProduct


router = APIRouter()


class ProductCreateRequest(BaseModel):
    """Product creation request model"""
    name: str = Field(..., min_length=1, max_length=255, description="Product name")
    description: Optional[str] = Field(None, max_length=1000, description="Product description")
    max_users: int = Field(..., gt=0, description="Maximum number of users")
    price: Decimal = Field(..., ge=0, description="Product price")
    credit_cost: int = Field(..., gt=0, description="Credits deducted from firm when users subscribe to this product")
    
    @validator('price')
    def validate_price(cls, v):
        if v < 0:
            raise ValueError("Price cannot be negative")
        return v


class ProductUpdateRequest(BaseModel):
    """Product update request model"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Product name")
    description: Optional[str] = Field(None, max_length=1000, description="Product description")
    max_users: Optional[int] = Field(None, gt=0, description="Maximum number of users")
    price: Optional[Decimal] = Field(None, ge=0, description="Product price")
    is_active: Optional[bool] = Field(None, description="Whether the product is active")
    
    @validator('price')
    def validate_price(cls, v):
        if v is not None and v < 0:
            raise ValueError("Price cannot be negative")
        return v


class ProductResponse(BaseModel):
    """Product response model"""
    id: str
    firm_id: str
    name: str
    description: Optional[str]
    max_users: int
    price: float
    credit_cost: int
    is_active: bool
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    """Product list response model"""
    products: List[ProductResponse]
    total_count: int


class ProductStatisticsResponse(BaseModel):
    """Product statistics response model"""
    product_id: str
    product_name: str
    total_purchases: int
    applied_subscriptions: int
    pending_subscriptions: int
    total_revenue: float
    price: float
    max_users: int
    is_active: bool


@router.post("/", response_model=ProductResponse)
async def create_product(
    request: ProductCreateRequest,
    current_user: UserContext = Depends(require_firm_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new subscription product
    
    Creates a subscription product for a security firm. No credits are required
    for product creation. Credits will be deducted from the firm's balance when
    users subscribe to this product.
    """
    try:
        subscription_service = SubscriptionService(db)
        product = await subscription_service.create_product(
            firm_id=str(current_user.firm_id),
            name=request.name,
            description=request.description,
            max_users=request.max_users,
            price=request.price,
            credit_cost=request.credit_cost
        )
        
        return ProductResponse(
            id=str(product.id),
            firm_id=str(product.firm_id),
            name=product.name,
            description=product.description,
            max_users=product.max_users,
            price=float(product.price),
            credit_cost=product.credit_cost,
            is_active=product.is_active,
            created_at=product.created_at.isoformat(),
            updated_at=product.updated_at.isoformat()
        )
        
    except InsufficientCreditsError as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create subscription product"
        )


@router.get("/my-products", response_model=ProductListResponse)
async def get_my_products(
    include_inactive: bool = False,
    current_user: UserContext = Depends(require_firm_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all products for the current firm admin's firm
    
    Returns a list of subscription products created by the current firm admin's
    security firm. Can optionally include inactive products.
    """
    try:
        subscription_service = SubscriptionService(db)
        products = await subscription_service.get_firm_products(
            firm_id=str(current_user.firm_id),
            include_inactive=include_inactive
        )
        
        # Handle empty results gracefully
        if not products:
            return ProductListResponse(
                products=[],
                total_count=0
            )
        
        product_responses = []
        for product in products:
            product_responses.append(ProductResponse(
                id=str(product.id),
                firm_id=str(product.firm_id),
                name=product.name,
                description=product.description,
                max_users=product.max_users,
                price=float(product.price),
                credit_cost=product.credit_cost,
                is_active=product.is_active,
                created_at=product.created_at.isoformat(),
                updated_at=product.updated_at.isoformat()
            ))
        
        return ProductListResponse(
            products=product_responses,
            total_count=len(product_responses)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve firm products"
        )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str,
    current_user: UserContext = Depends(require_firm_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get subscription product by ID
    
    Returns detailed information about a specific subscription product
    including pricing, user limits, and availability status.
    """
    try:
        subscription_service = SubscriptionService(db)
        product = await subscription_service.get_product_by_id(product_id)
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription product not found"
            )
        
        # Ensure firm admin can only view their own firm's products
        if str(current_user.firm_id) != str(product.firm_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view products from your own firm"
            )
        
        return ProductResponse(
            id=str(product.id),
            firm_id=str(product.firm_id),
            name=product.name,
            description=product.description,
            max_users=product.max_users,
            price=float(product.price),
            credit_cost=product.credit_cost,
            is_active=product.is_active,
            created_at=product.created_at.isoformat(),
            updated_at=product.updated_at.isoformat()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve subscription product"
        )


@router.get("/firm/{firm_id}", response_model=ProductListResponse)
async def get_firm_products(
    firm_id: str,
    include_inactive: bool = False,
    current_user: UserContext = Depends(require_firm_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all products for a security firm
    
    Returns a list of subscription products created by the specified
    security firm. Can optionally include inactive products.
    """
    # Ensure firm admin can only view their own firm's products
    if str(current_user.firm_id) != firm_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view products from your own firm"
        )
    
    try:
        subscription_service = SubscriptionService(db)
        products = await subscription_service.get_firm_products(
            firm_id=firm_id,
            include_inactive=include_inactive
        )
        
        # Handle empty results gracefully
        if not products:
            return ProductListResponse(
                products=[],
                total_count=0
            )
        
        product_responses = []
        for product in products:
            product_responses.append(ProductResponse(
                id=str(product.id),
                firm_id=str(product.firm_id),
                name=product.name,
                description=product.description,
                max_users=product.max_users,
                price=float(product.price),
                credit_cost=product.credit_cost,
                is_active=product.is_active,
                created_at=product.created_at.isoformat(),
                updated_at=product.updated_at.isoformat()
            ))
        
        return ProductListResponse(
            products=product_responses,
            total_count=len(product_responses)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve firm products"
        )


@router.get("/", response_model=ProductListResponse)
async def get_active_products(
    db: AsyncSession = Depends(get_db)
):
    """
    Get all active subscription products
    
    Returns a list of all active subscription products from all security
    firms, sorted by price. Used by registered users to browse available
    subscription options.
    """
    try:
        subscription_service = SubscriptionService(db)
        products = await subscription_service.get_active_products()
        
        # Handle empty results gracefully
        if not products:
            return ProductListResponse(
                products=[],
                total_count=0
            )
        
        product_responses = []
        for product in products:
            product_responses.append(ProductResponse(
                id=str(product.id),
                firm_id=str(product.firm_id),
                name=product.name,
                description=product.description,
                max_users=product.max_users,
                price=float(product.price),
                credit_cost=product.credit_cost,
                is_active=product.is_active,
                created_at=product.created_at.isoformat(),
                updated_at=product.updated_at.isoformat()
            ))
        
        return ProductListResponse(
            products=product_responses,
            total_count=len(product_responses)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve active products"
        )


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    request: ProductUpdateRequest,
    current_user: UserContext = Depends(require_firm_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Update subscription product
    
    Updates the specified subscription product with new information.
    Only non-null fields in the request will be updated.
    """
    try:
        subscription_service = SubscriptionService(db)
        
        # First get the product to check ownership
        existing_product = await subscription_service.get_product_by_id(product_id)
        if not existing_product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription product not found"
            )
        
        # Ensure firm admin can only update their own firm's products
        if str(current_user.firm_id) != str(existing_product.firm_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update products from your own firm"
            )
        
        product = await subscription_service.update_product(
            product_id=product_id,
            name=request.name,
            description=request.description,
            max_users=request.max_users,
            price=request.price,
            is_active=request.is_active
        )
        
        return ProductResponse(
            id=str(product.id),
            firm_id=str(product.firm_id),
            name=product.name,
            description=product.description,
            max_users=product.max_users,
            price=float(product.price),
            credit_cost=product.credit_cost,
            is_active=product.is_active,
            created_at=product.created_at.isoformat(),
            updated_at=product.updated_at.isoformat()
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update subscription product"
        )


@router.delete("/{product_id}")
async def delete_product(
    product_id: str,
    current_user: UserContext = Depends(require_firm_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete subscription product
    
    Permanently deletes the specified subscription product. This operation
    is only allowed if the product has never been used in the system (no subscriptions).
    """
    try:
        subscription_service = SubscriptionService(db)
        
        # First get the product to check ownership
        existing_product = await subscription_service.get_product_by_id(product_id)
        if not existing_product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription product not found"
            )
        
        # Ensure firm admin can only delete their own firm's products
        if str(current_user.firm_id) != str(existing_product.firm_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete products from your own firm"
            )
        
        await subscription_service.delete_product(product_id)
        
        return {"message": "Subscription product deleted successfully"}
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete subscription product"
        )


@router.get("/{product_id}/statistics", response_model=ProductStatisticsResponse)
async def get_product_statistics(
    product_id: str,
    current_user: UserContext = Depends(require_firm_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get subscription product statistics
    
    Returns detailed statistics for the specified subscription product
    including purchase counts, revenue, and usage metrics.
    """
    try:
        subscription_service = SubscriptionService(db)
        
        # First get the product to check ownership
        existing_product = await subscription_service.get_product_by_id(product_id)
        if not existing_product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription product not found"
            )
        
        # Ensure firm admin can only view statistics for their own firm's products
        if str(current_user.firm_id) != str(existing_product.firm_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view statistics for products from your own firm"
            )
        
        stats = await subscription_service.get_product_statistics(product_id)
        
        return ProductStatisticsResponse(**stats)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve product statistics"
        )