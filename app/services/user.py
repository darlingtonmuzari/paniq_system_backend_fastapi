"""
User service for registration and management
"""
import secrets
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from uuid import UUID
from decimal import Decimal

from app.models.user import RegisteredUser, UserGroup, GroupMobileNumber
from app.core.redis import cache
from app.core.cache import cache_result, cache_invalidate, invalidate_user_cache, CacheKey
from app.services.otp_delivery import OTPDeliveryService
from passlib.context import CryptContext


class UserService:
    """Service for managing user operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.otp_delivery = OTPDeliveryService()
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    async def register_user(
        self,
        email: str,
        phone: str,
        first_name: str,
        last_name: str,
        password: str = None
    ) -> RegisteredUser:
        """
        Register a new user
        """
        # Check if email or phone already exists
        existing_user = await self.db.execute(
            select(RegisteredUser).where(
                (RegisteredUser.email == email) |
                (RegisteredUser.phone == phone)
            )
        )
        if existing_user.scalar_one_or_none():
            raise ValueError("User with this email or phone number already exists")
        
        # Hash password if provided
        password_hash = None
        if password:
            password_hash = self.pwd_context.hash(password)
        
        # Create new user
        user = RegisteredUser(
            email=email,
            phone=phone,
            first_name=first_name,
            last_name=last_name,
            password_hash=password_hash,
            is_verified=False,
            prank_flags=0,
            total_fines=Decimal('0.00'),
            is_suspended=False,
            is_locked=False,
            failed_login_attempts=0
        )
        
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        
        return user
    
    @cache_result(expire=3600, key_prefix="user_by_id")
    async def get_user_by_id(self, user_id: UUID, include_firm_memberships: bool = True) -> RegisteredUser:
        """
        Get user by ID with optional firm memberships
        """
        if include_firm_memberships:
            from app.models.security_firm import FirmUser, SecurityFirm
            result = await self.db.execute(
                select(RegisteredUser)
                .options(
                    selectinload(RegisteredUser.firm_memberships)
                    .selectinload(FirmUser.firm)
                )
                .where(RegisteredUser.id == user_id)
            )
            user = result.scalar_one_or_none()
        else:
            user = await self.db.get(RegisteredUser, user_id)
        
        if not user:
            raise ValueError("User not found")
        return user
    
    async def get_user_by_email(self, email: str) -> Optional[RegisteredUser]:
        """
        Get user by email
        """
        result = await self.db.execute(
            select(RegisteredUser).where(RegisteredUser.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_phone(self, phone: str) -> Optional[RegisteredUser]:
        """
        Get user by phone number
        """
        result = await self.db.execute(
            select(RegisteredUser).where(RegisteredUser.phone == phone)
        )
        return result.scalar_one_or_none()
    
    @cache_invalidate("user_by_id:*", "user_groups:*")
    async def update_user_profile(
        self,
        user_id: UUID,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> RegisteredUser:
        """
        Update user profile
        """
        user = await self.get_user_by_id(user_id)
        
        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        
        await self.db.commit()
        await self.db.refresh(user)
        
        # Invalidate user-specific cache
        await invalidate_user_cache(user_id)
        
        return user
    
    async def request_phone_verification(self, phone: str) -> dict:
        """
        Request phone number verification OTP
        """
        # Generate 6-digit OTP
        otp = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
        
        # Store OTP in Redis with 10-minute expiration
        cache_key = f"phone_verification:{phone}"
        await cache.set(cache_key, otp, expire=600)  # 10 minutes
        
        # Send OTP via SMS
        success = await self.otp_delivery.send_sms_otp(phone, otp)
        
        if success:
            return {
                "success": True,
                "message": "OTP sent successfully",
                "expires_in_minutes": 10
            }
        else:
            return {
                "success": False,
                "message": "Failed to send OTP"
            }
    
    async def verify_phone_otp(self, phone: str, otp_code: str) -> dict:
        """
        Verify phone number with OTP
        """
        cache_key = f"phone_verification:{phone}"
        stored_otp = await cache.get(cache_key)
        
        if not stored_otp:
            return {
                "success": False,
                "message": "OTP expired or not found"
            }
        
        if stored_otp.decode() != otp_code:
            return {
                "success": False,
                "message": "Invalid OTP"
            }
        
        # Mark phone as verified for user
        user = await self.get_user_by_phone(phone)
        if user:
            user.is_verified = True
            await self.db.commit()
        
        # Remove OTP from cache
        await cache.delete(cache_key)
        
        return {
            "success": True,
            "message": "Phone number verified successfully"
        }
    
    async def create_user_group(
        self,
        user_id: UUID,
        name: str,
        address: str,
        latitude: float,
        longitude: float
    ) -> UserGroup:
        """
        Create a new user group
        """
        # Verify user exists
        user = await self.get_user_by_id(user_id)
        
        # Create point geometry
        point = Point(longitude, latitude)
        
        # Create group
        group = UserGroup(
            user_id=user_id,
            name=name,
            address=address,
            location=from_shape(point, srid=4326),
            subscription_id=None,
            subscription_expires_at=None
        )
        
        self.db.add(group)
        await self.db.commit()
        await self.db.refresh(group, ['mobile_numbers'])
        
        # Invalidate user groups cache
        await invalidate_user_cache(user_id)
        
        return group
    
    @cache_result(expire=1800, key_prefix="user_groups")
    async def get_user_groups(self, user_id: UUID) -> List[UserGroup]:
        """
        Get all groups for a user
        """
        # Verify user exists
        await self.get_user_by_id(user_id)
        
        result = await self.db.execute(
            select(UserGroup)
            .options(selectinload(UserGroup.mobile_numbers))
            .where(UserGroup.user_id == user_id)
        )
        return result.scalars().all()
    
    async def get_user_group_by_id(self, user_id: UUID, group_id: str) -> UserGroup:
        """
        Get specific group for user
        """
        result = await self.db.execute(
            select(UserGroup)
            .options(selectinload(UserGroup.mobile_numbers))
            .where(
                and_(
                    UserGroup.id == group_id,
                    UserGroup.user_id == user_id
                )
            )
        )
        group = result.scalar_one_or_none()
        if not group:
            raise ValueError("Group not found or not authorized")
        return group
    
    async def delete_user_group(self, user_id: UUID, group_id: str) -> None:
        """
        Delete a user group
        """
        group = await self.get_user_group_by_id(user_id, group_id)
        
        # Check if group has active subscription
        if group.subscription_expires_at and group.subscription_expires_at > group.created_at:
            raise ValueError("Cannot delete group with active subscription")
        
        await self.db.delete(group)
        await self.db.commit()
    
    async def add_mobile_number_to_group(
        self,
        user_id: UUID,
        group_id: str,
        phone_number: str,
        user_type: str
    ) -> GroupMobileNumber:
        """
        Add mobile number to group
        """
        # Verify group belongs to user
        group = await self.get_user_group_by_id(user_id, group_id)
        
        # Check if phone number already exists in this group
        existing_number = await self.db.execute(
            select(GroupMobileNumber).where(
                and_(
                    GroupMobileNumber.group_id == group_id,
                    GroupMobileNumber.phone_number == phone_number
                )
            )
        )
        if existing_number.scalar_one_or_none():
            raise ValueError("Phone number already exists in this group")
        
        # Create mobile number entry
        mobile_number = GroupMobileNumber(
            group_id=group_id,
            phone_number=phone_number,
            user_type=user_type,
            is_verified=False
        )
        
        self.db.add(mobile_number)
        await self.db.commit()
        await self.db.refresh(mobile_number)
        
        return mobile_number
    
    async def get_group_mobile_numbers(
        self,
        user_id: UUID,
        group_id: str
    ) -> List[GroupMobileNumber]:
        """
        Get mobile numbers for a group
        """
        # Verify group belongs to user
        group = await self.get_user_group_by_id(user_id, group_id)
        
        result = await self.db.execute(
            select(GroupMobileNumber).where(GroupMobileNumber.group_id == group_id)
        )
        return result.scalars().all()
    
    async def remove_mobile_number_from_group(
        self,
        user_id: UUID,
        group_id: str,
        mobile_number_id: str
    ) -> None:
        """
        Remove mobile number from group
        """
        # Verify group belongs to user
        await self.get_user_group_by_id(user_id, group_id)
        
        # Get mobile number
        mobile_number = await self.db.get(GroupMobileNumber, mobile_number_id)
        if not mobile_number or mobile_number.group_id != UUID(group_id):
            raise ValueError("Mobile number not found in this group")
        
        await self.db.delete(mobile_number)
        await self.db.commit()
    
    async def verify_mobile_number_in_group(
        self,
        user_id: UUID,
        group_id: str,
        mobile_number_id: str,
        otp_code: str
    ) -> dict:
        """
        Verify mobile number in group with OTP
        """
        # Verify group belongs to user
        await self.get_user_group_by_id(user_id, group_id)
        
        # Get mobile number
        mobile_number = await self.db.get(GroupMobileNumber, mobile_number_id)
        if not mobile_number or mobile_number.group_id != UUID(group_id):
            raise ValueError("Mobile number not found in this group")
        
        # Verify OTP
        result = await self.verify_phone_otp(mobile_number.phone_number, otp_code)
        
        if result["success"]:
            mobile_number.is_verified = True
            await self.db.commit()
        
        return result
    
    async def get_user_statistics(self, user_id: UUID) -> dict:
        """
        Get user statistics
        """
        user = await self.get_user_by_id(user_id)
        groups = await self.get_user_groups(user_id)
        
        total_mobile_numbers = sum(len(group.mobile_numbers) for group in groups)
        active_subscriptions = sum(
            1 for group in groups 
            if group.subscription_expires_at and group.subscription_expires_at > group.created_at
        )
        
        return {
            "total_groups": len(groups),
            "total_mobile_numbers": total_mobile_numbers,
            "active_subscriptions": active_subscriptions,
            "prank_flags": user.prank_flags,
            "total_fines": float(user.total_fines),
            "is_suspended": user.is_suspended,
            "is_verified": user.is_verified
        }