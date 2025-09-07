"""
Tests for user management API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import Mock, patch, AsyncMock
import json

from app.main import app
from app.models.user import RegisteredUser, UserGroup, GroupMobileNumber
from app.services.user import UserService


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


class TestUserRegistration:
    """Test user registration endpoints"""
    
    def test_register_user_success(self, client, sample_user_data):
        """Test successful user registration"""
        with patch('app.api.v1.users.UserService') as mock_service_class:
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
            
            # Make request
            response = client.post("/api/v1/users/register", json=sample_user_data)
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert data["email"] == sample_user_data["email"]
            assert data["phone"] == sample_user_data["phone"]
            assert data["first_name"] == sample_user_data["first_name"]
            assert data["last_name"] == sample_user_data["last_name"]
            assert data["is_verified"] == False
            
            # Verify service was called correctly
            mock_service.register_user.assert_called_once_with(
                email=sample_user_data["email"],
                phone=sample_user_data["phone"],
                first_name=sample_user_data["first_name"],
                last_name=sample_user_data["last_name"]
            )
    
    def test_register_user_duplicate_email(self, client, sample_user_data):
        """Test registration with duplicate email"""
        with patch('app.api.v1.users.UserService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock service to raise ValueError for duplicate
            mock_service.register_user = AsyncMock(
                side_effect=ValueError("User with this email or phone number already exists")
            )
            
            response = client.post("/api/v1/users/register", json=sample_user_data)
            
            assert response.status_code == 400
            assert "already exists" in response.json()["detail"]
    
    def test_register_user_invalid_data(self, client):
        """Test registration with invalid data"""
        invalid_data = {
            "email": "invalid-email",  # Invalid email
            "phone": "123",  # Too short
            "first_name": "A",  # Too short
            "last_name": ""  # Empty
        }
        
        response = client.post("/api/v1/users/register", json=invalid_data)
        assert response.status_code == 422  # Validation error


class TestPhoneVerification:
    """Test phone verification endpoints"""
    
    def test_request_phone_verification_success(self, client):
        """Test successful phone verification request"""
        with patch('app.api.v1.users.UserService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            mock_service.request_phone_verification = AsyncMock(return_value={
                "success": True,
                "message": "OTP sent successfully",
                "expires_in_minutes": 10
            })
            
            request_data = {"phone": "+1-555-123-4567"}
            response = client.post("/api/v1/users/verify-phone", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] == True
            assert "OTP sent" in data["message"]
    
    def test_verify_otp_success(self, client):
        """Test successful OTP verification"""
        with patch('app.api.v1.users.UserService') as mock_service_class:
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
            response = client.post("/api/v1/users/verify-otp", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] == True
            assert "verified successfully" in data["message"]
    
    def test_verify_otp_invalid_code(self, client):
        """Test OTP verification with invalid code"""
        with patch('app.api.v1.users.UserService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            mock_service.verify_phone_otp = AsyncMock(return_value={
                "success": False,
                "message": "Invalid OTP"
            })
            
            request_data = {
                "phone": "+1-555-123-4567",
                "otp_code": "999999"
            }
            response = client.post("/api/v1/users/verify-otp", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] == False
            assert "Invalid OTP" in data["message"]


class TestUserProfile:
    """Test user profile management endpoints"""
    
    @patch('app.core.auth.get_current_registered_user')
    def test_get_user_profile_success(self, mock_auth, client):
        """Test getting user profile"""
        # Mock authentication
        mock_user_context = Mock()
        mock_user_context.user_id = "123e4567-e89b-12d3-a456-426614174000"
        mock_auth.return_value = mock_user_context
        
        with patch('app.api.v1.users.UserService') as mock_service_class:
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
            
            response = client.get("/api/v1/users/profile")
            
            assert response.status_code == 200
            data = response.json()
            assert data["email"] == "john.doe@example.com"
            assert data["first_name"] == "John"
            assert data["last_name"] == "Doe"
    
    @patch('app.core.auth.get_current_registered_user')
    def test_update_user_profile_success(self, mock_auth, client):
        """Test updating user profile"""
        # Mock authentication
        mock_user_context = Mock()
        mock_user_context.user_id = "123e4567-e89b-12d3-a456-426614174000"
        mock_auth.return_value = mock_user_context
        
        with patch('app.api.v1.users.UserService') as mock_service_class:
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
            response = client.put("/api/v1/users/profile", json=update_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["first_name"] == "Johnny"
            assert data["last_name"] == "Smith"


class TestUserGroups:
    """Test user group management endpoints"""
    
    @patch('app.core.auth.get_current_registered_user')
    def test_create_user_group_success(self, mock_auth, client, sample_group_data):
        """Test successful group creation"""
        # Mock authentication
        mock_user_context = Mock()
        mock_user_context.user_id = "123e4567-e89b-12d3-a456-426614174000"
        mock_auth.return_value = mock_user_context
        
        with patch('app.api.v1.users.UserService') as mock_service_class:
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
            
            response = client.post("/api/v1/users/groups", json=sample_group_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == sample_group_data["name"]
            assert data["address"] == sample_group_data["address"]
            assert data["latitude"] == sample_group_data["latitude"]
            assert data["longitude"] == sample_group_data["longitude"]
            assert data["mobile_numbers_count"] == 0
    
    @patch('app.core.auth.get_current_registered_user')
    def test_get_user_groups_success(self, mock_auth, client):
        """Test getting user groups"""
        # Mock authentication
        mock_user_context = Mock()
        mock_user_context.user_id = "123e4567-e89b-12d3-a456-426614174000"
        mock_auth.return_value = mock_user_context
        
        with patch('app.api.v1.users.UserService') as mock_service_class:
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
            
            response = client.get("/api/v1/users/groups")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["name"] == "Home"
            assert data[0]["mobile_numbers_count"] == 0
            assert data[1]["name"] == "Office"
            assert data[1]["mobile_numbers_count"] == 2


class TestMobileNumbers:
    """Test mobile number management endpoints"""
    
    @patch('app.core.auth.get_current_registered_user')
    def test_add_mobile_number_success(self, mock_auth, client, sample_mobile_number_data):
        """Test adding mobile number to group"""
        # Mock authentication
        mock_user_context = Mock()
        mock_user_context.user_id = "123e4567-e89b-12d3-a456-426614174000"
        mock_auth.return_value = mock_user_context
        
        with patch('app.api.v1.users.UserService') as mock_service_class:
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
                f"/api/v1/users/groups/{group_id}/mobile-numbers",
                json=sample_mobile_number_data
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["phone_number"] == sample_mobile_number_data["phone_number"]
            assert data["user_type"] == sample_mobile_number_data["user_type"]
            assert data["is_verified"] == False
    
    @patch('app.core.auth.get_current_registered_user')
    def test_get_group_mobile_numbers_success(self, mock_auth, client):
        """Test getting mobile numbers for a group"""
        # Mock authentication
        mock_user_context = Mock()
        mock_user_context.user_id = "123e4567-e89b-12d3-a456-426614174000"
        mock_auth.return_value = mock_user_context
        
        with patch('app.api.v1.users.UserService') as mock_service_class:
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
            response = client.get(f"/api/v1/users/groups/{group_id}/mobile-numbers")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["phone_number"] == "+1-555-123-4567"
            assert data[0]["user_type"] == "individual"
            assert data[0]["is_verified"] == True
            assert data[1]["phone_number"] == "+1-555-987-6543"
            assert data[1]["user_type"] == "alarm"
            assert data[1]["is_verified"] == False
    
    @patch('app.core.auth.get_current_registered_user')
    def test_remove_mobile_number_success(self, mock_auth, client):
        """Test removing mobile number from group"""
        # Mock authentication
        mock_user_context = Mock()
        mock_user_context.user_id = "123e4567-e89b-12d3-a456-426614174000"
        mock_auth.return_value = mock_user_context
        
        with patch('app.api.v1.users.UserService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            mock_service.remove_mobile_number_from_group = AsyncMock()
            
            group_id = "group123"
            mobile_number_id = "mobile123"
            response = client.delete(f"/api/v1/users/groups/{group_id}/mobile-numbers/{mobile_number_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert "removed successfully" in data["message"]


class TestGroupDeletion:
    """Test group deletion endpoints"""
    
    @patch('app.core.auth.get_current_registered_user')
    def test_delete_group_success(self, mock_auth, client):
        """Test successful group deletion"""
        # Mock authentication
        mock_user_context = Mock()
        mock_user_context.user_id = "123e4567-e89b-12d3-a456-426614174000"
        mock_auth.return_value = mock_user_context
        
        with patch('app.api.v1.users.UserService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            mock_service.delete_user_group = AsyncMock()
            
            group_id = "group123"
            response = client.delete(f"/api/v1/users/groups/{group_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert "deleted successfully" in data["message"]
    
    @patch('app.core.auth.get_current_registered_user')
    def test_delete_group_with_active_subscription(self, mock_auth, client):
        """Test deleting group with active subscription"""
        # Mock authentication
        mock_user_context = Mock()
        mock_user_context.user_id = "123e4567-e89b-12d3-a456-426614174000"
        mock_auth.return_value = mock_user_context
        
        with patch('app.api.v1.users.UserService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            mock_service.delete_user_group = AsyncMock(
                side_effect=ValueError("Cannot delete group with active subscription")
            )
            
            group_id = "group123"
            response = client.delete(f"/api/v1/users/groups/{group_id}")
            
            assert response.status_code == 400
            assert "active subscription" in response.json()["detail"]