"""
Credit management API endpoints
"""
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user
from app.services.credit import CreditService, PaymentGatewayError, InsufficientCreditsError
from app.models.subscription import CreditTransaction


router = APIRouter()


class CardPaymentData(BaseModel):
    """Card payment data model"""
    card_number: str = Field(..., description="Credit/debit card number")
    expiry_month: int = Field(..., ge=1, le=12, description="Card expiry month")
    expiry_year: int = Field(..., ge=2024, description="Card expiry year")
    cvv: str = Field(..., min_length=3, max_length=4, description="Card CVV")
    cardholder_name: str = Field(..., description="Cardholder name")
    
    @validator('card_number')
    def validate_card_number(cls, v):
        # Remove spaces and validate
        card_number = v.replace(" ", "")
        if not card_number.isdigit():
            raise ValueError("Card number must contain only digits")
        if len(card_number) < 13 or len(card_number) > 19:
            raise ValueError("Invalid card number length")
        return card_number
    
    @validator('cvv')
    def validate_cvv(cls, v):
        if not v.isdigit():
            raise ValueError("CVV must contain only digits")
        return v


class BankTransferData(BaseModel):
    """Bank transfer payment data model"""
    account_number: str = Field(..., description="Bank account number")
    routing_number: str = Field(..., description="Bank routing number")
    account_holder_name: str = Field(..., description="Account holder name")
    
    @validator('account_number', 'routing_number')
    def validate_numbers(cls, v):
        if not v.isdigit():
            raise ValueError("Account and routing numbers must contain only digits")
        return v


class CreditPurchaseRequest(BaseModel):
    """Credit purchase request model"""
    firm_id: str = Field(..., description="Security firm ID")
    amount: int = Field(..., gt=0, description="Number of credits to purchase")
    payment_method: str = Field(..., description="Payment method: card or bank_transfer")
    card_data: CardPaymentData = Field(None, description="Card payment data")
    bank_data: BankTransferData = Field(None, description="Bank transfer data")
    
    @validator('payment_method')
    def validate_payment_method(cls, v):
        if v not in ['card', 'bank_transfer']:
            raise ValueError("Payment method must be 'card' or 'bank_transfer'")
        return v
    
    def validate_payment_data(self):
        """Validate that payment data matches payment method"""
        if self.payment_method == 'card' and not self.card_data:
            raise ValueError("Card data is required for card payments")
        if self.payment_method == 'bank_transfer' and not self.bank_data:
            raise ValueError("Bank data is required for bank transfers")


class CreditPurchaseResponse(BaseModel):
    """Credit purchase response model"""
    success: bool
    transaction_id: str
    payment_reference: str
    credits_purchased: int
    new_balance: int
    amount_paid: float


class CreditBalanceResponse(BaseModel):
    """Credit balance response model"""
    firm_id: str
    credit_balance: int


class TransactionResponse(BaseModel):
    """Transaction response model"""
    id: str
    transaction_type: str
    amount: int
    description: str
    reference_id: str = None
    created_at: str
    
    class Config:
        from_attributes = True


class TransactionHistoryResponse(BaseModel):
    """Transaction history response model"""
    transactions: List[TransactionResponse]
    total_count: int


@router.post("/purchase", response_model=CreditPurchaseResponse)
async def purchase_credits(
    request: CreditPurchaseRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Purchase credits for a security firm
    
    Allows security firms to purchase credits using credit/debit cards
    or bank transfers. Credits are used to create subscription products.
    """
    try:
        # Validate payment data
        request.validate_payment_data()
        
        # Prepare payment data
        if request.payment_method == 'card':
            payment_data = {
                "method": "card",
                **request.card_data.dict()
            }
        else:
            payment_data = {
                "method": "bank_transfer",
                **request.bank_data.dict()
            }
        
        # Process credit purchase
        credit_service = CreditService(db)
        result = await credit_service.purchase_credits(
            firm_id=request.firm_id,
            amount=request.amount,
            payment_data=payment_data
        )
        
        return CreditPurchaseResponse(**result)
        
    except PaymentGatewayError as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process credit purchase"
        )


@router.get("/balance/{firm_id}", response_model=CreditBalanceResponse)
async def get_credit_balance(
    firm_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current credit balance for a security firm
    
    Returns the current credit balance that can be used to create
    subscription products.
    """
    try:
        credit_service = CreditService(db)
        balance = await credit_service.get_credit_balance(firm_id)
        
        return CreditBalanceResponse(
            firm_id=firm_id,
            credit_balance=balance
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve credit balance"
        )


@router.get("/transactions/{firm_id}", response_model=TransactionHistoryResponse)
async def get_transaction_history(
    firm_id: str,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get transaction history for a security firm
    
    Returns a paginated list of credit transactions including purchases
    and deductions with audit information.
    """
    try:
        credit_service = CreditService(db)
        transactions = await credit_service.get_transaction_history(
            firm_id=firm_id,
            limit=limit,
            offset=offset
        )
        
        # Convert to response format
        transaction_responses = []
        for transaction in transactions:
            transaction_responses.append(TransactionResponse(
                id=str(transaction.id),
                transaction_type=transaction.transaction_type,
                amount=transaction.amount,
                description=transaction.description,
                reference_id=transaction.reference_id,
                created_at=transaction.created_at.isoformat()
            ))
        
        return TransactionHistoryResponse(
            transactions=transaction_responses,
            total_count=len(transaction_responses)
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve transaction history"
        )


@router.post("/deduct")
async def deduct_credits(
    firm_id: str,
    amount: int,
    description: str,
    reference_id: str = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Deduct credits from a security firm's balance
    
    Internal endpoint used by the system to deduct credits when
    subscription products are created. Requires admin privileges.
    """
    try:
        # TODO: Add admin authorization check
        # For now, allow any authenticated user
        
        credit_service = CreditService(db)
        result = await credit_service.deduct_credits(
            firm_id=firm_id,
            amount=amount,
            description=description,
            reference_id=reference_id
        )
        
        return result
        
    except InsufficientCreditsError as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deduct credits"
        )