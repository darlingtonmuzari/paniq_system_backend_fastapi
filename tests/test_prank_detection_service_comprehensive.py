"""
Comprehensive unit tests for prank detection service
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.prank_detection import (
    PrankDetectionService,
    PrankDetectionError,
    UserNotFoundError,
    FineNotFoundError,
    PaymentProcessingError
)
from app.models.user import RegisteredUser, UserFine
from app.models.emergency import RequestFeedback, PanicRequest
from app.core.exceptions import APIError


class TestPrankDetectionService:
    """Test prank detection service functionality"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        db = AsyncMock()
        return db
    
    @pytest.fixture
    def service(self, mock_db):
        """Prank detection service instance"""
        return PrankDetectionService(mock_db)
    
    @pytest.fixture
    def sample_user(self):
        """Sample registered user"""
        return RegisteredUser(
            id=uuid4(),
            email="test@example.com",
            phone="+1234567890",
            first_name="John",
            last_name="Doe",
            prank_flags=3,
            total_fines=Decimal("100.00"),
            is_suspended=False
        )
    
    @pytest.fixture
    def sample_fine(self):
        """Sample user fine"""
        return UserFine(
            id=uuid4(),
            user_id=uuid4(),
            amount=Decimal("75.00"),
            reason="Automatic fine for prank behavior - prank flags: 4",
            is_paid=False
        )
    
    def test_service_constants(self, service):
        """Test service constants are properly defined"""
        assert service.BASE_FINE_AMOUNT == Decimal("50.00")
        assert service.FINE_MULTIPLIER == Decimal("1.5")
        assert service.MAX_FINE_AMOUNT == Decimal("500.00")
        assert service.PERMANENT_BAN_THRESHOLD == 10
        assert service.SUSPENSION_THRESHOLD == 5
    
    @pytest.mark.asyncio
    async def test_track_prank_accumulation_success(self, service, mock_db, sample_user):
        """Test successful prank accumulation tracking"""
        user_id = sample_user.id
        
        # Mock database queries
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_user
        
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 2  # Recent pranks
        
        mock_db.execute.side_effect = [mock_user_result, mock_count_result]
        
        result = await service.track_prank_accumulation(user_id)
        
        assert result["user_id"] == str(user_id)
        assert result["total_prank_flags"] == 3
        assert result["recent_prank_flags"] == 2
        assert result["total_fines"] == 100.0
        assert result["is_suspended"] is False
        assert result["calculated_fine_amount"] == 50.0  # Base fine for 3 flags
        assert result["should_suspend"] is False
        assert result["should_ban"] is False
        assert result["days_until_ban"] == 7  # 10 - 3
    
    @pytest.mark.asyncio
    async def test_track_prank_accumulation_suspension_threshold(self, service, mock_db, sample_user):
        """Test prank accumulation tracking at suspension threshold"""
        sample_user.prank_flags = 5  # At suspension threshold
        user_id = sample_user.id
        
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_user
        
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 3
        
        mock_db.execute.side_effect = [mock_user_result, mock_count_result]
        
        result = await service.track_prank_accumulation(user_id)
        
        assert result["total_prank_flags"] == 5
        assert result["should_suspend"] is True
        assert result["should_ban"] is False
        assert result["calculated_fine_amount"] == 112.5  # 50 * 1.5^2
    
    @pytest.mark.asyncio
    async def test_track_prank_accumulation_ban_threshold(self, service, mock_db, sample_user):
        """Test prank accumulation tracking at ban threshold"""
        sample_user.prank_flags = 10  # At ban threshold
        user_id = sample_user.id
        
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_user
        
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 5
        
        mock_db.execute.side_effect = [mock_user_result, mock_count_result]
        
        result = await service.track_prank_accumulation(user_id)
        
        assert result["total_prank_flags"] == 10
        assert result["should_suspend"] is False  # Ban takes precedence
        assert result["should_ban"] is True
        assert result["days_until_ban"] == 0
    
    @pytest.mark.asyncio
    async def test_track_prank_accumulation_user_not_found(self, service, mock_db):
        """Test prank accumulation tracking with non-existent user"""
        user_id = uuid4()
        
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = None
        
        mock_db.execute.return_value = mock_user_result
        
        with pytest.raises(UserNotFoundError):
            await service.track_prank_accumulation(user_id)
    
    @pytest.mark.asyncio
    async def test_calculate_automatic_fine_success(self, service, mock_db, sample_user):
        """Test successful automatic fine calculation"""
        sample_user.prank_flags = 4  # Above threshold for fining
        user_id = sample_user.id
        
        # Mock user lookup
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_user
        
        # Mock existing fine check (no existing fine)
        mock_fine_result = MagicMock()
        mock_fine_result.scalar_one_or_none.return_value = None
        
        mock_db.execute.side_effect = [mock_user_result, mock_fine_result]
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        result = await service.calculate_automatic_fine(user_id)
        
        assert result is not None
        assert isinstance(result, UserFine)
        assert result.user_id == user_id
        assert result.amount == Decimal("75.00")  # 50 * 1.5^1
        assert "prank flags: 4" in result.reason
        
        # Verify database operations
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
        
        # Verify user's total fines were updated
        assert sample_user.total_fines == Decimal("175.00")  # 100 + 75
    
    @pytest.mark.asyncio
    async def test_calculate_automatic_fine_no_fine_needed(self, service, mock_db, sample_user):
        """Test automatic fine calculation when no fine is needed"""
        sample_user.prank_flags = 2  # Below threshold
        user_id = sample_user.id
        
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_user
        
        mock_db.execute.return_value = mock_user_result
        
        result = await service.calculate_automatic_fine(user_id)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_calculate_automatic_fine_existing_fine(self, service, mock_db, sample_user, sample_fine):
        """Test automatic fine calculation when fine already exists"""
        sample_user.prank_flags = 4
        user_id = sample_user.id
        
        # Mock user lookup
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_user
        
        # Mock existing fine check (fine exists)
        mock_fine_result = MagicMock()
        mock_fine_result.scalar_one_or_none.return_value = sample_fine
        
        mock_db.execute.side_effect = [mock_user_result, mock_fine_result]
        
        result = await service.calculate_automatic_fine(user_id)
        
        assert result == sample_fine
        # Should not create new fine
        mock_db.add.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_process_fine_payment_success(self, service, mock_db, sample_fine):
        """Test successful fine payment processing"""
        fine_id = sample_fine.id
        payment_method = "card"
        payment_reference = "txn_123456"
        
        # Add user to fine for relationship
        sample_user = RegisteredUser(
            id=sample_fine.user_id,
            email="test@example.com",
            phone="+1234567890",
            first_name="John",
            last_name="Doe",
            is_suspended=True
        )
        sample_fine.user = sample_user
        
        mock_fine_result = MagicMock()
        mock_fine_result.scalar_one_or_none.return_value = sample_fine
        
        mock_unpaid_count_result = MagicMock()
        mock_unpaid_count_result.scalar.return_value = 1  # This is the last unpaid fine
        
        mock_db.execute.side_effect = [mock_fine_result, mock_unpaid_count_result]
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        with patch.object(service, '_process_payment_gateway') as mock_payment:
            mock_payment.return_value = True
            
            result = await service.process_fine_payment(fine_id, payment_method, payment_reference)
            
            assert result.is_paid is True
            assert result.paid_at is not None
            assert result.user.is_suspended is False  # Should be unsuspended
            
            mock_payment.assert_called_once_with(
                amount=sample_fine.amount,
                payment_method=payment_method,
                payment_reference=payment_reference
            )
    
    @pytest.mark.asyncio
    async def test_process_fine_payment_fine_not_found(self, service, mock_db):
        """Test fine payment processing with non-existent fine"""
        fine_id = uuid4()
        
        mock_fine_result = MagicMock()
        mock_fine_result.scalar_one_or_none.return_value = None
        
        mock_db.execute.return_value = mock_fine_result
        
        with pytest.raises(FineNotFoundError):
            await service.process_fine_payment(fine_id, "card", "txn_123")
    
    @pytest.mark.asyncio
    async def test_process_fine_payment_already_paid(self, service, mock_db, sample_fine):
        """Test fine payment processing when fine is already paid"""
        sample_fine.is_paid = True
        sample_fine.paid_at = datetime.utcnow()
        fine_id = sample_fine.id
        
        mock_fine_result = MagicMock()
        mock_fine_result.scalar_one_or_none.return_value = sample_fine
        
        mock_db.execute.return_value = mock_fine_result
        
        result = await service.process_fine_payment(fine_id, "card", "txn_123")
        
        assert result == sample_fine
        assert result.is_paid is True
    
    @pytest.mark.asyncio
    async def test_process_fine_payment_gateway_failure(self, service, mock_db, sample_fine):
        """Test fine payment processing with payment gateway failure"""
        fine_id = sample_fine.id
        
        mock_fine_result = MagicMock()
        mock_fine_result.scalar_one_or_none.return_value = sample_fine
        
        mock_db.execute.return_value = mock_fine_result
        
        with patch.object(service, '_process_payment_gateway') as mock_payment:
            mock_payment.return_value = False
            
            with pytest.raises(PaymentProcessingError, match="Payment gateway rejected"):
                await service.process_fine_payment(fine_id, "card", "txn_123")
    
    @pytest.mark.asyncio
    async def test_suspend_account_for_unpaid_fines_success(self, service, mock_db, sample_user):
        """Test successful account suspension for unpaid fines"""
        user_id = sample_user.id
        sample_user.is_suspended = False
        
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_user
        
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 2  # Has unpaid fines
        
        mock_db.execute.side_effect = [mock_user_result, mock_count_result]
        mock_db.commit = AsyncMock()
        
        result = await service.suspend_account_for_unpaid_fines(user_id)
        
        assert result is True
        assert sample_user.is_suspended is True
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_suspend_account_already_suspended(self, service, mock_db, sample_user):
        """Test account suspension when already suspended"""
        user_id = sample_user.id
        sample_user.is_suspended = True
        
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_user
        
        mock_db.execute.return_value = mock_user_result
        
        result = await service.suspend_account_for_unpaid_fines(user_id)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_suspend_account_no_unpaid_fines(self, service, mock_db, sample_user):
        """Test account suspension when no unpaid fines exist"""
        user_id = sample_user.id
        sample_user.is_suspended = False
        
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_user
        
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0  # No unpaid fines
        
        mock_db.execute.side_effect = [mock_user_result, mock_count_result]
        
        result = await service.suspend_account_for_unpaid_fines(user_id)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_create_permanent_ban_success(self, service, mock_db, sample_user):
        """Test successful permanent ban creation"""
        user_id = sample_user.id
        sample_user.prank_flags = 10  # At ban threshold
        sample_user.is_suspended = False
        
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_user
        
        mock_db.execute.return_value = mock_user_result
        mock_db.commit = AsyncMock()
        
        result = await service.create_permanent_ban(user_id, "Excessive prank behavior")
        
        assert result is True
        assert sample_user.is_suspended is True
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_permanent_ban_insufficient_flags(self, service, mock_db, sample_user):
        """Test permanent ban creation with insufficient prank flags"""
        user_id = sample_user.id
        sample_user.prank_flags = 5  # Below ban threshold
        
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = sample_user
        
        mock_db.execute.return_value = mock_user_result
        
        result = await service.create_permanent_ban(user_id)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_user_fines_all_fines(self, service, mock_db):
        """Test getting all user fines"""
        user_id = uuid4()
        
        mock_fines = [
            UserFine(id=uuid4(), user_id=user_id, amount=Decimal("50.00"), is_paid=True),
            UserFine(id=uuid4(), user_id=user_id, amount=Decimal("75.00"), is_paid=False)
        ]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_fines
        
        mock_db.execute.return_value = mock_result
        
        result = await service.get_user_fines(user_id, include_paid=True)
        
        assert len(result) == 2
        assert result == mock_fines
    
    @pytest.mark.asyncio
    async def test_get_user_fines_unpaid_only(self, service, mock_db):
        """Test getting only unpaid user fines"""
        user_id = uuid4()
        
        mock_fines = [
            UserFine(id=uuid4(), user_id=user_id, amount=Decimal("75.00"), is_paid=False)
        ]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_fines
        
        mock_db.execute.return_value = mock_result
        
        result = await service.get_user_fines(user_id, include_paid=False)
        
        assert len(result) == 1
        assert result[0].is_paid is False
    
    @pytest.mark.asyncio
    async def test_get_fine_statistics(self, service, mock_db):
        """Test getting fine statistics"""
        mock_fines = [
            UserFine(id=uuid4(), user_id=uuid4(), amount=Decimal("50.00"), is_paid=True),
            UserFine(id=uuid4(), user_id=uuid4(), amount=Decimal("75.00"), is_paid=False),
            UserFine(id=uuid4(), user_id=uuid4(), amount=Decimal("100.00"), is_paid=True),
            UserFine(id=uuid4(), user_id=uuid4(), amount=Decimal("125.00"), is_paid=False)
        ]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_fines
        
        mock_db.execute.return_value = mock_result
        
        result = await service.get_fine_statistics()
        
        assert result["total_fines"] == 4
        assert result["paid_fines"] == 2
        assert result["unpaid_fines"] == 2
        assert result["total_amount"] == 350.0  # 50 + 75 + 100 + 125
        assert result["paid_amount"] == 150.0   # 50 + 100
        assert result["unpaid_amount"] == 200.0 # 75 + 125
        assert result["payment_rate_percentage"] == 50.0  # 2/4 * 100
    
    @pytest.mark.asyncio
    async def test_get_fine_statistics_with_date_range(self, service, mock_db):
        """Test getting fine statistics with date range"""
        date_from = datetime(2024, 1, 1)
        date_to = datetime(2024, 12, 31)
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        
        mock_db.execute.return_value = mock_result
        
        result = await service.get_fine_statistics(date_from, date_to)
        
        assert result["date_range"]["from"] == "2024-01-01T00:00:00"
        assert result["date_range"]["to"] == "2024-12-31T00:00:00"
    
    @pytest.mark.asyncio
    async def test_calculate_fine_amount_below_threshold(self, service):
        """Test fine amount calculation below threshold"""
        amount = await service._calculate_fine_amount(2)
        assert amount == Decimal("0.00")
    
    @pytest.mark.asyncio
    async def test_calculate_fine_amount_at_threshold(self, service):
        """Test fine amount calculation at threshold"""
        amount = await service._calculate_fine_amount(3)
        assert amount == Decimal("50.00")  # Base amount
    
    @pytest.mark.asyncio
    async def test_calculate_fine_amount_progressive(self, service):
        """Test progressive fine amount calculation"""
        # 4 flags: 50 * 1.5^1 = 75
        amount = await service._calculate_fine_amount(4)
        assert amount == Decimal("75.00")
        
        # 5 flags: 50 * 1.5^2 = 112.5
        amount = await service._calculate_fine_amount(5)
        assert amount == Decimal("112.50")
        
        # 6 flags: 50 * 1.5^3 = 168.75
        amount = await service._calculate_fine_amount(6)
        assert amount == Decimal("168.75")
    
    @pytest.mark.asyncio
    async def test_calculate_fine_amount_capped(self, service):
        """Test fine amount calculation is capped at maximum"""
        # High number of flags should be capped at MAX_FINE_AMOUNT
        amount = await service._calculate_fine_amount(20)
        assert amount == service.MAX_FINE_AMOUNT
    
    @pytest.mark.asyncio
    async def test_get_unpaid_fines_count(self, service, mock_db):
        """Test getting unpaid fines count"""
        user_id = uuid4()
        
        mock_result = MagicMock()
        mock_result.scalar.return_value = 3
        
        mock_db.execute.return_value = mock_result
        
        count = await service._get_unpaid_fines_count(user_id)
        
        assert count == 3
    
    @pytest.mark.asyncio
    async def test_get_unpaid_fines_count_none(self, service, mock_db):
        """Test getting unpaid fines count when result is None"""
        user_id = uuid4()
        
        mock_result = MagicMock()
        mock_result.scalar.return_value = None
        
        mock_db.execute.return_value = mock_result
        
        count = await service._get_unpaid_fines_count(user_id)
        
        assert count == 0
    
    @pytest.mark.asyncio
    async def test_process_payment_gateway_success(self, service):
        """Test payment gateway processing success"""
        amount = Decimal("100.00")
        payment_method = "card"
        payment_reference = "txn_123"
        
        result = await service._process_payment_gateway(amount, payment_method, payment_reference)
        
        assert result is True


