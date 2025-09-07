"""
Prank detection and user fining service
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc, update
from sqlalchemy.orm import selectinload
import structlog

from app.core.exceptions import APIError, ErrorCodes
from app.models.user import RegisteredUser, UserFine
from app.models.emergency import RequestFeedback, PanicRequest
from app.models.subscription import StoredSubscription

logger = structlog.get_logger()


class PrankDetectionError(APIError):
    """Base prank detection error"""
    def __init__(self, error_code: str, message: str):
        super().__init__(error_code, message)


class UserNotFoundError(PrankDetectionError):
    """User not found error"""
    def __init__(self, message: str = "User not found"):
        super().__init__(ErrorCodes.REQUEST_NOT_FOUND, message)


class FineNotFoundError(PrankDetectionError):
    """Fine not found error"""
    def __init__(self, message: str = "Fine not found"):
        super().__init__(ErrorCodes.REQUEST_NOT_FOUND, message)


class PaymentProcessingError(PrankDetectionError):
    """Payment processing error"""
    def __init__(self, message: str = "Payment processing failed"):
        super().__init__("PAYMENT_001", message)


class PrankDetectionService:
    """Service for prank detection and user fining system"""
    
    # Fine calculation constants
    BASE_FINE_AMOUNT = Decimal("50.00")  # Base fine for first prank
    FINE_MULTIPLIER = Decimal("1.5")     # Multiplier for subsequent pranks
    MAX_FINE_AMOUNT = Decimal("500.00")  # Maximum fine amount
    PERMANENT_BAN_THRESHOLD = 10         # Prank flags for permanent ban
    SUSPENSION_THRESHOLD = 5             # Prank flags for suspension
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def track_prank_accumulation(self, user_id: UUID) -> Dict[str, Any]:
        """
        Track prank flag accumulation for a user
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with prank tracking information
            
        Raises:
            UserNotFoundError: If user not found
        """
        logger.info("tracking_prank_accumulation", user_id=str(user_id))
        
        # Get user with current prank flags
        result = await self.db.execute(
            select(RegisteredUser).where(RegisteredUser.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise UserNotFoundError()
        
        # Get recent prank feedback (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        result = await self.db.execute(
            select(func.count(RequestFeedback.id)).select_from(RequestFeedback)
            .join(PanicRequest, RequestFeedback.request_id == PanicRequest.id)
            .join(RegisteredUser, PanicRequest.group_id.in_(
                select(RegisteredUser.groups.property.mapper.class_.id)
                .where(RegisteredUser.id == user_id)
            ))
            .where(
                and_(
                    RequestFeedback.is_prank == True,
                    RequestFeedback.created_at >= thirty_days_ago
                )
            )
        )
        recent_pranks = result.scalar() or 0
        
        # Calculate fine if needed
        fine_amount = None
        should_suspend = False
        should_ban = False
        
        if user.prank_flags >= self.PERMANENT_BAN_THRESHOLD:
            should_ban = True
        elif user.prank_flags >= self.SUSPENSION_THRESHOLD:
            should_suspend = True
            fine_amount = await self._calculate_fine_amount(user.prank_flags)
        elif user.prank_flags >= 3:  # Start fining after 3 pranks
            fine_amount = await self._calculate_fine_amount(user.prank_flags)
        
        tracking_info = {
            "user_id": str(user_id),
            "total_prank_flags": user.prank_flags,
            "recent_prank_flags": recent_pranks,
            "total_fines": float(user.total_fines),
            "is_suspended": user.is_suspended,
            "calculated_fine_amount": float(fine_amount) if fine_amount else None,
            "should_suspend": should_suspend,
            "should_ban": should_ban,
            "days_until_ban": max(0, self.PERMANENT_BAN_THRESHOLD - user.prank_flags) if not should_ban else 0
        }
        
        logger.info("prank_accumulation_tracked", **tracking_info)
        return tracking_info
    
    async def calculate_automatic_fine(self, user_id: UUID) -> Optional[UserFine]:
        """
        Calculate and create automatic fine based on prank frequency
        
        Args:
            user_id: User ID
            
        Returns:
            Created fine record or None if no fine needed
            
        Raises:
            UserNotFoundError: If user not found
        """
        logger.info("calculating_automatic_fine", user_id=str(user_id))
        
        # Get user
        result = await self.db.execute(
            select(RegisteredUser).where(RegisteredUser.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise UserNotFoundError()
        
        # Check if user should be fined
        if user.prank_flags < 3:
            logger.info("no_fine_needed", user_id=str(user_id), prank_flags=user.prank_flags)
            return None
        
        # Check if user already has an unpaid fine for current prank level
        result = await self.db.execute(
            select(UserFine).where(
                and_(
                    UserFine.user_id == user_id,
                    UserFine.is_paid == False,
                    UserFine.reason.contains(f"prank flags: {user.prank_flags}")
                )
            )
        )
        existing_fine = result.scalar_one_or_none()
        
        if existing_fine:
            logger.info("fine_already_exists", user_id=str(user_id), fine_id=str(existing_fine.id))
            return existing_fine
        
        # Calculate fine amount
        fine_amount = await self._calculate_fine_amount(user.prank_flags)
        
        # Create fine record
        fine = UserFine(
            user_id=user_id,
            amount=fine_amount,
            reason=f"Automatic fine for prank behavior - prank flags: {user.prank_flags}"
        )
        
        self.db.add(fine)
        
        # Update user's total fines
        user.total_fines += fine_amount
        
        await self.db.commit()
        await self.db.refresh(fine)
        
        logger.info(
            "automatic_fine_created",
            user_id=str(user_id),
            fine_id=str(fine.id),
            amount=float(fine_amount),
            prank_flags=user.prank_flags
        )
        
        return fine
    
    async def process_fine_payment(
        self,
        fine_id: UUID,
        payment_method: str,
        payment_reference: str
    ) -> UserFine:
        """
        Process fine payment
        
        Args:
            fine_id: Fine ID
            payment_method: Payment method (card, bank_transfer, etc.)
            payment_reference: Payment reference/transaction ID
            
        Returns:
            Updated fine record
            
        Raises:
            FineNotFoundError: If fine not found
            PaymentProcessingError: If payment processing fails
        """
        logger.info(
            "processing_fine_payment",
            fine_id=str(fine_id),
            payment_method=payment_method,
            payment_reference=payment_reference
        )
        
        # Get fine with user
        result = await self.db.execute(
            select(UserFine).options(
                selectinload(UserFine.user)
            ).where(UserFine.id == fine_id)
        )
        fine = result.scalar_one_or_none()
        
        if not fine:
            raise FineNotFoundError()
        
        if fine.is_paid:
            logger.warning("fine_already_paid", fine_id=str(fine_id))
            return fine
        
        # TODO: Integrate with actual payment gateway
        # For now, we'll simulate successful payment processing
        payment_successful = await self._process_payment_gateway(
            amount=fine.amount,
            payment_method=payment_method,
            payment_reference=payment_reference
        )
        
        if not payment_successful:
            raise PaymentProcessingError("Payment gateway rejected the transaction")
        
        # Mark fine as paid
        fine.is_paid = True
        fine.paid_at = datetime.utcnow()
        
        # If user was suspended due to unpaid fines, check if they can be unsuspended
        if fine.user.is_suspended:
            unpaid_fines = await self._get_unpaid_fines_count(fine.user_id)
            if unpaid_fines == 1:  # This was the last unpaid fine
                fine.user.is_suspended = False
                logger.info("user_unsuspended_after_payment", user_id=str(fine.user_id))
        
        await self.db.commit()
        await self.db.refresh(fine)
        
        logger.info(
            "fine_payment_processed",
            fine_id=str(fine_id),
            user_id=str(fine.user_id),
            amount=float(fine.amount),
            payment_reference=payment_reference
        )
        
        return fine
    
    async def suspend_account_for_unpaid_fines(self, user_id: UUID) -> bool:
        """
        Suspend user account for unpaid fines
        
        Args:
            user_id: User ID
            
        Returns:
            True if account was suspended, False if already suspended
            
        Raises:
            UserNotFoundError: If user not found
        """
        logger.info("suspending_account_for_unpaid_fines", user_id=str(user_id))
        
        # Get user
        result = await self.db.execute(
            select(RegisteredUser).where(RegisteredUser.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise UserNotFoundError()
        
        if user.is_suspended:
            logger.info("account_already_suspended", user_id=str(user_id))
            return False
        
        # Check for unpaid fines
        unpaid_fines_count = await self._get_unpaid_fines_count(user_id)
        
        if unpaid_fines_count == 0:
            logger.info("no_unpaid_fines", user_id=str(user_id))
            return False
        
        # Suspend account
        user.is_suspended = True
        
        await self.db.commit()
        
        logger.info(
            "account_suspended",
            user_id=str(user_id),
            unpaid_fines_count=unpaid_fines_count
        )
        
        return True
    
    async def create_permanent_ban(self, user_id: UUID, reason: str = None) -> bool:
        """
        Create permanent ban for repeat offenders
        
        Args:
            user_id: User ID
            reason: Optional ban reason
            
        Returns:
            True if user was banned, False if already banned
            
        Raises:
            UserNotFoundError: If user not found
        """
        logger.info("creating_permanent_ban", user_id=str(user_id), reason=reason)
        
        # Get user
        result = await self.db.execute(
            select(RegisteredUser).where(RegisteredUser.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise UserNotFoundError()
        
        # Check if user meets ban criteria
        if user.prank_flags < self.PERMANENT_BAN_THRESHOLD:
            logger.warning(
                "user_does_not_meet_ban_criteria",
                user_id=str(user_id),
                prank_flags=user.prank_flags,
                threshold=self.PERMANENT_BAN_THRESHOLD
            )
            return False
        
        # Suspend account (permanent ban is implemented as permanent suspension)
        if not user.is_suspended:
            user.is_suspended = True
        
        # Deactivate all user's subscriptions
        await self.db.execute(
            update(StoredSubscription)
            .where(StoredSubscription.user_id == user_id)
            .values(is_applied=False)
        )
        
        await self.db.commit()
        
        ban_reason = reason or f"Permanent ban for excessive prank behavior ({user.prank_flags} prank flags)"
        
        logger.info(
            "permanent_ban_created",
            user_id=str(user_id),
            prank_flags=user.prank_flags,
            reason=ban_reason
        )
        
        return True
    
    async def get_user_fines(
        self,
        user_id: UUID,
        include_paid: bool = True,
        limit: int = 50,
        offset: int = 0
    ) -> List[UserFine]:
        """
        Get user's fines
        
        Args:
            user_id: User ID
            include_paid: Whether to include paid fines
            limit: Maximum number of fines to return
            offset: Number of records to skip
            
        Returns:
            List of user fines
        """
        query = select(UserFine).where(UserFine.user_id == user_id)
        
        if not include_paid:
            query = query.where(UserFine.is_paid == False)
        
        query = query.order_by(desc(UserFine.created_at)).limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_fine_statistics(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get fine statistics
        
        Args:
            date_from: Optional start date filter
            date_to: Optional end date filter
            
        Returns:
            Dictionary with fine statistics
        """
        query = select(UserFine)
        
        if date_from:
            query = query.where(UserFine.created_at >= date_from)
        
        if date_to:
            query = query.where(UserFine.created_at <= date_to)
        
        result = await self.db.execute(query)
        fines = result.scalars().all()
        
        total_fines = len(fines)
        paid_fines = sum(1 for f in fines if f.is_paid)
        unpaid_fines = total_fines - paid_fines
        
        total_amount = sum(f.amount for f in fines)
        paid_amount = sum(f.amount for f in fines if f.is_paid)
        unpaid_amount = total_amount - paid_amount
        
        return {
            "total_fines": total_fines,
            "paid_fines": paid_fines,
            "unpaid_fines": unpaid_fines,
            "total_amount": float(total_amount),
            "paid_amount": float(paid_amount),
            "unpaid_amount": float(unpaid_amount),
            "payment_rate_percentage": round((paid_fines / total_fines * 100) if total_fines > 0 else 0, 2),
            "date_range": {
                "from": date_from.isoformat() if date_from else None,
                "to": date_to.isoformat() if date_to else None
            }
        }
    
    async def _calculate_fine_amount(self, prank_flags: int) -> Decimal:
        """
        Calculate fine amount based on prank flags
        
        Args:
            prank_flags: Number of prank flags
            
        Returns:
            Fine amount
        """
        if prank_flags < 3:
            return Decimal("0.00")
        
        # Calculate progressive fine: base_amount * (multiplier ^ (prank_flags - 3))
        fine_amount = self.BASE_FINE_AMOUNT * (self.FINE_MULTIPLIER ** (prank_flags - 3))
        
        # Cap at maximum fine amount
        return min(fine_amount, self.MAX_FINE_AMOUNT)
    
    async def _get_unpaid_fines_count(self, user_id: UUID) -> int:
        """
        Get count of unpaid fines for a user
        
        Args:
            user_id: User ID
            
        Returns:
            Number of unpaid fines
        """
        result = await self.db.execute(
            select(func.count(UserFine.id)).where(
                and_(
                    UserFine.user_id == user_id,
                    UserFine.is_paid == False
                )
            )
        )
        return result.scalar() or 0
    
    async def _process_payment_gateway(
        self,
        amount: Decimal,
        payment_method: str,
        payment_reference: str
    ) -> bool:
        """
        Process payment through payment gateway
        
        Args:
            amount: Payment amount
            payment_method: Payment method
            payment_reference: Payment reference
            
        Returns:
            True if payment successful, False otherwise
        """
        # TODO: Implement actual payment gateway integration
        # For now, simulate successful payment
        logger.info(
            "simulating_payment_gateway",
            amount=float(amount),
            payment_method=payment_method,
            payment_reference=payment_reference
        )
        
        # Simulate payment processing delay
        import asyncio
        await asyncio.sleep(0.1)
        
        # For testing purposes, assume all payments succeed
        # In production, this would integrate with Stripe, PayPal, etc.
        return True