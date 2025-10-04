"""
Authentication and JWT token management services
"""

import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple
from uuid import UUID, uuid4
import hashlib
import secrets
import structlog
from passlib.context import CryptContext

from app.core.config import settings
from app.core.redis import cache
from app.core.exceptions import APIError, ErrorCodes
from app.models.user import RegisteredUser
from app.models.security_firm import FirmPersonnel, SecurityFirm, Team
from app.services.account_security import AccountSecurityService
from app.services.otp_delivery import OTPDeliveryService
from sqlalchemy import select
from sqlalchemy.orm import selectinload

logger = structlog.get_logger()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthenticationError(APIError):
    """Authentication error"""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(ErrorCodes.EXPIRED_TOKEN, message)


class TokenExpiredError(APIError):
    """Token expired error"""

    def __init__(self, message: str = "Token has expired"):
        super().__init__(ErrorCodes.EXPIRED_TOKEN, message)


class InsufficientPermissionsError(APIError):
    """Insufficient permissions error"""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(ErrorCodes.INSUFFICIENT_PERMISSIONS, message)


class TokenPair:
    """Token pair containing access and refresh tokens"""

    def __init__(self, access_token: str, refresh_token: str, expires_in: int):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_in = expires_in
        self.token_type = "Bearer"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_type": self.token_type,
            "expires_in": self.expires_in,
        }


