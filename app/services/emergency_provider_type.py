"""
Emergency Provider Type service for managing provider type configurations
"""
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, exists
from sqlalchemy.exc import IntegrityError

from app.models.emergency_provider import EmergencyProviderType, EmergencyProvider
from app.core.logging import get_logger

logger = get_logger()


class EmergencyProviderTypeService:
    """Service for managing emergency provider types"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.logger = logger
    
    async def create_provider_type(
        self,
        name: str,
        code: str,
        description: Optional[str] = None,
        requires_license: bool = False,
        default_coverage_radius_km: float = 50.0,
        icon: Optional[str] = None,
        color: Optional[str] = None,
        priority_level: str = "medium"
    ) -> EmergencyProviderType:
        """Create a new emergency provider type"""
        
        try:
            # Check if code already exists
            existing_query = select(EmergencyProviderType).where(
                EmergencyProviderType.code == code
            )
            result = await self.db.execute(existing_query)
            existing_type = result.scalar_one_or_none()
            
            if existing_type:
                raise ValueError(f"Provider type with code '{code}' already exists")
            
            # Check if name already exists
            name_query = select(EmergencyProviderType).where(
                EmergencyProviderType.name == name
            )
            result = await self.db.execute(name_query)
            existing_name = result.scalar_one_or_none()
            
            if existing_name:
                raise ValueError(f"Provider type with name '{name}' already exists")
            
            provider_type = EmergencyProviderType(
                name=name,
                code=code,
                description=description,
                requires_license=requires_license,
                default_coverage_radius_km=default_coverage_radius_km,
                icon=icon,
                color=color,
                priority_level=priority_level
            )
            
            self.db.add(provider_type)
            await self.db.commit()
            await self.db.refresh(provider_type)
            
            self.logger.info(
                "provider_type_created",
                provider_type_id=str(provider_type.id),
                name=name,
                code=code
            )
            
            return provider_type
            
        except IntegrityError as e:
            await self.db.rollback()
            self.logger.error(f"Database integrity error creating provider type: {str(e)}")
            raise ValueError("Provider type with this code or name already exists")
        except Exception as e:
            await self.db.rollback()
            self.logger.error(f"Error creating provider type: {str(e)}", exc_info=True)
            raise
    
    async def list_provider_types(
        self,
        skip: int = 0,
        limit: int = 100,
        is_active: Optional[bool] = None
    ) -> List[EmergencyProviderType]:
        """List emergency provider types with optional filtering"""
        
        try:
            query = select(EmergencyProviderType)
            
            # Apply filters
            if is_active is not None:
                query = query.where(EmergencyProviderType.is_active == is_active)
            
            # Apply pagination
            query = query.offset(skip).limit(limit)
            
            # Order by name
            query = query.order_by(EmergencyProviderType.name)
            
            result = await self.db.execute(query)
            provider_types = result.scalars().all()
            
            return list(provider_types)
            
        except Exception as e:
            self.logger.error(f"Error listing provider types: {str(e)}", exc_info=True)
            raise
    
    async def get_provider_type_by_id(self, type_id: UUID) -> Optional[EmergencyProviderType]:
        """Get emergency provider type by ID"""
        
        try:
            query = select(EmergencyProviderType).where(EmergencyProviderType.id == type_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
            
        except Exception as e:
            self.logger.error(f"Error getting provider type by ID: {str(e)}", exc_info=True)
            raise
    
    async def get_provider_type_by_code(self, code: str) -> Optional[EmergencyProviderType]:
        """Get emergency provider type by code"""
        
        try:
            query = select(EmergencyProviderType).where(EmergencyProviderType.code == code)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
            
        except Exception as e:
            self.logger.error(f"Error getting provider type by code: {str(e)}", exc_info=True)
            raise
    
    async def update_provider_type(
        self,
        type_id: UUID,
        **updates
    ) -> EmergencyProviderType:
        """Update emergency provider type"""
        
        try:
            # Get existing provider type
            query = select(EmergencyProviderType).where(EmergencyProviderType.id == type_id)
            result = await self.db.execute(query)
            provider_type = result.scalar_one_or_none()
            
            if not provider_type:
                raise ValueError("Provider type not found")
            
            # Check for name conflicts if name is being updated
            if 'name' in updates and updates['name'] != provider_type.name:
                name_query = select(EmergencyProviderType).where(
                    and_(
                        EmergencyProviderType.name == updates['name'],
                        EmergencyProviderType.id != type_id
                    )
                )
                result = await self.db.execute(name_query)
                existing_name = result.scalar_one_or_none()
                
                if existing_name:
                    raise ValueError(f"Provider type with name '{updates['name']}' already exists")
            
            # Apply updates
            for key, value in updates.items():
                if hasattr(provider_type, key) and value is not None:
                    setattr(provider_type, key, value)
            
            await self.db.commit()
            await self.db.refresh(provider_type)
            
            self.logger.info(
                "provider_type_updated",
                provider_type_id=str(provider_type.id),
                updates=list(updates.keys())
            )
            
            return provider_type
            
        except IntegrityError as e:
            await self.db.rollback()
            self.logger.error(f"Database integrity error updating provider type: {str(e)}")
            raise ValueError("Provider type with this name already exists")
        except Exception as e:
            await self.db.rollback()
            self.logger.error(f"Error updating provider type: {str(e)}", exc_info=True)
            raise
    
    async def delete_provider_type(self, type_id: UUID) -> bool:
        """Delete emergency provider type"""
        
        try:
            # Get provider type
            query = select(EmergencyProviderType).where(EmergencyProviderType.id == type_id)
            result = await self.db.execute(query)
            provider_type = result.scalar_one_or_none()
            
            if not provider_type:
                return False
            
            await self.db.delete(provider_type)
            await self.db.commit()
            
            self.logger.info(
                "provider_type_deleted",
                provider_type_id=str(type_id),
                name=provider_type.name
            )
            
            return True
            
        except Exception as e:
            await self.db.rollback()
            self.logger.error(f"Error deleting provider type: {str(e)}", exc_info=True)
            raise
    
    async def is_provider_type_in_use(self, type_id: UUID) -> bool:
        """Check if provider type is in use by any emergency providers"""
        
        try:
            query = select(exists().where(EmergencyProvider.provider_type_id == type_id))
            result = await self.db.execute(query)
            return result.scalar()
            
        except Exception as e:
            self.logger.error(f"Error checking provider type usage: {str(e)}", exc_info=True)
            raise
    
    async def get_active_provider_types(self) -> List[EmergencyProviderType]:
        """Get all active provider types"""
        
        try:
            query = select(EmergencyProviderType).where(
                EmergencyProviderType.is_active == True
            ).order_by(EmergencyProviderType.name)
            
            result = await self.db.execute(query)
            return list(result.scalars().all())
            
        except Exception as e:
            self.logger.error(f"Error getting active provider types: {str(e)}", exc_info=True)
            raise