class TestPrankDetectionServiceIntegration:
    """Integration tests for prank detection service workflows"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session for integration tests"""
        db = AsyncMock()
        return db
    
    @pytest.fixture
    def service(self, mock_db):
        """Prank detection service instance"""
        return PrankDetectionService(mock_db)
    
    @pytest.mark.asyncio
    async def test_full_prank_detection_workflow(self, service, mock_db):
        """Test complete prank detection and fining workflow"""
        user_id = uuid4()
        
        # Create user with increasing prank flags
        user = RegisteredUser(
            id=user_id,
            email="test@example.com",
            phone="+1234567890",
            first_name="John",
            last_name="Doe",
            prank_flags=3,  # At fining threshold
            total_fines=Decimal("0.00"),
            is_suspended=False
        )
        
        # Mock database operations for tracking
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = user
        
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1  # Recent pranks
        
        # Mock fine creation
        mock_fine_result = MagicMock()
        mock_fine_result.scalar_one_or_none.return_value = None  # No existing fine
        
        mock_db.execute.side_effect = [
            mock_user_result,  # Track prank accumulation - get user
            mock_count_result,  # Track prank accumulation - count recent pranks
            mock_user_result,  # Calculate fine - get user
            mock_fine_result   # Calculate fine - check existing fine
        ]
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # 1. Track prank accumulation
        tracking_info = await service.track_prank_accumulation(user_id)
        
        assert tracking_info["total_prank_flags"] == 3
        assert tracking_info["calculated_fine_amount"] == 50.0
        assert tracking_info["should_suspend"] is False
        assert tracking_info["should_ban"] is False
        
        # 2. Calculate automatic fine
        fine = await service.calculate_automatic_fine(user_id)
        
        assert fine is not None
        assert fine.amount == Decimal("50.00")
        assert fine.user_id == user_id
        assert not fine.is_paid
        
        # Verify user's total fines were updated
        assert user.total_fines == Decimal("50.00")
    
    @pytest.mark.asyncio
    async def test_escalation_to_suspension_workflow(self, service, mock_db):
        """Test escalation from fining to suspension"""
        user_id = uuid4()
        
        # User with enough flags for suspension
        user = RegisteredUser(
            id=user_id,
            email="test@example.com",
            phone="+1234567890",
            first_name="John",
            last_name="Doe",
            prank_flags=5,  # At suspension threshold
            total_fines=Decimal("200.00"),
            is_suspended=False
        )
        
        # Mock tracking
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = user
        
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 3
        
        # Mock suspension check
        mock_unpaid_count_result = MagicMock()
        mock_unpaid_count_result.scalar.return_value = 2  # Has unpaid fines
        
        mock_db.execute.side_effect = [
            mock_user_result,      # Track accumulation - get user
            mock_count_result,     # Track accumulation - count recent
            mock_user_result,      # Suspend account - get user
            mock_unpaid_count_result  # Suspend account - count unpaid fines
        ]
        mock_db.commit = AsyncMock()
        
        # 1. Track accumulation (should indicate suspension needed)
        tracking_info = await service.track_prank_accumulation(user_id)
        
        assert tracking_info["should_suspend"] is True
        assert tracking_info["calculated_fine_amount"] == 112.5  # 50 * 1.5^2
        
        # 2. Suspend account for unpaid fines
        suspended = await service.suspend_account_for_unpaid_fines(user_id)
        
        assert suspended is True
        assert user.is_suspended is True
    
    @pytest.mark.asyncio
    async def test_escalation_to_permanent_ban_workflow(self, service, mock_db):
        """Test escalation to permanent ban"""
        user_id = uuid4()
        
        # User with enough flags for permanent ban
        user = RegisteredUser(
            id=user_id,
            email="test@example.com",
            phone="+1234567890",
            first_name="John",
            last_name="Doe",
            prank_flags=10,  # At ban threshold
            total_fines=Decimal("500.00"),
            is_suspended=False
        )
        
        # Mock tracking
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = user
        
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 5
        
        mock_db.execute.side_effect = [
            mock_user_result,  # Track accumulation - get user
            mock_count_result, # Track accumulation - count recent
            mock_user_result,  # Create ban - get user
            AsyncMock()        # Create ban - update subscriptions
        ]
        mock_db.commit = AsyncMock()
        
        # 1. Track accumulation (should indicate ban needed)
        tracking_info = await service.track_prank_accumulation(user_id)
        
        assert tracking_info["should_ban"] is True
        assert tracking_info["days_until_ban"] == 0
        
        # 2. Create permanent ban
        banned = await service.create_permanent_ban(user_id)
        
        assert banned is True
        assert user.is_suspended is True  # Permanent ban implemented as suspension
    
    @pytest.mark.asyncio
    async def test_fine_payment_and_unsuspension_workflow(self, service, mock_db):
        """Test fine payment and account unsuspension workflow"""
        user_id = uuid4()
        fine_id = uuid4()
        
        # Suspended user with unpaid fine
        user = RegisteredUser(
            id=user_id,
            email="test@example.com",
            phone="+1234567890",
            first_name="John",
            last_name="Doe",
            prank_flags=4,
            total_fines=Decimal("75.00"),
            is_suspended=True
        )
        
        fine = UserFine(
            id=fine_id,
            user_id=user_id,
            amount=Decimal("75.00"),
            reason="Automatic fine for prank behavior",
            is_paid=False
        )
        fine.user = user
        
        # Mock fine lookup
        mock_fine_result = MagicMock()
        mock_fine_result.scalar_one_or_none.return_value = fine
        
        # Mock unpaid fines count (this is the last one)
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1
        
        mock_db.execute.side_effect = [mock_fine_result, mock_count_result]
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        with patch.object(service, '_process_payment_gateway') as mock_payment:
            mock_payment.return_value = True
            
            # Process payment
            paid_fine = await service.process_fine_payment(fine_id, "card", "txn_123")
            
            assert paid_fine.is_paid is True
            assert paid_fine.paid_at is not None
            assert user.is_suspended is False  # Should be unsuspended
            
            mock_payment.assert_called_once()
            mock_db.commit.assert_called_once()


