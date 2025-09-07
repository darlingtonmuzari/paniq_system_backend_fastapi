"""
Authentication dependencies and utilities for FastAPI
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from uuid import UUID
import structlog
import secrets
import string

from app.services.auth import auth_service, UserContext, AuthenticationError, TokenExpiredError
from app.core.exceptions import ErrorCodes

logger = structlog.get_logger()

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> UserContext:
    """
    Get current authenticated user from JWT token
    
    Args:
        credentials: HTTP Bearer credentials from request
        
    Returns:
        UserContext object for authenticated user
        
    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        user_context = await auth_service.validate_token(credentials.credentials)
        
        logger.info(
            "user_authenticated",
            user_id=str(user_context.user_id),
            user_type=user_context.user_type,
            email=user_context.email
        )
        
        return user_context
        
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_registered_user(
    current_user: UserContext = Depends(get_current_user)
) -> UserContext:
    """
    Get current user ensuring they are a registered user
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        UserContext for registered user
        
    Raises:
        HTTPException: If user is not a registered user
    """
    if not current_user.is_registered_user():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to registered users"
        )
    
    return current_user


async def get_current_firm_personnel(
    current_user: UserContext = Depends(get_current_user)
) -> UserContext:
    """
    Get current user ensuring they are firm personnel
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        UserContext for firm personnel
        
    Raises:
        HTTPException: If user is not firm personnel
    """
    if not current_user.is_firm_personnel():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to firm personnel"
        )
    
    return current_user


async def require_admin(
    current_user: UserContext = Depends(get_current_user)
) -> UserContext:
    """
    Get current user ensuring they are an admin
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        UserContext for admin user
        
    Raises:
        HTTPException: If user is not an admin
    """
    # Check if user is admin type OR firm personnel with admin role
    is_admin = (
        current_user.user_type == "admin" or 
        (current_user.user_type == "firm_personnel" and current_user.role == "admin")
    )
    
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to administrators"
        )
    
    return current_user


async def require_firm_admin(
    current_user: UserContext = Depends(get_current_user)
) -> UserContext:
    """
    Get current user ensuring they are a firm admin
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        UserContext for firm admin user
        
    Raises:
        HTTPException: If user is not a firm admin
    """
    # Check if user is firm personnel with firm_admin role
    is_firm_admin = (
        current_user.user_type == "firm_personnel" and 
        current_user.role == "firm_admin"
    )
    
    if not is_firm_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to firm administrators"
        )
    
    return current_user


async def require_super_admin(
    current_user: UserContext = Depends(get_current_user)
) -> UserContext:
    """
    Get current user ensuring they are a super admin
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        UserContext for super admin user
        
    Raises:
        HTTPException: If user is not a super admin
    """
    # Check if user is system admin or super_admin role
    is_super_admin = (
        current_user.user_type == "admin" or 
        (current_user.user_type == "firm_personnel" and current_user.role == "super_admin")
    )
    
    if not is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to super administrators"
        )
    
    return current_user


async def require_admin_or_super_admin(
    current_user: UserContext = Depends(get_current_user)
) -> UserContext:
    """
    Get current user ensuring they are admin or super admin
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        UserContext for admin/super admin user
        
    Raises:
        HTTPException: If user is not admin or super admin
    """
    # Check if user is admin, super_admin, or system admin
    is_admin_or_super = (
        current_user.user_type == "admin" or 
        (current_user.user_type == "firm_personnel" and 
         current_user.role in ["admin", "super_admin"])
    )
    
    if not is_admin_or_super:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to administrators"
        )
    
    return current_user


def can_view_all_personnel(user: UserContext) -> bool:
    """
    Check if user can view all personnel across firms
    
    Args:
        user: User context
        
    Returns:
        True if user can view all personnel
    """
    return (
        user.user_type == "admin" or 
        (user.user_type == "firm_personnel" and 
         user.role in ["admin", "super_admin"])
    )


def can_manage_personnel(user: UserContext, target_firm_id: UUID = None) -> bool:
    """
    Check if user can perform CRU operations on personnel
    
    Args:
        user: User context
        target_firm_id: Target firm ID for the operation
        
    Returns:
        True if user can manage personnel
    """
    # Only firm_admin can perform CRU operations
    if user.user_type == "firm_personnel" and user.role == "firm_admin":
        # If target_firm_id is specified, check if it matches user's firm
        if target_firm_id and user.firm_id:
            return user.firm_id == target_firm_id
        return True
    
    return False


