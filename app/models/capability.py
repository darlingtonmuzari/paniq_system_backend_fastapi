"""
Capability models for emergency providers
"""
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from app.core.database import Base


class ProficiencyLevel(str, enum.Enum):
    """Proficiency levels for capabilities"""
    BASIC = "basic"
    STANDARD = "standard" 
    ADVANCED = "advanced"
    EXPERT = "expert"


class CapabilityCategory(Base):
    """Category classification for capabilities"""
    __tablename__ = "capability_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Category details
    name = Column(String(100), nullable=False, unique=True)
    code = Column(String(50), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)  # icon name for UI
    color = Column(String(7), nullable=True)  # hex color code
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    capabilities = relationship("Capability", back_populates="capability_category")


class Capability(Base):
    """Capability that emergency providers can have"""
    __tablename__ = "capabilities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Capability details
    name = Column(String(100), nullable=False, unique=True)
    code = Column(String(50), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("capability_categories.id"), nullable=False)
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    capability_category = relationship("CapabilityCategory", back_populates="capabilities")
    provider_capabilities = relationship("ProviderCapability", back_populates="capability")


class ProviderCapability(Base):
    """Junction table linking providers to their capabilities"""
    __tablename__ = "provider_capabilities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id = Column(UUID(as_uuid=True), ForeignKey("emergency_providers.id", ondelete="CASCADE"), nullable=False)
    capability_id = Column(UUID(as_uuid=True), ForeignKey("capabilities.id", ondelete="CASCADE"), nullable=False)
    
    # Additional attributes for the relationship
    proficiency_level = Column(Enum(ProficiencyLevel), nullable=False, default=ProficiencyLevel.STANDARD)
    certification_level = Column(String(50), nullable=True)  # certified, licensed, accredited, etc.
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    provider = relationship("EmergencyProvider", back_populates="provider_capabilities")
    capability = relationship("Capability", back_populates="provider_capabilities")
    
    # Unique constraint to prevent duplicate capability assignments
    __table_args__ = (
        {"extend_existing": True}
    )