class UserContext:
    """User context from validated token"""

    def __init__(
        self,
        user_id: UUID,
        user_type: str,
        email: str,
        permissions: list = None,
        firm_id: Optional[UUID] = None,
        role: Optional[str] = None,
    ):
        self.user_id = user_id
        self.user_type = user_type  # 'registered_user' or 'firm_personnel'
        self.email = email
        self.permissions = permissions or []
        self.firm_id = firm_id
        self.role = role

    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission"""
        return permission in self.permissions

    def is_firm_personnel(self) -> bool:
        """Check if user is firm personnel"""
        return self.user_type == "firm_personnel"

    def is_registered_user(self) -> bool:
        """Check if user is registered user"""
        return self.user_type == "registered_user"

    def is_admin(self) -> bool:
        """Check if user is admin"""
        return self.user_type == "admin"


class JWTTokenService:
    """JWT token management service"""

    def __init__(self):
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        self.access_token_expire_minutes = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS

    def create_access_token(
        self,
        user_id: UUID,
        user_type: str,
        email: str,
        permissions: list = None,
        firm_id: Optional[UUID] = None,
        role: Optional[str] = None,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """
        Create JWT access token

        Args:
            user_id: User identifier
            user_type: Type of user ('registered_user' or 'firm_personnel')
            email: User email
            permissions: List of user permissions
            firm_id: Firm ID for personnel
            role: User role for personnel
            expires_delta: Custom expiration time

        Returns:
            JWT access token string
        """
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=self.access_token_expire_minutes
            )

        # Create token payload
        payload = {
            "sub": str(user_id),
            "user_type": user_type,
            "email": email,
            "permissions": permissions or [],
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "jti": str(uuid4()),  # JWT ID for revocation
            "token_type": "access",
        }

        # Add firm-specific claims for personnel
        if firm_id:
            payload["firm_id"] = str(firm_id)
        if role:
            payload["role"] = role

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(
        self, user_id: UUID, user_type: str, expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create JWT refresh token

        Args:
            user_id: User identifier
            user_type: Type of user
            expires_delta: Custom expiration time

        Returns:
            JWT refresh token string
        """
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(days=self.refresh_token_expire_days)

        payload = {
            "sub": str(user_id),
            "user_type": user_type,
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "jti": str(uuid4()),
            "token_type": "refresh",
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_token_pair(
        self,
        user_id: UUID,
        user_type: str,
        email: str,
        permissions: list = None,
        firm_id: Optional[UUID] = None,
        role: Optional[str] = None,
    ) -> TokenPair:
        """
        Create access and refresh token pair

        Returns:
            TokenPair object with both tokens
        """
        access_token = self.create_access_token(
            user_id, user_type, email, permissions, firm_id, role
        )
        refresh_token = self.create_refresh_token(user_id, user_type)

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.access_token_expire_minutes * 60,
        )

    async def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify and decode JWT token

        Args:
            token: JWT token string

        Returns:
            Decoded token payload

        Raises:
            AuthenticationError: If token is invalid
            TokenExpiredError: If token is expired
        """
        try:
            payload = jwt.decode(
                token, self.secret_key, algorithms=[self.algorithm], options={"verify_exp": True}
            )

            # Check if token is blacklisted
            jti = payload.get("jti")
            if jti and await self.is_token_blacklisted(jti):
                raise AuthenticationError("Token has been revoked")

            return payload

        except jwt.ExpiredSignatureError:
            raise TokenExpiredError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(f"Invalid token: {str(e)}")

    async def refresh_access_token(self, refresh_token: str, db=None, auth_service=None) -> TokenPair:
        """
        Create new access token using refresh token

        Args:
            refresh_token: Valid refresh token
            db: Database session
            auth_service: Auth service for getting permissions

        Returns:
            New token pair

        Raises:
            AuthenticationError: If refresh token is invalid
        """
        try:
            # Verify refresh token
            payload = await self.verify_token(refresh_token)

            if payload.get("token_type") != "refresh":
                raise AuthenticationError("Invalid token type for refresh")

            user_id = UUID(payload["sub"])
            user_type = payload["user_type"]

            # Fetch user details from database to get current role, permissions, etc.
            email = ""
            permissions = []
            firm_id = None
            role = None

            if db:
                if user_type == "firm_personnel":
                    # Query firm personnel to get current data
                    query = select(FirmPersonnel).where(FirmPersonnel.id == user_id)
                    result = await db.execute(query)
                    user = result.scalar_one_or_none()
                    
                    if user and user.is_active:
                        email = user.email
                        role = user.role
                        firm_id = user.firm_id
                        # Get permissions from auth service if available
                        if auth_service:
                            permissions = auth_service._get_user_permissions(user_type, role)
                    else:
                        raise AuthenticationError("User not found or inactive")
                        
                elif user_type == "registered_user":
                    # Query registered user to get current data
                    query = select(RegisteredUser).where(RegisteredUser.id == user_id)
                    result = await db.execute(query)
                    user = result.scalar_one_or_none()
                    
                    if user and not user.is_suspended:
                        email = user.email
                        role = user.role
                        # Get permissions from auth service if available
                        if auth_service:
                            permissions = auth_service._get_user_permissions(user_type, role)
                    else:
                        raise AuthenticationError("User not found or suspended")

            # Revoke old refresh token
            await self.revoke_token(refresh_token)

            # Create new token pair with current user data
            return self.create_token_pair(
                user_id=user_id,
                user_type=user_type,
                email=email,
                permissions=permissions,
                firm_id=firm_id,
                role=role,
            )

        except (ValueError, KeyError) as e:
            raise AuthenticationError(f"Invalid refresh token format: {str(e)}")

    async def revoke_token(self, token: str) -> bool:
        """
        Revoke (blacklist) a token

        Args:
            token: JWT token to revoke

        Returns:
            True if successfully revoked
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False},  # Don't verify expiration for revocation
            )

            jti = payload.get("jti")
            if not jti:
                return False

            # Calculate remaining TTL
            exp = payload.get("exp")
            if exp:
                exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
                ttl = int((exp_datetime - datetime.now(timezone.utc)).total_seconds())
                if ttl > 0:
                    # Store in blacklist with TTL
                    await cache.set(f"blacklist:{jti}", "revoked", expire=ttl)

            logger.info("Token revoked", jti=jti)
            return True

        except jwt.InvalidTokenError:
            return False

    async def is_token_blacklisted(self, jti: str) -> bool:
        """
        Check if token is blacklisted

        Args:
            jti: JWT ID to check

        Returns:
            True if token is blacklisted
        """
        return await cache.exists(f"blacklist:{jti}")

    async def extract_user_context(self, token: str) -> UserContext:
        """
        Extract user context from validated token

        Args:
            token: Validated JWT token

        Returns:
            UserContext object
        """
        payload = await self.verify_token(token)

        return UserContext(
            user_id=UUID(payload["sub"]),
            user_type=payload["user_type"],
            email=payload.get("email", ""),
            permissions=payload.get("permissions", []),
            firm_id=UUID(payload["firm_id"]) if payload.get("firm_id") else None,
            role=payload.get("role"),
        )