def can_lock_unlock_personnel(user: UserContext) -> bool:
    """
    Check if user can lock/unlock personnel
    
    Args:
        user: User context
        
    Returns:
        True if user can lock/unlock personnel
    """
    return (
        user.user_type == "admin" or 
        (user.user_type == "firm_personnel" and 
         user.role in ["admin", "super_admin"])
    )


def get_personnel_filter_for_user(user: UserContext) -> dict:
    """
    Get personnel filter based on user permissions
    
    Args:
        user: User context
        
    Returns:
        Dictionary with filter parameters
    """
    if can_view_all_personnel(user):
        # Admin and super_admin can view all personnel
        return {"firm_id_filter": None}
    elif user.user_type == "firm_personnel" and user.firm_id:
        # Regular firm personnel can only view their firm's personnel
        return {"firm_id_filter": user.firm_id}
    else:
        # No access
        return {"firm_id_filter": "NO_ACCESS"}


def require_permission(permission: str):
    """
    Dependency factory to require specific permission
    
    Args:
        permission: Required permission string
        
    Returns:
        Dependency function that checks permission
    """
    async def check_permission(
        current_user: UserContext = Depends(get_current_user)
    ) -> UserContext:
        if not current_user.has_permission(permission):
            logger.warning(
                "permission_denied",
                user_id=str(current_user.user_id),
                required_permission=permission,
                user_permissions=current_user.permissions
            )
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {permission}"
            )
        
        return current_user
    
    return check_permission


def require_role(role: str):
    """
    Dependency factory to require specific role (for firm personnel)
    
    Args:
        role: Required role string
        
    Returns:
        Dependency function that checks role
    """
    async def check_role(
        current_user: UserContext = Depends(get_current_firm_personnel)
    ) -> UserContext:
        if current_user.role != role:
            logger.warning(
                "role_access_denied",
                user_id=str(current_user.user_id),
                required_role=role,
                user_role=current_user.role
            )
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role required: {role}"
            )
        
        return current_user
    
    return check_role


# Common permission dependencies
require_emergency_request = require_permission("emergency:request")
require_subscription_purchase = require_permission("subscription:purchase")
require_group_manage = require_permission("group:manage")
require_request_view = require_permission("request:view")
require_request_accept = require_permission("request:accept")
require_team_manage = require_permission("team:manage")

# Common role dependencies
require_field_agent = require_role("field_agent")
require_team_leader = require_role("team_leader")
require_office_staff = require_role("office_staff")


class OptionalAuth:
    """Optional authentication dependency"""
    
    def __init__(self):
        pass
    
    async def __call__(
        self,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
    ) -> Optional[UserContext]:
        """
        Get current user if authenticated, None otherwise
        
        Args:
            credentials: HTTP Bearer credentials from request
            
        Returns:
            UserContext if authenticated, None otherwise
        """
        if not credentials:
            return None
        
        try:
            return await auth_service.validate_token(credentials.credentials)
        except (AuthenticationError, TokenExpiredError):
            return None


# Optional authentication instance
optional_auth = OptionalAuth()


async def get_current_user_from_token(token: str) -> UserContext:
    """
    Get current authenticated user from JWT token string
    
    Args:
        token: JWT token string
        
    Returns:
        UserContext object for authenticated user
        
    Raises:
        AuthenticationError: If authentication fails
        TokenExpiredError: If token has expired
    """
    try:
        user_context = await auth_service.validate_token(token)
        
        logger.info(
            "user_authenticated_from_token",
            user_id=str(user_context.user_id),
            user_type=user_context.user_type,
            email=user_context.email
        )
        
        return user_context
        
    except (TokenExpiredError, AuthenticationError) as e:
        logger.warning(
            "token_validation_failed",
            error=str(e)
        )
        raise


def generate_secure_password(length: int = 12) -> str:
    """
    Generate a secure random password
    
    Args:
        length: Password length (default: 12)
        
    Returns:
        Randomly generated secure password
    """
    if length < 8:
        length = 8
    
    # Define character sets
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    special_chars = "!@#$%^&*"
    
    # Ensure at least one character from each set
    password = [
        secrets.choice(lowercase),
        secrets.choice(uppercase),
        secrets.choice(digits),
        secrets.choice(special_chars)
    ]
    
    # Fill the rest with random characters from all sets
    all_chars = lowercase + uppercase + digits + special_chars
    for _ in range(length - 4):
        password.append(secrets.choice(all_chars))
    
    # Shuffle the password list to avoid predictable patterns
    secrets.SystemRandom().shuffle(password)
    
    return ''.join(password)