"""
Capability service for managing emergency provider capabilities
"""
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.models.capability import Capability, ProviderCapability, ProficiencyLevel, CapabilityCategory
from app.models.emergency_provider import EmergencyProvider
from app.core.logging import get_logger

logger = get_logger(__name__)


class CapabilityService:
    """Service for managing capabilities"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_capability(
        self,
        name: str,
        code: str,
        description: Optional[str] = None,
        category_id: UUID = None,
        is_active: bool = True
    ) -> Capability:
        """Create a new capability"""
        
        # Check if code already exists
        existing_query = select(Capability).where(Capability.code == code)
        result = await self.db.execute(existing_query)
        existing = result.scalar_one_or_none()
        
        if existing:
            raise ValueError(f"Capability with code '{code}' already exists")
        
        # Check if name already exists
        name_query = select(Capability).where(Capability.name == name)
        result = await self.db.execute(name_query)
        existing_name = result.scalar_one_or_none()
        
        if existing_name:
            raise ValueError(f"Capability with name '{name}' already exists")
        
        # Verify category exists if provided
        if category_id:
            category_query = select(CapabilityCategory).where(CapabilityCategory.id == category_id)
            result = await self.db.execute(category_query)
            category = result.scalar_one_or_none()
            if not category:
                raise ValueError(f"Category with ID {category_id} not found")
            if not category.is_active:
                raise ValueError(f"Category '{category.name}' is not active")
        
        capability = Capability(
            name=name,
            code=code,
            description=description,
            category_id=category_id,
            is_active=is_active
        )
        
        self.db.add(capability)
        await self.db.commit()
        await self.db.refresh(capability, ['capability_category'])
        
        logger.info(
            "capability_created",
            capability_id=str(capability.id),
            name=name,
            code=code,
            category_id=str(category_id) if category_id else None
        )
        
        return capability

    async def get_capabilities(
        self,
        category_id: Optional[UUID] = None,
        include_inactive: bool = False,
        load_category: bool = False
    ) -> List[Capability]:
        """Get all capabilities with optional filtering"""
        
        query = select(Capability)
        
        if load_category:
            query = query.options(selectinload(Capability.capability_category))
        
        if not include_inactive:
            query = query.where(Capability.is_active == True)
            
        if category_id:
            query = query.where(Capability.category_id == category_id)
            
        query = query.order_by(Capability.name)
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_capability_by_id(self, capability_id: UUID, load_category: bool = False) -> Optional[Capability]:
        """Get capability by ID"""
        
        query = select(Capability).where(Capability.id == capability_id)
        
        if load_category:
            query = query.options(selectinload(Capability.capability_category))
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_capability_by_code(self, code: str) -> Optional[Capability]:
        """Get capability by code"""
        
        query = select(Capability).where(Capability.code == code)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_capability(
        self,
        capability_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        category_id: Optional[UUID] = None,
        is_active: Optional[bool] = None
    ) -> Optional[Capability]:
        """Update capability details"""
        
        capability = await self.get_capability_by_id(capability_id)
        if not capability:
            return None
        
        # Check if new name conflicts with existing capability
        if name and name != capability.name:
            name_query = select(Capability).where(
                and_(Capability.name == name, Capability.id != capability_id)
            )
            result = await self.db.execute(name_query)
            existing_name = result.scalar_one_or_none()
            
            if existing_name:
                raise ValueError(f"Capability with name '{name}' already exists")
        
        # Verify category exists if being updated
        if category_id is not None:
            category_query = select(CapabilityCategory).where(CapabilityCategory.id == category_id)
            result = await self.db.execute(category_query)
            category = result.scalar_one_or_none()
            if not category:
                raise ValueError(f"Category with ID {category_id} not found")
            if not category.is_active:
                raise ValueError(f"Category '{category.name}' is not active")
        
        # Update fields
        if name is not None:
            capability.name = name
        if description is not None:
            capability.description = description
        if category_id is not None:
            capability.category_id = category_id
        if is_active is not None:
            capability.is_active = is_active
            
        await self.db.commit()
        await self.db.refresh(capability, ['capability_category'])
        
        logger.info(
            "capability_updated",
            capability_id=str(capability_id),
            updated_fields=[k for k, v in locals().items() if k not in ['self', 'capability_id', 'capability', 'category_query', 'result', 'category', 'name_query', 'existing_name'] and v is not None]
        )
        
        return capability

    async def delete_capability(self, capability_id: UUID) -> bool:
        """Delete a capability (soft delete by setting inactive)"""
        
        capability = await self.get_capability_by_id(capability_id)
        if not capability:
            return False
        
        capability.is_active = False
        await self.db.commit()
        
        logger.info(
            "capability_deleted",
            capability_id=str(capability_id)
        )
        
        return True

    async def assign_capability_to_provider(
        self,
        provider_id: UUID,
        capability_id: UUID,
        proficiency_level: ProficiencyLevel = ProficiencyLevel.STANDARD,
        certification_level: Optional[str] = None
    ) -> ProviderCapability:
        """Assign a capability to a provider"""
        
        # Verify provider exists
        provider_query = select(EmergencyProvider).where(EmergencyProvider.id == provider_id)
        result = await self.db.execute(provider_query)
        provider = result.scalar_one_or_none()
        
        if not provider:
            raise ValueError(f"Provider with ID {provider_id} not found")
        
        # Verify capability exists
        capability = await self.get_capability_by_id(capability_id)
        if not capability:
            raise ValueError(f"Capability with ID {capability_id} not found")
        
        if not capability.is_active:
            raise ValueError(f"Capability '{capability.name}' is not active")
        
        # Check if assignment already exists
        existing_query = select(ProviderCapability).where(
            and_(
                ProviderCapability.provider_id == provider_id,
                ProviderCapability.capability_id == capability_id
            )
        )
        result = await self.db.execute(existing_query)
        existing = result.scalar_one_or_none()
        
        if existing:
            raise ValueError(f"Provider already has capability '{capability.name}'")
        
        provider_capability = ProviderCapability(
            provider_id=provider_id,
            capability_id=capability_id,
            proficiency_level=proficiency_level,
            certification_level=certification_level
        )
        
        self.db.add(provider_capability)
        await self.db.commit()
        await self.db.refresh(provider_capability)
        
        # Load the capability relationship
        await self.db.refresh(provider_capability, ['capability'])
        
        logger.info(
            "capability_assigned_to_provider",
            provider_id=str(provider_id),
            capability_id=str(capability_id),
            proficiency_level=proficiency_level.value
        )
        
        return provider_capability

    async def get_provider_capabilities(self, provider_id: UUID) -> List[ProviderCapability]:
        """Get all capabilities for a provider"""
        
        query = select(ProviderCapability).options(
            selectinload(ProviderCapability.capability)
        ).where(ProviderCapability.provider_id == provider_id)
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def remove_capability_from_provider(self, provider_capability_id: UUID) -> bool:
        """Remove a capability from a provider"""
        
        query = select(ProviderCapability).where(ProviderCapability.id == provider_capability_id)
        result = await self.db.execute(query)
        provider_capability = result.scalar_one_or_none()
        
        if not provider_capability:
            return False
        
        await self.db.delete(provider_capability)
        await self.db.commit()
        
        logger.info(
            "capability_removed_from_provider",
            provider_capability_id=str(provider_capability_id),
            provider_id=str(provider_capability.provider_id),
            capability_id=str(provider_capability.capability_id)
        )
        
        return True

    async def get_capabilities_by_category(self, category_id: UUID) -> List[Capability]:
        """Get all active capabilities in a specific category"""
        
        query = select(Capability).options(
            selectinload(Capability.capability_category)
        ).where(
            and_(
                Capability.category_id == category_id,
                Capability.is_active == True
            )
        ).order_by(Capability.name)
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_providers_with_capability(self, capability_id: UUID) -> List[ProviderCapability]:
        """Get all providers that have a specific capability"""
        
        query = select(ProviderCapability).options(
            selectinload(ProviderCapability.provider),
            selectinload(ProviderCapability.capability)
        ).where(ProviderCapability.capability_id == capability_id)
        
        result = await self.db.execute(query)
        return result.scalars().all()