"""
Document type service for managing allowed document types
"""
from typing import List, Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.document_type import DocumentType


class DocumentTypeService:
    """Service for managing document types"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_all_document_types(self) -> List[DocumentType]:
        """
        Get all active document types
        """
        query = select(DocumentType).where(DocumentType.is_active == True)
        
        result = await self.db.execute(query.order_by(DocumentType.name))
        return result.scalars().all()
    
    async def get_all_document_types_including_inactive(self) -> List[DocumentType]:
        """
        Get all document types (both active and inactive)
        """
        query = select(DocumentType)
        
        result = await self.db.execute(query.order_by(DocumentType.name))
        return result.scalars().all()
    
    async def get_document_type_by_id(self, document_type_id: str) -> Optional[DocumentType]:
        """
        Get document type by ID (active only)
        """
        result = await self.db.execute(
            select(DocumentType).where(
                DocumentType.id == document_type_id,
                DocumentType.is_active == True
            )
        )
        return result.scalar_one_or_none()
    
    async def get_document_type_by_id_for_admin(self, document_type_id: str) -> Optional[DocumentType]:
        """
        Get document type by ID (both active and inactive) - for admin operations
        """
        result = await self.db.execute(
            select(DocumentType).where(
                DocumentType.id == document_type_id
            )
        )
        return result.scalar_one_or_none()
    
    async def get_document_type_by_code(self, code: str) -> Optional[DocumentType]:
        """
        Get document type by code
        """
        result = await self.db.execute(
            select(DocumentType).where(
                DocumentType.code == code,
                DocumentType.is_active == True
            )
        )
        return result.scalar_one_or_none()
    
    async def validate_document_type(self, code: str) -> DocumentType:
        """
        Validate that a document type exists and is active
        """
        doc_type = await self.get_document_type_by_code(code)
        
        if not doc_type:
            raise ValueError(f"Invalid document type: {code}")
        
        return doc_type
    

    
    async def get_required_documents(self, is_active: Optional[bool] = None) -> List[DocumentType]:
        """
        Get all required document types with optional is_active filter
        """
        query = select(DocumentType).where(
            DocumentType.is_required == True
        )
        
        # Apply is_active filter if provided
        if is_active is not None:
            query = query.where(DocumentType.is_active == is_active)
        
        result = await self.db.execute(query.order_by(DocumentType.name))
        return result.scalars().all()
    
    async def create_document_type(
        self,
        code: str,
        name: str,
        description: Optional[str],
        created_by: str,
        is_required: bool = False
    ) -> DocumentType:
        """
        Create a new document type (admin only)
        """
        # Check if code already exists
        existing = await self.get_document_type_by_code(code)
        if existing:
            raise ValueError(f"Document type with code {code} already exists")
        
        # Handle different user types for created_by field
        from app.models.user import RegisteredUser
        from app.models.security_firm import FirmPersonnel
        from sqlalchemy import select
        
        # Check if the user exists in registered_users
        user_result = await self.db.execute(
            select(RegisteredUser).where(RegisteredUser.id == created_by)
        )
        user_exists = user_result.scalar_one_or_none()
        
        if not user_exists:
            # Check if it's a firm personnel (like super admin)
            personnel_result = await self.db.execute(
                select(FirmPersonnel).where(FirmPersonnel.id == created_by)
            )
            personnel = personnel_result.scalar_one_or_none()
            
            if personnel:
                # Create a corresponding registered user entry for the firm personnel
                system_user = RegisteredUser(
                    id=created_by,
                    email=personnel.email,
                    phone=personnel.phone,
                    first_name=personnel.first_name,
                    last_name=personnel.last_name,
                    role="admin",
                    is_verified=True,
                    password_hash="firm_personnel_admin"
                )
                self.db.add(system_user)
                await self.db.flush()  # Ensure the user is created before the document type
            else:
                # Fallback: create a generic system user
                system_user = RegisteredUser(
                    id=created_by,
                    email="system@paniq.co.za",
                    phone="+27000000000",
                    first_name="System",
                    last_name="Administrator", 
                    role="admin",
                    is_verified=True,
                    password_hash="system_user_no_login"
                )
                self.db.add(system_user)
                await self.db.flush()
        
        doc_type = DocumentType(
            code=code,
            name=name,
            description=description,
            is_required=is_required,
            created_by=created_by
        )
        
        self.db.add(doc_type)
        await self.db.commit()
        await self.db.refresh(doc_type)
        
        return doc_type
    
    async def update_document_type_by_id(
        self,
        document_type_id: str,
        **updates
    ) -> DocumentType:
        """
        Update a document type by ID (admin only)
        """
        doc_type = await self.get_document_type_by_id_for_admin(document_type_id)
        if not doc_type:
            raise ValueError(f"Document type with ID {document_type_id} not found")
        
        for field, value in updates.items():
            if hasattr(doc_type, field):
                # Handle boolean fields explicitly (False is a valid value)
                if isinstance(value, bool) or value is not None:
                    setattr(doc_type, field, value)
        
        await self.db.commit()
        await self.db.refresh(doc_type)
        
        return doc_type
    
    async def update_document_type_by_code(
        self,
        code: str,
        **updates
    ) -> DocumentType:
        """
        Update a document type by code (admin only)
        """
        doc_type = await self.get_document_type_by_code(code)
        if not doc_type:
            raise ValueError(f"Document type {code} not found")
        
        for field, value in updates.items():
            if hasattr(doc_type, field):
                # Handle boolean fields explicitly (False is a valid value)
                if isinstance(value, bool) or value is not None:
                    setattr(doc_type, field, value)
        
        await self.db.commit()
        await self.db.refresh(doc_type)
        
        return doc_type
    
    async def deactivate_document_type_by_id(self, document_type_id: str) -> DocumentType:
        """
        Deactivate a document type by ID (admin only)
        """
        doc_type = await self.get_document_type_by_id_for_admin(document_type_id)
        if not doc_type:
            raise ValueError(f"Document type with ID {document_type_id} not found")
        
        doc_type.is_active = False
        
        await self.db.commit()
        await self.db.refresh(doc_type)
        
        return doc_type
    
    async def deactivate_document_type_by_code(self, code: str) -> DocumentType:
        """
        Deactivate a document type by code (admin only)
        """
        doc_type = await self.get_document_type_by_code(code)
        if not doc_type:
            raise ValueError(f"Document type {code} not found")
        
        doc_type.is_active = False
        
        await self.db.commit()
        await self.db.refresh(doc_type)
        
        return doc_type