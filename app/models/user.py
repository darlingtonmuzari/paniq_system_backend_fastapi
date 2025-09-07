"""
User and group related models
"""
from sqlalchemy import Column, String, Boolean, Integer, DECIMAL, ForeignKey, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from app.models.base import BaseModel


class RegisteredUser(BaseModel):
    """Registered user model"""
    __tablename__ = "registered_users"
    
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String(20), unique=True, nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    password_hash = Column(String(255), nullable=True)  # Nullable for backward compatibility
    role = Column(String(20), default="user", nullable=False)  # user, firm_admin, admin
    is_verified = Column(Boolean, default=False, nullable=False)
    prank_flags = Column(Integer, default=0, nullable=False)
    total_fines = Column(DECIMAL(10, 2), default=0, nullable=False)
    is_suspended = Column(Boolean, default=False, nullable=False)
    
    # Account security fields
    is_locked = Column(Boolean, default=False, nullable=False)
    locked_at = Column(DateTime(timezone=True), nullable=True)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    last_login_attempt = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    groups = relationship("UserGroup", back_populates="user", cascade="all, delete-orphan")
    stored_subscriptions = relationship("StoredSubscription", back_populates="user", cascade="all, delete-orphan")
    fines = relationship("UserFine", back_populates="user", cascade="all, delete-orphan")
    firm_memberships = relationship("FirmUser", back_populates="user", cascade="all, delete-orphan")


class UserGroup(BaseModel):
    """User group model"""
    __tablename__ = "user_groups"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("registered_users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    address = Column(Text, nullable=False)
    location = Column(Geometry("POINT", srid=4326), nullable=False)
    subscription_id = Column(UUID(as_uuid=True), nullable=True)
    subscription_expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("RegisteredUser", back_populates="groups")
    mobile_numbers = relationship("GroupMobileNumber", back_populates="group", cascade="all, delete-orphan")
    panic_requests = relationship("PanicRequest", back_populates="group")
    
    @property
    def latitude(self) -> float:
        """Extract latitude from PostGIS point"""
        from geoalchemy2.shape import to_shape
        point = to_shape(self.location)
        return point.y
    
    @property
    def longitude(self) -> float:
        """Extract longitude from PostGIS point"""
        from geoalchemy2.shape import to_shape
        point = to_shape(self.location)
        return point.x


class GroupMobileNumber(BaseModel):
    """Group mobile number model"""
    __tablename__ = "group_mobile_numbers"
    
    group_id = Column(UUID(as_uuid=True), ForeignKey("user_groups.id"), nullable=False)
    phone_number = Column(String(20), nullable=False)
    user_type = Column(String(20), nullable=False)  # individual, alarm, camera
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    group = relationship("UserGroup", back_populates="mobile_numbers")


class UserFine(BaseModel):
    """User fine model for prank detection system"""
    __tablename__ = "user_fines"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("registered_users.id"), nullable=False)
    amount = Column(DECIMAL(10, 2), nullable=False)
    reason = Column(Text, nullable=False)
    is_paid = Column(Boolean, default=False, nullable=False)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("RegisteredUser", back_populates="fines")