"""
Security firm related models
"""
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from app.models.base import BaseModel


class SecurityFirm(BaseModel):
    """Security firm model"""
    __tablename__ = "security_firms"
    
    name = Column(String(255), nullable=False)
    registration_number = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String(20), nullable=False)
    address = Column(Text, nullable=False)
    province = Column(String(100), nullable=False)
    country = Column(String(100), nullable=False, default="South Africa")
    vat_number = Column(String(50), nullable=True)
    verification_status = Column(String(20), default="draft", nullable=False)  # draft, submitted, approved, rejected
    credit_balance = Column(Integer, default=0, nullable=False)
    
    # Account security fields
    is_locked = Column(Boolean, default=False, nullable=False)
    locked_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    coverage_areas = relationship("CoverageArea", back_populates="firm", cascade="all, delete-orphan")
    personnel = relationship("FirmPersonnel", back_populates="firm", cascade="all, delete-orphan")
    teams = relationship("Team", back_populates="firm", cascade="all, delete-orphan")
    subscription_products = relationship("SubscriptionProduct", back_populates="firm", cascade="all, delete-orphan")
    applications = relationship("FirmApplication", back_populates="firm", cascade="all, delete-orphan")
    documents = relationship("FirmDocument", back_populates="firm", cascade="all, delete-orphan")


class CoverageArea(BaseModel):
    """Coverage area model with PostGIS geometry"""
    __tablename__ = "coverage_areas"
    
    firm_id = Column(UUID(as_uuid=True), ForeignKey("security_firms.id"), nullable=False)
    name = Column(String(255), nullable=False)
    boundary = Column(Geometry("POLYGON", srid=4326), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    firm = relationship("SecurityFirm", back_populates="coverage_areas")
    teams = relationship("Team", back_populates="coverage_area")


class FirmPersonnel(BaseModel):
    """Firm personnel model"""
    __tablename__ = "firm_personnel"
    
    firm_id = Column(UUID(as_uuid=True), ForeignKey("security_firms.id"), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String(20), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False)  # field_agent, team_leader, office_staff
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    
    # Account security fields
    is_locked = Column(Boolean, default=False, nullable=False)
    locked_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    firm = relationship("SecurityFirm", back_populates="personnel")
    team = relationship("Team", back_populates="members", foreign_keys=[team_id])
    led_teams = relationship("Team", back_populates="team_leader", foreign_keys="Team.team_leader_id")


class Team(BaseModel):
    """Team model"""
    __tablename__ = "teams"
    
    firm_id = Column(UUID(as_uuid=True), ForeignKey("security_firms.id"), nullable=False)
    name = Column(String(255), nullable=False)
    team_leader_id = Column(UUID(as_uuid=True), ForeignKey("firm_personnel.id"), nullable=True)
    coverage_area_id = Column(UUID(as_uuid=True), ForeignKey("coverage_areas.id"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    firm = relationship("SecurityFirm", back_populates="teams")
    team_leader = relationship("FirmPersonnel", back_populates="led_teams", foreign_keys=[team_leader_id])
    coverage_area = relationship("CoverageArea", back_populates="teams")
    members = relationship("FirmPersonnel", back_populates="team", foreign_keys="FirmPersonnel.team_id")


class FirmApplication(BaseModel):
    """Security firm application model for approval workflow"""
    __tablename__ = "firm_applications"
    
    firm_id = Column(UUID(as_uuid=True), ForeignKey("security_firms.id"), nullable=False)
    status = Column(String(20), default="draft", nullable=False)  # draft, submitted, under_review, approved, rejected
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by = Column(UUID(as_uuid=True), nullable=True)  # Admin user ID
    rejection_reason = Column(Text, nullable=True)
    admin_notes = Column(Text, nullable=True)
    
    # Relationships
    firm = relationship("SecurityFirm", back_populates="applications")


class FirmDocument(BaseModel):
    """Security firm document model for verification documents"""
    __tablename__ = "firm_documents"
    
    firm_id = Column(UUID(as_uuid=True), ForeignKey("security_firms.id"), nullable=False)
    document_type = Column(String(50), nullable=False)  # registration_certificate, proof_of_address, vat_certificate, etc.
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    uploaded_by = Column(UUID(as_uuid=True), nullable=False)  # User ID who uploaded
    is_verified = Column(Boolean, default=False, nullable=False)
    verified_by = Column(UUID(as_uuid=True), nullable=True)  # Admin user ID
    verified_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    firm = relationship("SecurityFirm", back_populates="documents")


class FirmUser(BaseModel):
    """Security firm user model - links users to firms with roles"""
    __tablename__ = "firm_users"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("registered_users.id"), nullable=False)
    firm_id = Column(UUID(as_uuid=True), ForeignKey("security_firms.id"), nullable=False)
    role = Column(String(20), nullable=False)  # firm_admin, office_staff, field_staff
    status = Column(String(20), default="pending", nullable=False)  # pending, active, suspended
    invited_by = Column(UUID(as_uuid=True), nullable=True)  # User ID who sent invitation
    invited_at = Column(DateTime(timezone=True), nullable=True)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    firm = relationship("SecurityFirm")
    user = relationship("RegisteredUser")