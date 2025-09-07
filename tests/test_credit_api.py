"""
Unit tests for credit API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from datetime import datetime

from app.main import app
from app.services.credit import PaymentGatewayError, InsufficientCreditsError
from app.models.subscription import CreditTransaction


class TestCreditAPI:
    """Test cases for credit API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Test client"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_current_user(self):
        """Mock current user"""
        return {
            "id": "user-123",
            "email": "test@example.com"
        }
    
    @pytest.fixture
    def sample_transaction(self):
        """Sample credit transaction"""
        transaction = CreditTransaction(
            id="trans-123",
            firm_id="firm-123",
            transaction_type="purchase",
            amount=100,
            description="Credit purchase - 100 credits",
            reference_id="pay_123456"
        )
        transaction.created_at = datetime(2024, 1, 1, 12, 0, 0)
        return transaction
    
    @patch('app.api.v1.credits.get_current_user')
    @patch('app.api.v1.credits.get_db')
    def test_purchase_credits_success(self, mock_get_db, mock_get_current_user, client, mock_current_user):
        """Test successful credit purchase"""
        # Setup
        mock_get_current_user.return_value = mock_current_user
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        
        # Mock credit service
        with patch('app.api.v1.credits.CreditService') as mock_credit_service:
            mock_service = AsyncMock()
            mock_credit_service.return_value = mock_service
            mock_service.purchase_credits.return_value = {
                "success": True,
                "transaction_id": "trans-123",
                "payment_reference": "pay_123456",
                "credits_purchased": 100,
                "new_balance": 200,
                "amount_paid": 100.0
            }
            
            # Execute
            response = client.post("/api/v1/credits/purchase", json={
                "firm_id": "firm-123",
                "amount": 100,
                "payment_method": "card",
                "card_data": {
                    "card_number": "4111111111111111",
                    "expiry_month": 12,
                    "expiry_year": 2025,
                    "cvv": "123",
                    "cardholder_name": "John Doe"
                }
            })
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["credits_purchased"] == 100
        assert data["new_balance"] == 200
        assert data["transaction_id"] == "trans-123"
        assert data["payment_reference"] == "pay_123456"
    
    @patch('app.api.v1.credits.get_current_user')
    @patch('app.api.v1.credits.get_db')
    def test_purchase_credits_invalid_payment_method(self, mock_get_db, mock_get_current_user, client, mock_current_user):
        """Test credit purchase with invalid payment method"""
        # Setup
        mock_get_current_user.return_value = mock_current_user
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        
        # Execute
        response = client.post("/api/v1/credits/purchase", json={
            "firm_id": "firm-123",
            "amount": 100,
            "payment_method": "invalid_method",
            "card_data": {
                "card_number": "4111111111111111",
                "expiry_month": 12,
                "expiry_year": 2025,
                "cvv": "123",
                "cardholder_name": "John Doe"
            }
        })
        
        # Verify
        assert response.status_code == 422  # Validation error
    
    @patch('app.api.v1.credits.get_current_user')
    @patch('app.api.v1.credits.get_db')
    def test_purchase_credits_missing_card_data(self, mock_get_db, mock_get_current_user, client, mock_current_user):
        """Test credit purchase with missing card data"""
        # Setup
        mock_get_current_user.return_value = mock_current_user
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        
        # Execute
        response = client.post("/api/v1/credits/purchase", json={
            "firm_id": "firm-123",
            "amount": 100,
            "payment_method": "card"
            # Missing card_data
        })
        
        # Verify
        assert response.status_code == 400
        assert "Card data is required" in response.json()["detail"]
    
    @patch('app.api.v1.credits.get_current_user')
    @patch('app.api.v1.credits.get_db')
    def test_purchase_credits_payment_gateway_error(self, mock_get_db, mock_get_current_user, client, mock_current_user):
        """Test credit purchase with payment gateway error"""
        # Setup
        mock_get_current_user.return_value = mock_current_user
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        
        # Mock credit service to raise payment error
        with patch('app.api.v1.credits.CreditService') as mock_credit_service:
            mock_service = AsyncMock()
            mock_credit_service.return_value = mock_service
            mock_service.purchase_credits.side_effect = PaymentGatewayError("Card declined")
            
            # Execute
            response = client.post("/api/v1/credits/purchase", json={
                "firm_id": "firm-123",
                "amount": 100,
                "payment_method": "card",
                "card_data": {
                    "card_number": "4111111111111111",
                    "expiry_month": 12,
                    "expiry_year": 2025,
                    "cvv": "123",
                    "cardholder_name": "John Doe"
                }
            })
        
        # Verify
        assert response.status_code == 402  # Payment required
        assert "Card declined" in response.json()["detail"]
    
    @patch('app.api.v1.credits.get_current_user')
    @patch('app.api.v1.credits.get_db')
    def test_get_credit_balance_success(self, mock_get_db, mock_get_current_user, client, mock_current_user):
        """Test successful credit balance retrieval"""
        # Setup
        mock_get_current_user.return_value = mock_current_user
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        
        # Mock credit service
        with patch('app.api.v1.credits.CreditService') as mock_credit_service:
            mock_service = AsyncMock()
            mock_credit_service.return_value = mock_service
            mock_service.get_credit_balance.return_value = 150
            
            # Execute
            response = client.get("/api/v1/credits/balance/firm-123")
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["firm_id"] == "firm-123"
        assert data["credit_balance"] == 150
    
    @patch('app.api.v1.credits.get_current_user')
    @patch('app.api.v1.credits.get_db')
    def test_get_credit_balance_firm_not_found(self, mock_get_db, mock_get_current_user, client, mock_current_user):
        """Test credit balance retrieval for non-existent firm"""
        # Setup
        mock_get_current_user.return_value = mock_current_user
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        
        # Mock credit service to raise error
        with patch('app.api.v1.credits.CreditService') as mock_credit_service:
            mock_service = AsyncMock()
            mock_credit_service.return_value = mock_service
            mock_service.get_credit_balance.side_effect = ValueError("Security firm not found")
            
            # Execute
            response = client.get("/api/v1/credits/balance/nonexistent")
        
        # Verify
        assert response.status_code == 404
        assert "Security firm not found" in response.json()["detail"]
    
    @patch('app.api.v1.credits.get_current_user')
    @patch('app.api.v1.credits.get_db')
    def test_get_transaction_history_success(self, mock_get_db, mock_get_current_user, client, mock_current_user, sample_transaction):
        """Test successful transaction history retrieval"""
        # Setup
        mock_get_current_user.return_value = mock_current_user
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        
        # Mock credit service
        with patch('app.api.v1.credits.CreditService') as mock_credit_service:
            mock_service = AsyncMock()
            mock_credit_service.return_value = mock_service
            mock_service.get_transaction_history.return_value = [sample_transaction]
            
            # Execute
            response = client.get("/api/v1/credits/transactions/firm-123")
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        assert len(data["transactions"]) == 1
        assert data["transactions"][0]["id"] == "trans-123"
        assert data["transactions"][0]["transaction_type"] == "purchase"
        assert data["transactions"][0]["amount"] == 100
        assert data["total_count"] == 1
    
    @patch('app.api.v1.credits.get_current_user')
    @patch('app.api.v1.credits.get_db')
    def test_get_transaction_history_with_pagination(self, mock_get_db, mock_get_current_user, client, mock_current_user):
        """Test transaction history retrieval with pagination"""
        # Setup
        mock_get_current_user.return_value = mock_current_user
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        
        # Mock credit service
        with patch('app.api.v1.credits.CreditService') as mock_credit_service:
            mock_service = AsyncMock()
            mock_credit_service.return_value = mock_service
            mock_service.get_transaction_history.return_value = []
            
            # Execute
            response = client.get("/api/v1/credits/transactions/firm-123?limit=10&offset=20")
        
        # Verify
        assert response.status_code == 200
        mock_service.get_transaction_history.assert_called_once_with(
            firm_id="firm-123",
            limit=10,
            offset=20
        )
    
    @patch('app.api.v1.credits.get_current_user')
    @patch('app.api.v1.credits.get_db')
    def test_deduct_credits_success(self, mock_get_db, mock_get_current_user, client, mock_current_user):
        """Test successful credit deduction"""
        # Setup
        mock_get_current_user.return_value = mock_current_user
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        
        # Mock credit service
        with patch('app.api.v1.credits.CreditService') as mock_credit_service:
            mock_service = AsyncMock()
            mock_credit_service.return_value = mock_service
            mock_service.deduct_credits.return_value = {
                "success": True,
                "transaction_id": "trans-456",
                "credits_deducted": 50,
                "new_balance": 100,
                "description": "Product creation"
            }
            
            # Execute
            response = client.post("/api/v1/credits/deduct", params={
                "firm_id": "firm-123",
                "amount": 50,
                "description": "Product creation",
                "reference_id": "product-456"
            })
        
        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["credits_deducted"] == 50
        assert data["new_balance"] == 100
    
    @patch('app.api.v1.credits.get_current_user')
    @patch('app.api.v1.credits.get_db')
    def test_deduct_credits_insufficient_balance(self, mock_get_db, mock_get_current_user, client, mock_current_user):
        """Test credit deduction with insufficient balance"""
        # Setup
        mock_get_current_user.return_value = mock_current_user
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        
        # Mock credit service to raise insufficient credits error
        with patch('app.api.v1.credits.CreditService') as mock_credit_service:
            mock_service = AsyncMock()
            mock_credit_service.return_value = mock_service
            mock_service.deduct_credits.side_effect = InsufficientCreditsError("Insufficient credits")
            
            # Execute
            response = client.post("/api/v1/credits/deduct", params={
                "firm_id": "firm-123",
                "amount": 200,
                "description": "Product creation"
            })
        
        # Verify
        assert response.status_code == 402  # Payment required
        assert "Insufficient credits" in response.json()["detail"]
    
    def test_card_payment_data_validation(self):
        """Test card payment data validation"""
        from app.api.v1.credits import CardPaymentData
        
        # Valid card data
        valid_data = {
            "card_number": "4111 1111 1111 1111",
            "expiry_month": 12,
            "expiry_year": 2025,
            "cvv": "123",
            "cardholder_name": "John Doe"
        }
        card_data = CardPaymentData(**valid_data)
        assert card_data.card_number == "4111111111111111"  # Spaces removed
        
        # Invalid card number
        with pytest.raises(ValueError, match="Card number must contain only digits"):
            CardPaymentData(
                card_number="4111-1111-1111-1111",  # Contains dashes
                expiry_month=12,
                expiry_year=2025,
                cvv="123",
                cardholder_name="John Doe"
            )
        
        # Invalid CVV
        with pytest.raises(ValueError, match="CVV must contain only digits"):
            CardPaymentData(
                card_number="4111111111111111",
                expiry_month=12,
                expiry_year=2025,
                cvv="12a",  # Contains letter
                cardholder_name="John Doe"
            )
    
    def test_bank_transfer_data_validation(self):
        """Test bank transfer data validation"""
        from app.api.v1.credits import BankTransferData
        
        # Valid bank data
        valid_data = {
            "account_number": "1234567890",
            "routing_number": "021000021",
            "account_holder_name": "John Doe"
        }
        bank_data = BankTransferData(**valid_data)
        assert bank_data.account_number == "1234567890"
        
        # Invalid account number
        with pytest.raises(ValueError, match="Account and routing numbers must contain only digits"):
            BankTransferData(
                account_number="123-456-7890",  # Contains dashes
                routing_number="021000021",
                account_holder_name="John Doe"
            )
    
    def test_credit_purchase_request_validation(self):
        """Test credit purchase request validation"""
        from app.api.v1.credits import CreditPurchaseRequest, CardPaymentData
        
        # Valid request with card data
        card_data = CardPaymentData(
            card_number="4111111111111111",
            expiry_month=12,
            expiry_year=2025,
            cvv="123",
            cardholder_name="John Doe"
        )
        
        request = CreditPurchaseRequest(
            firm_id="firm-123",
            amount=100,
            payment_method="card",
            card_data=card_data
        )
        
        # Should not raise exception
        request.validate_payment_data()
        
        # Invalid request - card method without card data
        request_invalid = CreditPurchaseRequest(
            firm_id="firm-123",
            amount=100,
            payment_method="card"
            # Missing card_data
        )
        
        with pytest.raises(ValueError, match="Card data is required for card payments"):
            request_invalid.validate_payment_data()