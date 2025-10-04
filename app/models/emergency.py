"""
Emergency request and service provider models
"""
from sqlalchemy import Column, String, ForeignKey, Text, DateTime, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from app.models.base import BaseModel


class PanicRequest(BaseModel):
    """Panic request model"""
    __tablename__ = "panic_requests"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("registered_users.id"), nullable=False)
    group_id = Column(UUID(as_uuid=True), ForeignKey("user_groups.id"), nullable=False)
    requester_phone = Column(String(20), nullable=False)
    service_type = Column(String(20), nullable=False)  # call, security, ambulance, fire, towing
    location = Column(Geometry("POINT", srid=4326), nullable=False)
    address = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default="pending", nullable=False)
    assigned_team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True)
    assigned_service_provider_id = Column(UUID(as_uuid=True), ForeignKey("service_providers.id"), nullable=True)
    
    # Timestamps for metrics
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    arrived_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("RegisteredUser")
    group = relationship("UserGroup", back_populates="panic_requests")
    assigned_team = relationship("Team")
    assigned_service_provider = relationship("ServiceProvider")
    feedback = relationship("RequestFeedback", back_populates="request", cascade="all, delete-orphan")
    status_updates = relationship("RequestStatusUpdate", back_populates="request", cascade="all, delete-orphan")
    provider_assignments = relationship("ProviderAssignment", back_populates="request", cascade="all, delete-orphan")
    location_logs = relationship("LocationLog", cascade="all, delete-orphan")


class ServiceProvider(BaseModel):
    """External service provider model"""
    __tablename__ = "service_providers"
    
    firm_id = Column(UUID(as_uuid=True), ForeignKey("security_firms.id"), nullable=False)
    name = Column(String(255), nullable=False)
    service_type = Column(String(20), nullable=False)  # ambulance, fire, towing
    email = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)
    address = Column(Text, nullable=False)
    location = Column(Geometry("POINT", srid=4326), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    firm = relationship("SecurityFirm")
    assigned_requests = relationship("PanicRequest", back_populates="assigned_service_provider")


class RequestFeedback(BaseModel):
    """Request feedback model"""
    __tablename__ = "request_feedback"
    
    request_id = Column(UUID(as_uuid=True), ForeignKey("panic_requests.id"), nullable=False)
    team_member_id = Column(UUID(as_uuid=True), ForeignKey("firm_personnel.id"), nullable=True)
    is_prank = Column(Boolean, default=False, nullable=False)
    performance_rating = Column(Integer, nullable=True)  # 1-5 rating
    comments = Column(Text, nullable=True)
    
    # Relationships
    request = relationship("PanicRequest", back_populates="feedback")
    team_member = relationship("FirmPersonnel")


class RequestStatusUpdate(BaseModel):
    """Request status update model for real-time tracking"""
    __tablename__ = "request_status_updates"
    
    request_id = Column(UUID(as_uuid=True), ForeignKey("panic_requests.id"), nullable=False)
    status = Column(String(20), nullable=False)
    message = Column(Text, nullable=True)
    location = Column(Geometry("POINT", srid=4326), nullable=True)
    updated_by_id = Column(UUID(as_uuid=True), ForeignKey("firm_personnel.id"), nullable=True)
    
    # Relationships
    request = relationship("PanicRequest", back_populates="status_updates")
    updated_by = relationship("FirmPersonnel")


class LocationLog(BaseModel):
    """Location log model for tracking user location changes during panic requests"""
    __tablename__ = "location_logs"
    
    request_id = Column(UUID(as_uuid=True), ForeignKey("panic_requests.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("registered_users.id"), nullable=False)
    location = Column(Geometry("POINT", srid=4326), nullable=False)
    address = Column(Text, nullable=True)
    accuracy = Column(Integer, nullable=True)  # GPS accuracy in meters
    source = Column(String(20), default="mobile", nullable=False)  # mobile, web, manual
    
    # Relationships
    request = relationship("PanicRequest")
    user = relationship("RegisteredUser")