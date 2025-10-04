"""
Service layer for capability category operations
"""
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload

from app.models.capability import CapabilityCategory, Capability


class CapabilityCategoryService:
    """Service for managing capability categories"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_categories(
        self, 
        include_inactive: bool = True,
        load_capabilities: bool = False
    ) -> List[CapabilityCategory]:
        """
        Get all capability categories
        
        Args:
            include_inactive: Whether to include inactive categories
            load_capabilities: Whether to eagerly load associated capabilities
            
        Returns:
            List of CapabilityCategory objects
        """
        query = select(CapabilityCategory)
        
        if not include_inactive:
            query = query.where(CapabilityCategory.is_active == True)
        
        if load_capabilities:
            query = query.options(selectinload(CapabilityCategory.capabilities))
        
        query = query.order_by(CapabilityCategory.name)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_category_by_id(self, category_id: UUID) -> Optional[CapabilityCategory]:
        """Get capability category by ID"""
        query = select(CapabilityCategory).where(CapabilityCategory.id == category_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_category_by_code(self, code: str) -> Optional[CapabilityCategory]:
        """Get capability category by code"""
        query = select(CapabilityCategory).where(CapabilityCategory.code == code)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def create_category(
        self,
        name: str,
        code: str,
        description: Optional[str] = None,
        icon: Optional[str] = None,
        color: Optional[str] = None,
        is_active: bool = True
    ) -> CapabilityCategory:
        """
        Create a new capability category
        
        Args:
            name: Category name
            code: Unique category code
            description: Category description
            icon: Icon name for UI
            color: Hex color code
            is_active: Whether the category is active
            
        Returns:
            Created CapabilityCategory object
            
        Raises:
            ValueError: If name or code already exists
        """
        # Check for existing name
        existing_name = await self.session.execute(
            select(CapabilityCategory).where(CapabilityCategory.name == name)
        )
        if existing_name.scalar_one_or_none():
            raise ValueError(f"Category with name '{name}' already exists")
        
        # Check for existing code
        existing_code = await self.session.execute(
            select(CapabilityCategory).where(CapabilityCategory.code == code)
        )
        if existing_code.scalar_one_or_none():
            raise ValueError(f"Category with code '{code}' already exists")
        
        category = CapabilityCategory(
            name=name,
            code=code,
            description=description,
            icon=icon,
            color=color,
            is_active=is_active
        )
        
        self.session.add(category)
        await self.session.commit()
        await self.session.refresh(category)
        
        return category
    
    async def update_category(
        self,
        category_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        icon: Optional[str] = None,
        color: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Optional[CapabilityCategory]:
        """
        Update capability category
        
        Args:
            category_id: Category ID to update
            name: New name (optional)
            description: New description (optional)
            icon: New icon (optional)
            color: New color (optional)
            is_active: New active status (optional)
            
        Returns:
            Updated CapabilityCategory object or None if not found
            
        Raises:
            ValueError: If name already exists for another category
        """
        category = await self.get_category_by_id(category_id)
        if not category:
            return None
        
        # Check for name conflicts if name is being updated
        if name and name != category.name:
            existing_name = await self.session.execute(
                select(CapabilityCategory).where(
                    CapabilityCategory.name == name,
                    CapabilityCategory.id != category_id
                )
            )
            if existing_name.scalar_one_or_none():
                raise ValueError(f"Category with name '{name}' already exists")
        
        # Update fields
        update_data = {}
        if name is not None:
            update_data['name'] = name
        if description is not None:
            update_data['description'] = description
        if icon is not None:
            update_data['icon'] = icon
        if color is not None:
            update_data['color'] = color
        if is_active is not None:
            update_data['is_active'] = is_active
        
        if update_data:
            await self.session.execute(
                update(CapabilityCategory)
                .where(CapabilityCategory.id == category_id)
                .values(**update_data)
            )
            await self.session.commit()
            await self.session.refresh(category)
        
        return category
    
    async def delete_category(self, category_id: UUID) -> bool:
        """
        Delete capability category (soft delete by setting is_active = False)
        
        Args:
            category_id: Category ID to delete
            
        Returns:
            True if category was found and deleted, False otherwise
            
        Raises:
            ValueError: If category has active capabilities associated with it
        """
        category = await self.get_category_by_id(category_id)
        if not category:
            return False
        
        # Check if category has any active capabilities
        capabilities_count = await self.session.execute(
            select(Capability).where(
                Capability.category_id == category_id,
                Capability.is_active == True
            )
        )
        
        if capabilities_count.scalars().first():
            raise ValueError("Cannot delete category with active capabilities. Deactivate capabilities first.")
        
        # Soft delete by setting is_active = False
        await self.session.execute(
            update(CapabilityCategory)
            .where(CapabilityCategory.id == category_id)
            .values(is_active=False)
        )
        await self.session.commit()
        
        return True
    
    async def get_category_statistics(self) -> dict:
        """
        Get statistics about capability categories
        
        Returns:
            Dictionary with category statistics
        """
        # Count total categories
        total_categories = await self.session.execute(
            select(CapabilityCategory)
        )
        total_count = len(total_categories.scalars().all())
        
        # Count active categories
        active_categories = await self.session.execute(
            select(CapabilityCategory).where(CapabilityCategory.is_active == True)
        )
        active_count = len(active_categories.scalars().all())
        
        # Get categories with their capability counts
        categories_result = await self.session.execute(
            select(CapabilityCategory)
            .where(CapabilityCategory.is_active == True)
            .order_by(CapabilityCategory.name)
        )
        categories = categories_result.scalars().all()
        
        category_breakdown = []
        for category in categories:
            # Count capabilities for this category
            capability_count_result = await self.session.execute(
                select(Capability).where(Capability.category_id == category.id)
            )
            capability_count = len(capability_count_result.scalars().all())
            
            category_breakdown.append({
                'category_name': category.name,
                'category_code': category.code, 
                'capability_count': capability_count
            })
        
        return {
            'total_categories': total_count,
            'active_categories': active_count,
            'inactive_categories': total_count - active_count,
            'categories': category_breakdown
        }