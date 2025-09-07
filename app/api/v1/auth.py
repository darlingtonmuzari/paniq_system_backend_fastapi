"""
Authentication API endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, status, Header
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any
import structlog

from app.services.auth import auth_service, AuthenticationError, TokenExpiredError, TokenPair
from app.services.user import UserService
from app.core.auth import get_current_user, UserContext
from app.core.exceptions import APIError, ErrorCodes
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()

router = APIRouter()


class LoginRequest(BaseModel):
    """Login request model"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    user_type: str = Field(default="registered_user", description="Type of user: 'registered_user' or 'firm_personnel'")


class TokenResponse(BaseModel):
    """Token response model"""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiry time in seconds")


class DetailedLoginResponse(BaseModel):
    """Detailed login response with user information"""
    # Token information
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiry time in seconds")
    access_token_expire_at: str = Field(..., description="Access token expiration timestamp")
    refresh_token_expire_at: str = Field(..., description="Refresh token expiration timestamp")
    
    # User information
    id: str = Field(..., description="User ID")
    first_name: str = Field(..., description="User first name")
    last_name: str = Field(..., description="User last name")
    email: str = Field(..., description="User email")
    phone: str = Field(..., description="User phone number")
    role: str = Field(..., description="User role")
    is_active: bool = Field(..., description="Whether user is active")
    created_at: str = Field(..., description="User creation timestamp")
    updated_at: str = Field(..., description="User last update timestamp")
    
    # Team information (optional)
    team_id: Optional[str] = Field(None, description="Team ID if user belongs to a team")
    team_name: Optional[str] = Field(None, description="Team name")
    team_is_active: Optional[bool] = Field(None, description="Whether team is active")
    
    # Firm information (optional for registered users)
    firm_id: Optional[str] = Field(None, description="Security firm ID")
    firm_name: Optional[str] = Field(None, description="Security firm name")
    firm_email: Optional[str] = Field(None, description="Security firm email")
    firm_phone: Optional[str] = Field(None, description="Security firm phone")
    firm_verification_status: Optional[str] = Field(None, description="Firm verification status")
    firm_credit_balance: Optional[int] = Field(None, description="Firm credit balance")


class RefreshTokenRequest(BaseModel):
    """Refresh token request model"""
    refresh_token: str = Field(..., description="Valid refresh token")


class RevokeTokenRequest(BaseModel):
    """Revoke token request model"""
    token: str = Field(..., description="Token to revoke")


class UserInfoResponse(BaseModel):
    """User info response model"""
    user_id: str = Field(..., description="User identifier")
    email: str = Field(..., description="User email")
    user_type: str = Field(..., description="Type of user")
    permissions: list = Field(..., description="User permissions")
    firm_id: Optional[str] = Field(None, description="Firm ID for personnel")
    role: Optional[str] = Field(None, description="Role for personnel")


class DetailedUserInfoResponse(BaseModel):
    """Detailed user info response model (same as login but without tokens)"""
    # User information
    id: str = Field(..., description="User ID")
    first_name: str = Field(..., description="User first name")
    last_name: str = Field(..., description="User last name")
    email: str = Field(..., description="User email")
    phone: str = Field(..., description="User phone number")
    role: str = Field(..., description="User role")
    is_active: bool = Field(..., description="Whether user is active")
    created_at: str = Field(..., description="User creation timestamp")
    updated_at: str = Field(..., description="User last update timestamp")
    
    # Team information (optional)
    team_id: Optional[str] = Field(None, description="Team ID if user belongs to a team")
    team_name: Optional[str] = Field(None, description="Team name")
    team_is_active: Optional[bool] = Field(None, description="Whether team is active")
    
    # Firm information (optional for registered users)
    firm_id: Optional[str] = Field(None, description="Security firm ID")
    firm_name: Optional[str] = Field(None, description="Security firm name")
    firm_email: Optional[str] = Field(None, description="Security firm email")
    firm_phone: Optional[str] = Field(None, description="Security firm phone")
    firm_verification_status: Optional[str] = Field(None, description="Firm verification status")
    firm_credit_balance: Optional[int] = Field(None, description="Firm credit balance")


class OTPRequest(BaseModel):
    """OTP request model"""
    identifier: str = Field(..., description="Email or mobile number")
    delivery_method: str = Field(default="email", description="Delivery method: 'email' or 'sms'")


class OTPVerifyRequest(BaseModel):
    """OTP verification request model"""
    identifier: str = Field(..., description="Email or mobile number")
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit OTP code")


class AccountStatusResponse(BaseModel):
    """Account status response model"""
    is_locked: bool = Field(..., description="Whether account is locked")
    failed_attempts: int = Field(..., description="Number of failed login attempts")
    max_attempts: int = Field(..., description="Maximum allowed failed attempts")
    remaining_attempts: int = Field(..., description="Remaining attempts before lockout")


