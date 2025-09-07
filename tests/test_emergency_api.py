"""
Unit tests for emergency API endpoints
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import status

from app.main import app
from app.services.emergency import (
    EmergencyService,
    EmergencyRequestError,
    LocationNotCoveredError,
    SubscriptionExpiredError,
    InvalidServiceTypeError,
    DuplicateRequestError,
    UnauthorizedRequestError
)
from app.models.emergency import PanicRequest
from app.core.auth import UserContext


class TestEmergencyAPI:
    """Test cases for emergency API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Test client"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_user_context(self):
        """Mock user context"""
        return UserContext(
            user_id=uuid4(),
            user_type="registered_user",
            email="test@example.com",
            permissions=["emergency:request"]
        )
    
    @pytest.fixture
    def sample_panic_request(self):
        """Sample panic request data"""
        return {
            "requester_phone": "+1234567890",
            "group_id": str(uuid4()),
            "service_type": "security",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "address": "123 Main St, New York, NY",
            "description": "Emergency assistance needed"
        }
    
    @pytest.fixture
    def mock_panic_request(self):
        """Mock panic request model"""
        request = MagicMock(spec=PanicRequest)
        request.id = uuid4()
        request.requester_phone = "+1234567890"
        request.group_id = uuid4()
        request.service_type = "security"
        request.address = "123 Main St, New York, NY"
        request.description = "Emergency assistance needed"
        request.status = "pending"
        request.created_at = datetime.utcnow()
        request.accepted_at = None
        request.arrived_at = None
        request.completed_at = None
        
        # Mock location geometry
        mock_location = MagicMock()
        request.location = mock_location
        
        return request
    
    @patch('app.api.v1.emergency.require_mobile_attestation')
    @patch('app.api.v1.emergency.get_db')
    @patch('app.services.emergency.EmergencyService')
    def test_submit_panic_request_success(
        self,
        mock_emergency_service_class,
        mock_get_db,
        mock_require_attestation,
        client,
        sample_panic_request,
        mock_panic_request
    ):
        """Test successful panic request submission"""
        # Mock dependencies
        mock_require_attestation.return_value = {"valid": True}
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        
        # Mock service
        mock_service = AsyncMock()
        mock_service.submit_panic_request.return_value = mock_panic_request
        mock_emergency_service_class.return_value = mock_service
        
        # Mock location extraction
        with patch('geoalchemy2.shape.to_shape') as mock_to_shape:
            mock_point = MagicMock()
            mock_point.y = 40.7128
            mock_point.x = -74.0060
            mock_to_shape.return_value = mock_point
            
            # Make request
            response = client.post("/api/v1/emergency/request", json=sample_panic_request)
            
            # Assertions
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["requester_phone"] == sample_panic_request["requester_phone"]
            assert data["service_type"] == sample_panic_request["service_type"]
            assert data["status"] == "pending"
            assert "id" in data
            assert "created_at" in data
    
    @patch('app.api.v1.emergency.require_mobile_attestation')
    @patch('app.api.v1.emergency.get_db')
    def test_submit_panic_request_invalid_service_type(
        self,
        mock_get_db,
        mock_require_attestation,
        client,
        sample_panic_request
    ):
        """Test panic request with invalid service type"""
        # Mock dependencies
        mock_require_attestation.return_value = {"valid": True}
        mock_get_db.return_value = AsyncMock()
        
        # Invalid service type
        sample_panic_request["service_type"] = "invalid_type"
        
        response = client.post("/api/v1/emergency/request", json=sample_panic_request)
        
        # Should fail validation before reaching service
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @patch('app.api.v1.emergency.require_mobile_attestation')
    @patch('app.api.v1.emergency.get_db')
    @patch('app.services.emergency.EmergencyService')
    def test_submit_panic_request_unauthorized_phone(
        self,
        mock_emergency_service_class,
        mock_get_db,
        mock_require_attestation,
        client,
        sample_panic_request
    ):
        """Test panic request with unauthorized phone number"""
        # Mock dependencies
        mock_require_attestation.return_value = {"valid": True}
        mock_get_db.return_value = AsyncMock()
        
        # Mock service to raise unauthorized error
        mock_service = AsyncMock()
        mock_service.submit_panic_request.side_effect = UnauthorizedRequestError(
            "Phone number is not authorized"
        )
        mock_emergency_service_class.return_value = mock_service
        
        response = client.post("/api/v1/emergency/request", json=sample_panic_request)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "not authorized" in data["detail"]["message"]
        assert data["detail"]["error_code"] == "INSUFFICIENT_PERMISSIONS"
    
    @patch('app.api.v1.emergency.require_mobile_attestation')
    @patch('app.api.v1.emergency.get_db')
    @patch('app.services.emergency.EmergencyService')
    def test_submit_panic_request_rate_limited(
        self,
        mock_emergency_service_class,
        mock_get_db,
        mock_require_attestation,
        client,
        sample_panic_request
    ):
        """Test panic request with rate limiting"""
        # Mock dependencies
        mock_require_attestation.return_value = {"valid": True}
        mock_get_db.return_value = AsyncMock()
        
        # Mock service to raise rate limit error
        mock_service = AsyncMock()
        mock_service.submit_panic_request.side_effect = EmergencyRequestError(
            "Rate limit exceeded"
        )
        mock_emergency_service_class.return_value = mock_service
        
        response = client.post("/api/v1/emergency/request", json=sample_panic_request)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "Rate limit exceeded" in data["detail"]["message"]
    
    @patch('app.api.v1.emergency.require_mobile_attestation')
    @patch('app.api.v1.emergency.get_db')
    @patch('app.services.emergency.EmergencyService')
    def test_submit_panic_request_location_not_covered(
        self,
        mock_emergency_service_class,
        mock_get_db,
        mock_require_attestation,
        client,
        sample_panic_request
    ):
        """Test panic request with location not covered"""
        # Mock dependencies
        mock_require_attestation.return_value = {"valid": True}
        mock_get_db.return_value = AsyncMock()
        
        # Mock service to raise location error
        mock_service = AsyncMock()
        mock_service.submit_panic_request.side_effect = LocationNotCoveredError(
            "Location is outside coverage area"
        )
        mock_emergency_service_class.return_value = mock_service
        
        response = client.post("/api/v1/emergency/request", json=sample_panic_request)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "outside coverage area" in data["detail"]["message"]
        assert data["detail"]["error_code"] == "LOCATION_NOT_COVERED"
    
    @patch('app.api.v1.emergency.require_mobile_attestation')
    @patch('app.api.v1.emergency.get_db')
    @patch('app.services.emergency.EmergencyService')
    def test_submit_panic_request_subscription_expired(
        self,
        mock_emergency_service_class,
        mock_get_db,
        mock_require_attestation,
        client,
        sample_panic_request
    ):
        """Test panic request with expired subscription"""
        # Mock dependencies
        mock_require_attestation.return_value = {"valid": True}
        mock_get_db.return_value = AsyncMock()
        
        # Mock service to raise subscription error
        mock_service = AsyncMock()
        mock_service.submit_panic_request.side_effect = SubscriptionExpiredError(
            "Subscription has expired"
        )
        mock_emergency_service_class.return_value = mock_service
        
        response = client.post("/api/v1/emergency/request", json=sample_panic_request)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "expired" in data["detail"]["message"]
        assert data["detail"]["error_code"] == "SUBSCRIPTION_EXPIRED"
    
    @patch('app.api.v1.emergency.require_mobile_attestation')
    @patch('app.api.v1.emergency.get_db')
    @patch('app.services.emergency.EmergencyService')
    def test_submit_panic_request_duplicate_detected(
        self,
        mock_emergency_service_class,
        mock_get_db,
        mock_require_attestation,
        client,
        sample_panic_request
    ):
        """Test panic request duplicate detection"""
        # Mock dependencies
        mock_require_attestation.return_value = {"valid": True}
        mock_get_db.return_value = AsyncMock()
        
        # Mock service to raise duplicate error
        mock_service = AsyncMock()
        mock_service.submit_panic_request.side_effect = DuplicateRequestError(
            "Similar request already exists"
        )
        mock_emergency_service_class.return_value = mock_service
        
        response = client.post("/api/v1/emergency/request", json=sample_panic_request)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "already exists" in data["detail"]["message"]
        assert data["detail"]["error_code"] == "DUPLICATE_REQUEST"
    
    def test_submit_panic_request_validation_errors(self, client):
        """Test panic request with validation errors"""
        # Missing required fields
        invalid_request = {
            "service_type": "security"
            # Missing other required fields
        }
        
        response = client.post("/api/v1/emergency/request", json=invalid_request)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Invalid latitude
        invalid_request = {
            "requester_phone": "+1234567890",
            "group_id": str(uuid4()),
            "service_type": "security",
            "latitude": 91.0,  # Invalid latitude
            "longitude": -74.0060,
            "address": "123 Main St"
        }
        
        response = client.post("/api/v1/emergency/request", json=invalid_request)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Invalid longitude
        invalid_request["latitude"] = 40.7128
        invalid_request["longitude"] = 181.0  # Invalid longitude
        
        response = client.post("/api/v1/emergency/request", json=invalid_request)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @patch('app.api.v1.emergency.require_mobile_attestation')
    @patch('app.api.v1.emergency.get_current_user')
    @patch('app.api.v1.emergency.get_db')
    @patch('app.services.emergency.EmergencyService')
    def test_get_user_requests_success(
        self,
        mock_emergency_service_class,
        mock_get_db,
        mock_get_current_user,
        mock_require_attestation,
        client,
        mock_user_context,
        mock_panic_request
    ):
        """Test successful retrieval of user requests"""
        # Mock dependencies
        mock_require_attestation.return_value = {"valid": True}
        mock_get_current_user.return_value = mock_user_context
        mock_get_db.return_value = AsyncMock()
        
        # Mock service
        mock_service = AsyncMock()
        mock_service.get_user_requests.return_value = [mock_panic_request]
        mock_emergency_service_class.return_value = mock_service
        
        # Mock location extraction
        with patch('geoalchemy2.shape.to_shape') as mock_to_shape:
            mock_point = MagicMock()
            mock_point.y = 40.7128
            mock_point.x = -74.0060
            mock_to_shape.return_value = mock_point
            
            response = client.get("/api/v1/emergency/requests")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "requests" in data
            assert len(data["requests"]) == 1
            assert data["total"] == 1
            assert data["limit"] == 50
            assert data["offset"] == 0
    
    @patch('app.api.v1.emergency.require_mobile_attestation')
    @patch('app.api.v1.emergency.get_current_user')
    @patch('app.api.v1.emergency.get_db')
    @patch('app.services.emergency.EmergencyService')
    def test_get_user_requests_with_filters(
        self,
        mock_emergency_service_class,
        mock_get_db,
        mock_get_current_user,
        mock_require_attestation,
        client,
        mock_user_context
    ):
        """Test user requests with query parameters"""
        # Mock dependencies
        mock_require_attestation.return_value = {"valid": True}
        mock_get_current_user.return_value = mock_user_context
        mock_get_db.return_value = AsyncMock()
        
        # Mock service
        mock_service = AsyncMock()
        mock_service.get_user_requests.return_value = []
        mock_emergency_service_class.return_value = mock_service
        
        response = client.get(
            "/api/v1/emergency/requests?limit=10&offset=20&status_filter=pending"
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify service was called with correct parameters
        mock_service.get_user_requests.assert_called_once_with(
            user_id=mock_user_context.user_id,
            limit=10,
            offset=20,
            status_filter="pending"
        )
    
    @patch('app.api.v1.emergency.require_mobile_attestation')
    @patch('app.api.v1.emergency.get_current_user')
    @patch('app.api.v1.emergency.get_db')
    @patch('app.services.emergency.EmergencyService')
    def test_get_panic_request_success(
        self,
        mock_emergency_service_class,
        mock_get_db,
        mock_get_current_user,
        mock_require_attestation,
        client,
        mock_user_context,
        mock_panic_request
    ):
        """Test successful retrieval of specific panic request"""
        # Mock dependencies
        mock_require_attestation.return_value = {"valid": True}
        mock_get_current_user.return_value = mock_user_context
        mock_get_db.return_value = AsyncMock()
        
        # Mock group ownership
        mock_group = MagicMock()
        mock_group.user_id = mock_user_context.user_id
        mock_panic_request.group = mock_group
        
        # Mock service
        mock_service = AsyncMock()
        mock_service.get_request_by_id.return_value = mock_panic_request
        mock_emergency_service_class.return_value = mock_service
        
        # Mock location extraction
        with patch('geoalchemy2.shape.to_shape') as mock_to_shape:
            mock_point = MagicMock()
            mock_point.y = 40.7128
            mock_point.x = -74.0060
            mock_to_shape.return_value = mock_point
            
            request_id = str(mock_panic_request.id)
            response = client.get(f"/api/v1/emergency/requests/{request_id}")
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["id"] == request_id
            assert data["service_type"] == "security"
    
    @patch('app.api.v1.emergency.require_mobile_attestation')
    @patch('app.api.v1.emergency.get_current_user')
    @patch('app.api.v1.emergency.get_db')
    @patch('app.services.emergency.EmergencyService')
    def test_get_panic_request_not_found(
        self,
        mock_emergency_service_class,
        mock_get_db,
        mock_get_current_user,
        mock_require_attestation,
        client,
        mock_user_context
    ):
        """Test retrieval of non-existent panic request"""
        # Mock dependencies
        mock_require_attestation.return_value = {"valid": True}
        mock_get_current_user.return_value = mock_user_context
        mock_get_db.return_value = AsyncMock()
        
        # Mock service
        mock_service = AsyncMock()
        mock_service.get_request_by_id.return_value = None
        mock_emergency_service_class.return_value = mock_service
        
        request_id = str(uuid4())
        response = client.get(f"/api/v1/emergency/requests/{request_id}")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert data["detail"]["error_code"] == "REQUEST_NOT_FOUND"
    
    @patch('app.api.v1.emergency.require_mobile_attestation')
    @patch('app.api.v1.emergency.get_current_user')
    @patch('app.api.v1.emergency.get_db')
    @patch('app.services.emergency.EmergencyService')
    def test_get_panic_request_access_denied(
        self,
        mock_emergency_service_class,
        mock_get_db,
        mock_get_current_user,
        mock_require_attestation,
        client,
        mock_user_context,
        mock_panic_request
    ):
        """Test access denied for panic request from different user"""
        # Mock dependencies
        mock_require_attestation.return_value = {"valid": True}
        mock_get_current_user.return_value = mock_user_context
        mock_get_db.return_value = AsyncMock()
        
        # Mock group ownership by different user
        mock_group = MagicMock()
        mock_group.user_id = uuid4()  # Different user
        mock_panic_request.group = mock_group
        
        # Mock service
        mock_service = AsyncMock()
        mock_service.get_request_by_id.return_value = mock_panic_request
        mock_emergency_service_class.return_value = mock_service
        
        request_id = str(mock_panic_request.id)
        response = client.get(f"/api/v1/emergency/requests/{request_id}")
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert data["detail"]["error_code"] == "ACCESS_DENIED"
    
    @patch('app.api.v1.emergency.require_mobile_attestation')
    @patch('app.api.v1.emergency.get_current_user')
    @patch('app.api.v1.emergency.get_db')
    @patch('app.services.emergency.EmergencyService')
    def test_update_request_status_success(
        self,
        mock_emergency_service_class,
        mock_get_db,
        mock_get_current_user,
        mock_require_attestation,
        client,
        mock_user_context
    ):
        """Test successful request status update"""
        # Mock dependencies
        mock_require_attestation.return_value = {"valid": True}
        mock_get_current_user.return_value = mock_user_context
        mock_get_db.return_value = AsyncMock()
        
        # Mock service
        mock_service = AsyncMock()
        mock_service.update_request_status.return_value = True
        mock_emergency_service_class.return_value = mock_service
        
        request_id = str(uuid4())
        status_update = {
            "status": "accepted",
            "message": "Request accepted by field agent",
            "latitude": 40.7128,
            "longitude": -74.0060
        }
        
        response = client.put(
            f"/api/v1/emergency/requests/{request_id}/status",
            json=status_update
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "updated successfully" in data["message"]
        
        # Verify service was called with correct parameters
        mock_service.update_request_status.assert_called_once_with(
            request_id=uuid4(request_id),
            new_status="accepted",
            message="Request accepted by field agent",
            updated_by_id=mock_user_context.user_id,
            location=(40.7128, -74.0060)
        )
    
    @patch('app.api.v1.emergency.require_mobile_attestation')
    @patch('app.api.v1.emergency.get_current_user')
    @patch('app.api.v1.emergency.get_db')
    @patch('app.services.emergency.EmergencyService')
    def test_update_request_status_without_location(
        self,
        mock_emergency_service_class,
        mock_get_db,
        mock_get_current_user,
        mock_require_attestation,
        client,
        mock_user_context
    ):
        """Test request status update without location"""
        # Mock dependencies
        mock_require_attestation.return_value = {"valid": True}
        mock_get_current_user.return_value = mock_user_context
        mock_get_db.return_value = AsyncMock()
        
        # Mock service
        mock_service = AsyncMock()
        mock_service.update_request_status.return_value = True
        mock_emergency_service_class.return_value = mock_service
        
        request_id = str(uuid4())
        status_update = {
            "status": "completed",
            "message": "Service completed successfully"
        }
        
        response = client.put(
            f"/api/v1/emergency/requests/{request_id}/status",
            json=status_update
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify service was called without location
        mock_service.update_request_status.assert_called_once_with(
            request_id=uuid4(request_id),
            new_status="completed",
            message="Service completed successfully",
            updated_by_id=mock_user_context.user_id,
            location=None
        )
    
    @patch('app.api.v1.emergency.get_current_user')
    @patch('app.api.v1.emergency.get_db')
    @patch('app.services.emergency.EmergencyService')
    def test_get_request_statistics_success(
        self,
        mock_emergency_service_class,
        mock_get_db,
        mock_get_current_user,
        client,
        mock_user_context
    ):
        """Test successful retrieval of request statistics"""
        # Mock dependencies
        mock_get_current_user.return_value = mock_user_context
        mock_get_db.return_value = AsyncMock()
        
        # Mock service
        mock_service = AsyncMock()
        mock_service.get_request_statistics.return_value = {
            "total_requests": 100,
            "status_breakdown": {"pending": 20, "completed": 80},
            "service_type_breakdown": {"security": 60, "ambulance": 40},
            "average_response_time_minutes": 15.5,
            "completed_requests": 80,
            "date_range": {"from": None, "to": None}
        }
        mock_emergency_service_class.return_value = mock_service
        
        response = client.get("/api/v1/emergency/statistics")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_requests"] == 100
        assert data["status_breakdown"]["pending"] == 20
        assert data["average_response_time_minutes"] == 15.5
    
    def test_panic_request_response_model_from_panic_request(self, mock_panic_request):
        """Test PanicRequestResponse model creation from PanicRequest"""
        from app.api.v1.emergency import PanicRequestResponse
        
        # Mock location extraction
        with patch('geoalchemy2.shape.to_shape') as mock_to_shape:
            mock_point = MagicMock()
            mock_point.y = 40.7128
            mock_point.x = -74.0060
            mock_to_shape.return_value = mock_point
            
            response = PanicRequestResponse.from_panic_request(mock_panic_request)
            
            assert response.id == mock_panic_request.id
            assert response.requester_phone == mock_panic_request.requester_phone
            assert response.service_type == mock_panic_request.service_type
            assert response.latitude == 40.7128
            assert response.longitude == -74.0060
            assert response.status == mock_panic_request.status
    
    def test_request_validation_models(self):
        """Test request validation models"""
        from app.api.v1.emergency import PanicRequestCreate, RequestStatusUpdate
        
        # Test valid panic request
        valid_data = {
            "requester_phone": "+1234567890",
            "group_id": uuid4(),
            "service_type": "security",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "address": "123 Main St, New York, NY"
        }
        
        request = PanicRequestCreate(**valid_data)
        assert request.service_type == "security"
        assert request.latitude == 40.7128
        
        # Test status update
        status_data = {
            "status": "accepted",
            "message": "Request accepted",
            "latitude": 40.7128,
            "longitude": -74.0060
        }
        
        status_update = RequestStatusUpdate(**status_data)
        assert status_update.status == "accepted"
        assert status_update.latitude == 40.7128