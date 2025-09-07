"""
Subscription and product related models
"""
from sqlalchemy import Column, String, Integer, DECIMAL, Boolean, ForeignKey, Text, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class SubscriptionProduct(BaseModel):
    """Subscription product model"""
    __tablename__ = "subscription_products"
    
    firm_id = Column(UUID(as_uuid=True), ForeignKey("security_firms.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    max_users = Column(Integer, nullable=False)
    price = Column(DECIMAL(10, 2), nullable=False)
    credit_cost = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    firm = relationship("SecurityFirm", back_populates="subscription_products")
    stored_subscriptions = relationship("StoredSubscription", back_populates="product")


class StoredSubscription(BaseModel):
    """Stored subscription model"""
    __tablename__ = "stored_subscriptions"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("registered_users.id"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("subscription_products.id"), nullable=False)
    is_applied = Column(Boolean, default=False, nullable=False)
    applied_to_group_id = Column(UUID(as_uuid=True), ForeignKey("user_groups.id"), nullable=True)
    purchased_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    applied_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("RegisteredUser", back_populates="stored_subscriptions")
    product = relationship("SubscriptionProduct", back_populates="stored_subscriptions")
    applied_group = relationship("UserGroup", foreign_keys=[applied_to_group_id])


class CreditTransaction(BaseModel):
    """Credit transaction model"""
    __tablename__ = "credit_transactions"
    
    firm_id = Column(UUID(as_uuid=True), ForeignKey("security_firms.id"), nullable=False)
    transaction_type = Column(String(20), nullable=False)  # purchase, deduction
    amount = Column(Integer, nullable=False)
    description = Column(Text, nullable=False)
    reference_id = Column(String(255), nullable=True)  # Payment reference or product ID
    
    # Relationships
    firm = relationship("SecurityFirm")