class TestPrankDetectionErrors:
    """Test prank detection error classes"""
    
    def test_prank_detection_error(self):
        """Test base PrankDetectionError"""
        error = PrankDetectionError("TEST_001", "Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, APIError)
    
    def test_user_not_found_error(self):
        """Test UserNotFoundError"""
        error = UserNotFoundError("User does not exist")
        assert str(error) == "User does not exist"
        assert isinstance(error, PrankDetectionError)
    
    def test_user_not_found_error_default_message(self):
        """Test UserNotFoundError with default message"""
        error = UserNotFoundError()
        assert "User not found" in str(error)
    
    def test_fine_not_found_error(self):
        """Test FineNotFoundError"""
        error = FineNotFoundError("Fine does not exist")
        assert str(error) == "Fine does not exist"
        assert isinstance(error, PrankDetectionError)
    
    def test_fine_not_found_error_default_message(self):
        """Test FineNotFoundError with default message"""
        error = FineNotFoundError()
        assert "Fine not found" in str(error)
    
    def test_payment_processing_error(self):
        """Test PaymentProcessingError"""
        error = PaymentProcessingError("Payment gateway error")
        assert str(error) == "Payment gateway error"
        assert isinstance(error, PrankDetectionError)
    
    def test_payment_processing_error_default_message(self):
        """Test PaymentProcessingError with default message"""
        error = PaymentProcessingError()
        assert "Payment processing failed" in str(error)


class TestPrankDetectionServiceEdgeCases:
    """Test edge cases and boundary conditions"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        db = AsyncMock()
        return db
    
    @pytest.fixture
    def service(self, mock_db):
        """Prank detection service instance"""
        return PrankDetectionService(mock_db)
    
    @pytest.mark.asyncio
    async def test_fine_calculation_edge_cases(self, service):
        """Test fine calculation edge cases"""
        # Test boundary values
        assert await service._calculate_fine_amount(0) == Decimal("0.00")
        assert await service._calculate_fine_amount(1) == Decimal("0.00")
        assert await service._calculate_fine_amount(2) == Decimal("0.00")
        assert await service._calculate_fine_amount(3) == Decimal("50.00")
        
        # Test very high values (should be capped)
        high_amount = await service._calculate_fine_amount(100)
        assert high_amount == service.MAX_FINE_AMOUNT
    
    @pytest.mark.asyncio
    async def test_tracking_with_zero_recent_pranks(self, service, mock_db):
        """Test tracking when user has no recent pranks"""
        user_id = uuid4()
        
        user = RegisteredUser(
            id=user_id,
            email="test@example.com",
            phone="+1234567890",
            first_name="John",
            last_name="Doe",
            prank_flags=3,
            total_fines=Decimal("0.00"),
            is_suspended=False
        )
        
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = user
        
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0  # No recent pranks
        
        mock_db.execute.side_effect = [mock_user_result, mock_count_result]
        
        result = await service.track_prank_accumulation(user_id)
        
        assert result["recent_prank_flags"] == 0
        assert result["total_prank_flags"] == 3
    
    @pytest.mark.asyncio
    async def test_statistics_with_no_fines(self, service, mock_db):
        """Test statistics calculation with no fines"""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        
        mock_db.execute.return_value = mock_result
        
        result = await service.get_fine_statistics()
        
        assert result["total_fines"] == 0
        assert result["paid_fines"] == 0
        assert result["unpaid_fines"] == 0
        assert result["total_amount"] == 0.0
        assert result["paid_amount"] == 0.0
        assert result["unpaid_amount"] == 0.0
        assert result["payment_rate_percentage"] == 0.0