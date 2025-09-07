"""
Registered user management API endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr, validator
from uuid import UUID

from app.core.database import get_db
from app.models.user import RegisteredUser, UserGroup, GroupMobileNumber
from app.services.user import UserService
from app.core.auth import get_current_user, get_current_registered_user
from app.services.auth import UserContext

router = APIRouter()


class UserRegistrationRequest(BaseModel):
    """User registration request model"""
    email: EmailStr
    phone: str
    first_name: str
    last_name: str
    
    @validator('phone')
    def validate_phone(cls, v):
        # Basic phone validation - should be digits and common separators
        cleaned = ''.join(c for c in v if c.isdigit() or c in '+()-. ')
        digits_only = ''.join(c for c in cleaned if c.isdigit())
        if len(digits_only) < 10:
            raise ValueError('Phone number must be at least 10 digits')
        return cleaned
    
    @validator('first_name', 'last_name')
    def validate_names(cls, v):
        if len(v.strip()) < 2:
            raise ValueError('Name must be at least 2 characters long')
        return v.strip()


class FirmMembershipResponse(BaseModel):
    """Firm membership response model"""
    firm_id: str
    firm_name: str
    role: str
    status: str
    
    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    """User response model"""
    id: str
    email: str
    phone: str
    first_name: str
    last_name: str
    is_verified: bool
    prank_flags: int
    total_fines: str
    is_suspended: bool
    is_locked: bool
    created_at: str
    firm_memberships: List[FirmMembershipResponse] = []
    
    class Config:
        from_attributes = True
    
    @classmethod
    def from_orm(cls, obj):
        firm_memberships = []
        if hasattr(obj, 'firm_memberships') and obj.firm_memberships:
            for membership in obj.firm_memberships:
                firm_memberships.append(FirmMembershipResponse(
                    firm_id=str(membership.firm_id),
                    firm_name=membership.firm.name if membership.firm else "Unknown",
                    role=membership.role,
                    status=membership.status
                ))
        
        return cls(
            id=str(obj.id),
            email=obj.email,
            phone=obj.phone,
            first_name=obj.first_name,
            last_name=obj.last_name,
            is_verified=obj.is_verified,
            prank_flags=obj.prank_flags,
            total_fines=str(obj.total_fines),
            is_suspended=obj.is_suspended,
            is_locked=obj.is_locked,
            created_at=obj.created_at.isoformat(),
            firm_memberships=firm_memberships
        )


class UserProfileUpdateRequest(BaseModel):
    """User profile update request"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    
    @validator('first_name', 'last_name')
    def validate_names(cls, v):
        if v is not None and len(v.strip()) < 2:
            raise ValueError('Name must be at least 2 characters long')
        return v.strip() if v else v


class GroupCreationRequest(BaseModel):
    """Group creation request"""
    name: str
    address: str
    latitude: float
    longitude: float
    
    @validator('name')
    def validate_name(cls, v):
        if len(v.strip()) < 2:
            raise ValueError('Group name must be at least 2 characters long')
        return v.strip()
    
    @validator('latitude')
    def validate_latitude(cls, v):
        if not -90 <= v <= 90:
            raise ValueError('Latitude must be between -90 and 90')
        return v
    
    @validator('longitude')
    def validate_longitude(cls, v):
        if not -180 <= v <= 180:
            raise ValueError('Longitude must be between -180 and 180')
        return v


class GroupResponse(BaseModel):
    """Group response model"""
    id: str
    name: str
    address: str
    latitude: float
    longitude: float
    subscription_expires_at: Optional[str] = None
    mobile_numbers_count: int
    created_at: str
    
    class Config:
        from_attributes = True


class MobileNumberRequest(BaseModel):
    """Mobile number addition request"""
    phone_number: str
    user_type: str
    
    @validator('phone_number')
    def validate_phone(cls, v):
        cleaned = ''.join(c for c in v if c.isdigit() or c in '+()-. ')
        digits_only = ''.join(c for c in cleaned if c.isdigit())
        if len(digits_only) < 10:
            raise ValueError('Phone number must be at least 10 digits')
        return cleaned
    
    @validator('user_type')
    def validate_user_type(cls, v):
        if v not in ['individual', 'alarm', 'camera']:
            raise ValueError('User type must be individual, alarm, or camera')
        return v


class MobileNumberResponse(BaseModel):
    """Mobile number response model"""
    id: str
    phone_number: str
    user_type: str
    is_verified: bool
    created_at: str
    
    class Config:
        from_attributes = True


class PhoneVerificationRequest(BaseModel):
    """Phone verification request"""
    phone: str
    
    @validator('phone')
    def validate_phone(cls, v):
        cleaned = ''.join(c for c in v if c.isdigit() or c in '+()-. ')
        digits_only = ''.join(c for c in cleaned if c.isdigit())
        if len(digits_only) < 10:
            raise ValueError('Phone number must be at least 10 digits')
        return cleaned


