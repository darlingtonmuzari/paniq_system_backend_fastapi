"""
Unit tests for emergency field agent functionality
"""
import pytest
from datetime import datetime
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.emergency import EmergencyService, EmergencyRequestError
from app.models.emergency import PanicRequest, RequestStatusUpdate, RequestFeedback
from app.models.security_firm import FirmPersonnel
from app.models.user import UserGroup, RegisteredUser


class TestEmergencyFieldAgent:
    """Test cases for field agent functionality"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def emergency_service(self, mock_db):
        """Emergency service instance with mocked dependencies"""
        service = EmergencyService(mock_db)
        service.geolocation_service = AsyncMock()
        service.subscription_service = AsyncMock()
        return service
    
    @pytest.fixture
    def mock_panic_request(self):
        """Mock panic request"""
        request = MagicMock(spec=PanicRequest)
        request.id = uuid4()
        request.status = "assigned"
        request.service_type = "security"
        request.assigned_team_id = uuid4()
        request.group_id = uuid4()
        request.accepted_at = None
        request.arrived_at = None
        request.completed_at = None
        return request
    
    @pytest.fixture
    def mock_agent(self):
        """Mock field agent"""
        agent = MagicMock(spec=FirmPersonnel)
        agent.id = uuid4()
        agent.first_name = "John"
        agent.last_name = "Doe"
        agent.team_id = uuid4()
        agent.role = "field_agent"
        return agent
    
    @pytest.fixture
    def mock_group_with_user(self):
        """Mock group with user"""
        user = MagicMock(spec=RegisteredUser)
        user.id = uuid4()
        user.prank_flags = 0
        
        group = MagicMock(spec=UserGroup)
        group.id = uuid4()
        group.user = user
        
        return group
    
    @pytest.mark.asyncio
    async def test_get_agent_assigned_requests(self, emergency_service, mock_agent):
        """Test getting requests assigned to an agent"""
        agent_id = mock_agent.id
        mock_requests = [MagicMock(spec=PanicRequest) for _ in range(2)]
        
        # Mock agent lookup
        emergency_service.db.execute.return_value.scalar_one_or_none.return_value = mock_agent
        
        # Mock requests query
        emergency_service.db.execute.return_value.scalars.return_value.all.return_value = mock_requests
        
        result = await emergency_service.get_agent_assigned_requests(agent_id)
        
        assert len(result) == 2
        # Verify two database calls were made (agent lookup + requests query)
        assert emergency_service.db.execute.call_count == 2
    
    @pytest.mark.asyncio
    async def test_get_agent_assigned_requests_no_team(self, emergency_service):
        """Test getting requests when agent has no team"""
        agent_id = uuid4()
        
        # Mock agent with no team
        mock_agent = MagicMock(spec=FirmPersonnel)
        mock_agent.team_id = None
        emergency_service.db.execute.return_value.scalar_one_or_none.return_value = mock_agent
        
        result = await emergency_service.get_agent_assigned_requests(agent_id)
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_accept_request_success(
        self,
        emergency_service,
        mock_panic_request,
        mock_agent
    ):
        """Test successful request acceptance"""
        # Set up matching team IDs
        mock_panic_request.assigned_team_id = mock_agent.team_id
        
        # Mock get_request_by_id
        emergency_service.get_request_by_id = AsyncMock(return_value=mock_panic_request)
        
        # Mock agent lookup
        emergency_service.db.execute.return_value.scalar_one_or_none.return_value = mock_agent
        
        result = await emergency_service.accept_request(
            request_id=mock_panic_request.id,
            agent_id=mock_agent.id,
            estimated_arrival_minutes=15
        )
        
        assert result is True
        assert mock_panic_request.status == "accepted"
        assert mock_panic_request.accepted_at is not None
        emergency_service.db.add.assert_called()
        emergency_service.db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_accept_request_not_found(self, emergency_service):
        """Test accepting non-existent request"""
        request_id = uuid4()
        agent_id = uuid4()
        
        emergency_service.get_request_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(EmergencyRequestError) as exc_info:
            await emergency_service.accept_request(
                request_id=request_id,
                agent_id=agent_id
            )
        
        assert "not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_accept_request_wrong_status(
        self,
        emergency_service,
        mock_panic_request
    ):
        """Test accepting request in wrong status"""
        mock_panic_request.status = "completed"
        
        emergency_service.get_request_by_id = AsyncMock(return_value=mock_panic_request)
        
        with pytest.raises(EmergencyRequestError) as exc_info:
            await emergency_service.accept_request(
                request_id=mock_panic_request.id,
                agent_id=uuid4()
            )
        
        assert "not in assigned status" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_accept_request_wrong_team(
        self,
        emergency_service,
        mock_panic_request,
        mock_agent
    ):
        """Test accepting request when agent is not in assigned team"""
        # Set different team IDs
        mock_panic_request.assigned_team_id = uuid4()
        mock_agent.team_id = uuid4()
        
        emergency_service.get_request_by_id = AsyncMock(return_value=mock_panic_request)
        emergency_service.db.execute.return_value.scalar_one_or_none.return_value = mock_agent
        
        with pytest.raises(EmergencyRequestError) as exc_info:
            await emergency_service.accept_request(
                request_id=mock_panic_request.id,
                agent_id=mock_agent.id
            )
        
        assert "not part of the assigned team" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_reject_request_success(
        self,
        emergency_service,
        mock_panic_request,
        mock_agent
    ):
        """Test successful request rejection"""
        # Set up matching team IDs
        mock_panic_request.assigned_team_id = mock_agent.team_id
        
        emergency_service.get_request_by_id = AsyncMock(return_value=mock_panic_request)
        emergency_service.db.execute.return_value.scalar_one_or_none.return_value = mock_agent
        
        result = await emergency_service.reject_request(
            request_id=mock_panic_request.id,
            agent_id=mock_agent.id,
            reason="Unable to respond due to other emergency"
        )
        
        assert result is True
        assert mock_panic_request.status == "pending"
        assert mock_panic_request.assigned_team_id is None
        emergency_service.db.add.assert_called()
        emergency_service.db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_agent_location_success(
        self,
        emergency_service,
        mock_panic_request,
        mock_agent
    ):
        """Test successful agent location update"""
        mock_panic_request.status = "accepted"
        mock_panic_request.assigned_team_id = mock_agent.team_id
        
        emergency_service.get_request_by_id = AsyncMock(return_value=mock_panic_request)
        emergency_service.db.execute.return_value.scalar_one_or_none.return_value = mock_agent
        
        result = await emergency_service.update_agent_location(
            request_id=mock_panic_request.id,
            agent_id=mock_agent.id,
            latitude=40.7128,
            longitude=-74.0060,
            status_message="En route to location"
        )
        
        assert result is True
        assert mock_panic_request.status == "en_route"
        emergency_service.db.add.assert_called()
        emergency_service.db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_agent_location_wrong_status(
        self,
        emergency_service,
        mock_panic_request,
        mock_agent
    ):
        """Test location update with wrong request status"""
        mock_panic_request.status = "pending"
        
        emergency_service.get_request_by_id = AsyncMock(return_value=mock_panic_request)
        
        with pytest.raises(EmergencyRequestError) as exc_info:
            await emergency_service.update_agent_location(
                request_id=mock_panic_request.id,
                agent_id=mock_agent.id,
                latitude=40.7128,
                longitude=-74.0060
            )
        
        assert "not in a trackable status" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_mark_arrived_success(
        self,
        emergency_service,
        mock_panic_request,
        mock_agent
    ):
        """Test successful arrival marking"""
        mock_panic_request.status = "en_route"
        mock_panic_request.assigned_team_id = mock_agent.team_id
        
        emergency_service.get_request_by_id = AsyncMock(return_value=mock_panic_request)
        emergency_service.db.execute.return_value.scalar_one_or_none.return_value = mock_agent
        
        result = await emergency_service.mark_arrived(
            request_id=mock_panic_request.id,
            agent_id=mock_agent.id,
            arrival_notes="Arrived at scene, assessing situation"
        )
        
        assert result is True
        assert mock_panic_request.status == "arrived"
        assert mock_panic_request.arrived_at is not None
        emergency_service.db.add.assert_called()
        emergency_service.db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_mark_arrived_wrong_status(
        self,
        emergency_service,
        mock_panic_request
    ):
        """Test arrival marking with wrong status"""
        mock_panic_request.status = "pending"
        
        emergency_service.get_request_by_id = AsyncMock(return_value=mock_panic_request)
        
        with pytest.raises(EmergencyRequestError) as exc_info:
            await emergency_service.mark_arrived(
                request_id=mock_panic_request.id,
                agent_id=uuid4()
            )
        
        assert "not in a status that can be marked as arrived" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_complete_request_with_feedback_success(
        self,
        emergency_service,
        mock_panic_request,
        mock_agent,
        mock_group_with_user
    ):
        """Test successful request completion with feedback"""
        mock_panic_request.status = "arrived"
        mock_panic_request.assigned_team_id = mock_agent.team_id
        mock_panic_request.group_id = mock_group_with_user.id
        
        emergency_service.get_request_by_id = AsyncMock(return_value=mock_panic_request)
        emergency_service.db.execute.return_value.scalar_one_or_none.side_effect = [
            mock_agent,  # Agent lookup
            mock_group_with_user  # Group lookup for prank handling
        ]
        
        result = await emergency_service.complete_request_with_feedback(
            request_id=mock_panic_request.id,
            agent_id=mock_agent.id,
            is_prank=False,
            performance_rating=4,
            completion_notes="Service completed successfully"
        )
        
        assert result is True
        assert mock_panic_request.status == "completed"
        assert mock_panic_request.completed_at is not None
        # Should add both feedback and status update
        assert emergency_service.db.add.call_count == 2
        emergency_service.db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_complete_request_with_prank_flag(
        self,
        emergency_service,
        mock_panic_request,
        mock_agent,
        mock_group_with_user
    ):
        """Test request completion with prank flag"""
        mock_panic_request.status = "arrived"
        mock_panic_request.assigned_team_id = mock_agent.team_id
        mock_panic_request.group_id = mock_group_with_user.id
        
        emergency_service.get_request_by_id = AsyncMock(return_value=mock_panic_request)
        emergency_service.db.execute.return_value.scalar_one_or_none.side_effect = [
            mock_agent,  # Agent lookup
            mock_group_with_user  # Group lookup for prank handling
        ]
        
        result = await emergency_service.complete_request_with_feedback(
            request_id=mock_panic_request.id,
            agent_id=mock_agent.id,
            is_prank=True,
            performance_rating=1,
            completion_notes="False alarm - prank call"
        )
        
        assert result is True
        assert mock_panic_request.status == "completed"
        # Verify prank flag was incremented
        assert mock_group_with_user.user.prank_flags == 1
    
    @pytest.mark.asyncio
    async def test_complete_request_invalid_rating(
        self,
        emergency_service,
        mock_panic_request,
        mock_agent
    ):
        """Test completion with invalid performance rating"""
        mock_panic_request.status = "arrived"
        mock_panic_request.assigned_team_id = mock_agent.team_id
        
        emergency_service.get_request_by_id = AsyncMock(return_value=mock_panic_request)
        emergency_service.db.execute.return_value.scalar_one_or_none.return_value = mock_agent
        
        with pytest.raises(EmergencyRequestError) as exc_info:
            await emergency_service.complete_request_with_feedback(
                request_id=mock_panic_request.id,
                agent_id=mock_agent.id,
                performance_rating=6  # Invalid rating
            )
        
        assert "Performance rating must be between 1 and 5" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_complete_request_wrong_status(
        self,
        emergency_service,
        mock_panic_request
    ):
        """Test completion with wrong request status"""
        mock_panic_request.status = "pending"
        
        emergency_service.get_request_by_id = AsyncMock(return_value=mock_panic_request)
        
        with pytest.raises(EmergencyRequestError) as exc_info:
            await emergency_service.complete_request_with_feedback(
                request_id=mock_panic_request.id,
                agent_id=uuid4()
            )
        
        assert "not in a status that can be completed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_agent_active_requests(self, emergency_service):
        """Test getting active requests for an agent"""
        agent_id = uuid4()
        
        # Mock the get_agent_assigned_requests method
        emergency_service.get_agent_assigned_requests = AsyncMock(
            return_value=[MagicMock(spec=PanicRequest)]
        )
        
        result = await emergency_service.get_agent_active_requests(agent_id)
        
        assert len(result) == 1
        emergency_service.get_agent_assigned_requests.assert_called_once_with(
            agent_id=agent_id,
            status_filter=None
        )
    
    @pytest.mark.asyncio
    async def test_get_request_location_updates(self, emergency_service):
        """Test getting location updates for a request"""
        request_id = uuid4()
        mock_updates = [MagicMock(spec=RequestStatusUpdate) for _ in range(3)]
        
        emergency_service.db.execute.return_value.scalars.return_value.all.return_value = mock_updates
        
        result = await emergency_service.get_request_location_updates(request_id)
        
        assert len(result) == 3
        emergency_service.db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_prank_flag_increments_counter(
        self,
        emergency_service,
        mock_group_with_user
    ):
        """Test that prank flag handling increments user's prank counter"""
        emergency_service.db.execute.return_value.scalar_one_or_none.return_value = mock_group_with_user
        
        await emergency_service._handle_prank_flag(mock_group_with_user.id)
        
        assert mock_group_with_user.user.prank_flags == 1
    
    @pytest.mark.asyncio
    async def test_handle_prank_flag_no_group(self, emergency_service):
        """Test prank flag handling when group not found"""
        group_id = uuid4()
        emergency_service.db.execute.return_value.scalar_one_or_none.return_value = None
        
        # Should not raise an error, just do nothing
        await emergency_service._handle_prank_flag(group_id)
        
        # No assertions needed, just verify it doesn't crash


class TestEmergencyFieldAgentIntegration:
    """Integration tests for field agent functionality"""
    
    @pytest.mark.asyncio
    async def test_complete_request_workflow(self):
        """
        Test the complete field agent workflow:
        1. Agent accepts request (assigned -> accepted)
        2. Agent updates location (accepted -> en_route)
        3. Agent marks arrival (en_route -> arrived)
        4. Agent completes with feedback (arrived -> completed)
        """
        # This would be an integration test with actual database
        # Testing the complete workflow from assignment to completion
        pass
    
    @pytest.mark.asyncio
    async def test_prank_detection_and_user_flagging(self):
        """
        Test that prank detection properly flags users:
        1. Agent completes request with prank flag
        2. User's prank count is incremented
        3. Multiple prank flags lead to user penalties
        """
        pass
    
    @pytest.mark.asyncio
    async def test_location_tracking_accuracy(self):
        """
        Test that location tracking works accurately:
        1. Agent provides location updates
        2. Location history is stored correctly
        3. Real-time updates are sent to requesters
        """
        pass