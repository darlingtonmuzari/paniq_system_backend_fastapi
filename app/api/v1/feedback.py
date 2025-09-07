"""
Service completion feedback API endpoints
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user, UserContext
from app.core.middleware import require_mobile_attestation
from app.services.feedback import FeedbackService, FeedbackError, FeedbackNotFoundError, InvalidFeedbackError, UnauthorizedFeedbackError
from app.models.emergency import RequestFeedback

router = APIRouter()


class FeedbackSubmission(BaseModel):
    """Feedback submission model"""
    request_id: UUID = Field(..., description="Panic request ID")
    is_prank: bool = Field(False, description="Whether the request was a prank")
    performance_rating: Optional[int] = Field(None, ge=1, le=5, description="Performance rating (1-5)")
    comments: Optional[str] = Field(None, max_length=1000, description="Feedback comments")
    
    @validator('comments')
    def validate_comments(cls, v):
        if v and len(v.strip()) == 0:
            return None
        return v


class FeedbackUpdate(BaseModel):
    """Feedback update model"""
    is_prank: Optional[bool] = Field(None, description="Whether the request was a prank")
    performance_rating: Optional[int] = Field(None, ge=1, le=5, description="Performance rating (1-5)")
    comments: Optional[str] = Field(None, max_length=1000, description="Feedback comments")
    
    @validator('comments')
    def validate_comments(cls, v):
        if v and len(v.strip()) == 0:
            return None
        return v


class FeedbackResponse(BaseModel):
    """Feedback response model"""
    id: UUID
    request_id: UUID
    team_member_id: UUID
    team_member_name: Optional[str]
    is_prank: bool
    performance_rating: Optional[int]
    comments: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
    
    @classmethod
    def from_feedback(cls, feedback: RequestFeedback) -> "FeedbackResponse":
        """Create response from RequestFeedback model"""
        team_member_name = None
        if feedback.team_member:
            team_member_name = f"{feedback.team_member.first_name} {feedback.team_member.last_name}"
        
        return cls(
            id=feedback.id,
            request_id=feedback.request_id,
            team_member_id=feedback.team_member_id,
            team_member_name=team_member_name,
            is_prank=feedback.is_prank,
            performance_rating=feedback.performance_rating,
            comments=feedback.comments,
            created_at=feedback.created_at,
            updated_at=feedback.updated_at
        )


class FeedbackListResponse(BaseModel):
    """Feedback list response model"""
    feedback: List[FeedbackResponse]
    total: int
    limit: int
    offset: int


class FeedbackStatistics(BaseModel):
    """Feedback statistics model"""
    total_feedback: int
    prank_count: int
    prank_rate_percentage: float
    rated_feedback_count: int
    average_rating: float
    rating_distribution: Dict[str, int]
    date_range: Dict[str, Optional[str]]


class PrankFlaggedUser(BaseModel):
    """Prank flagged user model"""
    user_id: UUID
    email: str
    phone: str
    first_name: str
    last_name: str
    total_prank_flags: int
    firm_prank_count: int


@router.post("/feedback", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    feedback_data: FeedbackSubmission,
    db: AsyncSession = Depends(get_db),
    current_user: UserContext = Depends(get_current_user),
    _: dict = Depends(require_mobile_attestation)
):
    """
    Submit feedback for a completed service request
    
    This endpoint allows field team members to submit feedback
    for completed emergency requests, including prank flags
    and performance ratings.
    """
    try:
        # Authorization check - only firm personnel can submit feedback
        if not current_user.is_firm_personnel():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "ACCESS_DENIED",
                    "message": "Only firm personnel can submit feedback",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        if current_user.role not in ["field_agent", "team_leader"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "INSUFFICIENT_PERMISSIONS",
                    "message": "Only field agents and team leaders can submit feedback",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        feedback_service = FeedbackService(db)
        
        feedback = await feedback_service.submit_feedback(
            request_id=feedback_data.request_id,
            team_member_id=current_user.user_id,
            is_prank=feedback_data.is_prank,
            performance_rating=feedback_data.performance_rating,
            comments=feedback_data.comments
        )
        
        return FeedbackResponse.from_feedback(feedback)
        
    except FeedbackError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": e.error_code,
                "message": e.message,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "Failed to submit feedback",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/feedback/{feedback_id}", response_model=FeedbackResponse)
async def get_feedback(
    feedback_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: UserContext = Depends(get_current_user),
    _: dict = Depends(require_mobile_attestation)
):
    """
    Get feedback by ID
    
    Returns detailed information about a specific feedback record.
    Access is restricted to the submitter and firm management.
    """
    try:
        feedback_service = FeedbackService(db)
        
        feedback = await feedback_service.get_feedback_by_id(feedback_id)
        
        if not feedback:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "FEEDBACK_NOT_FOUND",
                    "message": "Feedback not found",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        # Authorization check
        if current_user.is_firm_personnel():
            # Firm personnel can only see feedback from their own firm
            if str(feedback.team_member.firm_id) != str(current_user.firm_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error_code": "ACCESS_DENIED",
                        "message": "You can only view feedback from your own firm",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
        elif not current_user.is_admin():
            # Non-admin, non-firm personnel cannot access feedback
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "ACCESS_DENIED",
                    "message": "Insufficient permissions to view feedback",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        return FeedbackResponse.from_feedback(feedback)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "Failed to retrieve feedback",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/requests/{request_id}/feedback", response_model=FeedbackResponse)
async def get_request_feedback(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: UserContext = Depends(get_current_user),
    _: dict = Depends(require_mobile_attestation)
):
    """
    Get feedback for a specific request
    
    Returns feedback information for a completed emergency request.
    """
    try:
        feedback_service = FeedbackService(db)
        
        feedback = await feedback_service.get_request_feedback(request_id)
        
        if not feedback:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "FEEDBACK_NOT_FOUND",
                    "message": "No feedback found for this request",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        # Authorization check - similar to get_feedback
        if current_user.is_firm_personnel():
            if str(feedback.team_member.firm_id) != str(current_user.firm_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error_code": "ACCESS_DENIED",
                        "message": "You can only view feedback from your own firm",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
        elif not current_user.is_admin():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "ACCESS_DENIED",
                    "message": "Insufficient permissions to view feedback",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        return FeedbackResponse.from_feedback(feedback)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "Failed to retrieve request feedback",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/team-members/{team_member_id}/feedback", response_model=FeedbackListResponse)
async def get_team_member_feedback(
    team_member_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: UserContext = Depends(get_current_user)
):
    """
    Get feedback submitted by a team member
    
    Returns a paginated list of feedback records submitted by
    a specific team member.
    """
    try:
        # Authorization check
        if not current_user.is_firm_personnel() and not current_user.is_admin():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "ACCESS_DENIED",
                    "message": "Only firm personnel and admins can view team member feedback",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        # If firm personnel, verify they can access this team member
        if current_user.is_firm_personnel():
            # Verify team member belongs to the same firm
            from app.models.security_firm import FirmPersonnel
            from sqlalchemy import select
            
            result = await db.execute(
                select(FirmPersonnel).where(FirmPersonnel.id == team_member_id)
            )
            team_member = result.scalar_one_or_none()
            
            if not team_member:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "error_code": "TEAM_MEMBER_NOT_FOUND",
                        "message": "Team member not found",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
            
            if str(team_member.firm_id) != str(current_user.firm_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error_code": "ACCESS_DENIED",
                        "message": "You can only view feedback from your own firm's team members",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
        
        feedback_service = FeedbackService(db)
        
        feedback_records = await feedback_service.get_team_member_feedback(
            team_member_id=team_member_id,
            limit=limit,
            offset=offset
        )
        
        # Convert to response models
        feedback_responses = [
            FeedbackResponse.from_feedback(feedback) for feedback in feedback_records
        ]
        
        return FeedbackListResponse(
            feedback=feedback_responses,
            total=len(feedback_responses),
            limit=limit,
            offset=offset
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "Failed to retrieve team member feedback",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.put("/feedback/{feedback_id}", response_model=FeedbackResponse)
async def update_feedback(
    feedback_id: UUID,
    feedback_update: FeedbackUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserContext = Depends(get_current_user),
    _: dict = Depends(require_mobile_attestation)
):
    """
    Update existing feedback
    
    Allows the original submitter to update their feedback.
    Only the team member who submitted the feedback can update it.
    """
    try:
        # Authorization check
        if not current_user.is_firm_personnel():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "ACCESS_DENIED",
                    "message": "Only firm personnel can update feedback",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        feedback_service = FeedbackService(db)
        
        feedback = await feedback_service.update_feedback(
            feedback_id=feedback_id,
            team_member_id=current_user.user_id,
            is_prank=feedback_update.is_prank,
            performance_rating=feedback_update.performance_rating,
            comments=feedback_update.comments
        )
        
        return FeedbackResponse.from_feedback(feedback)
        
    except (FeedbackNotFoundError, UnauthorizedFeedbackError, InvalidFeedbackError) as e:
        status_code = status.HTTP_404_NOT_FOUND if isinstance(e, FeedbackNotFoundError) else status.HTTP_403_FORBIDDEN if isinstance(e, UnauthorizedFeedbackError) else status.HTTP_400_BAD_REQUEST
        
        raise HTTPException(
            status_code=status_code,
            detail={
                "error_code": e.error_code,
                "message": e.message,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "Failed to update feedback",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/firms/{firm_id}/feedback/statistics", response_model=FeedbackStatistics)
async def get_firm_feedback_statistics(
    firm_id: UUID,
    date_from: Optional[datetime] = Query(None, description="Start date filter"),
    date_to: Optional[datetime] = Query(None, description="End date filter"),
    db: AsyncSession = Depends(get_db),
    current_user: UserContext = Depends(get_current_user)
):
    """
    Get feedback statistics for a security firm
    
    Returns comprehensive feedback statistics including prank rates,
    performance ratings, and trends over time.
    """
    try:
        # Authorization check
        if current_user.is_firm_personnel():
            # Firm personnel can only see their own firm's statistics
            if str(current_user.firm_id) != str(firm_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error_code": "ACCESS_DENIED",
                        "message": "You can only view statistics for your own firm",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
        elif not current_user.is_admin():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "ACCESS_DENIED",
                    "message": "Only firm personnel and admins can view feedback statistics",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        feedback_service = FeedbackService(db)
        
        statistics = await feedback_service.get_firm_feedback_statistics(
            firm_id=firm_id,
            date_from=date_from,
            date_to=date_to
        )
        
        return FeedbackStatistics(**statistics)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "Failed to retrieve feedback statistics",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/firms/{firm_id}/prank-flagged-users", response_model=List[PrankFlaggedUser])
async def get_prank_flagged_users(
    firm_id: UUID,
    min_prank_flags: int = Query(3, ge=1, description="Minimum number of prank flags"),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: UserContext = Depends(get_current_user)
):
    """
    Get users with multiple prank flags for a firm
    
    Returns a list of users who have been flagged for prank requests
    multiple times by this firm's team members.
    """
    try:
        # Authorization check
        if current_user.is_firm_personnel():
            if str(current_user.firm_id) != str(firm_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error_code": "ACCESS_DENIED",
                        "message": "You can only view prank-flagged users for your own firm",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
        elif not current_user.is_admin():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "ACCESS_DENIED",
                    "message": "Only firm personnel and admins can view prank-flagged users",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        feedback_service = FeedbackService(db)
        
        users = await feedback_service.get_prank_flagged_users(
            firm_id=firm_id,
            min_prank_flags=min_prank_flags,
            limit=limit
        )
        
        return [PrankFlaggedUser(**user) for user in users]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "Failed to retrieve prank-flagged users",
                "timestamp": datetime.utcnow().isoformat()
            }
        )