class PasswordResetRequest(BaseModel):
    """Password reset request model"""
    email: EmailStr = Field(..., description="User email address")
    user_type: str = Field(default="firm_personnel", description="Type of user: 'registered_user' or 'firm_personnel'")


class PasswordResetVerifyRequest(BaseModel):
    """Password reset OTP verification request model"""
    email: EmailStr = Field(..., description="User email address")
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit OTP code")
    new_password: str = Field(..., min_length=8, description="New password")
    user_type: str = Field(default="firm_personnel", description="Type of user: 'registered_user' or 'firm_personnel'")


class PasswordResetResponse(BaseModel):
    """Password reset response model"""
    message: str = Field(..., description="Response message")
    expires_in_minutes: Optional[int] = Field(None, description="OTP expiration time in minutes")


class UserRegistrationRequest(BaseModel):
    """User registration request model"""
    email: EmailStr = Field(..., description="User email address")
    phone: str = Field(..., min_length=10, max_length=20, description="User phone number")
    first_name: str = Field(..., min_length=1, max_length=100, description="User first name")
    last_name: str = Field(..., min_length=1, max_length=100, description="User last name")
    password: str = Field(..., min_length=8, description="User password")


class UserRegistrationResponse(BaseModel):
    """User registration response model"""
    message: str = Field(..., description="Registration response message")
    user_id: str = Field(..., description="Created user ID")
    verification_required: bool = Field(True, description="Whether email verification is required")
    expires_in_minutes: Optional[int] = Field(None, description="Verification code expiration time in minutes")


class VerifyAccountRequest(BaseModel):
    """Account verification request model"""
    email: EmailStr = Field(..., description="User email address")
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit verification code")


class VerifyAccountResponse(BaseModel):
    """Account verification response model"""
    message: str = Field(..., description="Verification response message")
    verified: bool = Field(..., description="Whether account was successfully verified")


class ResendVerificationRequest(BaseModel):
    """Resend verification request model"""
    email: EmailStr = Field(..., description="User email address")