class OTPVerificationRequest(BaseModel):
    """OTP verification request"""
    phone: str
    otp_code: str
    
    @validator('otp_code')
    def validate_otp(cls, v):
        if not v.isdigit() or len(v) != 6:
            raise ValueError('OTP must be 6 digits')
        return v


@router.post("/register", response_model=UserResponse)
async def register_user(
    request: UserRegistrationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user
    """
    service = UserService(db)
    
    try:
        user = await service.register_user(
            email=request.email,
            phone=request.phone,
            first_name=request.first_name,
            last_name=request.last_name
        )
        return UserResponse.from_orm(user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/verify-phone")
async def request_phone_verification(
    request: PhoneVerificationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Request phone number verification OTP
    """
    service = UserService(db)
    
    try:
        result = await service.request_phone_verification(request.phone)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/verify-otp")
async def verify_phone_otp(
    request: OTPVerificationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify phone number with OTP
    """
    service = UserService(db)
    
    try:
        result = await service.verify_phone_otp(request.phone, request.otp_code)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/profile", response_model=UserResponse)
async def get_user_profile(
    current_user: UserContext = Depends(get_current_registered_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user profile
    """
    service = UserService(db)
    
    try:
        user = await service.get_user_by_id(current_user.user_id)
        return UserResponse.from_orm(user)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )


@router.put("/profile", response_model=UserResponse)
async def update_user_profile(
    request: UserProfileUpdateRequest,
    current_user: UserContext = Depends(get_current_registered_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update user profile
    """
    service = UserService(db)
    
    try:
        user = await service.update_user_profile(
            user_id=current_user.user_id,
            first_name=request.first_name,
            last_name=request.last_name
        )
        return UserResponse.from_orm(user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )


@router.post("/groups", response_model=GroupResponse)
async def create_user_group(
    request: GroupCreationRequest,
    current_user: UserContext = Depends(get_current_registered_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new user group
    """
    service = UserService(db)
    
    try:
        group = await service.create_user_group(
            user_id=current_user.user_id,
            name=request.name,
            address=request.address,
            latitude=request.latitude,
            longitude=request.longitude
        )
        
        # Convert to response format
        return GroupResponse(
            id=str(group.id),
            name=group.name,
            address=group.address,
            latitude=group.latitude,
            longitude=group.longitude,
            subscription_expires_at=group.subscription_expires_at.isoformat() if group.subscription_expires_at else None,
            mobile_numbers_count=len(group.mobile_numbers),
            created_at=group.created_at.isoformat()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/groups", response_model=List[GroupResponse])
async def get_user_groups(
    current_user: UserContext = Depends(get_current_registered_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all groups for current user
    """
    service = UserService(db)
    
    try:
        groups = await service.get_user_groups(current_user.user_id)
        
        result = []
        for group in groups:
            result.append(GroupResponse(
                id=str(group.id),
                name=group.name,
                address=group.address,
                latitude=group.latitude,
                longitude=group.longitude,
                subscription_expires_at=group.subscription_expires_at.isoformat() if group.subscription_expires_at else None,
                mobile_numbers_count=len(group.mobile_numbers),
                created_at=group.created_at.isoformat()
            ))
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )


@router.post("/groups/{group_id}/mobile-numbers", response_model=MobileNumberResponse)
async def add_mobile_number_to_group(
    group_id: str,
    request: MobileNumberRequest,
    current_user: UserContext = Depends(get_current_registered_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Add mobile number to group
    """
    service = UserService(db)
    
    try:
        mobile_number = await service.add_mobile_number_to_group(
            user_id=current_user.user_id,
            group_id=group_id,
            phone_number=request.phone_number,
            user_type=request.user_type
        )
        return MobileNumberResponse.from_orm(mobile_number)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found or not authorized"
        )


@router.get("/groups/{group_id}/mobile-numbers", response_model=List[MobileNumberResponse])
async def get_group_mobile_numbers(
    group_id: str,
    current_user: UserContext = Depends(get_current_registered_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get mobile numbers for a group
    """
    service = UserService(db)
    
    try:
        mobile_numbers = await service.get_group_mobile_numbers(
            user_id=current_user.user_id,
            group_id=group_id
        )
        return [MobileNumberResponse.from_orm(mn) for mn in mobile_numbers]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found or not authorized"
        )


@router.delete("/groups/{group_id}/mobile-numbers/{mobile_number_id}")
async def remove_mobile_number_from_group(
    group_id: str,
    mobile_number_id: str,
    current_user: UserContext = Depends(get_current_registered_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove mobile number from group
    """
    service = UserService(db)
    
    try:
        await service.remove_mobile_number_from_group(
            user_id=current_user.user_id,
            group_id=group_id,
            mobile_number_id=mobile_number_id
        )
        return {"message": "Mobile number removed successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mobile number or group not found"
        )


@router.delete("/groups/{group_id}")
async def delete_user_group(
    group_id: str,
    current_user: UserContext = Depends(get_current_registered_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a user group
    """
    service = UserService(db)
    
    try:
        await service.delete_user_group(
            user_id=current_user.user_id,
            group_id=group_id
        )
        return {"message": "Group deleted successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found or not authorized"
        )