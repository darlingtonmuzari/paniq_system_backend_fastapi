"""
Tests for prank detection service
"""
import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.prank_detection import (
    PrankDetectionService, 
    UserNotFoundError, 
    FineNotFoundError,
    PaymentProcessingError
)
from app.models.user import RegisteredUser, UserFine, UserGroup
from app.models.emergency import PanicRequest, RequestFeedback
from app.models.subscription import StoredSubscription


class TestPrankDetectionService:
    """Test prank detection service"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.execute = AsyncMock()
        return db

    @pytest.fixture
    def prank_service(self, mock_db):
        """Create prank detection service"""
        return PrankDetectionService(mock_db)

    @pytest.fixture
    def test_user(self):
        """Create test user"""
        user = MagicMock(spec=RegisteredUser)
        user.id = uuid4()
        user.email = "test@example.com"
        user.phone = "+1234567890"
        user.first_name = "Test"
        user.last_name = "User"
        user.prank_flags = 0
        user.total_fines = Decimal("0.00")
        user.is_suspended = False
        return user

    @pytest.fixture
    def test_fine(self, test_user):
        """Create test fine"""
        fine = MagicMock(spec=UserFine)
        fine.id = uuid4()
        fine.user_id = test_user.id
        fine.amount = Decimal("50.00")
        fine.reason = "Test fine"
        fine.is_paid = False
        fine.user = test_user
        return fine
    
    async def test_track_prank_accumulation_user_not_found(self, prank_service, mock_db):
        """Test tracking prank accumulation for non-existent user"""
        # Mock database to return None for user query
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        with pytest.raises(UserNotFoundError):
            await prank_service.track_prank_accumulation(uuid4())
    
    async def test_track_prank_accumulation_no_pranks(self, prank_service, test_user, mock_db):
        """Test tracking prank accumulation for user with no pranks"""
        # Mock database to return user and recent pranks count
        mock_user_result = AsyncMock()
        mock_user_result.scalar_one_or_none.return_value = test_user
        
        mock_count_result = AsyncMock()
        mock_count_result.scalar.return_value = 0
        
        mock_db.execute.side_effect = [mock_user_result, mock_count_result]
        
        tracking_info = await prank_service.track_prank_accumulation(test_user.id)
        
        assert tracking_info["user_id"] == str(test_user.id)
        assert tracking_info["total_prank_flags"] == 0
        assert tracking_info["recent_prank_flags"] == 0
        assert tracking_info["total_fines"] == 0.0
        assert tracking_info["is_suspended"] is False
        assert tracking_info["calculated_fine_amount"] is None
        assert tracking_info["should_suspend"] is False
        assert tracking_info["should_ban"] is False
        assert tracking_info["days_until_ban"] == 10
    
    async def test_calculate_fine_amount(self, prank_service):
        """Test fine amount calculation"""
        # Test below threshold
        amount = await prank_service._calculate_fine_amount(2)
        assert amount == Decimal("0.00")
        
        # Test at threshold
        amount = await prank_service._calculate_fine_amount(3)
        assert amount == Decimal("50.00")  # Base amount
        
        # Test progressive calculation
        amount = await prank_service._calculate_fine_amount(4)
        assert amount == Decimal("75.00")  # 50 * 1.5^1
        
        amount = await prank_service._calculate_fine_amount(5)
        assert amount == Decimal("112.50")  # 50 * 1.5^2
        
        # Test maximum cap
        amount = await prank_service._calculate_fine_amount(20)
        assert amount == Decimal("500.00")  # Capped at maximum
    
    async def test_process_payment_gateway_simulation(self, prank_service):
        """Test payment gateway simulation"""
        result = await prank_service._process_payment_gateway(
            amount=Decimal("50.00"),
            payment_method="card",
            payment_reference="txn_123"
        )
        
        # Should always return True in test environment
        assert result is True
    
    async def test_calculate_automatic_fine_user_not_found(self, prank_service, mock_db):
        """Test automatic fine calculation for non-existent user"""
        # Mock database to return None for user query
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        with pytest.raises(UserNotFoundError):
            await prank_service.calculate_automatic_fine(uuid4())
    
    @patch('app.services.prank_detection.PrankDetectionService._process_payment_gateway')
    async def test_process_fine_payment_success(self, mock_payment, prank_service, test_fine, mock_db):
        """Test successful fine payment processing"""
        mock_payment.return_value = True
        
        # Mock database to return fine with user
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = test_fine
        mock_db.execute.return_value = mock_result
        
        # Mock unpaid fines count
        with patch.object(prank_service, '_get_unpaid_fines_count', return_value=1):
            paid_fine = await prank_service.process_fine_payment(
                fine_id=test_fine.id,
                payment_method="card",
                payment_reference="txn_123"
            )
        
        assert paid_fine.is_paid is True
        assert paid_fine.paid_at is not None
        mock_payment.assert_called_once()
    
    async def test_process_fine_payment_not_found(self, prank_service, mock_db):
        """Test fine payment processing for non-existent fine"""
        # Mock database to return None for fine query
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        with pytest.raises(FineNotFoundError):
            await prank_service.process_fine_payment(
                fine_id=uuid4(),
                payment_method="card",
                payment_reference="txn_123"
            )