"""
Comprehensive unit tests for credit service
"""
import pytest
from decimal import Decimal
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.credit import (
    CreditService,
    PaymentGatewayError,
    InsufficientCreditsError
)
from app.models.security_firm import SecurityFirm
from app.models.subscription import CreditTransaction


class TestCreditService:
    """Test credit service functionality"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        db = AsyncMock()
        return db
    
    @pytest.fixture
    def service(self, mock_db):
        """Credit service instance"""
        return CreditService(mock_db)
    
    @pytest.fixture
    def approved_firm(self):
        """Mock approved security firm"""
        firm = SecurityFirm(
            id=uuid4(),
            name="Test Security Firm",
            verification_status="approved",
            credit_balance=100
        )
        return firm
    
    @pytest.fixture
    def pending_firm(self):
        """Mock pending security firm"""
        firm = SecurityFirm(
            id=uuid4(),
            name="Pending Security Firm",
            verification_status="pending",
            credit_balance=0
        )
        return firm
    
    @pytest.fixture
    def valid_card_payment(self):
        """Valid card payment data"""
        return {
            "method": "card",
            "card_number": "4111111111111111",
            "expiry_month": "12",
            "expiry_year": "2025",
            "cvv": "123",
            "cardholder_name": "John Doe"
        }
    
    @pytest.fixture
    def valid_bank_payment(self):
        """Valid bank transfer payment data"""
        return {
            "method": "bank_transfer",
            "account_number": "1234567890",
            "routing_number": "021000021",
            "account_holder_name": "Test Security Firm"
        }
    
    @pytest.mark.asyncio
    async def test_purchase_credits_success_card(self, service, mock_db, approved_firm, valid_card_payment):
        """Test successful credit purchase with card payment"""
        firm_id = str(approved_firm.id)
        amount = 50
        
        # Mock database operations
        mock_db.get.return_value = approved_firm
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Mock successful payment processing
        with patch.object(service, '_process_payment') as mock_payment:
            mock_payment.return_value = {
                "success": True,
                "transaction_id": "card_123456789"
            }
            
            result = await service.purchase_credits(firm_id, amount, valid_card_payment)
            
            assert result["success"] is True
            assert result["credits_purchased"] == amount
            assert result["new_balance"] == 150  # 100 + 50
            assert result["amount_paid"] == 50.0
            assert "transaction_id" in result
            assert "payment_reference" in result
            
            # Verify firm balance was updated
            assert approved_firm.credit_balance == 150
            
            # Verify transaction was created
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_purchase_credits_success_bank_transfer(self, service, mock_db, approved_firm, valid_bank_payment):
        """Test successful credit purchase with bank transfer"""
        firm_id = str(approved_firm.id)
        amount = 100
        
        mock_db.get.return_value = approved_firm
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        with patch.object(service, '_process_payment') as mock_payment:
            mock_payment.return_value = {
                "success": True,
                "transaction_id": "bank_987654321"
            }
            
            result = await service.purchase_credits(firm_id, amount, valid_bank_payment)
            
            assert result["success"] is True
            assert result["credits_purchased"] == amount
            assert result["new_balance"] == 200  # 100 + 100
            assert result["payment_reference"] == "bank_987654321"
    
    @pytest.mark.asyncio
    async def test_purchase_credits_firm_not_found(self, service, mock_db, valid_card_payment):
        """Test credit purchase with non-existent firm"""
        firm_id = str(uuid4())
        amount = 50
        
        mock_db.get.return_value = None
        
        with pytest.raises(ValueError, match="Security firm not found"):
            await service.purchase_credits(firm_id, amount, valid_card_payment)
    
    @pytest.mark.asyncio
    async def test_purchase_credits_firm_not_approved(self, service, mock_db, pending_firm, valid_card_payment):
        """Test credit purchase with non-approved firm"""
        firm_id = str(pending_firm.id)
        amount = 50
        
        mock_db.get.return_value = pending_firm
        
        with pytest.raises(ValueError, match="Security firm must be approved"):
            await service.purchase_credits(firm_id, amount, valid_card_payment)
    
    @pytest.mark.asyncio
    async def test_purchase_credits_payment_failed(self, service, mock_db, approved_firm, valid_card_payment):
        """Test credit purchase with payment failure"""
        firm_id = str(approved_firm.id)
        amount = 50
        
        mock_db.get.return_value = approved_firm
        
        with patch.object(service, '_process_payment') as mock_payment:
            mock_payment.return_value = {
                "success": False,
                "error": "Card declined"
            }
            
            with pytest.raises(PaymentGatewayError, match="Payment failed: Card declined"):
                await service.purchase_credits(firm_id, amount, valid_card_payment)
    
    @pytest.mark.asyncio
    async def test_deduct_credits_success(self, service, mock_db, approved_firm):
        """Test successful credit deduction"""
        firm_id = str(approved_firm.id)
        amount = 30
        description = "Product creation - Premium Package"
        reference_id = "product_123"
        
        mock_db.get.return_value = approved_firm
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        result = await service.deduct_credits(firm_id, amount, description, reference_id)
        
        assert result["success"] is True
        assert result["credits_deducted"] == amount
        assert result["new_balance"] == 70  # 100 - 30
        assert result["description"] == description
        assert "transaction_id" in result
        
        # Verify firm balance was updated
        assert approved_firm.credit_balance == 70
        
        # Verify transaction was created
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_deduct_credits_insufficient_balance(self, service, mock_db, approved_firm):
        """Test credit deduction with insufficient balance"""
        firm_id = str(approved_firm.id)
        amount = 150  # More than available balance (100)
        description = "Expensive product"
        
        mock_db.get.return_value = approved_firm
        
        with pytest.raises(InsufficientCreditsError, match="Insufficient credits"):
            await service.deduct_credits(firm_id, amount, description)
    
    @pytest.mark.asyncio
    async def test_deduct_credits_firm_not_found(self, service, mock_db):
        """Test credit deduction with non-existent firm"""
        firm_id = str(uuid4())
        amount = 30
        description = "Test deduction"
        
        mock_db.get.return_value = None
        
        with pytest.raises(ValueError, match="Security firm not found"):
            await service.deduct_credits(firm_id, amount, description)
    
    @pytest.mark.asyncio
    async def test_get_credit_balance_success(self, service, mock_db, approved_firm):
        """Test getting credit balance"""
        firm_id = str(approved_firm.id)
        
        mock_db.get.return_value = approved_firm
        
        balance = await service.get_credit_balance(firm_id)
        
        assert balance == 100
        mock_db.get.assert_called_once_with(SecurityFirm, firm_id)
    
    @pytest.mark.asyncio
    async def test_get_credit_balance_firm_not_found(self, service, mock_db):
        """Test getting credit balance for non-existent firm"""
        firm_id = str(uuid4())
        
        mock_db.get.return_value = None
        
        with pytest.raises(ValueError, match="Security firm not found"):
            await service.get_credit_balance(firm_id)
    
    @pytest.mark.asyncio
    async def test_get_transaction_history(self, service, mock_db):
        """Test getting transaction history"""
        firm_id = str(uuid4())
        
        # Mock transactions
        transactions = [
            CreditTransaction(
                id=uuid4(),
                firm_id=firm_id,
                transaction_type="purchase",
                amount=100,
                description="Credit purchase"
            ),
            CreditTransaction(
                id=uuid4(),
                firm_id=firm_id,
                transaction_type="deduction",
                amount=-50,
                description="Product creation"
            )
        ]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = transactions
        mock_db.execute.return_value = mock_result
        
        result = await service.get_transaction_history(firm_id, limit=10, offset=0)
        
        assert len(result) == 2
        assert result[0].transaction_type == "purchase"
        assert result[1].transaction_type == "deduction"
        mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_card_payment_success(self, service, valid_card_payment):
        """Test successful card payment processing"""
        amount = Decimal("50.00")
        
        result = await service._process_card_payment(valid_card_payment, amount)
        
        assert result["success"] is True
        assert result["amount"] == 50.0
        assert result["method"] == "card"
        assert result["last_four"] == "1111"
        assert "transaction_id" in result
        assert result["transaction_id"].startswith("card_")
    
    @pytest.mark.asyncio
    async def test_process_card_payment_missing_field(self, service):
        """Test card payment with missing required field"""
        incomplete_payment = {
            "method": "card",
            "card_number": "4111111111111111",
            # Missing other required fields
        }
        amount = Decimal("50.00")
        
        result = await service._process_card_payment(incomplete_payment, amount)
        
        assert result["success"] is False
        assert "Missing required field" in result["error"]
    
    @pytest.mark.asyncio
    async def test_process_card_payment_invalid_card_number(self, service):
        """Test card payment with invalid card number"""
        invalid_payment = {
            "method": "card",
            "card_number": "123",  # Too short
            "expiry_month": "12",
            "expiry_year": "2025",
            "cvv": "123",
            "cardholder_name": "John Doe"
        }
        amount = Decimal("50.00")
        
        result = await service._process_card_payment(invalid_payment, amount)
        
        assert result["success"] is False
        assert "Invalid card number" in result["error"]
    
    @pytest.mark.asyncio
    async def test_process_card_payment_non_numeric_card(self, service):
        """Test card payment with non-numeric card number"""
        invalid_payment = {
            "method": "card",
            "card_number": "411111111111111a",  # Contains letter
            "expiry_month": "12",
            "expiry_year": "2025",
            "cvv": "123",
            "cardholder_name": "John Doe"
        }
        amount = Decimal("50.00")
        
        result = await service._process_card_payment(invalid_payment, amount)
        
        assert result["success"] is False
        assert "Card number must contain only digits" in result["error"]
    
    @pytest.mark.asyncio
    async def test_process_bank_transfer_success(self, service, valid_bank_payment):
        """Test successful bank transfer processing"""
        amount = Decimal("100.00")
        
        result = await service._process_bank_transfer(valid_bank_payment, amount)
        
        assert result["success"] is True
        assert result["amount"] == 100.0
        assert result["method"] == "bank_transfer"
        assert result["account_last_four"] == "7890"
        assert "transaction_id" in result
        assert result["transaction_id"].startswith("bank_")
    
    @pytest.mark.asyncio
    async def test_process_bank_transfer_missing_field(self, service):
        """Test bank transfer with missing required field"""
        incomplete_payment = {
            "method": "bank_transfer",
            "account_number": "1234567890",
            # Missing routing_number and account_holder_name
        }
        amount = Decimal("100.00")
        
        result = await service._process_bank_transfer(incomplete_payment, amount)
        
        assert result["success"] is False
        assert "Missing required field" in result["error"]
    
    @pytest.mark.asyncio
    async def test_process_payment_card_method(self, service, valid_card_payment):
        """Test payment processing with card method"""
        amount = Decimal("50.00")
        
        with patch.object(service, '_process_card_payment') as mock_card:
            mock_card.return_value = {"success": True, "transaction_id": "card_123"}
            
            result = await service._process_payment(valid_card_payment, amount)
            
            assert result["success"] is True
            mock_card.assert_called_once_with(valid_card_payment, amount)
    
    @pytest.mark.asyncio
    async def test_process_payment_bank_method(self, service, valid_bank_payment):
        """Test payment processing with bank transfer method"""
        amount = Decimal("100.00")
        
        with patch.object(service, '_process_bank_transfer') as mock_bank:
            mock_bank.return_value = {"success": True, "transaction_id": "bank_123"}
            
            result = await service._process_payment(valid_bank_payment, amount)
            
            assert result["success"] is True
            mock_bank.assert_called_once_with(valid_bank_payment, amount)
    
    @pytest.mark.asyncio
    async def test_process_payment_unsupported_method(self, service):
        """Test payment processing with unsupported method"""
        invalid_payment = {
            "method": "cryptocurrency",
            "wallet_address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
        }
        amount = Decimal("50.00")
        
        result = await service._process_payment(invalid_payment, amount)
        
        assert result["success"] is False
        assert "Unsupported payment method: cryptocurrency" in result["error"]
    
    @pytest.mark.asyncio
    async def test_process_payment_no_method_specified(self, service):
        """Test payment processing with no method specified (defaults to card)"""
        payment_data = {
            "card_number": "4111111111111111",
            "expiry_month": "12",
            "expiry_year": "2025",
            "cvv": "123",
            "cardholder_name": "John Doe"
        }
        amount = Decimal("50.00")
        
        with patch.object(service, '_process_card_payment') as mock_card:
            mock_card.return_value = {"success": True, "transaction_id": "card_123"}
            
            result = await service._process_payment(payment_data, amount)
            
            assert result["success"] is True
            mock_card.assert_called_once_with(payment_data, amount)


class TestCreditServiceIntegration:
    """Integration tests for credit service workflows"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session for integration tests"""
        db = AsyncMock()
        return db
    
    @pytest.fixture
    def service(self, mock_db):
        """Credit service instance"""
        return CreditService(mock_db)
    
    @pytest.fixture
    def firm_with_credits(self):
        """Mock firm with existing credits"""
        firm = SecurityFirm(
            id=uuid4(),
            name="Test Security Firm",
            verification_status="approved",
            credit_balance=200
        )
        return firm
    
    @pytest.mark.asyncio
    async def test_purchase_and_deduct_credits_workflow(self, service, mock_db, firm_with_credits):
        """Test complete workflow of purchasing and then deducting credits"""
        firm_id = str(firm_with_credits.id)
        
        # Setup mock database
        mock_db.get.return_value = firm_with_credits
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Mock successful payment
        with patch.object(service, '_process_payment') as mock_payment:
            mock_payment.return_value = {
                "success": True,
                "transaction_id": "payment_123"
            }
            
            # Purchase credits
            purchase_result = await service.purchase_credits(
                firm_id,
                100,
                {"method": "card", "card_number": "4111111111111111", "expiry_month": "12", "expiry_year": "2025", "cvv": "123", "cardholder_name": "Test"}
            )
            
            assert purchase_result["success"] is True
            assert purchase_result["new_balance"] == 300  # 200 + 100
            
            # Deduct credits
            deduct_result = await service.deduct_credits(
                firm_id,
                50,
                "Product creation",
                "product_456"
            )
            
            assert deduct_result["success"] is True
            assert deduct_result["new_balance"] == 250  # 300 - 50
            
            # Verify final balance
            final_balance = await service.get_credit_balance(firm_id)
            assert final_balance == 250
    
    @pytest.mark.asyncio
    async def test_multiple_deductions_until_insufficient(self, service, mock_db, firm_with_credits):
        """Test multiple deductions until insufficient credits"""
        firm_id = str(firm_with_credits.id)
        
        mock_db.get.return_value = firm_with_credits
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # First deduction - should succeed
        result1 = await service.deduct_credits(firm_id, 100, "First product")
        assert result1["success"] is True
        assert result1["new_balance"] == 100  # 200 - 100
        
        # Second deduction - should succeed
        result2 = await service.deduct_credits(firm_id, 80, "Second product")
        assert result2["success"] is True
        assert result2["new_balance"] == 20  # 100 - 80
        
        # Third deduction - should fail due to insufficient credits
        with pytest.raises(InsufficientCreditsError):
            await service.deduct_credits(firm_id, 50, "Third product")  # Only 20 credits left
    
    @pytest.mark.asyncio
    async def test_transaction_history_after_operations(self, service, mock_db, firm_with_credits):
        """Test transaction history reflects all operations"""
        firm_id = str(firm_with_credits.id)
        
        # Mock transaction history
        transactions = [
            CreditTransaction(
                id=uuid4(),
                firm_id=firm_id,
                transaction_type="purchase",
                amount=100,
                description="Credit purchase - 100 credits",
                reference_id="payment_123"
            ),
            CreditTransaction(
                id=uuid4(),
                firm_id=firm_id,
                transaction_type="deduction",
                amount=-50,
                description="Product creation - Premium Package",
                reference_id="product_456"
            ),
            CreditTransaction(
                id=uuid4(),
                firm_id=firm_id,
                transaction_type="deduction",
                amount=-30,
                description="Product creation - Basic Package",
                reference_id="product_789"
            )
        ]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = transactions
        mock_db.execute.return_value = mock_result
        
        history = await service.get_transaction_history(firm_id)
        
        assert len(history) == 3
        assert history[0].transaction_type == "purchase"
        assert history[0].amount == 100
        assert history[1].transaction_type == "deduction"
        assert history[1].amount == -50
        assert history[2].transaction_type == "deduction"
        assert history[2].amount == -30
        
        # Verify total credits from history
        total_credits = sum(t.amount for t in history)
        assert total_credits == 20  # 100 - 50 - 30


class TestPaymentGatewayError:
    """Test payment gateway error handling"""
    
    def test_payment_gateway_error_creation(self):
        """Test creating payment gateway error"""
        error = PaymentGatewayError("Card declined")
        assert str(error) == "Card declined"
        assert isinstance(error, Exception)
    
    def test_payment_gateway_error_inheritance(self):
        """Test payment gateway error inheritance"""
        error = PaymentGatewayError("Payment failed")
        assert isinstance(error, Exception)


class TestInsufficientCreditsError:
    """Test insufficient credits error handling"""
    
    def test_insufficient_credits_error_creation(self):
        """Test creating insufficient credits error"""
        error = InsufficientCreditsError("Not enough credits")
        assert str(error) == "Not enough credits"
        assert isinstance(error, Exception)
    
    def test_insufficient_credits_error_inheritance(self):
        """Test insufficient credits error inheritance"""
        error = InsufficientCreditsError("Insufficient balance")
        assert isinstance(error, Exception)