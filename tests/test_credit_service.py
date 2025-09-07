"""
Unit tests for credit service
"""
import pytest
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, patch

from app.services.credit import CreditService, PaymentGatewayError, InsufficientCreditsError
from app.models.security_firm import SecurityFirm
from app.models.subscription import CreditTransaction


class TestCreditService:
    """Test cases for CreditService"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def credit_service(self, mock_db):
        """Credit service instance with mocked database"""
        return CreditService(mock_db)
    
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
            credit_balance=100
        )
    
    @pytest.mark.asyncio
    async def test_purchase_credits_success(self, credit_service, mock_db, sample_firm):
        """Test successful credit purchase"""
        # Setup
        mock_db.get.return_value = sample_firm
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.add = AsyncMock()
        
        payment_data = {
            "method": "card",
            "card_number": "4111111111111111",
            "expiry_month": 12,
            "expiry_year": 2025,
            "cvv": "123",
            "cardholder_name": "John Doe"
        }
        
        # Mock payment processing
        with patch.object(credit_service, '_process_payment') as mock_payment:
            mock_payment.return_value = {
                "success": True,
                "transaction_id": "pay_123456"
            }
            
            # Execute
            result = await credit_service.purchase_credits(
                firm_id="firm-123",
                amount=50,
                payment_data=payment_data
            )
        
        # Verify
        assert result["success"] is True
        assert result["credits_purchased"] == 50
        assert result["new_balance"] == 150  # 100 + 50
        assert "transaction_id" in result
        assert "payment_reference" in result
        
        # Verify database operations
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        assert sample_firm.credit_balance == 150
    
    @pytest.mark.asyncio
    async def test_purchase_credits_firm_not_found(self, credit_service, mock_db):
        """Test credit purchase with non-existent firm"""
        # Setup
        mock_db.get.return_value = None
        
        payment_data = {"method": "card"}
        
        # Execute & Verify
        with pytest.raises(ValueError, match="Security firm not found"):
            await credit_service.purchase_credits(
                firm_id="nonexistent",
                amount=50,
                payment_data=payment_data
            )
    
    @pytest.mark.asyncio
    async def test_purchase_credits_firm_not_approved(self, credit_service, mock_db, sample_firm):
        """Test credit purchase with unapproved firm"""
        # Setup
        sample_firm.verification_status = "pending"
        mock_db.get.return_value = sample_firm
        
        payment_data = {"method": "card"}
        
        # Execute & Verify
        with pytest.raises(ValueError, match="Security firm must be approved"):
            await credit_service.purchase_credits(
                firm_id="firm-123",
                amount=50,
                payment_data=payment_data
            )
    
    @pytest.mark.asyncio
    async def test_purchase_credits_payment_failure(self, credit_service, mock_db, sample_firm):
        """Test credit purchase with payment failure"""
        # Setup
        mock_db.get.return_value = sample_firm
        
        payment_data = {"method": "card"}
        
        # Mock payment processing failure
        with patch.object(credit_service, '_process_payment') as mock_payment:
            mock_payment.return_value = {
                "success": False,
                "error": "Card declined"
            }
            
            # Execute & Verify
            with pytest.raises(PaymentGatewayError, match="Payment failed: Card declined"):
                await credit_service.purchase_credits(
                    firm_id="firm-123",
                    amount=50,
                    payment_data=payment_data
                )
    
    @pytest.mark.asyncio
    async def test_deduct_credits_success(self, credit_service, mock_db, sample_firm):
        """Test successful credit deduction"""
        # Setup
        mock_db.get.return_value = sample_firm
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.add = AsyncMock()
        
        # Execute
        result = await credit_service.deduct_credits(
            firm_id="firm-123",
            amount=30,
            description="Product creation",
            reference_id="product-456"
        )
        
        # Verify
        assert result["success"] is True
        assert result["credits_deducted"] == 30
        assert result["new_balance"] == 70  # 100 - 30
        assert result["description"] == "Product creation"
        
        # Verify database operations
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        assert sample_firm.credit_balance == 70
    
    @pytest.mark.asyncio
    async def test_deduct_credits_insufficient_balance(self, credit_service, mock_db, sample_firm):
        """Test credit deduction with insufficient balance"""
        # Setup
        sample_firm.credit_balance = 20
        mock_db.get.return_value = sample_firm
        
        # Execute & Verify
        with pytest.raises(InsufficientCreditsError, match="Insufficient credits"):
            await credit_service.deduct_credits(
                firm_id="firm-123",
                amount=50,
                description="Product creation"
            )
    
    @pytest.mark.asyncio
    async def test_get_credit_balance_success(self, credit_service, mock_db, sample_firm):
        """Test getting credit balance"""
        # Setup
        mock_db.get.return_value = sample_firm
        
        # Execute
        balance = await credit_service.get_credit_balance("firm-123")
        
        # Verify
        assert balance == 100
    
    @pytest.mark.asyncio
    async def test_get_credit_balance_firm_not_found(self, credit_service, mock_db):
        """Test getting credit balance for non-existent firm"""
        # Setup
        mock_db.get.return_value = None
        
        # Execute & Verify
        with pytest.raises(ValueError, match="Security firm not found"):
            await credit_service.get_credit_balance("nonexistent")
    
    @pytest.mark.asyncio
    async def test_get_transaction_history(self, credit_service, mock_db):
        """Test getting transaction history"""
        # Setup
        mock_transactions = [
            CreditTransaction(
                id="trans-1",
                firm_id="firm-123",
                transaction_type="purchase",
                amount=100,
                description="Credit purchase",
                reference_id="pay_123"
            ),
            CreditTransaction(
                id="trans-2",
                firm_id="firm-123",
                transaction_type="deduction",
                amount=-50,
                description="Product creation",
                reference_id="product-456"
            )
        ]
        
        # Create a proper mock for the SQLAlchemy result
        mock_scalars = type('MockScalars', (), {'all': lambda self: mock_transactions})()
        mock_result = type('MockResult', (), {'scalars': lambda self: mock_scalars})()
        mock_db.execute.return_value = mock_result
        
        # Execute
        transactions = await credit_service.get_transaction_history("firm-123")
        
        # Verify
        assert len(transactions) == 2
        assert transactions[0].transaction_type == "purchase"
        assert transactions[1].transaction_type == "deduction"
    
    @pytest.mark.asyncio
    async def test_process_card_payment_success(self, credit_service):
        """Test successful card payment processing"""
        # Setup
        payment_data = {
            "card_number": "4111111111111111",
            "expiry_month": 12,
            "expiry_year": 2025,
            "cvv": "123",
            "cardholder_name": "John Doe"
        }
        
        # Execute
        result = await credit_service._process_card_payment(payment_data, Decimal("100.00"))
        
        # Verify
        assert result["success"] is True
        assert result["amount"] == 100.0
        assert result["method"] == "card"
        assert result["last_four"] == "1111"
        assert "transaction_id" in result
    
    @pytest.mark.asyncio
    async def test_process_card_payment_missing_fields(self, credit_service):
        """Test card payment with missing required fields"""
        # Setup
        payment_data = {
            "card_number": "4111111111111111"
            # Missing other required fields
        }
        
        # Execute
        result = await credit_service._process_card_payment(payment_data, Decimal("100.00"))
        
        # Verify
        assert result["success"] is False
        assert "Missing required field" in result["error"]
    
    @pytest.mark.asyncio
    async def test_process_card_payment_invalid_card_number(self, credit_service):
        """Test card payment with invalid card number"""
        # Setup
        payment_data = {
            "card_number": "123",  # Too short
            "expiry_month": 12,
            "expiry_year": 2025,
            "cvv": "123",
            "cardholder_name": "John Doe"
        }
        
        # Execute
        result = await credit_service._process_card_payment(payment_data, Decimal("100.00"))
        
        # Verify
        assert result["success"] is False
        assert "Invalid card number" in result["error"]
    
    @pytest.mark.asyncio
    async def test_process_bank_transfer_success(self, credit_service):
        """Test successful bank transfer processing"""
        # Setup
        payment_data = {
            "account_number": "1234567890",
            "routing_number": "021000021",
            "account_holder_name": "John Doe"
        }
        
        # Execute
        result = await credit_service._process_bank_transfer(payment_data, Decimal("100.00"))
        
        # Verify
        assert result["success"] is True
        assert result["amount"] == 100.0
        assert result["method"] == "bank_transfer"
        assert result["account_last_four"] == "7890"
        assert "transaction_id" in result
    
    @pytest.mark.asyncio
    async def test_process_bank_transfer_missing_fields(self, credit_service):
        """Test bank transfer with missing required fields"""
        # Setup
        payment_data = {
            "account_number": "1234567890"
            # Missing other required fields
        }
        
        # Execute
        result = await credit_service._process_bank_transfer(payment_data, Decimal("100.00"))
        
        # Verify
        assert result["success"] is False
        assert "Missing required field" in result["error"]