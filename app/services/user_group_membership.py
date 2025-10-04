"""
User Group Membership service for managing many-to-many relationships between users and groups
"""
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from app.models.user import UserGroupMembership, UserGroup, RegisteredUser


class UserGroupMembershipService:
    """Service for managing user group memberships"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_user_to_group(
        self,
        user_id: UUID,
        group_id: UUID,
        role: str = "member"
    ) -> UserGroupMembership:
        """
        Add a user to a group with a specific role
        
        Args:
            user_id: The user ID
            group_id: The group ID
            role: The role in the group (member, admin, owner)
        
        Returns:
            The created UserGroupMembership instance
        
        Raises:
            ValueError: If user is already a member of the group
        """
        # Check if membership already exists
        existing = await self.get_membership(user_id, group_id)
        if existing and existing.is_active:
            raise ValueError("User is already a member of this group")
        
        # If inactive membership exists, reactivate it
        if existing and not existing.is_active:
            existing.is_active = True
            existing.role = role
            existing.joined_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(existing)
            return existing
        
        # Create new membership
        membership = UserGroupMembership(
            user_id=user_id,
            group_id=group_id,
            role=role,
            joined_at=datetime.utcnow(),
            is_active=True
        )
        
        self.db.add(membership)
        await self.db.commit()
        await self.db.refresh(membership)
        
        return membership

    async def remove_user_from_group(
        self,
        user_id: UUID,
        group_id: UUID
    ) -> bool:
        """
        Remove a user from a group (soft delete)
        
        Args:
            user_id: The user ID
            group_id: The group ID
        
        Returns:
            True if user was removed, False if not found
        """
        membership = await self.get_membership(user_id, group_id)
        if not membership or not membership.is_active:
            return False
        
        membership.is_active = False
        await self.db.commit()
        return True

    async def get_membership(
        self,
        user_id: UUID,
        group_id: UUID
    ) -> Optional[UserGroupMembership]:
        """
        Get a specific membership
        
        Args:
            user_id: The user ID
            group_id: The group ID
        
        Returns:
            UserGroupMembership or None if not found
        """
        query = select(UserGroupMembership).where(
            and_(
                UserGroupMembership.user_id == user_id,
                UserGroupMembership.group_id == group_id
            )
        )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_user_groups(
        self,
        user_id: UUID,
        active_only: bool = True
    ) -> List[UserGroup]:
        """
        Get all groups that a user is a member of
        
        Args:
            user_id: The user ID
            active_only: Only return active memberships
        
        Returns:
            List of UserGroup instances
        """
        query = (
            select(UserGroup)
            .join(UserGroupMembership)
            .where(UserGroupMembership.user_id == user_id)
        )
        
        if active_only:
            query = query.where(UserGroupMembership.is_active == True)
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_group_members(
        self,
        group_id: UUID,
        active_only: bool = True
    ) -> List[tuple[RegisteredUser, UserGroupMembership]]:
        """
        Get all members of a group with their membership details
        
        Args:
            group_id: The group ID
            active_only: Only return active memberships
        
        Returns:
            List of tuples (RegisteredUser, UserGroupMembership)
        """
        query = (
            select(RegisteredUser, UserGroupMembership)
            .join(UserGroupMembership)
            .where(UserGroupMembership.group_id == group_id)
        )
        
        if active_only:
            query = query.where(UserGroupMembership.is_active == True)
        
        result = await self.db.execute(query)
        return result.all()

    async def update_membership_role(
        self,
        user_id: UUID,
        group_id: UUID,
        new_role: str
    ) -> bool:
        """
        Update a user's role in a group
        
        Args:
            user_id: The user ID
            group_id: The group ID
            new_role: The new role (member, admin, owner)
        
        Returns:
            True if role was updated, False if membership not found
        """
        membership = await self.get_membership(user_id, group_id)
        if not membership or not membership.is_active:
            return False
        
        membership.role = new_role
        await self.db.commit()
        return True

    async def is_user_member_of_group(
        self,
        user_id: UUID,
        group_id: UUID
    ) -> bool:
        """
        Check if a user is an active member of a group
        
        Args:
            user_id: The user ID
            group_id: The group ID
        
        Returns:
            True if user is an active member
        """
        membership = await self.get_membership(user_id, group_id)
        return membership is not None and membership.is_active

    async def get_group_owners(
        self,
        group_id: UUID
    ) -> List[RegisteredUser]:
        """
        Get all owners of a group
        
        Args:
            group_id: The group ID
        
        Returns:
            List of RegisteredUser instances who are owners
        """
        query = (
            select(RegisteredUser)
            .join(UserGroupMembership)
            .where(
                and_(
                    UserGroupMembership.group_id == group_id,
                    UserGroupMembership.role == "owner",
                    UserGroupMembership.is_active == True
                )
            )
        )
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_group_admins(
        self,
        group_id: UUID
    ) -> List[RegisteredUser]:
        """
        Get all admins of a group (including owners)
        
        Args:
            group_id: The group ID
        
        Returns:
            List of RegisteredUser instances who are admins or owners
        """
        query = (
            select(RegisteredUser)
            .join(UserGroupMembership)
            .where(
                and_(
                    UserGroupMembership.group_id == group_id,
                    or_(
                        UserGroupMembership.role == "admin",
                        UserGroupMembership.role == "owner"
                    ),
                    UserGroupMembership.is_active == True
                )
            )
        )
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def transfer_group_ownership(
        self,
        group_id: UUID,
        current_owner_id: UUID,
        new_owner_id: UUID
    ) -> bool:
        """
        Transfer group ownership from one user to another
        
        Args:
            group_id: The group ID
            current_owner_id: Current owner's user ID
            new_owner_id: New owner's user ID
        
        Returns:
            True if ownership was transferred successfully
        """
        # Verify current owner
        current_membership = await self.get_membership(current_owner_id, group_id)
        if not current_membership or current_membership.role != "owner":
            return False
        
        # Verify new owner is a member
        new_membership = await self.get_membership(new_owner_id, group_id)
        if not new_membership or not new_membership.is_active:
            return False
        
        # Transfer ownership
        current_membership.role = "admin"  # Demote current owner to admin
        new_membership.role = "owner"      # Promote new member to owner
        
        await self.db.commit()
        return True

    async def get_membership_stats(self, group_id: UUID) -> dict:
        """
        Get membership statistics for a group
        
        Args:
            group_id: The group ID
        
        Returns:
            Dictionary with membership counts by role
        """
        query = (
            select(UserGroupMembership.role, 
                   select().select_from(UserGroupMembership).where(
                       and_(
                           UserGroupMembership.group_id == group_id,
                           UserGroupMembership.is_active == True
                       )
                   ).count().label('count'))
            .where(
                and_(
                    UserGroupMembership.group_id == group_id,
                    UserGroupMembership.is_active == True
                )
            )
            .group_by(UserGroupMembership.role)
        )
        
        result = await self.db.execute(query)
        stats = {role: count for role, count in result.all()}
        
        # Ensure all roles are represented
        for role in ["owner", "admin", "member"]:
            if role not in stats:
                stats[role] = 0
        
        stats["total"] = sum(stats.values())
        return stats