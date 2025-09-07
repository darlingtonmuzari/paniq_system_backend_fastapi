"""
Simplified unit tests for feedback service
"""
import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.feedback import (
    FeedbackService,
    FeedbackError,
    InvalidFeedbackError
)


class TestFeedbackServiceSimple:
    """Simplified test cases for feedback service"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return AsyncMock()
    
    @pytest.fixture
    def feedback_service(self, mock_db):
        """Feedback service instance"""
        return FeedbackService(mock_db)
    
    @pytest.mark.asyncio
    async def test_submit_feedback_invalid_rating(self, feedback_service):
        """Test feedback submission with invalid rating"""
        with pytest.raises(InvalidFeedbackError) as exc_info:
            await feedback_service.submit_feedback(
                request_id=uuid4(),
                team_member_id=uuid4(),
                performance_rating=6  # Invalid rating
            )
        
        assert "Performance rating must be between 1 and 5" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_submit_feedback_comments_too_long(self, feedback_service):
        """Test feedback submission with comments too long"""
        long_comments = "x" * 1001  # Exceeds 1000 character limit
        
        with pytest.raises(InvalidFeedbackError) as exc_info:
            await feedback_service.submit_feedback(
                request_id=uuid4(),
                team_member_id=uuid4(),
                comments=long_comments
            )
        
        assert "Comments must be 1000 characters or less" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_update_feedback_invalid_rating(self, feedback_service):
        """Test feedback update with invalid rating"""
        # Mock get_feedback_by_id to return a feedback object
        mock_feedback = MagicMock()
        mock_feedback.team_member_id = uuid4()
        
        with patch.object(feedback_service, 'get_feedback_by_id', return_value=mock_feedback):
            with pytest.raises(InvalidFeedbackError) as exc_info:
                await feedback_service.update_feedback(
                    feedback_id=uuid4(),
                    team_member_id=mock_feedback.team_member_id,
                    performance_rating=6  # Invalid rating
                )
        
        assert "Performance rating must be between 1 and 5" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_update_feedback_comments_too_long(self, feedback_service):
        """Test feedback update with comments too long"""
        mock_feedback = MagicMock()
        mock_feedback.team_member_id = uuid4()
        long_comments = "x" * 1001
        
        with patch.object(feedback_service, 'get_feedback_by_id', return_value=mock_feedback):
            with pytest.raises(InvalidFeedbackError) as exc_info:
                await feedback_service.update_feedback(
                    feedback_id=uuid4(),
                    team_member_id=mock_feedback.team_member_id,
                    comments=long_comments
                )
        
        assert "Comments must be 1000 characters or less" in str(exc_info.value)
    
    def test_feedback_service_initialization(self, mock_db):
        """Test feedback service initialization"""
        service = FeedbackService(mock_db)
        assert service.db == mock_db