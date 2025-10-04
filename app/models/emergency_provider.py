"""
Emergency Provider models for ambulances, tow trucks, etc.
"""
from sqlalchemy import Column, String, Float, Boolean, DateTime, Text, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from app.core.database import Base


class EmergencyProviderType(Base):
    """Emergency provider type configuration"""
    __tablename__ = "emergency_provider_types"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Type details
    name = Column(String(100), nullable=False, unique=True)  # e.g., "Ambulance", "Fire Department"
    code = Column(String(50), nullable=False, unique=True)  # e.g., "ambulance", "fire_department"
    description = Column(Text, nullable=True)
    
    # Configuration
    is_active = Column(Boolean, nullable=False, default=True)
    requires_license = Column(Boolean, nullable=False, default=False)
    default_coverage_radius_km = Column(Float, nullable=False, default=50.0)
    
    # Display settings
    icon = Column(String(100), nullable=True)  # Icon identifier for UI
    color = Column(String(7), nullable=True)  # Hex color code for UI
    priority_level = Column(String(20), nullable=False, default="medium")  # low, medium, high, critical
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    providers = relationship("EmergencyProvider", back_populates="provider_type_ref")


class ProviderType(str, enum.Enum):
    """Emergency provider types"""
    AMBULANCE = "ambulance"
    TOW_TRUCK = "tow_truck"
    FIRE_DEPARTMENT = "fire_department"
    POLICE = "police"
    SECURITY = "security"
    MEDICAL = "medical"
    ROADSIDE_ASSISTANCE = "roadside_assistance"


class ProviderStatus(str, enum.Enum):
    """Provider availability status"""
    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"


class EmergencyProvider(Base):
    """Emergency service provider model"""
    __tablename__ = "emergency_providers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firm_id = Column(UUID(as_uuid=True), ForeignKey("security_firms.id"), nullable=False)
    
    # Provider details
    name = Column(String(255), nullable=False)
    provider_type_id = Column(UUID(as_uuid=True), ForeignKey("emergency_provider_types.id"), nullable=False)
    provider_type = Column(Enum(ProviderType), nullable=False)  # Keep for backward compatibility
    license_number = Column(String(100), nullable=True)
    contact_phone = Column(String(20), nullable=False)
    contact_email = Column(String(255), nullable=True)
    
    # Address information
    street_address = Column(String(500), nullable=True)
    city = Column(String(100), nullable=True)
    province = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True, default="South Africa")
    postal_code = Column(String(20), nullable=True)
    
    # Location information
    current_latitude = Column(Float, nullable=False)
    current_longitude = Column(Float, nullable=False)
    base_latitude = Column(Float, nullable=False)  # Home base location
    base_longitude = Column(Float, nullable=False)
    coverage_radius_km = Column(Float, nullable=False, default=50.0)
    
    # Status and availability
    status = Column(Enum(ProviderStatus), nullable=False, default=ProviderStatus.AVAILABLE)
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Additional details
    description = Column(Text, nullable=True)
    equipment_details = Column(Text, nullable=True)  # JSON string of equipment
    capacity = Column(String(100), nullable=True)  # e.g., "4 passengers", "2 stretchers"
    capabilities = Column(ARRAY(String), nullable=True)  # Array of capabilities e.g., ["trauma_care", "rescue", "first_aid"]
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_location_update = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    firm = relationship("SecurityFirm", back_populates="emergency_providers")
    provider_type_ref = relationship("EmergencyProviderType", back_populates="providers")
    assignments = relationship("ProviderAssignment", back_populates="provider")
    provider_capabilities = relationship("ProviderCapability", back_populates="provider")


class ProviderAssignment(Base):
    """Assignment of providers to emergency requests"""
    __tablename__ = "provider_assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id = Column(UUID(as_uuid=True), ForeignKey("emergency_providers.id"), nullable=False)
    request_id = Column(UUID(as_uuid=True), ForeignKey("panic_requests.id"), nullable=False)
    
    # Assignment details
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    estimated_arrival_time = Column(DateTime(timezone=True), nullable=True)
    actual_arrival_time = Column(DateTime(timezone=True), nullable=True)
    completion_time = Column(DateTime(timezone=True), nullable=True)
    
    # Distance and routing
    distance_km = Column(Float, nullable=True)
    estimated_duration_minutes = Column(Float, nullable=True)
    
    # Status tracking
    status = Column(String(50), nullable=False, default="assigned")  # assigned, en_route, arrived, completed, cancelled
    notes = Column(Text, nullable=True)
    
    # Relationships
    provider = relationship("EmergencyProvider", back_populates="assignments")
    request = relationship("PanicRequest", back_populates="provider_assignments")