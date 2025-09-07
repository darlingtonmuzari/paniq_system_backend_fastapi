"""
Unit tests for emergency service
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.emergency import (
    EmergencyService,
    EmergencyRequestError,
    LocationNotCoveredError,
    SubscriptionExpiredError,
    InvalidServiceTypeError,
    DuplicateRequestError,
    UnauthorizedRequestError
)
from app.models.emergency import PanicRequest, RequestStatusUpdate
from app.models.user import UserGroup, GroupMobileNumber, RegisteredUser
from app.models.subscription import StoredSubscription, SubscriptionProduct
from app.models.security_firm import SecurityFirm


class TestEmergencyService:
    """Test cases for EmergencyService"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def mock_geolocation_service(self):
        """Mock geolocation service"""
        return AsyncMock()
    
    @pytest.fixture
    def mock_subscription_service(self):
        """Mock subscription service"""
        return AsyncMock()
    
    @pytest.fixture
    def emergency_service(self, mock_db, mock_geolocation_service, mock_subscription_service):
        """Emergency service instance with mocked dependencies"""
        service = EmergencyService(mock_db)
        service.geolocation_service = mock_geolocation_service
        service.subscription_service = mock_subscription_service
        return service
    
    @pytest.fixture
    def sample_request_data(self):
        """Sample panic request data"""
        return {
            "requester_phone": "+1234567890",
            "group_id": uuid4(),
            "service_type": "security",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "address": "123 Main St, New York, NY",
            "description": "Emergency assistance needed"
        }
    
    @pytest.fixture
    def mock_group(self):
        """Mock user group"""
        group = MagicMock(spec=UserGroup)
        group.id = uuid4()
        group.user_id = uuid4()
        group.subscription_id = uuid4()
        group.subscription_expires_at = datetime.utcnow() + timedelta(days=15)
        return group
    
    @pytest.fixture
    def mock_group_member(self):
        """Mock group mobile number"""
        member = MagicMock(spec=GroupMobileNumber)
        member.phone_number = "+1234567890"
        member.is_verified = True
        return member
    
    @pytest.fixture
    def mock_stored_subscription(self):
        """Mock stored subscription with product and firm"""
        subscription = MagicMock(spec=StoredSubscription)
        subscription.id = uuid4()
        subscription.is_applied = True
        
        product = MagicMock(spec=SubscriptionProduct)
        product.id = uuid4()
        
        firm = MagicMock(spec=SecurityFirm)
        firm.id = uuid4()
        firm.name = "Test Security Firm"
        
        product.firm = firm
        subscription.product = product
        
        return subscription
    
    @pytest.mark.asyncio
    async def test_submit_panic_request_success(
        self,
        emergency_service,
        sample_request_data,
        mock_group,
        mock_group_member,
        mock_stored_subscription
    ):
        """Test successful panic request submission"""
        # Mock database queries
        emergency_service.db.execute.return_value.scalar_one_or_none.side_effect = [
            mock_group_member,  # Authorization check
            mock_group,  # Group lookup
            mock_stored_subscription  # Subscription lookup
        ]
        
        # Mock service calls
        emergency_service.subscription_service.validate_subscription_status.return_value = {
            "is_active": True,
            "is_expired": False
        }
        emergency_service.geolocation_service.validate_location_in_coverage.return_value = True
        
        # Mock cache operations
        with patch('app.services.emergency.cache') as mock_cache:
            mock_cache.get.return_value = None  # No rate limiting
            mock_cache.set.return_value = True
            
            # Mock duplicate check
            emergency_service.db.execute.return_value.scalars.return_value.all.return_value = []
            
            # Execute
            result = await emergency_service.submit_panic_request(**sample_request_data)
            
            # Assertions
            assert isinstance(result, PanicRequest)
            emergency_service.db.add.assert_called()
            emergency_service.db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_submit_panic_request_invalid_service_type(
        self,
        emergency_service,
        sample_request_data
    ):
        """Test panic request with invalid service type"""
        sample_request_data["service_type"] = "invalid_type"
        
        with pytest.raises(InvalidServiceTypeError) as exc_info:
            await emergency_service.submit_panic_request(**sample_request_data)
        
        assert "Invalid service type" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_submit_panic_request_unauthorized_phone(
        self,
        emergency_service,
        sample_request_data
    ):
        """Test panic request with unauthorized phone number"""
        # Mock no group member found
        emergency_service.db.execute.return_value.scalar_one_or_none.return_value = None
        
        with pytest.raises(UnauthorizedRequestError) as exc_info:
            await emergency_service.submit_panic_request(**sample_request_data)
        
        assert "not authorized" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_submit_panic_request_rate_limited(
        self,
        emergency_service,
        sample_request_data,
        mock_group_member
    ):
        """Test panic request with rate limiting"""
        # Mock authorization success
        emergency_service.db.execute.return_value.scalar_one_or_none.return_value = mock_group_member
        
        # Mock rate limiting
        with patch('app.services.emergency.cache') as mock_cache:
            mock_cache.get.return_value = str(emergency_service.MAX_REQUESTS_PER_WINDOW)
            
            with pytest.raises(EmergencyRequestError) as exc_info:
                await emergency_service.submit_panic_request(**sample_request_data)
            
            assert "Rate limit exceeded" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_submit_panic_request_duplicate_detected(
        self,
        emergency_service,
        sample_request_data,
        mock_group_member
    ):
        """Test panic request duplicate detection"""
        # Mock authorization success
        emergency_service.db.execute.return_value.scalar_one_or_none.return_value = mock_group_member
        
        # Mock existing request
        existing_request = MagicMock(spec=PanicRequest)
        existing_request.id = uuid4()
        existing_request.location = MagicMock()
        
        # Mock location extraction
        with patch('geoalchemy2.shape.to_shape') as mock_to_shape:
            mock_point = MagicMock()
            mock_point.y = sample_request_data["latitude"]
            mock_point.x = sample_request_data["longitude"]
            mock_to_shape.return_value = mock_point
            
            emergency_service.db.execute.return_value.scalars.return_value.all.return_value = [existing_request]
            emergency_service.geolocation_service.calculate_distance_km.return_value = 0.05  # 50 meters
            
            with patch('app.services.emergency.cache') as mock_cache:
                mock_cache.get.return_value = None  # No rate limiting
                
                with pytest.raises(DuplicateRequestError) as exc_info:
                    await emergency_service.submit_panic_request(**sample_request_data)
                
                assert "Similar request already exists" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_submit_panic_request_expired_subscription(
        self,
        emergency_service,
        sample_request_data,
        mock_group_member,
        mock_group
    ):
        """Test panic request with expired subscription"""
        # Mock authorization and group lookup
        emergency_service.db.execute.return_value.scalar_one_or_none.side_effect = [
            mock_group_member,
            mock_group
        ]
        
        # Mock expired subscription
        emergency_service.subscription_service.validate_subscription_status.return_value = {
            "is_active": False,
            "is_expired": True
        }
        
        with patch('app.services.emergency.cache') as mock_cache:
            mock_cache.get.return_value = None  # No rate limiting
            emergency_service.db.execute.return_value.scalars.return_value.all.return_value = []  # No duplicates
            
            with pytest.raises(SubscriptionExpiredError) as exc_info:
                await emergency_service.submit_panic_request(**sample_request_data)
            
            assert "expired" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_submit_panic_request_location_not_covered(
        self,
        emergency_service,
        sample_request_data,
        mock_group_member,
        mock_group,
        mock_stored_subscription
    ):
        """Test panic request with location not covered"""
        # Mock successful validation up to coverage check
        emergency_service.db.execute.return_value.scalar_one_or_none.side_effect = [
            mock_group_member,
            mock_group,
            mock_stored_subscription
        ]
        
        emergency_service.subscription_service.validate_subscription_status.return_value = {
            "is_active": True,
            "is_expired": False
        }
        
        # Mock location not covered
        emergency_service.geolocation_service.validate_location_in_coverage.return_value = False
        emergency_service.subscription_service.get_alternative_firms_for_location.return_value = [
            {"firm_name": "Alternative Firm 1"},
            {"firm_name": "Alternative Firm 2"}
        ]
        
        with patch('app.services.emergency.cache') as mock_cache:
            mock_cache.get.return_value = None
            emergency_service.db.execute.return_value.scalars.return_value.all.return_value = []
            
            with pytest.raises(LocationNotCoveredError) as exc_info:
                await emergency_service.submit_panic_request(**sample_request_data)
            
            assert "outside the security firm's coverage area" in str(exc_info.value)
            assert "Alternative Firm 1" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_request_by_id_success(self, emergency_service):
        """Test successful request retrieval by ID"""
        request_id = uuid4()
        mock_request = MagicMock(spec=PanicRequest)
        mock_request.id = request_id
        
        emergency_service.db.execute.return_value.scalar_one_or_none.return_value = mock_request
        
        result = await emergency_service.get_request_by_id(request_id)
        
        assert result == mock_request
        emergency_service.db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_request_by_id_not_found(self, emergency_service):
        """Test request retrieval when request not found"""
        request_id = uuid4()
        emergency_service.db.execute.return_value.scalar_one_or_none.return_value = None
        
        result = await emergency_service.get_request_by_id(request_id)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_user_requests(self, emergency_service):
        """Test getting user requests"""
        user_id = uuid4()
        mock_requests = [MagicMock(spec=PanicRequest) for _ in range(3)]
        
        emergency_service.db.execute.return_value.scalars.return_value.all.return_value = mock_requests
        
        result = await emergency_service.get_user_requests(user_id, limit=10, offset=0)
        
        assert len(result) == 3
        assert all(isinstance(req, MagicMock) for req in result)
    
    @pytest.mark.asyncio
    async def test_get_user_requests_with_status_filter(self, emergency_service):
        """Test getting user requests with status filter"""
        user_id = uuid4()
        mock_requests = [MagicMock(spec=PanicRequest)]
        
        emergency_service.db.execute.return_value.scalars.return_value.all.return_value = mock_requests
        
        result = await emergency_service.get_user_requests(
            user_id, limit=10, offset=0, status_filter="pending"
        )
        
        assert len(result) == 1
    
    @pytest.mark.asyncio
    async def test_update_request_status_success(self, emergency_service):
        """Test successful request status update"""
        request_id = uuid4()
        mock_request = MagicMock(spec=PanicRequest)
        mock_request.id = request_id
        mock_request.status = "pending"
        mock_request.accepted_at = None
        
        emergency_service.get_request_by_id = AsyncMock(return_value=mock_request)
        
        result = await emergency_service.update_request_status(
            request_id=request_id,
            new_status="accepted",
            message="Request accepted by field agent"
        )
        
        assert result is True
        assert mock_request.status == "accepted"
        assert mock_request.accepted_at is not None
        emergency_service.db.add.assert_called()
        emergency_service.db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_request_status_not_found(self, emergency_service):
        """Test request status update when request not found"""
        request_id = uuid4()
        emergency_service.get_request_by_id = AsyncMock(return_value=None)
        
        with pytest.raises(EmergencyRequestError) as exc_info:
            await emergency_service.update_request_status(
                request_id=request_id,
                new_status="accepted"
            )
        
        assert "not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_update_request_status_with_location(self, emergency_service):
        """Test request status update with location tracking"""
        request_id = uuid4()
        mock_request = MagicMock(spec=PanicRequest)
        mock_request.id = request_id
        mock_request.status = "accepted"
        
        emergency_service.get_request_by_id = AsyncMock(return_value=mock_request)
        
        result = await emergency_service.update_request_status(
            request_id=request_id,
            new_status="en_route",
            location=(40.7128, -74.0060)
        )
        
        assert result is True
        emergency_service.db.add.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_request_statistics(self, emergency_service):
        """Test getting request statistics"""
        # Mock requests data
        mock_requests = []
        for i in range(5):
            req = MagicMock(spec=PanicRequest)
            req.status = "completed" if i < 3 else "pending"
            req.service_type = "security" if i < 2 else "ambulance"
            req.created_at = datetime.utcnow() - timedelta(hours=i)
            req.accepted_at = datetime.utcnow() - timedelta(hours=i, minutes=30) if i < 3 else None
            req.completed_at = datetime.utcnow() - timedelta(hours=i, minutes=10) if i < 3 else None
            mock_requests.append(req)
        
        emergency_service.db.execute.return_value.scalars.return_value.all.return_value = mock_requests
        
        result = await emergency_service.get_request_statistics()
        
        assert result["total_requests"] == 5
        assert result["status_breakdown"]["completed"] == 3
        assert result["status_breakdown"]["pending"] == 2
        assert result["service_type_breakdown"]["security"] == 2
        assert result["service_type_breakdown"]["ambulance"] == 3
        assert result["completed_requests"] == 3
        assert result["average_response_time_minutes"] > 0
    
    @pytest.mark.asyncio
    async def test_get_request_statistics_with_firm_filter(self, emergency_service):
        """Test getting request statistics filtered by firm"""
        firm_id = uuid4()
        mock_requests = [MagicMock(spec=PanicRequest)]
        
        emergency_service.db.execute.return_value.scalars.return_value.all.return_value = mock_requests
        
        result = await emergency_service.get_request_statistics(firm_id=firm_id)
        
        assert result["total_requests"] == 1
    
    @pytest.mark.asyncio
    async def test_get_request_statistics_with_date_range(self, emergency_service):
        """Test getting request statistics with date range"""
        date_from = datetime.utcnow() - timedelta(days=7)
        date_to = datetime.utcnow()
        
        mock_requests = [MagicMock(spec=PanicRequest)]
        emergency_service.db.execute.return_value.scalars.return_value.all.return_value = mock_requests
        
        result = await emergency_service.get_request_statistics(
            date_from=date_from,
            date_to=date_to
        )
        
        assert result["total_requests"] == 1
        assert result["date_range"]["from"] == date_from.isoformat()
        assert result["date_range"]["to"] == date_to.isoformat()
    
    def test_valid_service_types(self, emergency_service):
        """Test that valid service types are correctly defined"""
        expected_types = ["call", "security", "ambulance", "fire", "towing"]
        assert emergency_service.VALID_SERVICE_TYPES == expected_types
    
    def test_rate_limiting_constants(self, emergency_service):
        """Test rate limiting constants are properly set"""
        assert emergency_service.RATE_LIMIT_WINDOW_MINUTES == 5
        assert emergency_service.MAX_REQUESTS_PER_WINDOW == 3
        assert emergency_service.DUPLICATE_REQUEST_WINDOW_MINUTES == 10


class TestEmergencyServiceIntegration:
    """Integration tests for EmergencyService with real database operations"""
    
    @pytest.mark.asyncio
    async def test_panic_request_authorization_works_with_locked_accounts(self):
        """
        Test that panic request authorization works even when user account is locked
        This is a critical safety feature
        """
        # This would be an integration test with actual database
        # For now, we'll test the logic conceptually
        
        # The _validate_panic_request_authorization method should only check:
        # 1. Phone number exists in group
        # 2. Phone number is verified
        # It should NOT check if the user account is locked
        
        # This ensures emergency requests can be made even from locked accounts
        pass
    
    @pytest.mark.asyncio
    async def test_comprehensive_validation_flow(self):
        """
        Test the complete validation flow for panic request submission
        """
        # This would test the entire flow:
        # 1. Service type validation
        # 2. Authorization check (phone in group)
        # 3. Rate limiting check
        # 4. Duplicate detection
        # 5. Subscription validation
        # 6. Coverage area validation
        # 7. Request creation
        
        # Each step should be tested in sequence
        pass