class PasswordService:
    """Password hashing and verification service"""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt"""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """Generate a cryptographically secure random token"""
        return secrets.token_urlsafe(length)


class AuthService:
    """Main authentication service"""

    def __init__(self):
        self.jwt_service = JWTTokenService()
        self.password_service = PasswordService()
        self.account_security = AccountSecurityService()
        self.otp_delivery = OTPDeliveryService()

    async def authenticate_user(
        self, email: str, password: str, user_type: str = "registered_user", db=None
    ) -> TokenPair:
        """
        Authenticate user and return token pair

        Args:
            email: User email
            password: User password
            user_type: Type of user to authenticate
            db: Database session

        Returns:
            TokenPair with access and refresh tokens

        Raises:
            AuthenticationError: If authentication fails
        """
        # Check if account is locked
        if await self.account_security.is_account_locked(email, db):
            raise AuthenticationError("Account is locked. Please use OTP to unlock.")

        # This would typically involve database lookup
        # For now, we'll create a mock implementation

        # Verify password (would be from database)
        # stored_hash = get_user_password_hash(email, user_type)
        # if not self.password_service.verify_password(password, stored_hash):
        #     # Record failed login attempt
        #     await self.account_security.record_failed_login(email, db)
        #     raise AuthenticationError("Invalid credentials")

        # Clear failed attempts on successful login
        await self.account_security.clear_failed_attempts(email)

        # Create token pair
        user_id = uuid4()  # Would be from database
        permissions = self._get_user_permissions(user_type)

        return self.jwt_service.create_token_pair(
            user_id=user_id, user_type=user_type, email=email, permissions=permissions
        )

    async def authenticate_user_detailed(
        self, email: str, password: str, user_type: str = "firm_personnel", db=None
    ) -> Dict[str, Any]:
        """
        Authenticate user and return detailed user information with tokens

        Args:
            email: User email
            password: User password
            user_type: Type of user to authenticate
            db: Database session

        Returns:
            Dict with detailed user information and tokens

        Raises:
            AuthenticationError: If authentication fails
        """
        # Check if account is locked
        if await self.account_security.is_account_locked(email, db):
            raise AuthenticationError("Account is locked. Please use OTP to unlock.")

        try:
            if user_type == "firm_personnel":
                # Query firm personnel with related data
                query = (
                    select(FirmPersonnel)
                    .options(selectinload(FirmPersonnel.firm), selectinload(FirmPersonnel.team))
                    .where(FirmPersonnel.email == email)
                )

                result = await db.execute(query)
                user = result.scalar_one_or_none()

                if not user:
                    await self.account_security.record_failed_login(email, db)
                    raise AuthenticationError("Invalid credentials")

                # Verify password
                if not self.password_service.verify_password(password, user.password_hash):
                    await self.account_security.record_failed_login(email, db)
                    raise AuthenticationError("Invalid credentials")

                # Check if user is active
                if not user.is_active:
                    raise AuthenticationError("Account is inactive")

                # Clear failed attempts on successful login
                await self.account_security.clear_failed_attempts(email)

                # Get permissions based on role
                permissions = self._get_user_permissions(user_type, user.role)

                # Create token pair
                token_pair = self.jwt_service.create_token_pair(
                    user_id=user.id,
                    user_type=user_type,
                    email=user.email,
                    permissions=permissions,
                    firm_id=user.firm_id,
                    role=user.role,
                )

                # Calculate token expiration times
                access_expire_at = datetime.now(timezone.utc) + timedelta(
                    minutes=self.jwt_service.access_token_expire_minutes
                )
                refresh_expire_at = datetime.now(timezone.utc) + timedelta(
                    days=self.jwt_service.refresh_token_expire_days
                )

                # Build detailed response
                response = {
                    # Token information
                    "access_token": token_pair.access_token,
                    "refresh_token": token_pair.refresh_token,
                    "token_type": token_pair.token_type,
                    "expires_in": token_pair.expires_in,
                    "access_token_expire_at": access_expire_at.isoformat(),
                    "refresh_token_expire_at": refresh_expire_at.isoformat(),
                    # User information
                    "id": str(user.id),
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email,
                    "phone": user.phone,
                    "role": user.role,
                    "is_active": user.is_active,
                    "created_at": user.created_at.isoformat(),
                    "updated_at": user.updated_at.isoformat(),
                    # Team information (if user belongs to a team)
                    "team_id": str(user.team.id) if user.team else None,
                    "team_name": user.team.name if user.team else None,
                    "team_is_active": user.team.is_active if user.team else None,
                    # Firm information
                    "firm_id": str(user.firm.id),
                    "firm_name": user.firm.name,
                    "firm_email": user.firm.email,
                    "firm_phone": user.firm.phone,
                    "firm_verification_status": user.firm.verification_status,
                    "firm_credit_balance": user.firm.credit_balance,
                }

                return response

            elif user_type == "registered_user":
                # Query registered user with firm memberships
                from app.models.user import RegisteredUser
                from app.models.security_firm import FirmUser, SecurityFirm

                query = (
                    select(RegisteredUser)
                    .options(
                        selectinload(RegisteredUser.firm_memberships).selectinload(FirmUser.firm)
                    )
                    .where(RegisteredUser.email == email)
                )

                result = await db.execute(query)
                user = result.scalar_one_or_none()

                if not user:
                    await self.account_security.record_failed_login(email, db)
                    raise AuthenticationError("Invalid credentials")

                # Check if user has a password hash
                if not user.password_hash:
                    raise AuthenticationError(
                        "Account not properly configured. Please contact support."
                    )

                # Verify password
                if not self.password_service.verify_password(password, user.password_hash):
                    await self.account_security.record_failed_login(email, db)
                    raise AuthenticationError("Invalid credentials")

                # Check if user is verified
                if not user.is_verified:
                    raise AuthenticationError(
                        "Account not verified. Please verify your email address."
                    )

                # Check if user is suspended
                if user.is_suspended:
                    raise AuthenticationError("Account is suspended")

                # Clear failed attempts on successful login
                await self.account_security.clear_failed_attempts(email)

                # Get permissions based on user type
                permissions = self._get_user_permissions(user_type)

                # Check for active firm membership
                active_firm_membership = None
                for membership in user.firm_memberships:
                    if membership.status == "active":
                        active_firm_membership = membership
                        break

                # Create token pair
                token_pair = self.jwt_service.create_token_pair(
                    user_id=user.id,
                    user_type=user_type,
                    email=user.email,
                    permissions=permissions,
                    firm_id=active_firm_membership.firm_id if active_firm_membership else None,
                    role=active_firm_membership.role if active_firm_membership else None,
                )

                # Calculate token expiration times
                access_expire_at = datetime.now(timezone.utc) + timedelta(
                    minutes=self.jwt_service.access_token_expire_minutes
                )
                refresh_expire_at = datetime.now(timezone.utc) + timedelta(
                    days=self.jwt_service.refresh_token_expire_days
                )

                # Build detailed response for registered user
                response = {
                    # Token information
                    "access_token": token_pair.access_token,
                    "refresh_token": token_pair.refresh_token,
                    "token_type": token_pair.token_type,
                    "expires_in": token_pair.expires_in,
                    "access_token_expire_at": access_expire_at.isoformat(),
                    "refresh_token_expire_at": refresh_expire_at.isoformat(),
                    # User information
                    "id": str(user.id),
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email,
                    "phone": user.phone,
                    "role": active_firm_membership.role if active_firm_membership else "user",
                    "is_active": not user.is_suspended,
                    "created_at": user.created_at.isoformat(),
                    "updated_at": user.updated_at.isoformat(),
                    # No team information for registered users
                    "team_id": None,
                    "team_name": None,
                    "team_is_active": None,
                    # Firm information (if user has active firm membership)
                    "firm_id": (
                        str(active_firm_membership.firm.id) if active_firm_membership else None
                    ),
                    "firm_name": (
                        active_firm_membership.firm.name if active_firm_membership else None
                    ),
                    "firm_email": (
                        active_firm_membership.firm.email if active_firm_membership else None
                    ),
                    "firm_phone": (
                        active_firm_membership.firm.phone if active_firm_membership else None
                    ),
                    "firm_verification_status": (
                        active_firm_membership.firm.verification_status
                        if active_firm_membership
                        else None
                    ),
                    "firm_credit_balance": (
                        active_firm_membership.firm.credit_balance if active_firm_membership else 0
                    ),
                }

                return response

            else:
                raise AuthenticationError("User type not supported for detailed authentication")

        except AuthenticationError:
            raise
        except Exception as e:
            logger.error("detailed_authentication_error", email=email, error=str(e), exc_info=True)
            raise AuthenticationError("Authentication failed")

    async def refresh_token(self, refresh_token: str, db=None) -> TokenPair:
        """
        Refresh access token using refresh token

        Args:
            refresh_token: Valid refresh token
            db: Database session

        Returns:
            New token pair
        """
        return await self.jwt_service.refresh_access_token(refresh_token, db, self)

    async def revoke_token(self, token: str) -> bool:
        """
        Revoke a token

        Args:
            token: Token to revoke

        Returns:
            True if successfully revoked
        """
        return await self.jwt_service.revoke_token(token)

    async def validate_token(self, token: str) -> UserContext:
        """
        Validate token and return user context

        Args:
            token: JWT token to validate

        Returns:
            UserContext object

        Raises:
            AuthenticationError: If token is invalid
        """
        return await self.jwt_service.extract_user_context(token)

    async def request_account_unlock_otp(
        self, identifier: str, delivery_method: str = "email", db=None
    ) -> Dict[str, Any]:
        """
        Generate and send OTP for account unlock

        Args:
            identifier: Email or mobile number
            delivery_method: 'email' or 'sms'
            db: Database session

        Returns:
            Dict with success status and message
        """
        # Check if account is actually locked
        if not await self.account_security.is_account_locked(identifier, db):
            raise AuthenticationError("Account is not locked")

        # Generate OTP
        otp = await self.account_security.generate_otp(identifier)

        # Send OTP
        success = await self.otp_delivery.send_otp(identifier, otp, delivery_method)

        if success:
            return {
                "success": True,
                "message": f"OTP sent via {delivery_method}",
                "expires_in_minutes": 10,
            }
        else:
            return {"success": False, "message": f"Failed to send OTP via {delivery_method}"}

    async def verify_unlock_otp(self, identifier: str, otp: str, db=None) -> Dict[str, Any]:
        """
        Verify OTP and unlock account

        Args:
            identifier: Email or mobile number
            otp: OTP code to verify
            db: Database session

        Returns:
            Dict with verification result
        """
        success = await self.account_security.verify_otp(identifier, otp, db)

        if success:
            return {"success": True, "message": "Account unlocked successfully"}
        else:
            return {"success": False, "message": "Invalid or expired OTP"}

    async def get_account_status(self, identifier: str, db=None) -> Dict[str, Any]:
        """
        Get account lock status and failed attempts

        Args:
            identifier: Email or mobile number
            db: Database session

        Returns:
            Dict with account status information
        """
        is_locked = await self.account_security.is_account_locked(identifier, db)
        failed_attempts = await self.account_security.get_failed_attempts_count(identifier)

        return {
            "is_locked": is_locked,
            "failed_attempts": failed_attempts,
            "max_attempts": self.account_security.max_failed_attempts,
            "remaining_attempts": max(
                0, self.account_security.max_failed_attempts - failed_attempts
            ),
        }

    async def get_user_detailed_info(
        self, user_id: UUID, user_type: str, db=None
    ) -> Dict[str, Any]:
        """
        Get detailed user information (same as login response but without tokens)

        Args:
            user_id: User identifier
            user_type: Type of user
            db: Database session

        Returns:
            Dict with detailed user information

        Raises:
            AuthenticationError: If user not found
        """
        try:
            if user_type == "firm_personnel":
                # Query firm personnel with related data
                query = (
                    select(FirmPersonnel)
                    .options(selectinload(FirmPersonnel.firm), selectinload(FirmPersonnel.team))
                    .where(FirmPersonnel.id == user_id)
                )

                result = await db.execute(query)
                user = result.scalar_one_or_none()

                if not user:
                    raise AuthenticationError("User not found")

                # Build detailed response (same as login but without tokens)
                response = {
                    # User information
                    "id": str(user.id),
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email,
                    "phone": user.phone,
                    "role": user.role,
                    "is_active": user.is_active,
                    "created_at": user.created_at.isoformat(),
                    "updated_at": user.updated_at.isoformat(),
                    # Team information (if user belongs to a team)
                    "team_id": str(user.team.id) if user.team else None,
                    "team_name": user.team.name if user.team else None,
                    "team_is_active": user.team.is_active if user.team else None,
                    # Firm information
                    "firm_id": str(user.firm.id),
                    "firm_name": user.firm.name,
                    "firm_email": user.firm.email,
                    "firm_phone": user.firm.phone,
                    "firm_verification_status": user.firm.verification_status,
                    "firm_credit_balance": user.firm.credit_balance,
                }

                return response

            elif user_type == "registered_user":
                # Query registered user
                from app.models.user import RegisteredUser

                query = select(RegisteredUser).where(RegisteredUser.id == user_id)

                result = await db.execute(query)
                user = result.scalar_one_or_none()

                if not user:
                    raise AuthenticationError("User not found")

                # Build detailed response for registered user (same as login but without tokens)
                response = {
                    # User information
                    "id": str(user.id),
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email,
                    "phone": user.phone,
                    "role": "user",  # Default role for registered users
                    "is_active": not user.is_suspended,
                    "created_at": user.created_at.isoformat(),
                    "updated_at": user.updated_at.isoformat(),
                    # No team information for registered users
                    "team_id": None,
                    "team_name": None,
                    "team_is_active": None,
                    # No firm information for registered users
                    "firm_id": None,
                    "firm_name": None,
                    "firm_email": None,
                    "firm_phone": None,
                    "firm_verification_status": None,
                    "firm_credit_balance": 0,
                }

                return response

            else:
                raise AuthenticationError("User type not supported for detailed info")

        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(
                "get_user_detailed_info_error", user_id=str(user_id), error=str(e), exc_info=True
            )
            raise AuthenticationError("Failed to get user information")

    async def request_password_reset_otp(
        self, email: str, user_type: str = "firm_personnel", db=None
    ) -> Dict[str, Any]:
        """
        Generate and send OTP for password reset

        Args:
            email: User email address
            user_type: Type of user ('registered_user' or 'firm_personnel')
            db: Database session

        Returns:
            Dict with success status and message
        """
        try:
            # Check if user exists
            user_exists = await self._check_user_exists(email, user_type, db)

            if not user_exists:
                # For security, don't reveal if email exists or not
                return {
                    "success": True,
                    "message": "If the email exists in our system, a password reset code has been sent",
                    "expires_in_minutes": 10,
                }

            # Generate OTP for password reset
            otp = await self.account_security.generate_password_reset_otp(email)

            # Send OTP via email
            success = await self.otp_delivery.send_password_reset_email(email, otp)

            if success:
                return {
                    "success": True,
                    "message": "Password reset code sent to your email",
                    "expires_in_minutes": 10,
                }
            else:
                return {"success": False, "message": "Failed to send password reset code"}

        except Exception as e:
            logger.error("password_reset_otp_error", email=email, error=str(e), exc_info=True)
            return {"success": False, "message": "Failed to process password reset request"}

    async def verify_password_reset_otp(
        self, email: str, otp: str, new_password: str, user_type: str = "firm_personnel", db=None
    ) -> Dict[str, Any]:
        """
        Verify OTP and reset password

        Args:
            email: User email address
            otp: OTP code to verify
            new_password: New password to set
            user_type: Type of user ('registered_user' or 'firm_personnel')
            db: Database session

        Returns:
            Dict with verification result
        """
        try:
            # Verify OTP
            otp_valid = await self.account_security.verify_password_reset_otp(email, otp)

            if not otp_valid:
                return {"success": False, "message": "Invalid or expired password reset code"}

            # Update user password
            password_updated = await self._update_user_password(email, new_password, user_type, db)

            if password_updated:
                # Clear any failed login attempts
                await self.account_security.clear_failed_attempts(email)

                # Invalidate all existing tokens for this user (optional security measure)
                await self._invalidate_user_tokens(email, user_type)

                return {"success": True, "message": "Password reset successfully"}
            else:
                return {"success": False, "message": "Failed to update password"}

        except Exception as e:
            logger.error("password_reset_verify_error", email=email, error=str(e), exc_info=True)
            return {"success": False, "message": "Failed to reset password"}

    async def _check_user_exists(self, email: str, user_type: str, db) -> bool:
        """Check if user exists in the database"""
        try:
            if user_type == "firm_personnel":
                query = select(FirmPersonnel).where(FirmPersonnel.email == email)
                result = await db.execute(query)
                user = result.scalar_one_or_none()
                return user is not None
            elif user_type == "registered_user":
                query = select(RegisteredUser).where(RegisteredUser.email == email)
                result = await db.execute(query)
                user = result.scalar_one_or_none()
                return user is not None

            return False

        except Exception as e:
            logger.error("check_user_exists_error", email=email, error=str(e), exc_info=True)
            return False

    async def _update_user_password(
        self, email: str, new_password: str, user_type: str, db
    ) -> bool:
        """Update user password in the database"""
        try:
            # Hash the new password
            password_hash = self.password_service.hash_password(new_password)

            if user_type == "firm_personnel":
                query = select(FirmPersonnel).where(FirmPersonnel.email == email)
                result = await db.execute(query)
                user = result.scalar_one_or_none()

                if user:
                    user.password_hash = password_hash
                    user.updated_at = datetime.now(timezone.utc)
                    await db.commit()
                    return True

            elif user_type == "registered_user":
                query = select(RegisteredUser).where(RegisteredUser.email == email)
                result = await db.execute(query)
                user = result.scalar_one_or_none()

                if user:
                    user.password_hash = password_hash
                    user.updated_at = datetime.now(timezone.utc)
                    await db.commit()
                    return True

            return False

        except Exception as e:
            logger.error("update_user_password_error", email=email, error=str(e), exc_info=True)
            await db.rollback()
            return False

    async def _invalidate_user_tokens(self, email: str, user_type: str):
        """Invalidate all existing tokens for a user (optional security measure)"""
        try:
            # This would typically involve adding all user's tokens to blacklist
            # For now, we'll just log the action
            logger.info("user_tokens_invalidated", email=email, user_type=user_type)

        except Exception as e:
            logger.error("invalidate_user_tokens_error", email=email, error=str(e), exc_info=True)

    def _get_user_permissions(self, user_type: str, role: str = None) -> list:
        """Get default permissions for user type and role"""
        if user_type == "registered_user":
            return ["emergency:request", "subscription:purchase", "group:manage"]
        elif user_type == "firm_personnel":
            base_permissions = ["request:view", "request:accept"]

            if role == "admin":
                return base_permissions + [
                    "admin:all",
                    "firm:manage",
                    "user:manage",
                    "system:manage",
                    "team:manage",
                    "personnel:manage",
                ]
            elif role == "team_leader":
                return base_permissions + ["team:manage", "team:view", "personnel:view"]
            elif role == "field_agent":
                return base_permissions + ["request:respond", "location:update"]
            elif role == "office_staff":
                return base_permissions + ["request:dispatch", "report:generate"]
            else:
                return base_permissions

        return []


# Global service instances
auth_service = AuthService()
jwt_service = JWTTokenService()
password_service = PasswordService()
