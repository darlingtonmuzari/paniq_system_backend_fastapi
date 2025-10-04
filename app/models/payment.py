"""
Payment and invoice related models
"""
from sqlalchemy import Column, String, Integer, DECIMAL, Boolean, ForeignKey, Text, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class CreditTier(BaseModel):
    """Credit pricing tier model"""
    __tablename__ = "credit_tiers"
    
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    min_credits = Column(Integer, nullable=False)
    max_credits = Column(Integer, nullable=False)
    price = Column(DECIMAL(10, 2), nullable=False)
    discount_percentage = Column(DECIMAL(5, 2), nullable=True, default=0.00)
    is_active = Column(Boolean, default=True, nullable=False)
    sort_order = Column(Integer, nullable=True, default=0)
    
    def __repr__(self):
        return f"<CreditTier {self.name}: {self.min_credits}-{self.max_credits} credits: R{self.price}>"


class Invoice(BaseModel):
    """Invoice model for credit purchases"""
    __tablename__ = "invoices"
    
    firm_id = Column(UUID(as_uuid=True), ForeignKey("security_firms.id"), nullable=False)
    invoice_number = Column(String(50), unique=True, nullable=False)
    credits_amount = Column(Integer, nullable=False)
    total_amount = Column(DECIMAL(10, 2), nullable=False)
    status = Column(String(20), default="pending", nullable=False)  # pending, paid, cancelled, failed
    payment_method = Column(String(20), default="ozow", nullable=False)
    
    # OZOW specific fields
    ozow_transaction_id = Column(String(100), nullable=True)
    ozow_payment_request_id = Column(String(100), nullable=True)  # Ozow paymentRequestId
    ozow_reference = Column(String(100), nullable=True)
    ozow_payment_url = Column(Text, nullable=True)
    
    # Payment tracking
    paid_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Additional fields
    description = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Relationships
    firm = relationship("SecurityFirm")
    payment_notifications = relationship("PaymentNotification", back_populates="invoice")


class PaymentNotification(BaseModel):
    """Payment notification/webhook model"""
    __tablename__ = "payment_notifications"
    
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=True)
    provider = Column(String(20), default="ozow", nullable=False)
    transaction_id = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)
    amount = Column(DECIMAL(10, 2), nullable=False)
    reference = Column(String(100), nullable=True)
    
    # Raw notification data
    raw_data = Column(Text, nullable=True)  # JSON string of the full webhook payload
    processed = Column(Boolean, default=False, nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    invoice = relationship("Invoice", back_populates="payment_notifications")