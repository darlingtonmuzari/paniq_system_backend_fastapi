"""
Unit tests for subscription service
"""
import pytest
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, patch

from app.services.subscription import SubscriptionService
from app.services.credit import InsufficientCreditsError
from app.models.security_firm import SecurityFirm
from app.models.subscription import SubscriptionProduct, StoredSubscription


class TestSubscriptionService:
    """Test cases for SubscriptionService"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def subscription_service(self, mock_db):
        """Subscription service instance with mocked database"""
        return SubscriptionService(mock_db)
    
    @pytest.fixture
    def sample_firm(self):
        """Sample security firm for testing"""
        return SecurityFirm(
            id="firm-123",
            name="Test Security Firm",
            registration_number="REG123",
            email="test@security.com",
            phone="+1234567890",
            address="123 Test St",
            verification_status="approved",
            credit_balance=200
        )
    
    @pytest.fixture
    def sample_product(self):
        """Sample subscription product for testing"""
        return SubscriptionProduct(
            id="product-123",
            firm_id="firm-123",
            name="Basic Security Package",
            description="Basic security services",
            max_users=10,
            price=Decimal("99.99"),
            credit_cost=50,
            is_active=True
        )
    
    @pytest.mark.asyncio
    async def test_create_product_success(self, subscription_service, mock_db, sample_firm):
        """Test successful product creation"""
        # Setup
        mock_db.get.return_value = sample_firm
        mock_db.add = AsyncMock()
        mock_db.flush = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Mock credit service
        with patch.object(subscription_service, 'credit_service') as mock_credit_service:
            mock_credit_service.deduct_credits = AsyncMock()
            
            # Execute
            product = await subscription_service.create_product(
                firm_id="firm-123",
                name="Premium Package",
                description="Premium security services",
                max_users=20,
                price=Decimal("199.99"),
                credit_cost=100
            )
        
        # Verify
        assert product.name == "Premium Package"
        assert product.max_users == 20
        assert product.price == Decimal("199.99")
        assert product.credit_cost == 100
        assert product.is_active is True
        
        # Verify database operations
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()
        mock_db.commit.assert_called_once()
        
        # Verify credit deduction
        mock_credit_service.deduct_credits.assert_called_once_with(
            firm_id="firm-123",
            amount=100,
            description="Product creation - Premium Package",
            reference_id=str(product.id)
        )
    
    @pytest.mark.asyncio
    async def test_create_product_firm_not_found(self, subscription_service, mock_db):
        """Test product creation with non-existent firm"""
        # Setup
        mock_db.get.return_value = None
        
        # Execute & Verify
        with pytest.raises(ValueError, match="Security firm not found"):
            await subscription_service.create_product(
                firm_id="nonexistent",
                name="Test Package",
                description="Test",
                max_users=10,
                price=Decimal("99.99"),
                credit_cost=50
            )
    
    @pytest.mark.asyncio
    async def test_create_product_firm_not_approved(self, subscription_service, mock_db, sample_firm):
        """Test product creation with unapproved firm"""
        # Setup
        sample_firm.verification_status = "pending"
        mock_db.get.return_value = sample_firm
        
        # Execute & Verify
        with pytest.raises(ValueError, match="Security firm must be approved"):
            await subscription_service.create_product(
                firm_id="firm-123",
                name="Test Package",
                description="Test",
                max_users=10,
                price=Decimal("99.99"),
                credit_cost=50
            )
    
    @pytest.mark.asyncio
    async def test_create_product_invalid_max_users(self, subscription_service, mock_db, sample_firm):
        """Test product creation with invalid max users"""
        # Setup
        mock_db.get.return_value = sample_firm
        
        # Execute & Verify
        with pytest.raises(ValueError, match="Maximum users must be greater than 0"):
            await subscription_service.create_product(
                firm_id="firm-123",
                name="Test Package",
                description="Test",
                max_users=0,  # Invalid
                price=Decimal("99.99"),
                credit_cost=50
            )
    
    @pytest.mark.asyncio
    async def test_create_product_negative_price(self, subscription_service, mock_db, sample_firm):
        """Test product creation with negative price"""
        # Setup
        mock_db.get.return_value = sample_firm
        
        # Execute & Verify
        with pytest.raises(ValueError, match="Price cannot be negative"):
            await subscription_service.create_product(
                firm_id="firm-123",
                name="Test Package",
                description="Test",
                max_users=10,
                price=Decimal("-10.00"),  # Invalid
                credit_cost=50
            )
    
    @pytest.mark.asyncio
    async def test_create_product_insufficient_credits(self, subscription_service, mock_db, sample_firm):
        """Test product creation with insufficient credits"""
        # Setup
        sample_firm.credit_balance = 25  # Less than required
        mock_db.get.return_value = sample_firm
        
        # Execute & Verify
        with pytest.raises(InsufficientCreditsError):
            await subscription_service.create_product(
                firm_id="firm-123",
                name="Test Package",
                description="Test",
                max_users=10,
                price=Decimal("99.99"),
                credit_cost=50  # More than available
            )
    
    @pytest.mark.asyncio
    async def test_get_product_by_id_success(self, subscription_service, mock_db, sample_product):
        """Test successful product retrieval by ID"""
        # Setup
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_product
        mock_db.execute.return_value = mock_result
        
        # Execute
        product = await subscription_service.get_product_by_id("product-123")
        
        # Verify
        assert product == sample_product
    
    @pytest.mark.asyncio
    async def test_get_product_by_id_not_found(self, subscription_service, mock_db):
        """Test product retrieval by ID when not found"""
        # Setup
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        # Execute
        product = await subscription_service.get_product_by_id("nonexistent")
        
        # Verify
        assert product is None
    
    @pytest.mark.asyncio
    async def test_get_firm_products_active_only(self, subscription_service, mock_db, sample_product):
        """Test getting firm products (active only)"""
        # Setup
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [sample_product]
        mock_db.execute.return_value = mock_result
        
        # Execute
        products = await subscription_service.get_firm_products("firm-123", include_inactive=False)
        
        # Verify
        assert len(products) == 1
        assert products[0] == sample_product
    
    @pytest.mark.asyncio
    async def test_get_firm_products_include_inactive(self, subscription_service, mock_db):
        """Test getting firm products including inactive"""
        # Setup
        active_product = SubscriptionProduct(id="active", is_active=True)
        inactive_product = SubscriptionProduct(id="inactive", is_active=False)
        
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [active_product, inactive_product]
        mock_db.execute.return_value = mock_result
        
        # Execute
        products = await subscription_service.get_firm_products("firm-123", include_inactive=True)
        
        # Verify
        assert len(products) == 2
    
    @pytest.mark.asyncio
    async def test_get_active_products(self, subscription_service, mock_db, sample_product):
        """Test getting all active products"""
        # Setup
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [sample_product]
        mock_db.execute.return_value = mock_result
        
        # Execute
        products = await subscription_service.get_active_products()
        
        # Verify
        assert len(products) == 1
        assert products[0] == sample_product
    
    @pytest.mark.asyncio
    async def test_update_product_success(self, subscription_service, mock_db, sample_product):
        """Test successful product update"""
        # Setup
        mock_db.get.return_value = sample_product
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Execute
        updated_product = await subscription_service.update_product(
            product_id="product-123",
            name="Updated Package",
            price=Decimal("149.99")
        )
        
        # Verify
        assert updated_product.name == "Updated Package"
        assert updated_product.price == Decimal("149.99")
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_product_not_found(self, subscription_service, mock_db):
        """Test product update when product not found"""
        # Setup
        mock_db.get.return_value = None
        
        # Execute & Verify
        with pytest.raises(ValueError, match="Subscription product not found"):
            await subscription_service.update_product(
                product_id="nonexistent",
                name="Updated Package"
            )
    
    @pytest.mark.asyncio
    async def test_activate_product_success(self, subscription_service, mock_db, sample_product):
        """Test successful product activation"""
        # Setup
        sample_product.is_active = False
        mock_db.get.return_value = sample_product
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Execute
        activated_product = await subscription_service.activate_product("product-123")
        
        # Verify
        assert activated_product.is_active is True
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_deactivate_product_success(self, subscription_service, mock_db, sample_product):
        """Test successful product deactivation"""
        # Setup
        mock_db.get.return_value = sample_product
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Execute
        deactivated_product = await subscription_service.deactivate_product("product-123")
        
        # Verify
        assert deactivated_product.is_active is False
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_product_success(self, subscription_service, mock_db, sample_product):
        """Test successful product deletion"""
        # Setup
        mock_db.get.return_value = sample_product
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()
        
        # Mock no existing subscriptions
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        # Execute
        result = await subscription_service.delete_product("product-123")
        
        # Verify
        assert result is True
        mock_db.delete.assert_called_once_with(sample_product)
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_product_with_existing_subscriptions(self, subscription_service, mock_db, sample_product):
        """Test product deletion with existing subscriptions"""
        # Setup
        mock_db.get.return_value = sample_product
        
        # Mock existing subscriptions
        existing_subscription = StoredSubscription(id="sub-123", product_id="product-123")
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [existing_subscription]
        mock_db.execute.return_value = mock_result
        
        # Execute & Verify
        with pytest.raises(ValueError, match="Cannot delete product with existing subscriptions"):
            await subscription_service.delete_product("product-123")
    
    @pytest.mark.asyncio
    async def test_get_product_statistics(self, subscription_service, mock_db, sample_product):
        """Test getting product statistics"""
        # Setup
        mock_db.get.return_value = sample_product
        
        # Mock stored subscriptions
        applied_sub = StoredSubscription(id="sub-1", product_id="product-123", is_applied=True)
        pending_sub = StoredSubscription(id="sub-2", product_id="product-123", is_applied=False)
        
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [applied_sub, pending_sub]
        mock_db.execute.return_value = mock_result
        
        # Execute
        stats = await subscription_service.get_product_statistics("product-123")
        
        # Verify
        assert stats["product_id"] == str(sample_product.id)
        assert stats["product_name"] == sample_product.name
        assert stats["total_purchases"] == 2
        assert stats["applied_subscriptions"] == 1
        assert stats["pending_subscriptions"] == 1
        assert stats["total_revenue"] == float(sample_product.price) * 2
        assert stats["price"] == float(sample_product.price)
        assert stats["max_users"] == sample_product.max_users
        assert stats["is_active"] == sample_product.is_active


class TestSubscriptionPurchaseAndApplication:
    """Test subscription purchase and application functionality"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def subscription_service(self, mock_db):
        """Subscription service instance with mocked database"""
        return SubscriptionService(mock_db)
    
    @pytest.fixture
    def sample_user(self):
        from app.models.user import RegisteredUser
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
    def sample_user_group(self, sample_user):
        from app.models.user import UserGroup
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
    def sample_security_firm(self):
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
    def sample_subscription_product(self, sample_security_firm):
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
    def sample_coverage_area(self, sample_security_firm):
        from app.models.security_firm import CoverageArea
        from geoalchemy2.elements import WKTElement
        return CoverageArea(
            id="coverage-123",
            firm_id="firm-123",
            name="Downtown Area",
            boundary=WKTElement("POLYGON((-74.01 40.71, -74.00 40.71, -74.00 40.72, -74.01 40.72, -74.01 40.71))", srid=4326)
        )
    
    @pytest.mark.asyncio
    async def test_purchase_subscription_success(self, subscription_service, mock_db, sample_user, sample_subscription_product):
        """Test successful subscription purchase"""
        mock_db.get.side_effect = lambda model, id: {
            sample_user.__class__: sample_user,
            sample_subscription_product.__class__: sample_subscription_product
        }.get(model)
        mock_db.add = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        stored_subscription = await subscription_service.purchase_subscription(
            user_id="user-123",
            product_id="product-123"
        )
        
        assert stored_subscription.user_id == "user-123"
        assert stored_subscription.product_id == "product-123"
        assert stored_subscription.is_applied == False
        assert stored_subscription.applied_to_group_id is None
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_purchase_subscription_user_not_found(self, subscription_service, mock_db):
        """Test purchase with non-existent user"""
        mock_db.get.return_value = None
        
        with pytest.raises(ValueError, match="User not found"):
            await subscription_service.purchase_subscription(
                user_id="invalid-user",
                product_id="product-123"
            )
    
    @pytest.mark.asyncio
    async def test_purchase_subscription_suspended_user(self, subscription_service, mock_db, sample_user, sample_subscription_product):
        """Test purchase with suspended user"""
        sample_user.is_suspended = True
        mock_db.get.side_effect = lambda model, id: {
            sample_user.__class__: sample_user,
            sample_subscription_product.__class__: sample_subscription_product
        }.get(model)
        
        with pytest.raises(ValueError, match="User account is suspended"):
            await subscription_service.purchase_subscription(
                user_id="user-123",
                product_id="product-123"
            )
    
    @pytest.mark.asyncio
    async def test_purchase_subscription_inactive_product(self, subscription_service, mock_db, sample_user, sample_subscription_product):
        """Test purchase with inactive product"""
        sample_subscription_product.is_active = False
        mock_db.get.side_effect = lambda model, id: {
            sample_user.__class__: sample_user,
            sample_subscription_product.__class__: sample_subscription_product
        }.get(model)
        
        with pytest.raises(ValueError, match="not available for purchase"):
            await subscription_service.purchase_subscription(
                user_id="user-123",
                product_id="product-123"
            )
    
    @pytest.mark.asyncio
    async def test_get_user_stored_subscriptions(self, subscription_service, mock_db):
        """Test getting user's stored subscriptions"""
        from datetime import datetime
        
        # Mock stored subscriptions
        stored_subscription = StoredSubscription(
            id="subscription-123",
            user_id="user-123",
            product_id="product-123",
            is_applied=False,
            purchased_at=datetime.utcnow()
        )
        
        # Create a mock result that behaves like the actual result
        class MockResult:
            def scalars(self):
                class MockScalars:
                    def all(self):
                        return [stored_subscription]
                return MockScalars()
        
        mock_db.execute.return_value = MockResult()
        
        subscriptions = await subscription_service.get_user_stored_subscriptions("user-123")
        
        assert len(subscriptions) == 1
        assert subscriptions[0].id == "subscription-123"
        assert subscriptions[0].is_applied == False
    
    @pytest.mark.asyncio
    async def test_apply_subscription_to_group_success(
        self, subscription_service, mock_db, sample_user, sample_user_group, 
        sample_subscription_product, sample_coverage_area
    ):
        """Test successful subscription application to group"""
        from datetime import datetime
        
        stored_subscription = StoredSubscription(
            id="subscription-123",
            user_id="user-123",
            product_id="product-123",
            is_applied=False,
            purchased_at=datetime.utcnow()
        )
        
        mock_db.get.side_effect = lambda model, id: {
            StoredSubscription: stored_subscription,
            sample_user_group.__class__: sample_user_group,
            sample_subscription_product.__class__: sample_subscription_product
        }.get(model)
        mock_db.commit = AsyncMock()
        
        # Mock the coverage validation method directly
        with patch.object(subscription_service, '_validate_group_coverage', return_value=True):
            result = await subscription_service.apply_subscription_to_group(
                user_id="user-123",
                subscription_id="subscription-123",
                group_id="group-123"
            )
        
        assert result == True
        assert stored_subscription.is_applied == True
        assert stored_subscription.applied_to_group_id == "group-123"
        assert sample_user_group.subscription_id == "subscription-123"
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_apply_subscription_already_applied(self, subscription_service, mock_db):
        """Test applying already applied subscription"""
        from datetime import datetime
        
        stored_subscription = StoredSubscription(
            id="subscription-123",
            user_id="user-123",
            product_id="product-123",
            is_applied=True,  # Already applied
            purchased_at=datetime.utcnow()
        )
        
        mock_db.get.return_value = stored_subscription
        
        with pytest.raises(ValueError, match="already been applied"):
            await subscription_service.apply_subscription_to_group(
                user_id="user-123",
                subscription_id="subscription-123",
                group_id="group-123"
            )
    
    @pytest.mark.asyncio
    async def test_apply_subscription_wrong_user(self, subscription_service, mock_db):
        """Test applying subscription that doesn't belong to user"""
        from datetime import datetime
        
        stored_subscription = StoredSubscription(
            id="subscription-123",
            user_id="other-user-123",  # Different user
            product_id="product-123",
            is_applied=False,
            purchased_at=datetime.utcnow()
        )
        
        mock_db.get.return_value = stored_subscription
        
        with pytest.raises(ValueError, match="does not belong to this user"):
            await subscription_service.apply_subscription_to_group(
                user_id="user-123",
                subscription_id="subscription-123",
                group_id="group-123"
            )
    
    @pytest.mark.asyncio
    async def test_apply_subscription_outside_coverage(
        self, subscription_service, mock_db, sample_user, sample_user_group, sample_subscription_product
    ):
        """Test applying subscription when group is outside coverage area"""
        from datetime import datetime
        
        stored_subscription = StoredSubscription(
            id="subscription-123",
            user_id="user-123",
            product_id="product-123",
            is_applied=False,
            purchased_at=datetime.utcnow()
        )
        
        mock_db.get.side_effect = lambda model, id: {
            StoredSubscription: stored_subscription,
            sample_user_group.__class__: sample_user_group,
            sample_subscription_product.__class__: sample_subscription_product
        }.get(model)
        
        # Mock coverage validation to return False (outside coverage)
        with patch.object(subscription_service, '_validate_group_coverage', return_value=False):
            with pytest.raises(ValueError, match="outside the security firm's coverage area"):
                await subscription_service.apply_subscription_to_group(
                    user_id="user-123",
                    subscription_id="subscription-123",
                    group_id="group-123"
                )
    
    @pytest.mark.asyncio
    async def test_validate_subscription_status_active(self, subscription_service, mock_db, sample_user_group):
        """Test validating active subscription status"""
        from datetime import datetime, timedelta
        
        # Set subscription to expire in 15 days
        sample_user_group.subscription_expires_at = datetime.utcnow() + timedelta(days=15)
        sample_user_group.subscription_id = "subscription-123"
        
        mock_db.get.return_value = sample_user_group
        
        status = await subscription_service.validate_subscription_status("group-123")
        
        assert status["group_id"] == "group-123"
        assert status["is_active"] == True
        assert status["is_expired"] == False
        assert status["days_remaining"] >= 14  # Allow for timing differences
        assert status["subscription_id"] == "subscription-123"
    
    @pytest.mark.asyncio
    async def test_validate_subscription_status_expired(self, subscription_service, mock_db, sample_user_group):
        """Test validating expired subscription status"""
        from datetime import datetime, timedelta
        
        # Set subscription to have expired 5 days ago
        sample_user_group.subscription_expires_at = datetime.utcnow() - timedelta(days=5)
        sample_user_group.subscription_id = "subscription-123"
        
        mock_db.get.return_value = sample_user_group
        
        status = await subscription_service.validate_subscription_status("group-123")
        
        assert status["group_id"] == "group-123"
        assert status["is_active"] == False
        assert status["is_expired"] == True
        assert status["days_remaining"] == 0
    
    @pytest.mark.asyncio
    async def test_validate_subscription_status_no_subscription(self, subscription_service, mock_db, sample_user_group):
        """Test validating status when no subscription exists"""
        sample_user_group.subscription_expires_at = None
        sample_user_group.subscription_id = None
        
        mock_db.get.return_value = sample_user_group
        
        status = await subscription_service.validate_subscription_status("group-123")
        
        assert status["group_id"] == "group-123"
        assert status["is_active"] == False
        assert status["is_expired"] == True
        assert status["days_remaining"] == 0
        assert status["subscription_id"] is None
    
    @pytest.mark.asyncio
    async def test_get_alternative_firms_for_location(self, subscription_service, mock_db, sample_security_firm, sample_coverage_area):
        """Test getting alternative firms for a location"""
        # Create a mock result that behaves like the actual result
        class MockResult:
            def all(self):
                return [(sample_security_firm, sample_coverage_area)]
        
        mock_db.execute.return_value = MockResult()
        
        alternatives = await subscription_service.get_alternative_firms_for_location(40.7128, -74.0060)
        
        assert len(alternatives) == 1
        assert alternatives[0]["firm_id"] == "firm-123"
        assert alternatives[0]["firm_name"] == "Test Security Firm"
        assert alternatives[0]["coverage_area_name"] == "Downtown Area"
    
    @pytest.mark.asyncio
    async def test_get_group_active_subscriptions(self, subscription_service, mock_db, sample_user_group):
        """Test getting active subscriptions for user's groups"""
        from datetime import datetime, timedelta
        
        # Set up active subscription
        sample_user_group.subscription_expires_at = datetime.utcnow() + timedelta(days=20)
        sample_user_group.subscription_id = "subscription-123"
        sample_user_group.mobile_numbers = []  # Empty list for simplicity
        
        # Create a mock result that behaves like the actual result
        class MockResult:
            def scalars(self):
                class MockScalars:
                    def all(self):
                        return [sample_user_group]
                return MockScalars()
        
        mock_db.execute.return_value = MockResult()
        
        # Mock validate_subscription_status method
        with patch.object(subscription_service, 'validate_subscription_status') as mock_validate:
            mock_validate.return_value = {
                "group_id": "group-123",
                "is_active": True,
                "is_expired": False,
                "expires_at": (datetime.utcnow() + timedelta(days=20)).isoformat(),
                "days_remaining": 20,
                "subscription_id": "subscription-123"
            }
            
            active_subscriptions = await subscription_service.get_group_active_subscriptions("user-123")
            
            assert len(active_subscriptions) == 1
            assert active_subscriptions[0]["group_id"] == "group-123"
            assert active_subscriptions[0]["group_name"] == "Home Group"
            assert active_subscriptions[0]["is_active"] == True