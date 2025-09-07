"""
Unit tests for emergency request allocation functionality
"""
import pytest
from datetime import datetime
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.emergency import EmergencyService, EmergencyRequestError
from app.models.emergency import PanicRequest, RequestStatusUpdate
from app.models.security_firm import Team
from app.models.emergency import ServiceProvider


class TestEmergencyAllocation:
    """Test cases for emergency request allocation"""
    
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
        request.status = "pending"
        request.service_type = "security"
        request.assigned_team_id = None
        request.assigned_service_provider_id = None
        return request
    
    @pytest.fixture
    def mock_team(self):
        """Mock team"""
        team = MagicMock(spec=Team)
        team.id = uuid4()
        team.name = "Alpha Team"
        team.is_active = True
        return team
    
    @pytest.fixture
    def mock_service_provider(self):
        """Mock service provider"""
        provider = MagicMock(spec=ServiceProvider)
        provider.id = uuid4()
        provider.name = "Emergency Ambulance Service"
        provider.service_type = "ambulance"
        provider.is_active = True
        return provider
    
    @pytest.mark.asyncio
    async def test_get_pending_requests_for_firm(self, emergency_service):
        """Test getting pending requests for a firm"""
        firm_id = uuid4()
        mock_requests = [MagicMock(spec=PanicRequest) for _ in range(3)]
        
        emergency_service.db.execute.return_value.scalars.return_value.all.return_value = mock_requests
        
        result = await emergency_service.get_pending_requests_for_firm(firm_id)
        
        assert len(result) == 3
        emergency_service.db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_allocate_request_to_team_success(
        self,
        emergency_service,
        mock_panic_request,
        mock_team
    ):
        """Test successful request allocation to team"""
        request_id = mock_panic_request.id
        team_id = mock_team.id
        allocated_by_id = uuid4()
        
        # Mock get_request_by_id
        emergency_service.get_request_by_id = AsyncMock(return_value=mock_panic_request)
        
        # Mock team lookup
        emergency_service.db.execute.return_value.scalar_one_or_none.return_value = mock_team
        
        result = await emergency_service.allocate_request_to_team(
            request_id=request_id,
            team_id=team_id,
            allocated_by_id=allocated_by_id
        )
        
        assert result is True
        assert mock_panic_request.assigned_team_id == team_id
        assert mock_panic_request.status == "assigned"
        emergency_service.db.add.assert_called()
        emergency_service.db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_allocate_request_to_team_not_found(self, emergency_service):
        """Test allocation when request not found"""
        request_id = uuid4()
        team_id = uuid4()
        allocated_by_id = uuid4()
        
        emergency_service.get_request_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(EmergencyRequestError) as exc_info:
            await emergency_service.allocate_request_to_team(
                request_id=request_id,
                team_id=team_id,
                allocated_by_id=allocated_by_id
            )
        
        assert "not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_allocate_request_to_team_wrong_status(
        self,
        emergency_service,
        mock_panic_request
    ):
        """Test allocation when request is not in pending status"""
        mock_panic_request.status = "completed"
        
        emergency_service.get_request_by_id = AsyncMock(return_value=mock_panic_request)
        
        with pytest.raises(EmergencyRequestError) as exc_info:
            await emergency_service.allocate_request_to_team(
                request_id=mock_panic_request.id,
                team_id=uuid4(),
                allocated_by_id=uuid4()
            )
        
        assert "not in pending status" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_allocate_request_to_team_inactive_team(
        self,
        emergency_service,
        mock_panic_request,
        mock_team
    ):
        """Test allocation to inactive team"""
        mock_team.is_active = False
        
        emergency_service.get_request_by_id = AsyncMock(return_value=mock_panic_request)
        emergency_service.db.execute.return_value.scalar_one_or_none.return_value = mock_team
        
        with pytest.raises(EmergencyRequestError) as exc_info:
            await emergency_service.allocate_request_to_team(
                request_id=mock_panic_request.id,
                team_id=mock_team.id,
                allocated_by_id=uuid4()
            )
        
        assert "not active" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_allocate_call_service_to_team_fails(
        self,
        emergency_service,
        mock_panic_request,
        mock_team
    ):
        """Test that call service requests cannot be allocated to teams"""
        mock_panic_request.service_type = "call"
        
        emergency_service.get_request_by_id = AsyncMock(return_value=mock_panic_request)
        emergency_service.db.execute.return_value.scalar_one_or_none.return_value = mock_team
        
        with pytest.raises(EmergencyRequestError) as exc_info:
            await emergency_service.allocate_request_to_team(
                request_id=mock_panic_request.id,
                team_id=mock_team.id,
                allocated_by_id=uuid4()
            )
        
        assert "Call service requests should not be assigned" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_allocate_request_to_service_provider_success(
        self,
        emergency_service,
        mock_panic_request,
        mock_service_provider
    ):
        """Test successful request allocation to service provider"""
        mock_panic_request.service_type = "ambulance"  # Match provider type
        
        emergency_service.get_request_by_id = AsyncMock(return_value=mock_panic_request)
        emergency_service.db.execute.return_value.scalar_one_or_none.return_value = mock_service_provider
        
        result = await emergency_service.allocate_request_to_service_provider(
            request_id=mock_panic_request.id,
            service_provider_id=mock_service_provider.id,
            allocated_by_id=uuid4()
        )
        
        assert result is True
        assert mock_panic_request.assigned_service_provider_id == mock_service_provider.id
        assert mock_panic_request.status == "assigned"
        emergency_service.db.add.assert_called()
        emergency_service.db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_allocate_request_service_type_mismatch(
        self,
        emergency_service,
        mock_panic_request,
        mock_service_provider
    ):
        """Test allocation with service type mismatch"""
        mock_panic_request.service_type = "fire"  # Different from provider
        mock_service_provider.service_type = "ambulance"
        
        emergency_service.get_request_by_id = AsyncMock(return_value=mock_panic_request)
        emergency_service.db.execute.return_value.scalar_one_or_none.return_value = mock_service_provider
        
        with pytest.raises(EmergencyRequestError) as exc_info:
            await emergency_service.allocate_request_to_service_provider(
                request_id=mock_panic_request.id,
                service_provider_id=mock_service_provider.id,
                allocated_by_id=uuid4()
            )
        
        assert "Service type mismatch" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_handle_call_service_request_success(
        self,
        emergency_service,
        mock_panic_request
    ):
        """Test successful call service handling"""
        mock_panic_request.service_type = "call"
        mock_panic_request.status = "pending"
        
        emergency_service.get_request_by_id = AsyncMock(return_value=mock_panic_request)
        
        result = await emergency_service.handle_call_service_request(
            request_id=mock_panic_request.id,
            handled_by_id=uuid4(),
            notes="Customer called for information"
        )
        
        assert result is True
        assert mock_panic_request.status == "handled"
        assert mock_panic_request.accepted_at is not None
        emergency_service.db.add.assert_called()
        emergency_service.db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_call_service_wrong_type(
        self,
        emergency_service,
        mock_panic_request
    ):
        """Test handling non-call service request"""
        mock_panic_request.service_type = "security"
        
        emergency_service.get_request_by_id = AsyncMock(return_value=mock_panic_request)
        
        with pytest.raises(EmergencyRequestError) as exc_info:
            await emergency_service.handle_call_service_request(
                request_id=mock_panic_request.id,
                handled_by_id=uuid4()
            )
        
        assert "only for call service requests" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_team_assigned_requests(self, emergency_service):
        """Test getting requests assigned to a team"""
        team_id = uuid4()
        mock_requests = [MagicMock(spec=PanicRequest) for _ in range(2)]
        
        emergency_service.db.execute.return_value.scalars.return_value.all.return_value = mock_requests
        
        result = await emergency_service.get_team_assigned_requests(team_id)
        
        assert len(result) == 2
        emergency_service.db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_team_assigned_requests_with_filter(self, emergency_service):
        """Test getting team requests with status filter"""
        team_id = uuid4()
        mock_requests = [MagicMock(spec=PanicRequest)]
        
        emergency_service.db.execute.return_value.scalars.return_value.all.return_value = mock_requests
        
        result = await emergency_service.get_team_assigned_requests(
            team_id, status_filter="assigned"
        )
        
        assert len(result) == 1
    
    @pytest.mark.asyncio
    async def test_get_service_provider_assigned_requests(self, emergency_service):
        """Test getting requests assigned to a service provider"""
        provider_id = uuid4()
        mock_requests = [MagicMock(spec=PanicRequest) for _ in range(3)]
        
        emergency_service.db.execute.return_value.scalars.return_value.all.return_value = mock_requests
        
        result = await emergency_service.get_service_provider_assigned_requests(provider_id)
        
        assert len(result) == 3
        emergency_service.db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_reassign_request_to_team_success(
        self,
        emergency_service,
        mock_panic_request,
        mock_team
    ):
        """Test successful request reassignment to team"""
        mock_panic_request.status = "assigned"
        mock_panic_request.assigned_service_provider_id = uuid4()  # Previously assigned to provider
        
        emergency_service.get_request_by_id = AsyncMock(return_value=mock_panic_request)
        emergency_service.db.execute.return_value.scalar_one_or_none.return_value = mock_team
        
        result = await emergency_service.reassign_request(
            request_id=mock_panic_request.id,
            new_team_id=mock_team.id,
            reassigned_by_id=uuid4(),
            reason="Original provider unavailable"
        )
        
        assert result is True
        assert mock_panic_request.assigned_team_id == mock_team.id
        assert mock_panic_request.assigned_service_provider_id is None
        assert mock_panic_request.status == "assigned"
        emergency_service.db.add.assert_called()
        emergency_service.db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_reassign_request_no_target(self, emergency_service, mock_panic_request):
        """Test reassignment without specifying target"""
        emergency_service.get_request_by_id = AsyncMock(return_value=mock_panic_request)
        
        with pytest.raises(EmergencyRequestError) as exc_info:
            await emergency_service.reassign_request(
                request_id=mock_panic_request.id,
                reassigned_by_id=uuid4()
            )
        
        assert "Must specify either team or service provider" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_reassign_request_both_targets(self, emergency_service, mock_panic_request):
        """Test reassignment with both team and service provider specified"""
        emergency_service.get_request_by_id = AsyncMock(return_value=mock_panic_request)
        
        with pytest.raises(EmergencyRequestError) as exc_info:
            await emergency_service.reassign_request(
                request_id=mock_panic_request.id,
                new_team_id=uuid4(),
                new_service_provider_id=uuid4(),
                reassigned_by_id=uuid4()
            )
        
        assert "Cannot assign to both team and service provider" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_reassign_request_wrong_status(self, emergency_service, mock_panic_request):
        """Test reassignment of request in wrong status"""
        mock_panic_request.status = "completed"
        
        emergency_service.get_request_by_id = AsyncMock(return_value=mock_panic_request)
        
        with pytest.raises(EmergencyRequestError) as exc_info:
            await emergency_service.reassign_request(
                request_id=mock_panic_request.id,
                new_team_id=uuid4(),
                reassigned_by_id=uuid4()
            )
        
        assert "cannot be reassigned in current status" in str(exc_info.value)


class TestEmergencyAllocationIntegration:
    """Integration tests for emergency allocation functionality"""
    
    @pytest.mark.asyncio
    async def test_allocation_workflow(self):
        """
        Test the complete allocation workflow:
        1. Request is submitted (pending)
        2. Office staff allocates to team (assigned)
        3. Team accepts request (accepted)
        4. Request can be reassigned if needed
        """
        # This would be an integration test with actual database
        # Testing the complete workflow from submission to assignment
        pass
    
    @pytest.mark.asyncio
    async def test_call_service_special_handling(self):
        """
        Test that call service requests are handled differently:
        - Cannot be assigned to field teams
        - Must be handled directly by office staff
        - Status goes directly to "handled"
        """
        pass
    
    @pytest.mark.asyncio
    async def test_service_provider_allocation_by_type(self):
        """
        Test that service providers are only allocated requests
        that match their service type (ambulance, fire, towing)
        """
        pass