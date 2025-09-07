"""
Service completion feedback service
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from sqlalchemy.orm import selectinload
import structlog

from app.core.exceptions import APIError, ErrorCodes
from app.models.emergency import PanicRequest, RequestFeedback
from app.models.security_firm import FirmPersonnel
from app.models.user import RegisteredUser, UserGroup

logger = structlog.get_logger()


class FeedbackError(APIError):
    """Base feedback error"""
    def __init__(self, error_code: str, message: str):
        super().__init__(error_code, message)


class FeedbackNotFoundError(FeedbackError):
    """Feedback not found error"""
    def __init__(self, message: str = "Feedback not found"):
        super().__init__(ErrorCodes.REQUEST_NOT_FOUND, message)


class InvalidFeedbackError(FeedbackError):
    """Invalid feedback error"""
    def __init__(self, message: str = "Invalid feedback data"):
        super().__init__(ErrorCodes.VALIDATION_ERROR, message)


class UnauthorizedFeedbackError(FeedbackError):
    """Unauthorized feedback access error"""
    def __init__(self, message: str = "Unauthorized to access this feedback"):
        super().__init__(ErrorCodes.INSUFFICIENT_PERMISSIONS, message)


class FeedbackService:
    """Service for managing service completion feedback"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def submit_feedback(
        self,
        request_id: UUID,
        team_member_id: UUID,
        is_prank: bool = False,
        performance_rating: Optional[int] = None,
        comments: Optional[str] = None
    ) -> RequestFeedback:
        """
        Submit feedback for a completed service request
        
        Args:
            request_id: Panic request ID
            team_member_id: ID of team member submitting feedback
            is_prank: Whether the request was a prank
            performance_rating: Performance rating (1-5)
            comments: Optional feedback comments
            
        Returns:
            Created feedback record
            
        Raises:
            InvalidFeedbackError: If feedback data is invalid
            FeedbackError: If feedback cannot be submitted
        """
        logger.info(
            "feedback_submission_started",
            request_id=str(request_id),
            team_member_id=str(team_member_id),
            is_prank=is_prank,
            performance_rating=performance_rating
        )
        
        # Validate performance rating
        if performance_rating is not None and (performance_rating < 1 or performance_rating > 5):
            raise InvalidFeedbackError("Performance rating must be between 1 and 5")
        
        # Validate comments length
        if comments and len(comments) > 1000:
            raise InvalidFeedbackError("Comments must be 1000 characters or less")
        
        # Verify request exists and is completed
        result = await self.db.execute(
            select(PanicRequest).where(PanicRequest.id == request_id)
        )
        panic_request = result.scalar_one_or_none()
        
        if not panic_request:
            raise FeedbackError(ErrorCodes.REQUEST_NOT_FOUND, "Panic request not found")
        
        if panic_request.status != "completed":
            raise InvalidFeedbackError("Can only submit feedback for completed requests")
        
        # Verify team member exists and has permission
        result = await self.db.execute(
            select(FirmPersonnel).where(FirmPersonnel.id == team_member_id)
        )
        team_member = result.scalar_one_or_none()
        
        if not team_member:
            raise FeedbackError(ErrorCodes.REQUEST_NOT_FOUND, "Team member not found")
        
        # Check if feedback already exists for this request
        result = await self.db.execute(
            select(RequestFeedback).where(RequestFeedback.request_id == request_id)
        )
        existing_feedback = result.scalar_one_or_none()
        
        if existing_feedback:
            raise InvalidFeedbackError("Feedback already exists for this request")
        
        # Create feedback record
        feedback = RequestFeedback(
            request_id=request_id,
            team_member_id=team_member_id,
            is_prank=is_prank,
            performance_rating=performance_rating,
            comments=comments
        )
        
        self.db.add(feedback)
        
        # If flagged as prank, update user's prank count and trigger fine calculation
        if is_prank:
            await self._handle_prank_flag(panic_request.group_id)
        
        await self.db.commit()
        await self.db.refresh(feedback)
        
        logger.info(
            "feedback_submitted_successfully",
            feedback_id=str(feedback.id),
            request_id=str(request_id),
            team_member_id=str(team_member_id),
            is_prank=is_prank,
            performance_rating=performance_rating
        )
        
        return feedback
    
    async def get_feedback_by_id(self, feedback_id: UUID) -> Optional[RequestFeedback]:
        """
        Get feedback by ID with related data
        
        Args:
            feedback_id: Feedback ID
            
        Returns:
            RequestFeedback object or None
        """
        result = await self.db.execute(
            select(RequestFeedback).options(
                selectinload(RequestFeedback.request),
                selectinload(RequestFeedback.team_member)
            ).where(RequestFeedback.id == feedback_id)
        )
        
        return result.scalar_one_or_none()
    
    async def get_request_feedback(self, request_id: UUID) -> Optional[RequestFeedback]:
        """
        Get feedback for a specific request
        
        Args:
            request_id: Panic request ID
            
        Returns:
            RequestFeedback object or None
        """
        result = await self.db.execute(
            select(RequestFeedback).options(
                selectinload(RequestFeedback.team_member)
            ).where(RequestFeedback.request_id == request_id)
        )
        
        return result.scalar_one_or_none()
    
    async def get_team_member_feedback(
        self,
        team_member_id: UUID,
        limit: int = 50,
        offset: int = 0
    ) -> List[RequestFeedback]:
        """
        Get feedback submitted by a team member
        
        Args:
            team_member_id: Team member ID
            limit: Maximum number of feedback records to return
            offset: Number of records to skip
            
        Returns:
            List of feedback records
        """
        result = await self.db.execute(
            select(RequestFeedback).options(
                selectinload(RequestFeedback.request)
            ).where(RequestFeedback.team_member_id == team_member_id)
            .order_by(desc(RequestFeedback.created_at))
            .limit(limit)
            .offset(offset)
        )
        
        return result.scalars().all()
    
    async def get_firm_feedback_statistics(
        self,
        firm_id: UUID,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get feedback statistics for a security firm
        
        Args:
            firm_id: Security firm ID
            date_from: Optional start date filter
            date_to: Optional end date filter
            
        Returns:
            Dictionary with feedback statistics
        """
        # Build base query
        query = select(RequestFeedback).join(
            FirmPersonnel, RequestFeedback.team_member_id == FirmPersonnel.id
        ).where(FirmPersonnel.firm_id == firm_id)
        
        if date_from:
            query = query.where(RequestFeedback.created_at >= date_from)
        
        if date_to:
            query = query.where(RequestFeedback.created_at <= date_to)
        
        result = await self.db.execute(query)
        feedback_records = result.scalars().all()
        
        # Calculate statistics
        total_feedback = len(feedback_records)
        prank_count = sum(1 for f in feedback_records if f.is_prank)
        rated_feedback = [f for f in feedback_records if f.performance_rating is not None]
        
        # Calculate rating statistics
        if rated_feedback:
            ratings = [f.performance_rating for f in rated_feedback]
            avg_rating = sum(ratings) / len(ratings)
            rating_distribution = {}
            for rating in range(1, 6):
                rating_distribution[str(rating)] = sum(1 for r in ratings if r == rating)
        else:
            avg_rating = 0
            rating_distribution = {}
        
        # Calculate prank rate
        prank_rate = (prank_count / total_feedback * 100) if total_feedback > 0 else 0
        
        return {
            "total_feedback": total_feedback,
            "prank_count": prank_count,
            "prank_rate_percentage": round(prank_rate, 2),
            "rated_feedback_count": len(rated_feedback),
            "average_rating": round(avg_rating, 2),
            "rating_distribution": rating_distribution,
            "date_range": {
                "from": date_from.isoformat() if date_from else None,
                "to": date_to.isoformat() if date_to else None
            }
        }
    
    async def get_prank_flagged_users(
        self,
        firm_id: UUID,
        min_prank_flags: int = 3,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get users with multiple prank flags for a firm
        
        Args:
            firm_id: Security firm ID
            min_prank_flags: Minimum number of prank flags
            limit: Maximum number of users to return
            
        Returns:
            List of user information with prank statistics
        """
        # Query for users with prank flags from this firm's requests
        result = await self.db.execute(
            select(
                RegisteredUser.id,
                RegisteredUser.email,
                RegisteredUser.phone,
                RegisteredUser.first_name,
                RegisteredUser.last_name,
                RegisteredUser.prank_flags,
                func.count(RequestFeedback.id).label('firm_prank_count')
            ).select_from(RegisteredUser)
            .join(UserGroup, RegisteredUser.id == UserGroup.user_id)
            .join(PanicRequest, UserGroup.id == PanicRequest.group_id)
            .join(RequestFeedback, PanicRequest.id == RequestFeedback.request_id)
            .join(FirmPersonnel, RequestFeedback.team_member_id == FirmPersonnel.id)
            .where(
                and_(
                    FirmPersonnel.firm_id == firm_id,
                    RequestFeedback.is_prank == True,
                    RegisteredUser.prank_flags >= min_prank_flags
                )
            )
            .group_by(
                RegisteredUser.id,
                RegisteredUser.email,
                RegisteredUser.phone,
                RegisteredUser.first_name,
                RegisteredUser.last_name,
                RegisteredUser.prank_flags
            )
            .order_by(desc(RegisteredUser.prank_flags))
            .limit(limit)
        )
        
        users = result.all()
        
        return [
            {
                "user_id": str(user.id),
                "email": user.email,
                "phone": user.phone,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "total_prank_flags": user.prank_flags,
                "firm_prank_count": user.firm_prank_count
            }
            for user in users
        ]
    
    async def update_feedback(
        self,
        feedback_id: UUID,
        team_member_id: UUID,
        is_prank: Optional[bool] = None,
        performance_rating: Optional[int] = None,
        comments: Optional[str] = None
    ) -> RequestFeedback:
        """
        Update existing feedback (only by the original submitter)
        
        Args:
            feedback_id: Feedback ID
            team_member_id: ID of team member updating feedback
            is_prank: Updated prank flag
            performance_rating: Updated performance rating
            comments: Updated comments
            
        Returns:
            Updated feedback record
            
        Raises:
            FeedbackNotFoundError: If feedback not found
            UnauthorizedFeedbackError: If not authorized to update
            InvalidFeedbackError: If update data is invalid
        """
        # Get existing feedback
        feedback = await self.get_feedback_by_id(feedback_id)
        if not feedback:
            raise FeedbackNotFoundError()
        
        # Verify authorization
        if str(feedback.team_member_id) != str(team_member_id):
            raise UnauthorizedFeedbackError("Only the original submitter can update feedback")
        
        # Validate performance rating
        if performance_rating is not None and (performance_rating < 1 or performance_rating > 5):
            raise InvalidFeedbackError("Performance rating must be between 1 and 5")
        
        # Validate comments length
        if comments and len(comments) > 1000:
            raise InvalidFeedbackError("Comments must be 1000 characters or less")
        
        # Update fields
        if is_prank is not None:
            old_prank_flag = feedback.is_prank
            feedback.is_prank = is_prank
            
            # Handle prank flag changes
            if is_prank != old_prank_flag:
                if is_prank:
                    await self._handle_prank_flag(feedback.request.group_id)
                else:
                    await self._remove_prank_flag(feedback.request.group_id)
        
        if performance_rating is not None:
            feedback.performance_rating = performance_rating
        
        if comments is not None:
            feedback.comments = comments
        
        feedback.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(feedback)
        
        logger.info(
            "feedback_updated_successfully",
            feedback_id=str(feedback_id),
            team_member_id=str(team_member_id),
            is_prank=is_prank,
            performance_rating=performance_rating
        )
        
        return feedback
    
    async def _handle_prank_flag(self, group_id: UUID) -> None:
        """
        Handle prank flag by updating user's prank count and triggering fine calculation
        
        Args:
            group_id: User group ID
        """
        # Get the group and user
        result = await self.db.execute(
            select(UserGroup).options(
                selectinload(UserGroup.user)
            ).where(UserGroup.id == group_id)
        )
        
        group = result.scalar_one_or_none()
        if group and group.user:
            # Increment prank flags
            group.user.prank_flags += 1
            
            logger.info(
                "user_prank_flag_incremented",
                user_id=str(group.user.id),
                total_prank_flags=group.user.prank_flags
            )
            
            # Trigger automatic fine calculation and account actions
            from app.services.prank_detection import PrankDetectionService
            prank_service = PrankDetectionService(self.db)
            
            # Calculate automatic fine if needed
            await prank_service.calculate_automatic_fine(group.user.id)
            
            # Check if user should be suspended or banned
            if group.user.prank_flags >= PrankDetectionService.PERMANENT_BAN_THRESHOLD:
                await prank_service.create_permanent_ban(group.user.id)
            elif group.user.prank_flags >= PrankDetectionService.SUSPENSION_THRESHOLD:
                # Check for unpaid fines and suspend if any exist
                unpaid_fines = await prank_service._get_unpaid_fines_count(group.user.id)
                if unpaid_fines > 0:
                    await prank_service.suspend_account_for_unpaid_fines(group.user.id)
    
    async def _remove_prank_flag(self, group_id: UUID) -> None:
        """
        Remove prank flag by decrementing user's prank count
        
        Args:
            group_id: User group ID
        """
        # Get the group and user
        result = await self.db.execute(
            select(UserGroup).options(
                selectinload(UserGroup.user)
            ).where(UserGroup.id == group_id)
        )
        
        group = result.scalar_one_or_none()
        if group and group.user and group.user.prank_flags > 0:
            # Decrement prank flags
            group.user.prank_flags -= 1
            
            logger.info(
                "user_prank_flag_decremented",
                user_id=str(group.user.id),
                total_prank_flags=group.user.prank_flags
            )