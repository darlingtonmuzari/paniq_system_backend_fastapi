"""
Tests for mobile subscription API endpoints
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.user import RegisteredUser, UserGroup, GroupMobileNumber
from app.models.subscription import SubscriptionProduct, StoredSubscription
from app.models.security_firm import SecurityFirm, CoverageArea
from app.services.auth import UserContext


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_user_context():
    from uuid import UUID
    return UserContext(
        user_id=UUID("12345678-1234-5678-9012-123456789012"),
        user_type="registered_user",
        email="test@example.com"
    )


@pytest.fixture
def mock_db():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def sample_security_firm():
    return SecurityFirm(
        id="firm-123",
        name="Test Security Firm",
        email="firm@test.com",
        phone="+1234567890",
        address="123 Test St",
        verification_status="approved",
        credit_balance=1000
    )


@pytest.fixture
def sample_subscription_product(sample_security_firm):
    return SubscriptionProduct(
        id="product-123",
        firm_id="firm-123",
        name="Basic Security Package",
        description="Basic security services",
        max_users=10,
        price=Decimal("99.99"),
        credit_cost=50,
        is_active=True,
        firm=sample_security_firm
    )


@pytest.fixture
def sample_user():
    return RegisteredUser(
        id="user-123",
        email="test@example.com",
        phone="+1234567890",
        first_name="John",
        last_name="Doe",
        is_verified=True,
        is_suspended=False
    )


@pytest.fixture
def sample_user_group(sample_user):
    from geoalchemy2.elements import WKTElement
    return UserGroup(
        id="group-123",
        user_id="user-123",
        name="Home Group",
        address="123 Main St",
        location=WKTElement("POINT(-74.006 40.7128)", srid=4326),
        user=sample_user
    )


@pytest.fixture
def sample_stored_subscription(sample_user, sample_subscription_product):
    return StoredSubscription(
        id="subscription-123",
        user_id="user-123",
        product_id="product-123",
        is_applied=False,
        purchased_at=datetime.utcnow(),
        user=sample_user,
        product=sample_subscription_product
    )


class TestGetAvailableProducts:
    """Test getting available subscription products"""
    
    @patch('app.api.v1.mobile_subscriptions.get_current_registered_user')
    @patch('app.api.v1.mobile_subscriptions.get_db')
    async def test_get_available_products_success(
        self, mock_get_db, mock_get_user, client, mock_db, mock_user_context, 
        sample_subscription_product
    ):
        """Test successful retrieval of available products"""
        mock_get_user.return_value = mock_user_context
        mock_get_db.return_value = mock_db
        
        with patch('app.services.subscription.SubscriptionService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_active_products.return_value = [sample_subscription_product]
            
            response = client.get("/api/v1/mobile/subscriptions/products")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["id"] == "product-123"
            assert data[0]["name"] == "Basic Security Package"
            assert data[0]["price"] == 99.99
            assert data[0]["firm_name"] == "Test Security Firm"
    
    @patch('app.api.v1.mobile_subscriptions.get_current_registered_user')
    @patch('app.api.v1.mobile_subscriptions.get_db')
    async def test_get_available_products_empty(
        self, mock_get_db, mock_get_user, client, mock_db, mock_user_context
    ):
        """Test retrieval when no products are available"""
        mock_get_user.return_value = mock_user_context
        mock_get_db.return_value = mock_db
        
        with patch('app.services.subscription.SubscriptionService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_active_products.return_value = []
            
            response = client.get("/api/v1/mobile/subscriptions/products")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 0


class TestPurchaseSubscription:
    """Test subscription purchase functionality"""
    
    @patch('app.api.v1.mobile_subscriptions.get_current_registered_user')
    @patch('app.api.v1.mobile_subscriptions.get_db')
    async def test_purchase_subscription_success(
        self, mock_get_db, mock_get_user, client, mock_db, mock_user_context,
        sample_stored_subscription, sample_subscription_product
    ):
        """Test successful subscription purchase"""
        mock_get_user.return_value = mock_user_context
        mock_get_db.return_value = mock_db
        
        with patch('app.services.subscription.SubscriptionService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.purchase_subscription.return_value = sample_stored_subscription
            mock_service.get_product_by_id.return_value = sample_subscription_product
            
            request_data = {
                "product_id": "product-123",
                "payment_method": "credit_card",
                "payment_token": "tok_123"
            }
            
            response = client.post("/api/v1/mobile/subscriptions/purchase", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "subscription-123"
            assert data["product_id"] == "product-123"
            assert data["product_name"] == "Basic Security Package"
            assert data["is_applied"] == False
            assert data["firm_name"] == "Test Security Firm"
    
    @patch('app.api.v1.mobile_subscriptions.get_current_registered_user')
    @patch('app.api.v1.mobile_subscriptions.get_db')
    async def test_purchase_subscription_invalid_product(
        self, mock_get_db, mock_get_user, client, mock_db, mock_user_context
    ):
        """Test purchase with invalid product ID"""
        mock_get_user.return_value = mock_user_context
        mock_get_db.return_value = mock_db
        
        with patch('app.services.subscription.SubscriptionService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.purchase_subscription.side_effect = ValueError("Subscription product not found")
            
            request_data = {
                "product_id": "invalid-product-id",
                "payment_method": "credit_card"
            }
            
            response = client.post("/api/v1/mobile/subscriptions/purchase", json=request_data)
            
            assert response.status_code == 400
            assert "Subscription product not found" in response.json()["detail"]
    
    @patch('app.api.v1.mobile_subscriptions.get_current_registered_user')
    @patch('app.api.v1.mobile_subscriptions.get_db')
    async def test_purchase_subscription_suspended_user(
        self, mock_get_db, mock_get_user, client, mock_db, mock_user_context
    ):
        """Test purchase with suspended user account"""
        mock_get_user.return_value = mock_user_context
        mock_get_db.return_value = mock_db
        
        with patch('app.services.subscription.SubscriptionService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.purchase_subscription.side_effect = ValueError("User account is suspended")
            
            request_data = {
                "product_id": "product-123",
                "payment_method": "credit_card"
            }
            
            response = client.post("/api/v1/mobile/subscriptions/purchase", json=request_data)
            
            assert response.status_code == 400
            assert "User account is suspended" in response.json()["detail"]


class TestGetStoredSubscriptions:
    """Test getting stored subscriptions"""
    
    @patch('app.api.v1.mobile_subscriptions.get_current_registered_user')
    @patch('app.api.v1.mobile_subscriptions.get_db')
    async def test_get_stored_subscriptions_success(
        self, mock_get_db, mock_get_user, client, mock_db, mock_user_context,
        sample_stored_subscription
    ):
        """Test successful retrieval of stored subscriptions"""
        mock_get_user.return_value = mock_user_context
        mock_get_db.return_value = mock_db
        
        with patch('app.services.subscription.SubscriptionService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_user_stored_subscriptions.return_value = [sample_stored_subscription]
            
            response = client.get("/api/v1/mobile/subscriptions/stored")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["id"] == "subscription-123"
            assert data[0]["is_applied"] == False
    
    @patch('app.api.v1.mobile_subscriptions.get_current_registered_user')
    @patch('app.api.v1.mobile_subscriptions.get_db')
    async def test_get_stored_subscriptions_include_applied(
        self, mock_get_db, mock_get_user, client, mock_db, mock_user_context,
        sample_stored_subscription
    ):
        """Test retrieval including applied subscriptions"""
        mock_get_user.return_value = mock_user_context
        mock_get_db.return_value = mock_db
        
        # Create applied subscription
        applied_subscription = sample_stored_subscription
        applied_subscription.is_applied = True
        applied_subscription.applied_to_group_id = "group-123"
        applied_subscription.applied_at = datetime.utcnow()
        
        with patch('app.services.subscription.SubscriptionService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_user_stored_subscriptions.return_value = [applied_subscription]
            
            response = client.get("/api/v1/mobile/subscriptions/stored?include_applied=true")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["is_applied"] == True
            assert data[0]["applied_to_group_id"] == "group-123"


class TestApplySubscriptionToGroup:
    """Test applying subscription to group"""
    
    @patch('app.api.v1.mobile_subscriptions.get_current_registered_user')
    @patch('app.api.v1.mobile_subscriptions.get_db')
    async def test_apply_subscription_success(
        self, mock_get_db, mock_get_user, client, mock_db, mock_user_context
    ):
        """Test successful subscription application"""
        mock_get_user.return_value = mock_user_context
        mock_get_db.return_value = mock_db
        
        with patch('app.services.subscription.SubscriptionService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.apply_subscription_to_group.return_value = True
            mock_service.validate_subscription_status.return_value = {
                "group_id": "group-123",
                "is_active": True,
                "is_expired": False,
                "expires_at": (datetime.utcnow() + timedelta(days=30)).isoformat(),
                "days_remaining": 30,
                "subscription_id": "subscription-123"
            }
            
            request_data = {
                "subscription_id": "subscription-123",
                "group_id": "group-123"
            }
            
            response = client.post("/api/v1/mobile/subscriptions/apply", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Subscription applied successfully"
            assert data["subscription_status"]["is_active"] == True
    
    @patch('app.api.v1.mobile_subscriptions.get_current_registered_user')
    @patch('app.api.v1.mobile_subscriptions.get_db')
    async def test_apply_subscription_coverage_error(
        self, mock_get_db, mock_get_user, client, mock_db, mock_user_context,
        sample_user_group
    ):
        """Test application failure due to coverage area"""
        mock_get_user.return_value = mock_user_context
        mock_get_db.return_value = mock_db
        mock_db.get.return_value = sample_user_group
        
        with patch('app.services.subscription.SubscriptionService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.apply_subscription_to_group.side_effect = ValueError(
                "Group location is outside the security firm's coverage area"
            )
            mock_service.get_alternative_firms_for_location.return_value = [
                {
                    "firm_id": "firm-456",
                    "firm_name": "Alternative Security",
                    "coverage_area_name": "Downtown Area"
                }
            ]
            
            request_data = {
                "subscription_id": "subscription-123",
                "group_id": "group-123"
            }
            
            response = client.post("/api/v1/mobile/subscriptions/apply", json=request_data)
            
            assert response.status_code == 400
            data = response.json()["detail"]
            assert "coverage area" in data["error"]
            assert len(data["alternative_firms"]) == 1
    
    @patch('app.api.v1.mobile_subscriptions.get_current_registered_user')
    @patch('app.api.v1.mobile_subscriptions.get_db')
    async def test_apply_subscription_already_applied(
        self, mock_get_db, mock_get_user, client, mock_db, mock_user_context
    ):
        """Test application of already applied subscription"""
        mock_get_user.return_value = mock_user_context
        mock_get_db.return_value = mock_db
        
        with patch('app.services.subscription.SubscriptionService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.apply_subscription_to_group.side_effect = ValueError(
                "Subscription has already been applied"
            )
            
            request_data = {
                "subscription_id": "subscription-123",
                "group_id": "group-123"
            }
            
            response = client.post("/api/v1/mobile/subscriptions/apply", json=request_data)
            
            assert response.status_code == 400
            assert "already been applied" in response.json()["detail"]


class TestGetActiveSubscriptions:
    """Test getting active subscriptions"""
    
    @patch('app.api.v1.mobile_subscriptions.get_current_registered_user')
    @patch('app.api.v1.mobile_subscriptions.get_db')
    async def test_get_active_subscriptions_success(
        self, mock_get_db, mock_get_user, client, mock_db, mock_user_context
    ):
        """Test successful retrieval of active subscriptions"""
        mock_get_user.return_value = mock_user_context
        mock_get_db.return_value = mock_db
        
        active_subscription = {
            "group_id": "group-123",
            "group_name": "Home Group",
            "group_address": "123 Main St",
            "mobile_numbers_count": 3,
            "is_active": True,
            "is_expired": False,
            "expires_at": (datetime.utcnow() + timedelta(days=15)).isoformat(),
            "days_remaining": 15,
            "subscription_id": "subscription-123"
        }
        
        with patch('app.services.subscription.SubscriptionService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_group_active_subscriptions.return_value = [active_subscription]
            
            response = client.get("/api/v1/mobile/subscriptions/active")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["group_id"] == "group-123"
            assert data[0]["is_active"] == True
            assert data[0]["days_remaining"] == 15


class TestGetGroupSubscriptionStatus:
    """Test getting group subscription status"""
    
    @patch('app.api.v1.mobile_subscriptions.get_current_registered_user')
    @patch('app.api.v1.mobile_subscriptions.get_db')
    async def test_get_group_status_success(
        self, mock_get_db, mock_get_user, client, mock_db, mock_user_context,
        sample_user_group
    ):
        """Test successful retrieval of group subscription status"""
        mock_get_user.return_value = mock_user_context
        mock_get_db.return_value = mock_db
        mock_db.get.return_value = sample_user_group
        
        status_info = {
            "group_id": "group-123",
            "is_active": True,
            "is_expired": False,
            "expires_at": (datetime.utcnow() + timedelta(days=20)).isoformat(),
            "days_remaining": 20,
            "subscription_id": "subscription-123"
        }
        
        with patch('app.services.subscription.SubscriptionService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.validate_subscription_status.return_value = status_info
            
            response = client.get("/api/v1/mobile/subscriptions/groups/group-123/status")
            
            assert response.status_code == 200
            data = response.json()
            assert data["group_id"] == "group-123"
            assert data["is_active"] == True
            assert data["days_remaining"] == 20
    
    @patch('app.api.v1.mobile_subscriptions.get_current_registered_user')
    @patch('app.api.v1.mobile_subscriptions.get_db')
    async def test_get_group_status_unauthorized(
        self, mock_get_db, mock_get_user, client, mock_db, mock_user_context
    ):
        """Test retrieval with unauthorized group access"""
        mock_get_user.return_value = mock_user_context
        mock_get_db.return_value = mock_db
        mock_db.get.return_value = None  # Group not found or not owned by user
        
        response = client.get("/api/v1/mobile/subscriptions/groups/group-456/status")
        
        assert response.status_code == 404
        assert "not found or not authorized" in response.json()["detail"]


class TestValidateCoverage:
    """Test coverage validation"""
    
    @patch('app.api.v1.mobile_subscriptions.get_current_registered_user')
    @patch('app.api.v1.mobile_subscriptions.get_db')
    async def test_validate_coverage_success(
        self, mock_get_db, mock_get_user, client, mock_db, mock_user_context
    ):
        """Test successful coverage validation"""
        mock_get_user.return_value = mock_user_context
        mock_get_db.return_value = mock_db
        
        alternative_firms = [
            {
                "firm_id": "firm-123",
                "firm_name": "Test Security Firm",
                "coverage_area_name": "Downtown Area"
            },
            {
                "firm_id": "firm-456",
                "firm_name": "Another Security Firm",
                "coverage_area_name": "Uptown Area"
            }
        ]
        
        with patch('app.services.subscription.SubscriptionService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_alternative_firms_for_location.return_value = alternative_firms
            
            request_data = {
                "latitude": 40.7128,
                "longitude": -74.0060
            }
            
            response = client.post("/api/v1/mobile/subscriptions/validate-coverage", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["firm_name"] == "Test Security Firm"
            assert data[1]["firm_name"] == "Another Security Firm"
    
    @patch('app.api.v1.mobile_subscriptions.get_current_registered_user')
    @patch('app.api.v1.mobile_subscriptions.get_db')
    async def test_validate_coverage_no_coverage(
        self, mock_get_db, mock_get_user, client, mock_db, mock_user_context
    ):
        """Test validation when no coverage is available"""
        mock_get_user.return_value = mock_user_context
        mock_get_db.return_value = mock_db
        
        with patch('app.services.subscription.SubscriptionService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service
            mock_service.get_alternative_firms_for_location.return_value = []
            
            request_data = {
                "latitude": 45.0000,
                "longitude": -90.0000
            }
            
            response = client.post("/api/v1/mobile/subscriptions/validate-coverage", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 0
    
    def test_validate_coverage_invalid_coordinates(self, client):
        """Test validation with invalid coordinates"""
        request_data = {
            "latitude": 95.0,  # Invalid latitude
            "longitude": -74.0060
        }
        
        response = client.post("/api/v1/mobile/subscriptions/validate-coverage", json=request_data)
        
        # Mobile endpoints require authentication, so we expect 401 without proper auth
        assert response.status_code == 401