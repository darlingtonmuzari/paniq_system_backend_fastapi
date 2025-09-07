"""
Unit tests for feedback service
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.feedback import (
    FeedbackService,
    FeedbackError,
    FeedbackNotFoundError,
    InvalidFeedbackError,
    UnauthorizedFeedbackError
)
from app.models.emergency import RequestFeedback, PanicRequest
from app.models.security_firm import FirmPersonnel
from app.models.user import RegisteredUser, UserGroup


class TestFeedbackService:
    """Test cases for feedback service"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.flush = AsyncMock()
        return db
    
    @pytest.fixture
    def feedback_service(self, mock_db):
        """Feedback service instance"""
        return FeedbackService(mock_db)
    
    @pytest.fixture
    def mock_panic_request(self):
        """Mock panic request"""
        request = MagicMock(spec=PanicRequest)
        request.id = uuid4()
        request.group_id = uuid4()
        request.status = "completed"
        request.service_type = "security"
        request.requester_phone = "+1234567890"
        return request
    
    @pytest.fixture
    def mock_team_member(self):
        """Mock team member"""
        member = MagicMock(spec=FirmPersonnel)
        member.id = uuid4()
        member.firm_id = uuid4()
        member.first_name = "John"
        member.last_name = "Doe"
        member.role = "field_agent"
        return member
    
    @pytest.fixture
    def mock_user_group(self):
        """Mock user group with user"""
        user = MagicMock(spec=RegisteredUser)
        user.id = uuid4()
        user.prank_flags = 0
        
        group = MagicMock(spec=UserGroup)
        group.id = uuid4()
        group.user_id = user.id
        group.user = user
        
        return group
    
    @pytest.fixture
    def mock_feedback(self, mock_panic_request, mock_team_member):
        """Mock feedback record"""
        feedback = MagicMock(spec=RequestFeedback)
        feedback.id = uuid4()
        feedback.request_id = mock_panic_request.id
        feedback.team_member_id = mock_team_member.id
        feedback.is_prank = False
        feedback.performance_rating = 4
        feedback.comments = "Service completed successfully"
        feedback.created_at = datetime.utcnow()
        feedback.updated_at = datetime.utcnow()
        feedback.request = mock_panic_request
        feedback.team_member = mock_team_member
        return feedback
    
    @pytest.mark.asyncio
    async def test_submit_feedback_success(
        self,
        feedback_service,
        mock_panic_request,
        mock_team_member,
        mock_user_group
    ):
        """Test successful feedback submission"""
        # Mock database responses
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.side_effect = [
            mock_panic_request,  # Request lookup
            mock_team_member,    # Team member lookup
            None,                # No existing feedback
            mock_user_group      # Group lookup for prank handling
        ]
        feedback_service.db.execute.return_value = mock_result
        
        result = await feedback_service.submit_feedback(
            request_id=mock_panic_request.id,
            team_member_id=mock_team_member.id,
            is_prank=False,
            performance_rating=4,
            comments="Service completed successfully"
        )
        
        # Verify feedback was created and added to database
        feedback_service.db.add.assert_called_once()
        feedback_service.db.commit.assert_called_once()
        feedback_service.db.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_submit_feedback_with_prank_flag(
        self,
        feedback_service,
        mock_panic_request,
        mock_team_member,
        mock_user_group
    ):
        """Test feedback submission with prank flag"""
        # Mock database responses
        feedback_service.db.execute.return_value.scalar_one_or_none.side_effect = [
            mock_panic_request,  # Request lookup
            mock_team_member,    # Team member lookup
            None,                # No existing feedback
            mock_user_group      # Group lookup for prank handling
        ]
        
        result = await feedback_service.submit_feedback(
            request_id=mock_panic_request.id,
            team_member_id=mock_team_member.id,
            is_prank=True,
            performance_rating=1,
            comments="False alarm - prank call"
        )
        
        # Verify prank flag was incremented
        assert mock_user_group.user.prank_flags == 1
        feedback_service.db.add.assert_called_once()
        feedback_service.db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_submit_feedback_invalid_rating(
        self,
        feedback_service,
        mock_panic_request,
        mock_team_member
    ):
        """Test feedback submission with invalid rating"""
        with pytest.raises(InvalidFeedbackError) as exc_info:
            await feedback_service.submit_feedback(
                request_id=mock_panic_request.id,
                team_member_id=mock_team_member.id,
                performance_rating=6  # Invalid rating
            )
        
        assert "Performance rating must be between 1 and 5" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_submit_feedback_comments_too_long(
        self,
        feedback_service,
        mock_panic_request,
        mock_team_member
    ):
        """Test feedback submission with comments too long"""
        long_comments = "x" * 1001  # Exceeds 1000 character limit
        
        with pytest.raises(InvalidFeedbackError) as exc_info:
            await feedback_service.submit_feedback(
                request_id=mock_panic_request.id,
                team_member_id=mock_team_member.id,
                comments=long_comments
            )
        
        assert "Comments must be 1000 characters or less" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_submit_feedback_request_not_found(
        self,
        feedback_service,
        mock_team_member
    ):
        """Test feedback submission for non-existent request"""
        # Mock database to return None for request lookup
        feedback_service.db.execute.return_value.scalar_one_or_none.return_value = None
        
        with pytest.raises(FeedbackError) as exc_info:
            await feedback_service.submit_feedback(
                request_id=uuid4(),
                team_member_id=mock_team_member.id
            )
        
        assert "Panic request not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_submit_feedback_request_not_completed(
        self,
        feedback_service,
        mock_panic_request,
        mock_team_member
    ):
        """Test feedback submission for non-completed request"""
        mock_panic_request.status = "pending"
        
        feedback_service.db.execute.return_value.scalar_one_or_none.side_effect = [
            mock_panic_request,  # Request lookup
            mock_team_member     # Team member lookup
        ]
        
        with pytest.raises(InvalidFeedbackError) as exc_info:
            await feedback_service.submit_feedback(
                request_id=mock_panic_request.id,
                team_member_id=mock_team_member.id
            )
        
        assert "Can only submit feedback for completed requests" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_submit_feedback_team_member_not_found(
        self,
        feedback_service,
        mock_panic_request
    ):
        """Test feedback submission with non-existent team member"""
        feedback_service.db.execute.return_value.scalar_one_or_none.side_effect = [
            mock_panic_request,  # Request lookup
            None                 # Team member not found
        ]
        
        with pytest.raises(FeedbackError) as exc_info:
            await feedback_service.submit_feedback(
                request_id=mock_panic_request.id,
                team_member_id=uuid4()
            )
        
        assert "Team member not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_submit_feedback_already_exists(
        self,
        feedback_service,
        mock_panic_request,
        mock_team_member,
        mock_feedback
    ):
        """Test feedback submission when feedback already exists"""
        feedback_service.db.execute.return_value.scalar_one_or_none.side_effect = [
            mock_panic_request,  # Request lookup
            mock_team_member,    # Team member lookup
            mock_feedback        # Existing feedback found
        ]
        
        with pytest.raises(InvalidFeedbackError) as exc_info:
            await feedback_service.submit_feedback(
                request_id=mock_panic_request.id,
                team_member_id=mock_team_member.id
            )
        
        assert "Feedback already exists for this request" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_feedback_by_id_success(
        self,
        feedback_service,
        mock_feedback
    ):
        """Test successful feedback retrieval by ID"""
        feedback_service.db.execute.return_value.scalar_one_or_none.return_value = mock_feedback
        
        result = await feedback_service.get_feedback_by_id(mock_feedback.id)
        
        assert result == mock_feedback
    
    @pytest.mark.asyncio
    async def test_get_feedback_by_id_not_found(
        self,
        feedback_service
    ):
        """Test feedback retrieval by ID when not found"""
        feedback_service.db.execute.return_value.scalar_one_or_none.return_value = None
        
        result = await feedback_service.get_feedback_by_id(uuid4())
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_request_feedback_success(
        self,
        feedback_service,
        mock_feedback,
        mock_panic_request
    ):
        """Test successful request feedback retrieval"""
        feedback_service.db.execute.return_value.scalar_one_or_none.return_value = mock_feedback
        
        result = await feedback_service.get_request_feedback(mock_panic_request.id)
        
        assert result == mock_feedback
    
    @pytest.mark.asyncio
    async def test_get_team_member_feedback_success(
        self,
        feedback_service,
        mock_feedback,
        mock_team_member
    ):
        """Test successful team member feedback retrieval"""
        feedback_service.db.execute.return_value.scalars.return_value.all.return_value = [mock_feedback]
        
        result = await feedback_service.get_team_member_feedback(
            team_member_id=mock_team_member.id,
            limit=50,
            offset=0
        )
        
        assert result == [mock_feedback]
    
    @pytest.mark.asyncio
    async def test_get_firm_feedback_statistics_success(
        self,
        feedback_service,
        mock_team_member
    ):
        """Test successful firm feedback statistics retrieval"""
        # Mock feedback records
        mock_feedback_1 = MagicMock()
        mock_feedback_1.is_prank = False
        mock_feedback_1.performance_rating = 4
        
        mock_feedback_2 = MagicMock()
        mock_feedback_2.is_prank = True
        mock_feedback_2.performance_rating = 2
        
        mock_feedback_3 = MagicMock()
        mock_feedback_3.is_prank = False
        mock_feedback_3.performance_rating = 5
        
        feedback_service.db.execute.return_value.scalars.return_value.all.return_value = [
            mock_feedback_1, mock_feedback_2, mock_feedback_3
        ]
        
        result = await feedback_service.get_firm_feedback_statistics(
            firm_id=mock_team_member.firm_id
        )
        
        assert result["total_feedback"] == 3
        assert result["prank_count"] == 1
        assert result["prank_rate_percentage"] == 33.33
        assert result["rated_feedback_count"] == 3
        assert result["average_rating"] == 3.67
    
    @pytest.mark.asyncio
    async def test_get_prank_flagged_users_success(
        self,
        feedback_service,
        mock_team_member
    ):
        """Test successful prank flagged users retrieval"""
        # Mock user data
        mock_user_data = MagicMock()
        mock_user_data.id = uuid4()
        mock_user_data.email = "test@example.com"
        mock_user_data.phone = "+1234567890"
        mock_user_data.first_name = "John"
        mock_user_data.last_name = "Doe"
        mock_user_data.prank_flags = 5
        mock_user_data.firm_prank_count = 3
        
        feedback_service.db.execute.return_value.all.return_value = [mock_user_data]
        
        result = await feedback_service.get_prank_flagged_users(
            firm_id=mock_team_member.firm_id,
            min_prank_flags=3,
            limit=50
        )
        
        assert len(result) == 1
        assert result[0]["user_id"] == str(mock_user_data.id)
        assert result[0]["email"] == mock_user_data.email
        assert result[0]["total_prank_flags"] == 5
        assert result[0]["firm_prank_count"] == 3
    
    @pytest.mark.asyncio
    async def test_update_feedback_success(
        self,
        feedback_service,
        mock_feedback,
        mock_team_member
    ):
        """Test successful feedback update"""
        # Mock get_feedback_by_id to return the feedback
        feedback_service.get_feedback_by_id = AsyncMock(return_value=mock_feedback)
        
        result = await feedback_service.update_feedback(
            feedback_id=mock_feedback.id,
            team_member_id=mock_team_member.id,
            is_prank=True,
            performance_rating=2,
            comments="Updated: This was actually a prank"
        )
        
        assert mock_feedback.is_prank == True
        assert mock_feedback.performance_rating == 2
        assert mock_feedback.comments == "Updated: This was actually a prank"
        feedback_service.db.commit.assert_called_once()
        feedback_service.db.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_feedback_not_found(
        self,
        feedback_service,
        mock_team_member
    ):
        """Test feedback update when feedback not found"""
        feedback_service.get_feedback_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(FeedbackNotFoundError):
            await feedback_service.update_feedback(
                feedback_id=uuid4(),
                team_member_id=mock_team_member.id
            )
    
    @pytest.mark.asyncio
    async def test_update_feedback_unauthorized(
        self,
        feedback_service,
        mock_feedback,
        mock_team_member
    ):
        """Test feedback update by unauthorized user"""
        # Set different team member ID
        mock_feedback.team_member_id = uuid4()
        feedback_service.get_feedback_by_id = AsyncMock(return_value=mock_feedback)
        
        with pytest.raises(UnauthorizedFeedbackError) as exc_info:
            await feedback_service.update_feedback(
                feedback_id=mock_feedback.id,
                team_member_id=mock_team_member.id
            )
        
        assert "Only the original submitter can update feedback" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_update_feedback_invalid_rating(
        self,
        feedback_service,
        mock_feedback,
        mock_team_member
    ):
        """Test feedback update with invalid rating"""
        feedback_service.get_feedback_by_id = AsyncMock(return_value=mock_feedback)
        
        with pytest.raises(InvalidFeedbackError) as exc_info:
            await feedback_service.update_feedback(
                feedback_id=mock_feedback.id,
                team_member_id=mock_team_member.id,
                performance_rating=6  # Invalid rating
            )
        
        assert "Performance rating must be between 1 and 5" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_update_feedback_comments_too_long(
        self,
        feedback_service,
        mock_feedback,
        mock_team_member
    ):
        """Test feedback update with comments too long"""
        feedback_service.get_feedback_by_id = AsyncMock(return_value=mock_feedback)
        long_comments = "x" * 1001
        
        with pytest.raises(InvalidFeedbackError) as exc_info:
            await feedback_service.update_feedback(
                feedback_id=mock_feedback.id,
                team_member_id=mock_team_member.id,
                comments=long_comments
            )
        
        assert "Comments must be 1000 characters or less" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_handle_prank_flag_increment(
        self,
        feedback_service,
        mock_user_group
    ):
        """Test prank flag increment"""
        feedback_service.db.execute.return_value.scalar_one_or_none.return_value = mock_user_group
        
        await feedback_service._handle_prank_flag(mock_user_group.id)
        
        assert mock_user_group.user.prank_flags == 1
    
    @pytest.mark.asyncio
    async def test_remove_prank_flag_decrement(
        self,
        feedback_service,
        mock_user_group
    ):
        """Test prank flag decrement"""
        mock_user_group.user.prank_flags = 3
        feedback_service.db.execute.return_value.scalar_one_or_none.return_value = mock_user_group
        
        await feedback_service._remove_prank_flag(mock_user_group.id)
        
        assert mock_user_group.user.prank_flags == 2
    
    @pytest.mark.asyncio
    async def test_remove_prank_flag_no_decrement_when_zero(
        self,
        feedback_service,
        mock_user_group
    ):
        """Test prank flag doesn't go below zero"""
        mock_user_group.user.prank_flags = 0
        feedback_service.db.execute.return_value.scalar_one_or_none.return_value = mock_user_group
        
        await feedback_service._remove_prank_flag(mock_user_group.id)
        
        assert mock_user_group.user.prank_flags == 0