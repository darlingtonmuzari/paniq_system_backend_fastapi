"""
Document type models
"""
from sqlalchemy import Column, String, Boolean, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class DocumentType(BaseModel):
    """Document type model for managing allowed document types"""
    __tablename__ = "document_types"
    
    code = Column(String(50), unique=True, nullable=False)  # e.g., 'registration_certificate'
    name = Column(String(255), nullable=False)  # e.g., 'Registration Certificate'
    description = Column(Text, nullable=True)
    is_required = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(UUID(as_uuid=True), nullable=False)  # Admin who created it (can be RegisteredUser or FirmPersonnel)
    
    # Note: No foreign key constraint to allow both RegisteredUser and FirmPersonnel IDs
    # The relationship is handled at the application level
    
    def __repr__(self):
        return f"<DocumentType(code='{self.code}', name='{self.name}')>"