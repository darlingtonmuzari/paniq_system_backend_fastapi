"""
Unit tests for feedback API endpoints
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import status

from app.main import app
from app.services.feedback import (
    FeedbackService,
    FeedbackError,
    FeedbackNotFoundError,
    InvalidFeedbackError,
    UnauthorizedFeedbackError
)
from app.models.emergency import RequestFeedback
from app.core.auth import UserContext


class TestFeedbackAPI:
    """Test cases for feedback API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Test client"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_firm_personnel_context(self):
        """Mock firm personnel user context"""
        return UserContext(
            user_id=uuid4(),
            user_type="firm_personnel",
            email="agent@security.com",
            firm_id=uuid4(),
            role="field_agent",
            permissions=["feedback:submit", "feedback:view"]
        )
    
    @pytest.fixture
    def mock_admin_context(self):
        """Mock admin user context"""
        return UserContext(
            user_id=uuid4(),
            user_type="admin",
            email="admin@platform.com",
            permissions=["feedback:view", "feedback:manage"]
        )
    
    @pytest.fixture
    def sample_feedback_data(self):
        """Sample feedback submission data"""
        return {
            "request_id": str(uuid4()),
            "is_prank": False,
            "performance_rating": 4,
            "comments": "Service completed successfully"
        }
    
    @pytest.fixture
    def mock_feedback(self):
        """Mock feedback record"""
        feedback = MagicMock(spec=RequestFeedback)
        feedback.id = uuid4()
        feedback.request_id = uuid4()
        feedback.team_member_id = uuid4()
        feedback.is_prank = False
        feedback.performance_rating = 4
        feedback.comments = "Service completed successfully"
        feedback.created_at = datetime.utcnow()
        feedback.updated_at = datetime.utcnow()
        
        # Mock team member
        team_member = MagicMock()
        team_member.first_name = "John"
        team_member.last_name = "Doe"
        team_member.firm_id = uuid4()
        feedback.team_member = team_member
        
        return feedback
    
    @pytest.mark.asyncio
    async def test_submit_feedback_success(
        self,
        client,
        sample_feedback_data,
        mock_firm_personnel_context,
        mock_feedback
    ):
        """Test successful feedback submission"""
        with patch('app.core.auth.get_current_user', return_value=mock_firm_personnel_context), \
             patch('app.core.middleware.require_mobile_attestation', return_value={}), \
             patch('app.services.feedback.FeedbackService.submit_feedback', return_value=mock_feedback):
            
            response = client.post(
                "/api/v1/feedback/feedback",
                json=sample_feedback_data
            )
            
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["id"] == str(mock_feedback.id)
            assert data["is_prank"] == False
            assert data["performance_rating"] == 4
            assert data["comments"] == "Service completed successfully"
    
    @pytest.mark.asyncio
    async def test_submit_feedback_unauthorized_user_type(
        self,
        client,
        sample_feedback_data
    ):
        """Test feedback submission by unauthorized user type"""
        unauthorized_context = UserContext(
            user_id=uuid4(),
            user_type="registered_user",
            email="user@example.com",
            permissions=[]
        )
        
        with patch('app.core.auth.get_current_user', return_value=unauthorized_context), \
             patch('app.core.middleware.require_mobile_attestation', return_value={}):
            
            response = client.post(
                "/api/v1/feedback/feedback",
                json=sample_feedback_data
            )
            
            assert response.status_code == status.HTTP_403_FORBIDDEN
            data = response.json()
            assert data["detail"]["error_code"] == "ACCESS_DENIED"
    
    @pytest.mark.asyncio
    async def test_submit_feedback_unauthorized_role(
        self,
        client,
        sample_feedback_data
    ):
        """Test feedback submission by unauthorized role"""
        office_staff_context = UserContext(
            user_id=uuid4(),
            user_type="firm_personnel",
            email="office@security.com",
            firm_id=uuid4(),
            role="office_staff",
            permissions=["feedback:view"]
        )
        
        with patch('app.core.auth.get_current_user', return_value=office_staff_context), \
             patch('app.core.middleware.require_mobile_attestation', return_value={}):
            
            response = client.post(
                "/api/v1/feedback/feedback",
                json=sample_feedback_data
            )
            
            assert response.status_code == status.HTTP_403_FORBIDDEN
            data = response.json()
            assert data["detail"]["error_code"] == "INSUFFICIENT_PERMISSIONS"
    
    @pytest.mark.asyncio
    async def test_submit_feedback_invalid_data(
        self,
        client,
        mock_firm_personnel_context
    ):
        """Test feedback submission with invalid data"""
        invalid_data = {
            "request_id": str(uuid4()),
            "performance_rating": 6,  # Invalid rating
            "comments": "x" * 1001    # Too long
        }
        
        with patch('app.core.auth.get_current_user', return_value=mock_firm_personnel_context), \
             patch('app.core.middleware.require_mobile_attestation', return_value={}):
            
            response = client.post(
                "/api/v1/feedback/feedback",
                json=invalid_data
            )
            
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.asyncio
    async def test_submit_feedback_service_error(
        self,
        client,
        sample_feedback_data,
        mock_firm_personnel_context
    ):
        """Test feedback submission with service error"""
        with patch('app.core.auth.get_current_user', return_value=mock_firm_personnel_context), \
             patch('app.core.middleware.require_mobile_attestation', return_value={}), \
             patch('app.services.feedback.FeedbackService.submit_feedback', 
                   side_effect=InvalidFeedbackError("Request not completed")):
            
            response = client.post(
                "/api/v1/feedback/feedback",
                json=sample_feedback_data
            )
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            data = response.json()
            assert "Request not completed" in data["detail"]["message"]
    
    @pytest.mark.asyncio
    async def test_get_feedback_success(
        self,
        client,
        mock_firm_personnel_context,
        mock_feedback
    ):
        """Test successful feedback retrieval"""
        with patch('app.core.auth.get_current_user', return_value=mock_firm_personnel_context), \
             patch('app.core.middleware.require_mobile_attestation', return_value={}), \
             patch('app.services.feedback.FeedbackService.get_feedback_by_id', return_value=mock_feedback):
            
            # Set firm_id to match
            mock_feedback.team_member.firm_id = mock_firm_personnel_context.firm_id
            
            response = client.get(f"/api/v1/feedback/feedback/{mock_feedback.id}")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == str(mock_feedback.id)
            assert data["team_member_name"] == "John Doe"
    
    @pytest.mark.asyncio
    async def test_get_feedback_not_found(
        self,
        client,
        mock_firm_personnel_context
    ):
        """Test feedback retrieval when not found"""
        with patch('app.core.auth.get_current_user', return_value=mock_firm_personnel_context), \
             patch('app.core.middleware.require_mobile_attestation', return_value={}), \
             patch('app.services.feedback.FeedbackService.get_feedback_by_id', return_value=None):
            
            response = client.get(f"/api/v1/feedback/feedback/{uuid4()}")
            
            assert response.status_code == status.HTTP_404_NOT_FOUND
            data = response.json()
            assert data["detail"]["error_code"] == "FEEDBACK_NOT_FOUND"
    
    @pytest.mark.asyncio
    async def test_get_feedback_unauthorized_firm(
        self,
        client,
        mock_firm_personnel_context,
        mock_feedback
    ):
        """Test feedback retrieval by unauthorized firm"""
        with patch('app.core.auth.get_current_user', return_value=mock_firm_personnel_context), \
             patch('app.core.middleware.require_mobile_attestation', return_value={}), \
             patch('app.services.feedback.FeedbackService.get_feedback_by_id', return_value=mock_feedback):
            
            # Set different firm_id
            mock_feedback.team_member.firm_id = uuid4()
            
            response = client.get(f"/api/v1/feedback/feedback/{mock_feedback.id}")
            
            assert response.status_code == status.HTTP_403_FORBIDDEN
            data = response.json()
            assert data["detail"]["error_code"] == "ACCESS_DENIED"
    
    @pytest.mark.asyncio
    async def test_get_request_feedback_success(
        self,
        client,
        mock_firm_personnel_context,
        mock_feedback
    ):
        """Test successful request feedback retrieval"""
        with patch('app.core.auth.get_current_user', return_value=mock_firm_personnel_context), \
             patch('app.core.middleware.require_mobile_attestation', return_value={}), \
             patch('app.services.feedback.FeedbackService.get_request_feedback', return_value=mock_feedback):
            
            # Set firm_id to match
            mock_feedback.team_member.firm_id = mock_firm_personnel_context.firm_id
            
            response = client.get(f"/api/v1/feedback/requests/{mock_feedback.request_id}/feedback")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["request_id"] == str(mock_feedback.request_id)
    
    @pytest.mark.asyncio
    async def test_get_request_feedback_not_found(
        self,
        client,
        mock_firm_personnel_context
    ):
        """Test request feedback retrieval when not found"""
        with patch('app.core.auth.get_current_user', return_value=mock_firm_personnel_context), \
             patch('app.core.middleware.require_mobile_attestation', return_value={}), \
             patch('app.services.feedback.FeedbackService.get_request_feedback', return_value=None):
            
            response = client.get(f"/api/v1/feedback/requests/{uuid4()}/feedback")
            
            assert response.status_code == status.HTTP_404_NOT_FOUND
            data = response.json()
            assert data["detail"]["error_code"] == "FEEDBACK_NOT_FOUND"
    
    @pytest.mark.asyncio
    async def test_get_team_member_feedback_success(
        self,
        client,
        mock_firm_personnel_context,
        mock_feedback
    ):
        """Test successful team member feedback retrieval"""
        with patch('app.core.auth.get_current_user', return_value=mock_firm_personnel_context), \
             patch('app.services.feedback.FeedbackService.get_team_member_feedback', return_value=[mock_feedback]):
            
            # Mock team member lookup
            team_member = MagicMock()
            team_member.firm_id = mock_firm_personnel_context.firm_id
            
            with patch('app.core.database.get_db') as mock_get_db:
                mock_db = AsyncMock()
                mock_db.execute.return_value.scalar_one_or_none.return_value = team_member
                mock_get_db.return_value = mock_db
                
                response = client.get(f"/api/v1/feedback/team-members/{uuid4()}/feedback")
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert len(data["feedback"]) == 1
                assert data["feedback"][0]["id"] == str(mock_feedback.id)
    
    @pytest.mark.asyncio
    async def test_get_team_member_feedback_unauthorized_firm(
        self,
        client,
        mock_firm_personnel_context
    ):
        """Test team member feedback retrieval by unauthorized firm"""
        # Mock team member from different firm
        team_member = MagicMock()
        team_member.firm_id = uuid4()  # Different firm
        
        with patch('app.core.auth.get_current_user', return_value=mock_firm_personnel_context), \
             patch('app.core.database.get_db') as mock_get_db:
            
            mock_db = AsyncMock()
            mock_db.execute.return_value.scalar_one_or_none.return_value = team_member
            mock_get_db.return_value = mock_db
            
            response = client.get(f"/api/v1/feedback/team-members/{uuid4()}/feedback")
            
            assert response.status_code == status.HTTP_403_FORBIDDEN
            data = response.json()
            assert data["detail"]["error_code"] == "ACCESS_DENIED"
    
    @pytest.mark.asyncio
    async def test_update_feedback_success(
        self,
        client,
        mock_firm_personnel_context,
        mock_feedback
    ):
        """Test successful feedback update"""
        update_data = {
            "is_prank": True,
            "performance_rating": 2,
            "comments": "Updated: This was actually a prank"
        }
        
        with patch('app.core.auth.get_current_user', return_value=mock_firm_personnel_context), \
             patch('app.core.middleware.require_mobile_attestation', return_value={}), \
             patch('app.services.feedback.FeedbackService.update_feedback', return_value=mock_feedback):
            
            response = client.put(
                f"/api/v1/feedback/feedback/{mock_feedback.id}",
                json=update_data
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == str(mock_feedback.id)
    
    @pytest.mark.asyncio
    async def test_update_feedback_unauthorized(
        self,
        client,
        mock_firm_personnel_context
    ):
        """Test feedback update by unauthorized user"""
        update_data = {"is_prank": True}
        
        with patch('app.core.auth.get_current_user', return_value=mock_firm_personnel_context), \
             patch('app.core.middleware.require_mobile_attestation', return_value={}), \
             patch('app.services.feedback.FeedbackService.update_feedback', 
                   side_effect=UnauthorizedFeedbackError("Only the original submitter can update feedback")):
            
            response = client.put(
                f"/api/v1/feedback/feedback/{uuid4()}",
                json=update_data
            )
            
            assert response.status_code == status.HTTP_403_FORBIDDEN
            data = response.json()
            assert "Only the original submitter can update feedback" in data["detail"]["message"]
    
    @pytest.mark.asyncio
    async def test_get_firm_feedback_statistics_success(
        self,
        client,
        mock_firm_personnel_context
    ):
        """Test successful firm feedback statistics retrieval"""
        mock_statistics = {
            "total_feedback": 100,
            "prank_count": 5,
            "prank_rate_percentage": 5.0,
            "rated_feedback_count": 95,
            "average_rating": 4.2,
            "rating_distribution": {"1": 2, "2": 3, "3": 10, "4": 40, "5": 40},
            "date_range": {"from": None, "to": None}
        }
        
        with patch('app.core.auth.get_current_user', return_value=mock_firm_personnel_context), \
             patch('app.services.feedback.FeedbackService.get_firm_feedback_statistics', 
                   return_value=mock_statistics):
            
            response = client.get(f"/api/v1/feedback/firms/{mock_firm_personnel_context.firm_id}/feedback/statistics")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["total_feedback"] == 100
            assert data["prank_count"] == 5
            assert data["prank_rate_percentage"] == 5.0
            assert data["average_rating"] == 4.2
    
    @pytest.mark.asyncio
    async def test_get_firm_feedback_statistics_unauthorized_firm(
        self,
        client,
        mock_firm_personnel_context
    ):
        """Test firm feedback statistics retrieval for unauthorized firm"""
        different_firm_id = uuid4()
        
        with patch('app.core.auth.get_current_user', return_value=mock_firm_personnel_context):
            
            response = client.get(f"/api/v1/feedback/firms/{different_firm_id}/feedback/statistics")
            
            assert response.status_code == status.HTTP_403_FORBIDDEN
            data = response.json()
            assert data["detail"]["error_code"] == "ACCESS_DENIED"
    
    @pytest.mark.asyncio
    async def test_get_prank_flagged_users_success(
        self,
        client,
        mock_firm_personnel_context
    ):
        """Test successful prank flagged users retrieval"""
        mock_users = [
            {
                "user_id": str(uuid4()),
                "email": "user1@example.com",
                "phone": "+1234567890",
                "first_name": "John",
                "last_name": "Doe",
                "total_prank_flags": 5,
                "firm_prank_count": 3
            },
            {
                "user_id": str(uuid4()),
                "email": "user2@example.com",
                "phone": "+1234567891",
                "first_name": "Jane",
                "last_name": "Smith",
                "total_prank_flags": 4,
                "firm_prank_count": 2
            }
        ]
        
        with patch('app.core.auth.get_current_user', return_value=mock_firm_personnel_context), \
             patch('app.services.feedback.FeedbackService.get_prank_flagged_users', 
                   return_value=mock_users):
            
            response = client.get(f"/api/v1/feedback/firms/{mock_firm_personnel_context.firm_id}/prank-flagged-users")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 2
            assert data[0]["email"] == "user1@example.com"
            assert data[0]["total_prank_flags"] == 5
            assert data[1]["email"] == "user2@example.com"
            assert data[1]["total_prank_flags"] == 4
    
    @pytest.mark.asyncio
    async def test_get_prank_flagged_users_with_filters(
        self,
        client,
        mock_firm_personnel_context
    ):
        """Test prank flagged users retrieval with filters"""
        with patch('app.core.auth.get_current_user', return_value=mock_firm_personnel_context), \
             patch('app.services.feedback.FeedbackService.get_prank_flagged_users', 
                   return_value=[]) as mock_service:
            
            response = client.get(
                f"/api/v1/feedback/firms/{mock_firm_personnel_context.firm_id}/prank-flagged-users"
                "?min_prank_flags=5&limit=25"
            )
            
            assert response.status_code == status.HTTP_200_OK
            
            # Verify service was called with correct parameters
            mock_service.assert_called_once_with(
                firm_id=mock_firm_personnel_context.firm_id,
                min_prank_flags=5,
                limit=25
            )
    
    @pytest.mark.asyncio
    async def test_admin_can_access_all_feedback(
        self,
        client,
        mock_admin_context,
        mock_feedback
    ):
        """Test that admin can access feedback from any firm"""
        with patch('app.core.auth.get_current_user', return_value=mock_admin_context), \
             patch('app.core.middleware.require_mobile_attestation', return_value={}), \
             patch('app.services.feedback.FeedbackService.get_feedback_by_id', return_value=mock_feedback):
            
            response = client.get(f"/api/v1/feedback/feedback/{mock_feedback.id}")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == str(mock_feedback.id)
    
    @pytest.mark.asyncio
    async def test_non_firm_non_admin_cannot_access_feedback(
        self,
        client,
        mock_feedback
    ):
        """Test that non-firm, non-admin users cannot access feedback"""
        regular_user_context = UserContext(
            user_id=uuid4(),
            user_type="registered_user",
            email="user@example.com",
            permissions=[]
        )
        
        with patch('app.core.auth.get_current_user', return_value=regular_user_context), \
             patch('app.core.middleware.require_mobile_attestation', return_value={}), \
             patch('app.services.feedback.FeedbackService.get_feedback_by_id', return_value=mock_feedback):
            
            response = client.get(f"/api/v1/feedback/feedback/{mock_feedback.id}")
            
            assert response.status_code == status.HTTP_403_FORBIDDEN
            data = response.json()
            assert data["detail"]["error_code"] == "ACCESS_DENIED"