"""
Credit management service for security firms
"""
from typing import List, Optional, Dict, Any
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from sqlalchemy.orm import selectinload

from app.models.security_firm import SecurityFirm
from app.models.subscription import CreditTransaction


class PaymentGatewayError(Exception):
    """Payment gateway related errors"""
    pass


class InsufficientCreditsError(Exception):
    """Insufficient credits error"""
    pass


class CreditService:
    """Service for managing credit operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def purchase_credits(
        self,
        firm_id: str,
        amount: int,
        payment_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Purchase credits for a security firm
        
        Args:
            firm_id: Security firm ID
            amount: Number of credits to purchase
            payment_data: Payment information including method, card details, etc.
            
        Returns:
            Transaction result with payment reference and updated balance
        """
        # Verify firm exists and is approved
        firm = await self.db.get(SecurityFirm, firm_id)
        if not firm:
            raise ValueError("Security firm not found")
        
        if firm.verification_status != "approved":
            raise ValueError("Security firm must be approved to purchase credits")
        
        # Calculate total cost (assuming $1 per credit for now)
        total_cost = Decimal(str(amount))
        
        # Process payment through gateway
        payment_result = await self._process_payment(payment_data, total_cost)
        
        if not payment_result["success"]:
            raise PaymentGatewayError(f"Payment failed: {payment_result['error']}")
        
        # Add credits to firm balance
        firm.credit_balance += amount
        
        # Create transaction record
        transaction = CreditTransaction(
            firm_id=firm_id,
            transaction_type="purchase",
            amount=amount,
            description=f"Credit purchase - {amount} credits",
            reference_id=payment_result["transaction_id"]
        )
        
        self.db.add(transaction)
        await self.db.commit()
        await self.db.refresh(firm)
        await self.db.refresh(transaction)
        
        return {
            "success": True,
            "transaction_id": str(transaction.id),
            "payment_reference": payment_result["transaction_id"],
            "credits_purchased": amount,
            "new_balance": firm.credit_balance,
            "amount_paid": float(total_cost)
        }
    
    async def deduct_credits(
        self,
        firm_id: str,
        amount: int,
        description: str,
        reference_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Deduct credits from a security firm's balance
        
        Args:
            firm_id: Security firm ID
            amount: Number of credits to deduct
            description: Description of the deduction
            reference_id: Optional reference ID (e.g., product ID)
            
        Returns:
            Transaction result with updated balance
        """
        # Verify firm exists
        firm = await self.db.get(SecurityFirm, firm_id)
        if not firm:
            raise ValueError("Security firm not found")
        
        # Check if firm has sufficient credits
        if firm.credit_balance < amount:
            raise InsufficientCreditsError(
                f"Insufficient credits. Current balance: {firm.credit_balance}, Required: {amount}"
            )
        
        # Deduct credits
        firm.credit_balance -= amount
        
        # Create transaction record
        transaction = CreditTransaction(
            firm_id=firm_id,
            transaction_type="deduction",
            amount=-amount,  # Negative for deduction
            description=description,
            reference_id=reference_id
        )
        
        self.db.add(transaction)
        await self.db.commit()
        await self.db.refresh(firm)
        await self.db.refresh(transaction)
        
        return {
            "success": True,
            "transaction_id": str(transaction.id),
            "credits_deducted": amount,
            "new_balance": firm.credit_balance,
            "description": description
        }
    
    async def get_credit_balance(self, firm_id: str) -> int:
        """
        Get current credit balance for a security firm
        
        Args:
            firm_id: Security firm ID
            
        Returns:
            Current credit balance
        """
        firm = await self.db.get(SecurityFirm, firm_id)
        if not firm:
            raise ValueError("Security firm not found")
        
        return firm.credit_balance
    
    async def get_transaction_history(
        self,
        firm_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[CreditTransaction]:
        """
        Get transaction history for a security firm
        
        Args:
            firm_id: Security firm ID
            limit: Maximum number of transactions to return
            offset: Number of transactions to skip
            
        Returns:
            List of credit transactions
        """
        result = await self.db.execute(
            select(CreditTransaction)
            .where(CreditTransaction.firm_id == firm_id)
            .order_by(desc(CreditTransaction.created_at))
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()
    
    async def _process_payment(
        self,
        payment_data: Dict[str, Any],
        amount: Decimal
    ) -> Dict[str, Any]:
        """
        Process payment through payment gateway
        
        This is a mock implementation. In production, this would integrate
        with actual payment gateways like Stripe, PayPal, etc.
        
        Args:
            payment_data: Payment information
            amount: Amount to charge
            
        Returns:
            Payment result
        """
        payment_method = payment_data.get("method", "card")
        
        # Mock payment processing
        if payment_method == "card":
            return await self._process_card_payment(payment_data, amount)
        elif payment_method == "bank_transfer":
            return await self._process_bank_transfer(payment_data, amount)
        else:
            return {
                "success": False,
                "error": f"Unsupported payment method: {payment_method}"
            }
    
    async def _process_card_payment(
        self,
        payment_data: Dict[str, Any],
        amount: Decimal
    ) -> Dict[str, Any]:
        """
        Process credit/debit card payment
        
        Mock implementation for card payment processing
        """
        # Validate required fields
        required_fields = ["card_number", "expiry_month", "expiry_year", "cvv", "cardholder_name"]
        for field in required_fields:
            if field not in payment_data:
                return {
                    "success": False,
                    "error": f"Missing required field: {field}"
                }
        
        # Mock validation - in production, use actual payment gateway
        card_number = payment_data["card_number"].replace(" ", "")
        
        # Simple validation for demo purposes
        if len(card_number) < 13 or len(card_number) > 19:
            return {
                "success": False,
                "error": "Invalid card number"
            }
        
        if not card_number.isdigit():
            return {
                "success": False,
                "error": "Card number must contain only digits"
            }
        
        # Mock successful payment
        import uuid
        return {
            "success": True,
            "transaction_id": f"card_{uuid.uuid4().hex[:12]}",
            "amount": float(amount),
            "method": "card",
            "last_four": card_number[-4:]
        }
    
    async def _process_bank_transfer(
        self,
        payment_data: Dict[str, Any],
        amount: Decimal
    ) -> Dict[str, Any]:
        """
        Process bank transfer payment
        
        Mock implementation for bank transfer processing
        """
        # Validate required fields
        required_fields = ["account_number", "routing_number", "account_holder_name"]
        for field in required_fields:
            if field not in payment_data:
                return {
                    "success": False,
                    "error": f"Missing required field: {field}"
                }
        
        # Mock successful bank transfer
        import uuid
        return {
            "success": True,
            "transaction_id": f"bank_{uuid.uuid4().hex[:12]}",
            "amount": float(amount),
            "method": "bank_transfer",
            "account_last_four": payment_data["account_number"][-4:]
        }