"""
Base model with common fields and utilities
"""
from sqlalchemy import Column, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from app.core.database import Base
import uuid


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps"""
    
    @declared_attr
    def created_at(cls):
        return Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    @declared_attr
    def updated_at(cls):
        return Column(
            DateTime(timezone=True), 
            server_default=func.now(), 
            onupdate=func.now(), 
            nullable=False
        )


class UUIDMixin:
    """Mixin for UUID primary key"""
    
    @declared_attr
    def id(cls):
        return Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class BaseModel(Base, UUIDMixin, TimestampMixin):
    """Base model class with UUID and timestamps"""
    __abstract__ = True