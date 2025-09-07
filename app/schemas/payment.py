"""
Payment related Pydantic schemas
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, model_validator


class CreditTierResponse(BaseModel):
    """Credit tier response schema"""
    id: UUID
    min_credits: int
    max_credits: int
    price: Decimal
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class CreditPurchaseRequest(BaseModel):
    """Credit purchase request schema"""
    firm_id: UUID = Field(..., description="Firm ID for the credit purchase")
    amount: Decimal = Field(..., gt=0, description="Amount to pay (system will calculate credits)")
    payment_method: str = Field(default="ozow", description="Payment method")


class InvoiceResponse(BaseModel):
    """Invoice response schema"""
    id: UUID
    invoice_number: str
    credits_amount: int
    total_amount: Decimal
    status: str
    payment_method: str
    ozow_payment_request_id: Optional[str] = None
    ozow_payment_url: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: datetime
    paid_at: Optional[datetime] = None
    description: Optional[str] = None
    
    class Config:
        from_attributes = True


class PaymentInitiationResponse(BaseModel):
    """Payment initiation response schema"""
    invoice: InvoiceResponse
    payment_url: str
    transaction_id: str
    expires_at: datetime
    calculated_credits: int


class PaymentWebhookRequest(BaseModel):
    """OZOW webhook request schema"""
    SiteCode: str
    TransactionId: str
    TransactionReference: str
    Amount: str
    Status: str
    StatusMessage: Optional[str] = None
    Currency: str
    IsTest: str
    RequestId: Optional[str] = None
    BankReference: Optional[str] = None
    
    # Additional fields that might be present
    Customer: Optional[str] = None
    CustomerEmail: Optional[str] = None
    CustomerPhone: Optional[str] = None


class PaymentStatusResponse(BaseModel):
    """Payment status response schema"""
    invoice_id: UUID
    status: str
    amount: Decimal
    credits: int
    paid_at: Optional[datetime] = None
    transaction_id: Optional[str] = None


class CreditBalanceResponse(BaseModel):
    """Credit balance response schema"""
    firm_id: UUID
    current_balance: int
    recent_transactions: List[dict] = []


class CreditTransactionResponse(BaseModel):
    """Credit transaction response schema"""
    id: UUID
    transaction_type: str
    amount: int
    description: str
    reference_id: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class TransactionProcessResponse(BaseModel):
    """Transaction processing response schema"""
    transaction_id: str
    status: str
    processed: bool
    message: str
    invoice_id: Optional[str] = None
    credits_added: Optional[int] = None


class PaymentRequestVerificationResponse(BaseModel):
    """Payment request verification response schema"""
    payment_request_id: str
    invoice_id: str
    invoice_number: str
    invoice_status: str
    verification_result: dict


class PaymentRequestProcessResponse(BaseModel):
    """Payment request processing response schema"""
    payment_request_id: str
    invoice_id: str
    invoice_number: str
    status: str
    processed: bool
    message: str
    credits_added: Optional[int] = None


class OzowPaymentStatusResponse(BaseModel):
    """Ozow payment status processing response schema"""
    status: str  # success, error, warning
    message: str
    transaction_id: str
    invoice_id: Optional[str] = None
    invoice_status: Optional[str] = None
    credits_added: Optional[int] = None


class OzowPaymentDataRequest(BaseModel):
    """Ozow payment data request schema"""
    TransactionId: str
    TransactionReference: str
    Amount: str
    Status: str
    CurrencyCode: str
    IsTest: str
    Hash: Optional[str] = None
    SubStatus: Optional[str] = None
    MaskedAccountNumber: Optional[str] = None
    BankName: Optional[str] = None
    SiteCode: Optional[str] = None
    StatusMessage: Optional[str] = None
    Optional1: Optional[str] = None
    Optional2: Optional[str] = None
    Optional3: Optional[str] = None
    Optional4: Optional[str] = None
    Optional5: Optional[str] = None