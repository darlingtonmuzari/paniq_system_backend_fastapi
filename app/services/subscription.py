"""
Subscription product management service
"""
from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func
from sqlalchemy.orm import selectinload
from geoalchemy2.functions import ST_Within, ST_GeomFromText

from app.models.security_firm import SecurityFirm, CoverageArea
from app.models.subscription import SubscriptionProduct, CreditTransaction, StoredSubscription
from app.models.user import RegisteredUser, UserGroup
from app.services.credit import CreditService, InsufficientCreditsError
from app.core.cache import cache_result, cache_invalidate, invalidate_user_cache, invalidate_firm_cache


class SubscriptionService:
    """Service for managing subscription products"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.credit_service = CreditService(db)
    
    async def create_product(
        self,
        firm_id: str,
        name: str,
        description: Optional[str],
        max_users: int,
        price: Decimal,
        credit_cost: int
    ) -> SubscriptionProduct:
        """
        Create a new subscription product for a security firm
        
        Args:
            firm_id: Security firm ID
            name: Product name
            description: Product description
            max_users: Maximum number of users allowed
            price: Product price
            credit_cost: Number of credits that will be deducted when users subscribe to this product
            
        Returns:
            Created subscription product
        """
        # Verify firm exists and is approved
        firm = await self.db.get(SecurityFirm, firm_id)
        if not firm:
            raise ValueError("Security firm not found")
        
        if firm.verification_status != "approved":
            raise ValueError("Security firm must be approved to create products")
        
        # Validate input parameters
        if max_users <= 0:
            raise ValueError("Maximum users must be greater than 0")
        
        if price < 0:
            raise ValueError("Price cannot be negative")
        
        if credit_cost <= 0:
            raise ValueError("Credit cost must be greater than 0")
        
        # Create the product (no credit check required for product creation)
        product = SubscriptionProduct(
            firm_id=firm_id,
            name=name,
            description=description,
            max_users=max_users,
            price=price,
            credit_cost=credit_cost,
            is_active=True
        )
        
        self.db.add(product)
        await self.db.commit()
        await self.db.refresh(product)
        
        return product
    
    @cache_result(expire=3600, key_prefix="product_by_id")
    async def get_product_by_id(self, product_id: str) -> Optional[SubscriptionProduct]:
        """
        Get subscription product by ID
        
        Args:
            product_id: Product ID
            
        Returns:
            Subscription product or None if not found
        """
        result = await self.db.execute(
            select(SubscriptionProduct)
            .options(selectinload(SubscriptionProduct.firm))
            .where(SubscriptionProduct.id == product_id)
        )
        return result.scalar_one_or_none()
    
    async def get_firm_products(
        self,
        firm_id: str,
        include_inactive: bool = False
    ) -> List[SubscriptionProduct]:
        """
        Get all products for a security firm
        
        Args:
            firm_id: Security firm ID
            include_inactive: Whether to include inactive products
            
        Returns:
            List of subscription products (empty list if none found)
        """
        query = select(SubscriptionProduct).where(SubscriptionProduct.firm_id == firm_id)
        
        if not include_inactive:
            query = query.where(SubscriptionProduct.is_active == True)
        
        query = query.order_by(desc(SubscriptionProduct.created_at))
        
        result = await self.db.execute(query)
        products = result.scalars().all()
        return products if products else []
    
    @cache_result(expire=1800, key_prefix="active_products")
    async def get_active_products(self) -> List[SubscriptionProduct]:
        """
        Get all active subscription products from all firms
        
        Returns:
            List of active subscription products (empty list if none found)
        """
        result = await self.db.execute(
            select(SubscriptionProduct)
            .options(selectinload(SubscriptionProduct.firm))
            .where(SubscriptionProduct.is_active == True)
            .order_by(SubscriptionProduct.price)
        )
        products = result.scalars().all()
        return products if products else []
    
    async def update_product(
        self,
        product_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        max_users: Optional[int] = None,
        price: Optional[Decimal] = None,
        is_active: Optional[bool] = None
    ) -> SubscriptionProduct:
        """
        Update an existing subscription product
        
        Args:
            product_id: Product ID
            name: New product name
            description: New product description
            max_users: New maximum users
            price: New product price
            is_active: New active status
            
        Returns:
            Updated subscription product
        """
        product = await self.db.get(SubscriptionProduct, product_id)
        if not product:
            raise ValueError("Subscription product not found")
        
        # Validate updates
        if max_users is not None and max_users <= 0:
            raise ValueError("Maximum users must be greater than 0")
        
        if price is not None and price < 0:
            raise ValueError("Price cannot be negative")
        
        # Apply updates
        if name is not None:
            product.name = name
        
        if description is not None:
            product.description = description
        
        if max_users is not None:
            product.max_users = max_users
        
        if price is not None:
            product.price = price
        
        if is_active is not None:
            product.is_active = is_active
        
        await self.db.commit()
        await self.db.refresh(product)
        
        return product
    
    async def activate_product(self, product_id: str) -> SubscriptionProduct:
        """
        Activate a subscription product
        
        Args:
            product_id: Product ID
            
        Returns:
            Activated subscription product
        """
        product = await self.db.get(SubscriptionProduct, product_id)
        if not product:
            raise ValueError("Subscription product not found")
        
        product.is_active = True
        
        await self.db.commit()
        await self.db.refresh(product)
        
        return product
    
    async def deactivate_product(self, product_id: str) -> SubscriptionProduct:
        """
        Deactivate a subscription product
        
        Args:
            product_id: Product ID
            
        Returns:
            Deactivated subscription product
        """
        product = await self.db.get(SubscriptionProduct, product_id)
        if not product:
            raise ValueError("Subscription product not found")
        
        product.is_active = False
        
        await self.db.commit()
        await self.db.refresh(product)
        
        return product
    
    async def delete_product(self, product_id: str) -> bool:
        """
        Delete a subscription product
        
        Note: This should only be allowed if no active subscriptions exist
        
        Args:
            product_id: Product ID
            
        Returns:
            True if deleted successfully
        """
        product = await self.db.get(SubscriptionProduct, product_id)
        if not product:
            raise ValueError("Subscription product not found")
        
        # Check if there are any stored subscriptions using this product
        from app.models.subscription import StoredSubscription
        result = await self.db.execute(
            select(StoredSubscription).where(StoredSubscription.product_id == product_id)
        )
        existing_subscriptions = result.scalars().all()
        
        if existing_subscriptions:
            raise ValueError(
                f"Cannot delete product that has been used in the system. "
                f"This product has {len(existing_subscriptions)} subscription(s) associated with it."
            )
        
        await self.db.delete(product)
        await self.db.commit()
        
        return True
    
    async def get_product_statistics(self, product_id: str) -> Dict[str, Any]:
        """
        Get statistics for a subscription product
        
        Args:
            product_id: Product ID
            
        Returns:
            Product statistics including purchase count, revenue, etc.
        """
        product = await self.db.get(SubscriptionProduct, product_id)
        if not product:
            raise ValueError("Subscription product not found")
        
        # Get stored subscriptions count
        from app.models.subscription import StoredSubscription
        result = await self.db.execute(
            select(StoredSubscription).where(StoredSubscription.product_id == product_id)
        )
        stored_subscriptions = result.scalars().all()
        
        # Calculate statistics
        total_purchases = len(stored_subscriptions)
        applied_subscriptions = len([s for s in stored_subscriptions if s.is_applied])
        pending_subscriptions = total_purchases - applied_subscriptions
        total_revenue = float(product.price) * total_purchases
        
        return {
            "product_id": str(product.id),
            "product_name": product.name,
            "total_purchases": total_purchases,
            "applied_subscriptions": applied_subscriptions,
            "pending_subscriptions": pending_subscriptions,
            "total_revenue": total_revenue,
            "price": float(product.price),
            "max_users": product.max_users,
            "is_active": product.is_active
        }
    
    async def purchase_subscription(
        self,
        user_id: str,
        product_id: str,
        payment_data: Optional[Dict[str, Any]] = None
    ) -> StoredSubscription:
        """
        Purchase a subscription product for a registered user
        
        Args:
            user_id: Registered user ID
            product_id: Subscription product ID
            payment_data: Payment information (for future payment processing)
            
        Returns:
            Stored subscription
        """
        # Verify user exists
        user = await self.db.get(RegisteredUser, user_id)
        if not user:
            raise ValueError("User not found")
        
        if user.is_suspended:
            raise ValueError("User account is suspended")
        
        # Verify product exists and is active
        product = await self.db.get(SubscriptionProduct, product_id)
        if not product:
            raise ValueError("Subscription product not found")
        
        if not product.is_active:
            raise ValueError("Subscription product is not available for purchase")
        
        # Get the firm to check credit balance
        firm = await self.db.get(SecurityFirm, product.firm_id)
        if not firm:
            raise ValueError("Security firm not found")
        
        # Check if firm has sufficient credits for this subscription
        if firm.credit_balance < product.credit_cost:
            raise InsufficientCreditsError(
                f"Security firm has insufficient credits. Current balance: {firm.credit_balance}, Required: {product.credit_cost}"
            )
        
        # TODO: Process payment using payment_data
        # For now, we'll assume payment is successful
        
        # Deduct credits from firm balance when user subscribes
        await self.credit_service.deduct_credits(
            firm_id=str(product.firm_id),
            amount=product.credit_cost,
            description=f"User subscription - {product.name}",
            reference_id=f"subscription_{user_id}_{product_id}"
        )
        
        # Create stored subscription
        stored_subscription = StoredSubscription(
            user_id=user_id,
            product_id=product_id,
            is_applied=False,
            applied_to_group_id=None,
            purchased_at=datetime.utcnow()
        )
        
        self.db.add(stored_subscription)
        await self.db.commit()
        await self.db.refresh(stored_subscription)
        
        return stored_subscription
    
    @cache_result(expire=900, key_prefix="user_stored_subscriptions")
    async def get_user_stored_subscriptions(
        self,
        user_id: str,
        include_applied: bool = False
    ) -> List[StoredSubscription]:
        """
        Get stored subscriptions for a user
        
        Args:
            user_id: User ID
            include_applied: Whether to include already applied subscriptions
            
        Returns:
            List of stored subscriptions
        """
        query = select(StoredSubscription).options(
            selectinload(StoredSubscription.product).selectinload(SubscriptionProduct.firm)
        ).where(StoredSubscription.user_id == user_id)
        
        if not include_applied:
            query = query.where(StoredSubscription.is_applied == False)
        
        query = query.order_by(desc(StoredSubscription.purchased_at))
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def apply_subscription_to_group(
        self,
        user_id: str,
        subscription_id: str,
        group_id: str
    ) -> bool:
        """
        Apply a stored subscription to a user group
        
        Args:
            user_id: User ID
            subscription_id: Stored subscription ID
            group_id: User group ID
            
        Returns:
            True if successfully applied
        """
        # Verify stored subscription exists and belongs to user
        stored_subscription = await self.db.get(StoredSubscription, subscription_id)
        if not stored_subscription:
            raise ValueError("Stored subscription not found")
        
        if str(stored_subscription.user_id) != user_id:
            raise ValueError("Subscription does not belong to this user")
        
        if stored_subscription.is_applied:
            raise ValueError("Subscription has already been applied")
        
        # Verify group exists and belongs to user
        group = await self.db.get(UserGroup, group_id)
        if not group:
            raise ValueError("User group not found")
        
        if str(group.user_id) != user_id:
            raise ValueError("Group does not belong to this user")
        
        # Get product and firm information
        product = await self.db.get(SubscriptionProduct, stored_subscription.product_id)
        if not product:
            raise ValueError("Subscription product not found")
        
        # Verify group location is within firm's coverage area
        coverage_valid = await self._validate_group_coverage(group, str(product.firm_id))
        if not coverage_valid:
            raise ValueError("Group location is outside the security firm's coverage area")
        
        # Check if group already has an active subscription
        if group.subscription_expires_at and group.subscription_expires_at > datetime.utcnow():
            # Extend existing subscription by 1 month
            group.subscription_expires_at = group.subscription_expires_at + timedelta(days=30)
        else:
            # Create new subscription with 1 month expiry
            group.subscription_expires_at = datetime.utcnow() + timedelta(days=30)
        
        # Mark subscription as applied
        stored_subscription.is_applied = True
        stored_subscription.applied_to_group_id = group_id
        stored_subscription.applied_at = datetime.utcnow()
        
        # Update group subscription reference
        group.subscription_id = subscription_id
        
        await self.db.commit()
        
        # Invalidate user-related cache
        await invalidate_user_cache(user_id)
        
        return True
    
    async def _validate_group_coverage(self, group: UserGroup, firm_id: str) -> bool:
        """
        Validate that a group's location is within a firm's coverage area
        
        Args:
            group: User group
            firm_id: Security firm ID
            
        Returns:
            True if location is covered
        """
        # Get firm's active coverage areas only
        result = await self.db.execute(
            select(CoverageArea).where(
                and_(
                    CoverageArea.firm_id == firm_id,
                    CoverageArea.is_active == True
                )
            )
        )
        coverage_areas = result.scalars().all()
        
        if not coverage_areas:
            return False
        
        # Check if group location is within any active coverage area
        for coverage_area in coverage_areas:
            result = await self.db.execute(
                select(func.count()).where(
                    ST_Within(group.location, coverage_area.boundary)
                )
            )
            if result.scalar() > 0:
                return True
        
        return False
    
    async def get_alternative_firms_for_location(
        self,
        latitude: float,
        longitude: float
    ) -> List[Dict[str, Any]]:
        """
        Get alternative security firms that cover a specific location
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            
        Returns:
            List of firms with coverage for the location
        """
        point_wkt = f"POINT({longitude} {latitude})"
        
        result = await self.db.execute(
            select(SecurityFirm, CoverageArea).join(
                CoverageArea, SecurityFirm.id == CoverageArea.firm_id
            ).where(
                and_(
                    SecurityFirm.verification_status == "approved",
                    CoverageArea.is_active == True,
                    ST_Within(ST_GeomFromText(point_wkt, 4326), CoverageArea.boundary)
                )
            )
        )
        
        firms_data = result.all()
        
        alternative_firms = []
        for firm, coverage_area in firms_data:
            alternative_firms.append({
                "firm_id": str(firm.id),
                "firm_name": firm.name,
                "coverage_area_name": coverage_area.name
            })
        
        return alternative_firms
    
    async def validate_subscription_status(self, group_id: str) -> Dict[str, Any]:
        """
        Validate subscription status for a group
        
        Args:
            group_id: User group ID
            
        Returns:
            Subscription status information
        """
        group = await self.db.get(UserGroup, group_id)
        if not group:
            raise ValueError("User group not found")
        
        now = datetime.utcnow()
        is_active = False
        is_expired = True
        days_remaining = 0
        
        if group.subscription_expires_at:
            is_expired = group.subscription_expires_at <= now
            is_active = not is_expired
            if is_active:
                days_remaining = (group.subscription_expires_at - now).days
        
        return {
            "group_id": str(group.id),
            "is_active": is_active,
            "is_expired": is_expired,
            "expires_at": group.subscription_expires_at.isoformat() if group.subscription_expires_at else None,
            "days_remaining": days_remaining,
            "subscription_id": str(group.subscription_id) if group.subscription_id else None
        }
    
    async def get_group_active_subscriptions(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all active subscriptions for user's groups
        
        Args:
            user_id: User ID
            
        Returns:
            List of active group subscriptions
        """
        result = await self.db.execute(
            select(UserGroup).options(
                selectinload(UserGroup.mobile_numbers)
            ).where(
                and_(
                    UserGroup.user_id == user_id,
                    UserGroup.subscription_expires_at > datetime.utcnow()
                )
            ).order_by(UserGroup.subscription_expires_at)
        )
        
        groups = result.scalars().all()
        
        active_subscriptions = []
        for group in groups:
            subscription_status = await self.validate_subscription_status(str(group.id))
            active_subscriptions.append({
                "group_id": str(group.id),
                "group_name": group.name,
                "group_address": group.address,
                "mobile_numbers_count": len(group.mobile_numbers),
                **subscription_status
            })
        
        return active_subscriptions