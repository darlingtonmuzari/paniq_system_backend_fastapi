"""
Tests for mobile user management API endpoints with attestation
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import Mock, patch, AsyncMock
import json
from uuid import UUID

from app.main import app
from app.models.user import RegisteredUser, UserGroup, GroupMobileNumber
from app.services.user import UserService
from app.services.auth import UserContext


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


@pytest.fixture
def mock_db():
    """Mock database session"""
    return Mock(spec=AsyncSession)


@pytest.fixture
def sample_user_data():
    """Sample user registration data"""
    return {
        "email": "john.doe@example.com",
        "phone": "+1-555-123-4567",
        "first_name": "John",
        "last_name": "Doe"
    }


@pytest.fixture
def sample_group_data():
    """Sample group creation data"""
    return {
        "name": "Home Security",
        "address": "123 Main Street, Anytown, ST 12345",
        "latitude": 40.7128,
        "longitude": -74.0060
    }


@pytest.fixture
def sample_mobile_number_data():
    """Sample mobile number data"""
    return {
        "phone_number": "+1-555-987-6543",
        "user_type": "individual"
    }


@pytest.fixture
def android_headers():
    """Headers for Android attestation"""
    return {
        "X-Platform": "android",
        "X-Integrity-Token": "mock_integrity_token_12345",
        "Authorization": "Bearer mock_jwt_token_12345"
    }


@pytest.fixture
def ios_headers():
    """Headers for iOS attestation"""
    return {
        "X-Platform": "ios",
        "X-Attestation-Object": "mock_attestation_object_12345",
        "X-Key-ID": "mock_key_id_12345",
        "X-Challenge": "mock_challenge_12345",
        "Authorization": "Bearer mock_jwt_token_12345"
    }


@pytest.fixture
def mock_user_context():
    """Mock user context for authentication"""
    return UserContext(
        user_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
        user_type="registered_user",
        email="john.doe@example.com",
        permissions=["emergency:request", "subscription:purchase", "group:manage"]
    )


class TestMobileUserRegistration:
    """Test mobile user registration endpoints with attestation"""
    
    @patch('app.services.attestation.attestation_service.verify_android_integrity')
    def test_register_user_success_android(self, mock_verify, client, sample_user_data, android_headers):
        """Test successful user registration with Android attestation"""
        # Mock attestation verification
        mock_verify.return_value = True
        
        with patch('app.api.v1.mobile_users.UserService') as mock_service_class:
            # Mock the service
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock the register_user method
            mock_user = Mock()
            mock_user.id = "123e4567-e89b-12d3-a456-426614174000"
            mock_user.email = sample_user_data["email"]
            mock_user.phone = sample_user_data["phone"]
            mock_user.first_name = sample_user_data["first_name"]
            mock_user.last_name = sample_user_data["last_name"]
            mock_user.is_verified = False
            mock_user.prank_flags = 0
            mock_user.total_fines = "0.00"
            mock_user.is_suspended = False
            mock_user.is_locked = False
            mock_user.created_at = "2024-01-01T00:00:00"
            
            mock_service.register_user = AsyncMock(return_value=mock_user)
            
            # Make request with attestation headers
            response = client.post(
                "/api/v1/mobile/users/register", 
                json=sample_user_data,
                headers=android_headers
            )
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert data["email"] == sample_user_data["email"]
            assert data["phone"] == sample_user_data["phone"]
            assert data["first_name"] == sample_user_data["first_name"]
            assert data["last_name"] == sample_user_data["last_name"]
            assert data["is_verified"] == False
            
            # Verify attestation was called
            mock_verify.assert_called_once()
            
            # Verify service was called correctly
            mock_service.register_user.assert_called_once_with(
                email=sample_user_data["email"],
                phone=sample_user_data["phone"],
                first_name=sample_user_data["first_name"],
                last_name=sample_user_data["last_name"]
            )
    
    @patch('app.services.attestation.attestation_service.verify_ios_attestation')
    def test_register_user_success_ios(self, mock_verify, client, sample_user_data, ios_headers):
        """Test successful user registration with iOS attestation"""
        # Mock attestation verification
        mock_verify.return_value = True
        
        with patch('app.api.v1.mobile_users.UserService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock user
            mock_user = Mock()
            mock_user.id = "123e4567-e89b-12d3-a456-426614174000"
            mock_user.email = sample_user_data["email"]
            mock_user.phone = sample_user_data["phone"]
            mock_user.first_name = sample_user_data["first_name"]
            mock_user.last_name = sample_user_data["last_name"]
            mock_user.is_verified = False
            mock_user.prank_flags = 0
            mock_user.total_fines = "0.00"
            mock_user.is_suspended = False
            mock_user.is_locked = False
            mock_user.created_at = "2024-01-01T00:00:00"
            
            mock_service.register_user = AsyncMock(return_value=mock_user)
            
            # Make request with iOS attestation headers
            response = client.post(
                "/api/v1/mobile/users/register", 
                json=sample_user_data,
                headers=ios_headers
            )
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert data["email"] == sample_user_data["email"]
            
            # Verify attestation was called
            mock_verify.assert_called_once()
    
    def test_register_user_without_attestation(self, client, sample_user_data):
        """Test user registration without attestation fails"""
        response = client.post("/api/v1/mobile/users/register", json=sample_user_data)
        
        assert response.status_code == 401
        assert "attestation" in response.json()["message"].lower()
    
    def test_register_user_invalid_attestation(self, client, sample_user_data):
        """Test user registration with invalid attestation"""
        headers = {
            "X-Platform": "android",
            "X-Integrity-Token": "invalid_token"
        }
        
        with patch('app.services.attestation.attestation_service.verify_android_integrity') as mock_verify:
            from app.services.attestation import AttestationError
            mock_verify.side_effect = AttestationError("Invalid token")
            
            response = client.post(
                "/api/v1/mobile/users/register", 
                json=sample_user_data,
                headers=headers
            )
            
            assert response.status_code == 401
            assert "attestation" in response.json()["message"].lower()
    
    @patch('app.services.attestation.attestation_service.verify_android_integrity')
    def test_register_user_duplicate_email(self, mock_verify, client, sample_user_data, android_headers):
        """Test registration with duplicate email"""
        mock_verify.return_value = True
        
        with patch('app.api.v1.mobile_users.UserService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock service to raise ValueError for duplicate
            mock_service.register_user = AsyncMock(
                side_effect=ValueError("User with this email or phone number already exists")
            )
            
            response = client.post(
                "/api/v1/mobile/users/register", 
                json=sample_user_data,
                headers=android_headers
            )
            
            assert response.status_code == 400
            response_data = response.json()
            # The response might be in different formats depending on FastAPI version
            error_message = response_data.get("detail", response_data.get("message", ""))
            assert "already exists" in error_message


class TestMobilePhoneVerification:
    """Test mobile phone verification endpoints with attestation"""
    
    @patch('app.services.attestation.attestation_service.verify_android_integrity')
    def test_request_phone_verification_success(self, mock_verify, client, android_headers):
        """Test successful phone verification request with attestation"""
        mock_verify.return_value = True
        
        with patch('app.api.v1.mobile_users.UserService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            mock_service.request_phone_verification = AsyncMock(return_value={
                "success": True,
                "message": "OTP sent successfully",
                "expires_in_minutes": 10
            })
            
            request_data = {"phone": "+1-555-123-4567"}
            response = client.post(
                "/api/v1/mobile/users/verify-phone", 
                json=request_data,
                headers=android_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] == True
            assert "OTP sent" in data["message"]
            
            # Verify attestation was called
            mock_verify.assert_called_once()
    
    @patch('app.services.attestation.attestation_service.verify_android_integrity')
    def test_verify_otp_success(self, mock_verify, client, android_headers):
        """Test successful OTP verification with attestation"""
        mock_verify.return_value = True
        
        with patch('app.api.v1.mobile_users.UserService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            mock_service.verify_phone_otp = AsyncMock(return_value={
                "success": True,
                "message": "Phone number verified successfully"
            })
            
            request_data = {
                "phone": "+1-555-123-4567",
                "otp_code": "123456"
            }
            response = client.post(
                "/api/v1/mobile/users/verify-otp", 
                json=request_data,
                headers=android_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] == True
            assert "verified successfully" in data["message"]
    
    def test_phone_verification_without_attestation(self, client):
        """Test phone verification without attestation fails"""
        request_data = {"phone": "+1-555-123-4567"}
        response = client.post("/api/v1/mobile/users/verify-phone", json=request_data)
        
        assert response.status_code == 401
        assert "attestation" in response.json()["message"].lower()


class TestMobileUserProfile:
    """Test mobile user profile management endpoints with attestation"""
    
    @patch('app.services.auth.auth_service.validate_token')
    @patch('app.services.attestation.attestation_service.verify_android_integrity')
    def test_get_user_profile_success(self, mock_verify, mock_validate_token, client, android_headers):
        """Test getting user profile with attestation"""
        mock_verify.return_value = True
        
        # Mock JWT token validation
        from app.services.auth import UserContext
        from uuid import UUID
        mock_user_context = UserContext(
            user_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
            user_type="registered_user",
            email="john.doe@example.com",
            permissions=["emergency:request", "subscription:purchase", "group:manage"]
        )
        mock_validate_token.return_value = mock_user_context
        
        with patch('app.api.v1.mobile_users.UserService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock user
            mock_user = Mock()
            mock_user.id = mock_user_context.user_id
            mock_user.email = "john.doe@example.com"
            mock_user.phone = "+1-555-123-4567"
            mock_user.first_name = "John"
            mock_user.last_name = "Doe"
            mock_user.is_verified = True
            mock_user.prank_flags = 0
            mock_user.total_fines = "0.00"
            mock_user.is_suspended = False
            mock_user.is_locked = False
            mock_user.created_at = "2024-01-01T00:00:00"
            
            mock_service.get_user_by_id = AsyncMock(return_value=mock_user)
            
            response = client.get("/api/v1/mobile/users/profile", headers=android_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["email"] == "john.doe@example.com"
            assert data["first_name"] == "John"
            assert data["last_name"] == "Doe"
            
            # Verify attestation was called
            mock_verify.assert_called_once()
    
    @patch('app.core.auth.get_current_registered_user')
    @patch('app.services.attestation.attestation_service.verify_android_integrity')
    def test_update_user_profile_success(self, mock_verify, mock_auth, client, android_headers):
        """Test updating user profile with attestation"""
        mock_verify.return_value = True
        
        # Mock authentication
        mock_user_context = Mock()
        mock_user_context.user_id = "123e4567-e89b-12d3-a456-426614174000"
        mock_auth.return_value = mock_user_context
        
        with patch('app.api.v1.mobile_users.UserService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock updated user
            mock_user = Mock()
            mock_user.id = mock_user_context.user_id
            mock_user.email = "john.doe@example.com"
            mock_user.phone = "+1-555-123-4567"
            mock_user.first_name = "Johnny"  # Updated
            mock_user.last_name = "Smith"   # Updated
            mock_user.is_verified = True
            mock_user.prank_flags = 0
            mock_user.total_fines = "0.00"
            mock_user.is_suspended = False
            mock_user.is_locked = False
            mock_user.created_at = "2024-01-01T00:00:00"
            
            mock_service.update_user_profile = AsyncMock(return_value=mock_user)
            
            update_data = {
                "first_name": "Johnny",
                "last_name": "Smith"
            }
            response = client.put(
                "/api/v1/mobile/users/profile", 
                json=update_data,
                headers=android_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["first_name"] == "Johnny"
            assert data["last_name"] == "Smith"
            
            # Verify attestation was called
            mock_verify.assert_called_once()
    
    def test_get_profile_without_attestation(self, client):
        """Test getting profile without attestation fails"""
        response = client.get("/api/v1/mobile/users/profile")
        
        assert response.status_code == 401
        assert "attestation" in response.json()["message"].lower()


class TestMobileUserGroups:
    """Test mobile user group management endpoints with attestation"""
    
    @patch('app.core.auth.get_current_registered_user')
    @patch('app.services.attestation.attestation_service.verify_android_integrity')
    def test_create_user_group_success(self, mock_verify, mock_auth, client, sample_group_data, android_headers):
        """Test successful group creation with attestation"""
        mock_verify.return_value = True
        
        # Mock authentication
        mock_user_context = Mock()
        mock_user_context.user_id = "123e4567-e89b-12d3-a456-426614174000"
        mock_auth.return_value = mock_user_context
        
        with patch('app.api.v1.mobile_users.UserService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock group
            mock_group = Mock()
            mock_group.id = "group123"
            mock_group.name = sample_group_data["name"]
            mock_group.address = sample_group_data["address"]
            mock_group.latitude = sample_group_data["latitude"]
            mock_group.longitude = sample_group_data["longitude"]
            mock_group.subscription_expires_at = None
            mock_group.mobile_numbers = []
            mock_group.created_at = "2024-01-01T00:00:00"
            
            mock_service.create_user_group = AsyncMock(return_value=mock_group)
            
            response = client.post(
                "/api/v1/mobile/users/groups", 
                json=sample_group_data,
                headers=android_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == sample_group_data["name"]
            assert data["address"] == sample_group_data["address"]
            assert data["latitude"] == sample_group_data["latitude"]
            assert data["longitude"] == sample_group_data["longitude"]
            assert data["mobile_numbers_count"] == 0
            
            # Verify attestation was called
            mock_verify.assert_called_once()
    
    @patch('app.core.auth.get_current_registered_user')
    @patch('app.services.attestation.attestation_service.verify_android_integrity')
    def test_get_user_groups_success(self, mock_verify, mock_auth, client, android_headers):
        """Test getting user groups with attestation"""
        mock_verify.return_value = True
        
        # Mock authentication
        mock_user_context = Mock()
        mock_user_context.user_id = "123e4567-e89b-12d3-a456-426614174000"
        mock_auth.return_value = mock_user_context
        
        with patch('app.api.v1.mobile_users.UserService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock groups
            mock_group1 = Mock()
            mock_group1.id = "group1"
            mock_group1.name = "Home"
            mock_group1.address = "123 Main St"
            mock_group1.latitude = 40.7128
            mock_group1.longitude = -74.0060
            mock_group1.subscription_expires_at = None
            mock_group1.mobile_numbers = []
            mock_group1.created_at = "2024-01-01T00:00:00"
            
            mock_group2 = Mock()
            mock_group2.id = "group2"
            mock_group2.name = "Office"
            mock_group2.address = "456 Business Ave"
            mock_group2.latitude = 40.7589
            mock_group2.longitude = -73.9851
            mock_group2.subscription_expires_at = None
            mock_group2.mobile_numbers = [Mock(), Mock()]  # 2 mobile numbers
            mock_group2.created_at = "2024-01-01T00:00:00"
            
            mock_service.get_user_groups = AsyncMock(return_value=[mock_group1, mock_group2])
            
            response = client.get("/api/v1/mobile/users/groups", headers=android_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["name"] == "Home"
            assert data[0]["mobile_numbers_count"] == 0
            assert data[1]["name"] == "Office"
            assert data[1]["mobile_numbers_count"] == 2
            
            # Verify attestation was called
            mock_verify.assert_called_once()
    
    def test_create_group_without_attestation(self, client, sample_group_data):
        """Test creating group without attestation fails"""
        response = client.post("/api/v1/mobile/users/groups", json=sample_group_data)
        
        assert response.status_code == 401
        assert "attestation" in response.json()["message"].lower()


class TestMobileMobileNumbers:
    """Test mobile number management endpoints with attestation"""
    
    @patch('app.core.auth.get_current_registered_user')
    @patch('app.services.attestation.attestation_service.verify_android_integrity')
    def test_add_mobile_number_success(self, mock_verify, mock_auth, client, sample_mobile_number_data, android_headers):
        """Test adding mobile number to group with attestation"""
        mock_verify.return_value = True
        
        # Mock authentication
        mock_user_context = Mock()
        mock_user_context.user_id = "123e4567-e89b-12d3-a456-426614174000"
        mock_auth.return_value = mock_user_context
        
        with patch('app.api.v1.mobile_users.UserService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock mobile number
            mock_mobile_number = Mock()
            mock_mobile_number.id = "mobile123"
            mock_mobile_number.phone_number = sample_mobile_number_data["phone_number"]
            mock_mobile_number.user_type = sample_mobile_number_data["user_type"]
            mock_mobile_number.is_verified = False
            mock_mobile_number.created_at = "2024-01-01T00:00:00"
            
            mock_service.add_mobile_number_to_group = AsyncMock(return_value=mock_mobile_number)
            
            group_id = "group123"
            response = client.post(
                f"/api/v1/mobile/users/groups/{group_id}/mobile-numbers",
                json=sample_mobile_number_data,
                headers=android_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["phone_number"] == sample_mobile_number_data["phone_number"]
            assert data["user_type"] == sample_mobile_number_data["user_type"]
            assert data["is_verified"] == False
            
            # Verify attestation was called
            mock_verify.assert_called_once()
    
    @patch('app.core.auth.get_current_registered_user')
    @patch('app.services.attestation.attestation_service.verify_android_integrity')
    def test_get_group_mobile_numbers_success(self, mock_verify, mock_auth, client, android_headers):
        """Test getting mobile numbers for a group with attestation"""
        mock_verify.return_value = True
        
        # Mock authentication
        mock_user_context = Mock()
        mock_user_context.user_id = "123e4567-e89b-12d3-a456-426614174000"
        mock_auth.return_value = mock_user_context
        
        with patch('app.api.v1.mobile_users.UserService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock mobile numbers
            mock_mobile1 = Mock()
            mock_mobile1.id = "mobile1"
            mock_mobile1.phone_number = "+1-555-123-4567"
            mock_mobile1.user_type = "individual"
            mock_mobile1.is_verified = True
            mock_mobile1.created_at = "2024-01-01T00:00:00"
            
            mock_mobile2 = Mock()
            mock_mobile2.id = "mobile2"
            mock_mobile2.phone_number = "+1-555-987-6543"
            mock_mobile2.user_type = "alarm"
            mock_mobile2.is_verified = False
            mock_mobile2.created_at = "2024-01-01T00:00:00"
            
            mock_service.get_group_mobile_numbers = AsyncMock(return_value=[mock_mobile1, mock_mobile2])
            
            group_id = "group123"
            response = client.get(
                f"/api/v1/mobile/users/groups/{group_id}/mobile-numbers",
                headers=android_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["phone_number"] == "+1-555-123-4567"
            assert data[0]["user_type"] == "individual"
            assert data[0]["is_verified"] == True
            assert data[1]["phone_number"] == "+1-555-987-6543"
            assert data[1]["user_type"] == "alarm"
            assert data[1]["is_verified"] == False
            
            # Verify attestation was called
            mock_verify.assert_called_once()
    
    def test_add_mobile_number_without_attestation(self, client, sample_mobile_number_data):
        """Test adding mobile number without attestation fails"""
        group_id = "group123"
        response = client.post(
            f"/api/v1/mobile/users/groups/{group_id}/mobile-numbers",
            json=sample_mobile_number_data
        )
        
        assert response.status_code == 401
        assert "attestation" in response.json()["message"].lower()


class TestMobileUserStatistics:
    """Test mobile user statistics endpoint with attestation"""
    
    @patch('app.core.auth.get_current_registered_user')
    @patch('app.services.attestation.attestation_service.verify_android_integrity')
    def test_get_user_statistics_success(self, mock_verify, mock_auth, client, android_headers):
        """Test getting user statistics with attestation"""
        mock_verify.return_value = True
        
        # Mock authentication
        mock_user_context = Mock()
        mock_user_context.user_id = "123e4567-e89b-12d3-a456-426614174000"
        mock_auth.return_value = mock_user_context
        
        with patch('app.api.v1.mobile_users.UserService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            mock_stats = {
                "total_groups": 2,
                "total_mobile_numbers": 5,
                "active_subscriptions": 1,
                "prank_flags": 0,
                "total_fines": 0.0,
                "is_suspended": False,
                "is_verified": True
            }
            
            mock_service.get_user_statistics = AsyncMock(return_value=mock_stats)
            
            response = client.get("/api/v1/mobile/users/statistics", headers=android_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["total_groups"] == 2
            assert data["total_mobile_numbers"] == 5
            assert data["active_subscriptions"] == 1
            assert data["prank_flags"] == 0
            assert data["is_verified"] == True
            
            # Verify attestation was called
            mock_verify.assert_called_once()
    
    def test_get_statistics_without_attestation(self, client):
        """Test getting statistics without attestation fails"""
        response = client.get("/api/v1/mobile/users/statistics")
        
        assert response.status_code == 401
        assert "attestation" in response.json()["message"].lower()


class TestMobileEndpointValidation:
    """Test validation for mobile endpoints"""
    
    @patch('app.services.attestation.attestation_service.verify_android_integrity')
    def test_invalid_phone_number_validation(self, mock_verify, client, android_headers):
        """Test phone number validation on mobile endpoints"""
        mock_verify.return_value = True
        
        invalid_data = {
            "email": "test@example.com",
            "phone": "123",  # Too short
            "first_name": "John",
            "last_name": "Doe"
        }
        
        response = client.post(
            "/api/v1/mobile/users/register",
            json=invalid_data,
            headers=android_headers
        )
        
        assert response.status_code == 422  # Validation error
    
    @patch('app.services.attestation.attestation_service.verify_android_integrity')
    def test_invalid_coordinates_validation(self, mock_verify, client, android_headers):
        """Test coordinate validation on mobile endpoints"""
        mock_verify.return_value = True
        
        with patch('app.core.auth.get_current_registered_user') as mock_auth:
            mock_user_context = Mock()
            mock_user_context.user_id = "123e4567-e89b-12d3-a456-426614174000"
            mock_auth.return_value = mock_user_context
            
            invalid_data = {
                "name": "Test Group",
                "address": "123 Main St",
                "latitude": 91.0,  # Invalid latitude
                "longitude": -74.0060
            }
            
            response = client.post(
                "/api/v1/mobile/users/groups",
                json=invalid_data,
                headers=android_headers
            )
            
            assert response.status_code == 422  # Validation error
    
    @patch('app.services.attestation.attestation_service.verify_android_integrity')
    def test_invalid_user_type_validation(self, mock_verify, client, android_headers):
        """Test user type validation on mobile endpoints"""
        mock_verify.return_value = True
        
        with patch('app.core.auth.get_current_registered_user') as mock_auth:
            mock_user_context = Mock()
            mock_user_context.user_id = "123e4567-e89b-12d3-a456-426614174000"
            mock_auth.return_value = mock_user_context
            
            invalid_data = {
                "phone_number": "+1-555-123-4567",
                "user_type": "invalid_type"  # Invalid user type
            }
            
            group_id = "group123"
            response = client.post(
                f"/api/v1/mobile/users/groups/{group_id}/mobile-numbers",
                json=invalid_data,
                headers=android_headers
            )
            
            assert response.status_code == 422  # Validation error