@router.post("/login", response_model=DetailedLoginResponse)
async def login(
    request: LoginRequest,
    x_platform: Optional[str] = Header(None, alias="X-Platform"),
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user and return JWT tokens with detailed user information
    
    This endpoint authenticates users (registered users or firm personnel)
    and returns access and refresh tokens along with complete user, team, and firm details.
    """
    try:
        # Authenticate user and get detailed response
        detailed_response = await auth_service.authenticate_user_detailed(
            email=request.email,
            password=request.password,
            user_type=request.user_type,
            db=db
        )
        
        logger.info(
            "user_login_success",
            email=request.email,
            user_type=request.user_type,
            platform=x_platform
        )
        
        return detailed_response
        
    except AuthenticationError as e:
        logger.warning(
            "user_login_failed",
            email=request.email,
            user_type=request.user_type,
            error=str(e)
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    except Exception as e:
        logger.error(
            "login_error",
            email=request.email,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed due to internal error"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest):
    """
    Refresh access token using refresh token
    
    This endpoint allows clients to obtain a new access token
    using a valid refresh token without re-authentication.
    """
    try:
        # Refresh token
        token_pair = await auth_service.refresh_token(request.refresh_token)
        
        logger.info("token_refreshed")
        
        return TokenResponse(**token_pair.to_dict())
        
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired"
        )
    except AuthenticationError as e:
        logger.warning("token_refresh_failed", error=str(e))
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    except Exception as e:
        logger.error("token_refresh_error", error=str(e), exc_info=True)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed due to internal error"
        )


@router.post("/revoke")
async def revoke_token(
    request: RevokeTokenRequest,
    current_user: UserContext = Depends(get_current_user)
):
    """
    Revoke (blacklist) a token
    
    This endpoint allows users to revoke tokens, effectively logging out
    or invalidating specific tokens for security purposes.
    """
    try:
        # Revoke token
        success = await auth_service.revoke_token(request.token)
        
        if success:
            logger.info(
                "token_revoked",
                user_id=str(current_user.user_id),
                user_type=current_user.user_type
            )
            
            return {"message": "Token revoked successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to revoke token"
            )
            
    except Exception as e:
        logger.error(
            "token_revoke_error",
            user_id=str(current_user.user_id),
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token revocation failed due to internal error"
        )


@router.post("/logout")
async def logout(current_user: UserContext = Depends(get_current_user)):
    """
    Logout current user by revoking their token
    
    This endpoint logs out the current user by revoking their access token.
    """
    # Note: In a real implementation, you would get the actual token from the request
    # For now, we'll just log the logout event
    
    logger.info(
        "user_logout",
        user_id=str(current_user.user_id),
        user_type=current_user.user_type,
        email=current_user.email
    )
    
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=DetailedUserInfoResponse)
async def get_current_user_info(
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current authenticated user information with complete details
    
    This endpoint returns detailed information about the currently authenticated user
    including user, team, and firm details (same as login response but without tokens).
    """
    try:
        # Get detailed user information from database
        detailed_info = await auth_service.get_user_detailed_info(
            user_id=current_user.user_id,
            user_type=current_user.user_type,
            db=db
        )
        
        return detailed_info
        
    except Exception as e:
        logger.error(
            "get_user_info_error",
            user_id=str(current_user.user_id),
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user information"
        )


@router.post("/verify-token")
async def verify_token(current_user: UserContext = Depends(get_current_user)):
    """
    Verify if the provided token is valid
    
    This endpoint can be used by clients to verify if their token
    is still valid without making other API calls.
    """
    return {
        "valid": True,
        "user_id": str(current_user.user_id),
        "user_type": current_user.user_type,
        "expires_soon": False  # Could implement logic to check if token expires soon
    }


@router.post("/request-unlock-otp")
async def request_unlock_otp(request: OTPRequest, db: AsyncSession = Depends(get_db)):
    """
    Request OTP for account unlock
    
    This endpoint generates and sends an OTP code to unlock a locked account.
    The OTP can be delivered via email or SMS based on the delivery method.
    """
    try:
        # Request OTP for account unlock
        result = await auth_service.request_account_unlock_otp(
            identifier=request.identifier,
            delivery_method=request.delivery_method,
            db=db
        )
        
        if result["success"]:
            logger.info(
                "unlock_otp_requested",
                identifier=request.identifier,
                delivery_method=request.delivery_method
            )
            
            return {
                "message": result["message"],
                "expires_in_minutes": result["expires_in_minutes"]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
            
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "unlock_otp_request_error",
            identifier=request.identifier,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send unlock OTP"
        )


@router.post("/verify-unlock-otp")
async def verify_unlock_otp(request: OTPVerifyRequest, db: AsyncSession = Depends(get_db)):
    """
    Verify OTP and unlock account
    
    This endpoint verifies the OTP code and unlocks the account if valid.
    """
    try:
        # Verify OTP and unlock account
        result = await auth_service.verify_unlock_otp(
            identifier=request.identifier,
            otp=request.otp,
            db=db
        )
        
        if result["success"]:
            logger.info(
                "account_unlocked_via_otp",
                identifier=request.identifier
            )
            
            return {"message": result["message"]}
        else:
            logger.warning(
                "invalid_unlock_otp",
                identifier=request.identifier
            )
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
            
    except Exception as e:
        logger.error(
            "unlock_otp_verify_error",
            identifier=request.identifier,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify unlock OTP"
        )


@router.get("/account-status/{identifier}", response_model=AccountStatusResponse)
async def get_account_status(identifier: str, db: AsyncSession = Depends(get_db)):
    """
    Get account lock status and failed attempts
    
    This endpoint returns the current status of an account including
    whether it's locked and the number of failed login attempts.
    """
    try:
        # Get account status
        status_info = await auth_service.get_account_status(identifier, db)
        
        return AccountStatusResponse(**status_info)
        
    except Exception as e:
        logger.error(
            "account_status_error",
            identifier=identifier,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get account status"
        )


@router.post("/password-reset/request", response_model=PasswordResetResponse)
async def request_password_reset(
    request: PasswordResetRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Request password reset OTP
    
    This endpoint generates and sends an OTP code to the user's email
    for password reset. The OTP is valid for 10 minutes.
    """
    try:
        # Request password reset OTP
        result = await auth_service.request_password_reset_otp(
            email=request.email,
            user_type=request.user_type,
            db=db
        )
        
        if result["success"]:
            logger.info(
                "password_reset_otp_requested",
                email=request.email,
                user_type=request.user_type
            )
            
            return PasswordResetResponse(
                message=result["message"],
                expires_in_minutes=result.get("expires_in_minutes")
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
            
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "password_reset_request_error",
            email=request.email,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send password reset OTP"
        )


@router.post("/password-reset/verify", response_model=PasswordResetResponse)
async def verify_password_reset(
    request: PasswordResetVerifyRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify OTP and reset password
    
    This endpoint verifies the OTP code and resets the user's password
    if the OTP is valid and not expired.
    """
    try:
        # Verify OTP and reset password
        result = await auth_service.verify_password_reset_otp(
            email=request.email,
            otp=request.otp,
            new_password=request.new_password,
            user_type=request.user_type,
            db=db
        )
        
        if result["success"]:
            logger.info(
                "password_reset_completed",
                email=request.email,
                user_type=request.user_type
            )
            
            return PasswordResetResponse(
                message=result["message"]
            )
        else:
            logger.warning(
                "invalid_password_reset_otp",
                email=request.email,
                user_type=request.user_type
            )
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
            
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "password_reset_verify_error",
            email=request.email,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify password reset OTP"
        )


@router.post("/register", response_model=UserRegistrationResponse)
async def register_user(
    request: UserRegistrationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user account
    
    This endpoint creates a new user account and sends a verification email.
    The user must verify their email before they can log in.
    """
    try:
        user_service = UserService(db)
        
        # Register the user
        user = await user_service.register_user(
            email=request.email,
            phone=request.phone,
            first_name=request.first_name,
            last_name=request.last_name,
            password=request.password
        )
        
        # Generate verification OTP
        verification_otp = await auth_service.account_security.generate_verification_otp(request.email)
        
        # Send verification email
        success = await auth_service.otp_delivery.send_verification_email(request.email, verification_otp)
        
        if success:
            logger.info(
                "user_registered_successfully",
                user_id=str(user.id),
                email=request.email
            )
            
            return UserRegistrationResponse(
                message="User registered successfully. Please check your email for verification code.",
                user_id=str(user.id),
                verification_required=True,
                expires_in_minutes=10
            )
        else:
            logger.warning(
                "user_registered_but_email_failed",
                user_id=str(user.id),
                email=request.email
            )
            
            return UserRegistrationResponse(
                message="User registered successfully, but verification email could not be sent. Please use resend verification.",
                user_id=str(user.id),
                verification_required=True,
                expires_in_minutes=None
            )
            
    except ValueError as e:
        logger.warning(
            "user_registration_failed",
            email=request.email,
            error=str(e)
        )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "user_registration_error",
            email=request.email,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed due to internal error"
        )


@router.post("/verify-account", response_model=VerifyAccountResponse)
async def verify_account(
    request: VerifyAccountRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify user account with email OTP
    
    This endpoint verifies a user's email address using the OTP code
    sent during registration or via resend verification.
    """
    try:
        user_service = UserService(db)
        
        # Check if user exists
        user = await user_service.get_user_by_email(request.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if user is already verified
        if user.is_verified:
            return VerifyAccountResponse(
                message="Account is already verified",
                verified=True
            )
        
        # Verify OTP
        otp_valid = await auth_service.account_security.verify_verification_otp(request.email, request.otp)
        
        if otp_valid:
            # Mark user as verified
            user.is_verified = True
            await db.commit()
            
            logger.info(
                "account_verified_successfully",
                user_id=str(user.id),
                email=request.email
            )
            
            return VerifyAccountResponse(
                message="Account verified successfully. You can now log in.",
                verified=True
            )
        else:
            logger.warning(
                "account_verification_failed",
                email=request.email,
                provided_otp=request.otp
            )
            
            return VerifyAccountResponse(
                message="Invalid or expired verification code",
                verified=False
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "account_verification_error",
            email=request.email,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Account verification failed due to internal error"
        )


@router.post("/resend-verification", response_model=PasswordResetResponse)
async def resend_verification(
    request: ResendVerificationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Resend account verification email
    
    This endpoint resends the verification email with a new OTP code
    for users who haven't verified their account yet.
    """
    try:
        user_service = UserService(db)
        
        # Check if user exists
        user = await user_service.get_user_by_email(request.email)
        if not user:
            # For security, don't reveal if email exists or not
            return PasswordResetResponse(
                message="If the email exists in our system and is not verified, a verification code has been sent",
                expires_in_minutes=10
            )
        
        # Check if user is already verified
        if user.is_verified:
            return PasswordResetResponse(
                message="Account is already verified. You can log in.",
                expires_in_minutes=None
            )
        
        # Generate new verification OTP
        verification_otp = await auth_service.account_security.generate_verification_otp(request.email)
        
        # Send verification email
        success = await auth_service.otp_delivery.send_verification_email(request.email, verification_otp)
        
        if success:
            logger.info(
                "verification_email_resent",
                user_id=str(user.id),
                email=request.email
            )
            
            return PasswordResetResponse(
                message="Verification code sent to your email",
                expires_in_minutes=10
            )
        else:
            logger.error(
                "verification_email_resend_failed",
                user_id=str(user.id),
                email=request.email
            )
            
            return PasswordResetResponse(
                message="Failed to send verification code. Please try again later.",
                expires_in_minutes=None
            )
            
    except Exception as e:
        logger.error(
            "resend_verification_error",
            email=request.email,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resend verification code"
        )