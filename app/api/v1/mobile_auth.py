"""
Mobile Authentication API endpoints with enhanced security features
"""
from fastapi import APIRouter, HTTPException, Depends, status, Header, Request
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, Dict, Any, List
import structlog
import hashlib
import hmac
import base64
import json
from datetime import datetime, timezone

from app.services.auth import auth_service, AuthenticationError, TokenExpiredError, TokenPair
from app.services.user import UserService
from app.core.auth import get_current_user, UserContext
from app.core.exceptions import APIError, ErrorCodes
from app.core.database import get_db
from app.core.config import settings
from app.core.redis import cache
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()

router = APIRouter()


class DeviceInfo(BaseModel):
    """Device information for attestation"""
    device_id: str = Field(..., description="Unique device identifier")
    device_type: str = Field(..., description="Device type (ios/android/web)")
    device_model: str = Field(..., description="Device model")
    os_version: str = Field(..., description="Operating system version")
    app_version: str = Field(..., description="Application version")
    platform_version: str = Field(..., description="Platform version")


class SecurityAttestation(BaseModel):
    """Security attestation data"""
    attestation_token: Optional[str] = Field(None, description="Platform attestation token")
    integrity_verdict: Optional[str] = Field(None, description="Play Integrity verdict")
    safety_net_token: Optional[str] = Field(None, description="SafetyNet attestation token")
    app_attest_token: Optional[str] = Field(None, description="iOS App Attest token")
    timestamp: str = Field(..., description="Attestation timestamp")
    nonce: str = Field(..., description="Cryptographic nonce")


class MobileRegistrationRequest(BaseModel):
    """Mobile user registration request with security features"""
    email: EmailStr = Field(..., description="User email address")
    phone: str = Field(..., min_length=10, max_length=20, description="User phone number")
    first_name: str = Field(..., min_length=1, max_length=100, description="User first name")
    last_name: str = Field(..., min_length=1, max_length=100, description="User last name")
    password: str = Field(..., min_length=8, description="User password")
    device_info: DeviceInfo = Field(..., description="Device information")
    security_attestation: Optional[SecurityAttestation] = Field(None, description="Security attestation")
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in v):
            raise ValueError('Password must contain at least one special character')
        return v


class MobileLoginRequest(BaseModel):
    """Mobile login request with security features"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    device_info: DeviceInfo = Field(..., description="Device information")
    security_attestation: Optional[SecurityAttestation] = Field(None, description="Security attestation")
    biometric_hash: Optional[str] = Field(None, description="Biometric authentication hash")


class MobileTokenResponse(BaseModel):
    """Enhanced mobile token response"""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiry time in seconds")
    
    # Enhanced mobile fields
    user_id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    first_name: str = Field(..., description="User first name")
    last_name: str = Field(..., description="User last name")
    is_verified: bool = Field(..., description="Whether email is verified")
    
    # Security metadata
    device_registered: bool = Field(..., description="Whether device is registered")
    requires_additional_verification: bool = Field(False, description="Whether additional verification is needed")
    session_id: str = Field(..., description="Session identifier")


class MobileRegistrationResponse(BaseModel):
    """Mobile registration response"""
    message: str = Field(..., description="Registration response message")
    user_id: str = Field(..., description="Created user ID")
    email_verification_sent: bool = Field(..., description="Whether verification email was sent")
    session_id: str = Field(..., description="Session identifier")
    requires_verification: bool = Field(True, description="Whether email verification is required")


class EmailVerificationRequest(BaseModel):
    """Email verification request"""
    email: EmailStr = Field(..., description="User email address")
    verification_code: str = Field(..., min_length=6, max_length=6, description="6-digit verification code")
    session_id: str = Field(..., description="Session identifier")


class ResendVerificationRequest(BaseModel):
    """Resend verification request"""
    email: EmailStr = Field(..., description="User email address")
    session_id: Optional[str] = Field(None, description="Session identifier")


class DeviceRegistrationRequest(BaseModel):
    """Device registration for push notifications"""
    device_token: str = Field(..., description="Push notification device token")
    device_info: DeviceInfo = Field(..., description="Device information")


class MobilePasswordResetRequest(BaseModel):
    """Mobile password reset request"""
    email: EmailStr = Field(..., description="User email address")
    device_info: DeviceInfo = Field(..., description="Device information")


class MobilePasswordResetVerifyRequest(BaseModel):
    """Mobile password reset verification request"""
    email: EmailStr = Field(..., description="User email address")
    reset_code: str = Field(..., min_length=6, max_length=6, description="6-digit reset code")
    new_password: str = Field(..., min_length=8, description="New password")
    device_info: DeviceInfo = Field(..., description="Device information")
    
    @validator('new_password')
    def validate_new_password(cls, v):
        """Validate new password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in v):
            raise ValueError('Password must contain at least one special character')
        return v


def verify_security_attestation(attestation: Optional[SecurityAttestation], device_info: DeviceInfo) -> bool:
    """Verify security attestation based on platform"""
    if not attestation:
        logger.warning("No security attestation provided")
        return False
    
    try:
        # Verify timestamp is recent (within 5 minutes)
        attestation_time = datetime.fromisoformat(attestation.timestamp.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        time_diff = (now - attestation_time).total_seconds()
        
        if time_diff > 300:  # 5 minutes
            logger.warning("Attestation timestamp too old", time_diff=time_diff)
            return False
        
        # Platform-specific attestation verification
        if device_info.device_type.lower() == "android":
            return verify_android_attestation(attestation)
        elif device_info.device_type.lower() == "ios":
            return verify_ios_attestation(attestation)
        elif device_info.device_type.lower() == "web":
            # Web platform doesn't have attestation, return True for development
            return True
        
        return False
        
    except Exception as e:
        logger.error("Attestation verification failed", error=str(e))
        return False


def verify_android_attestation(attestation: SecurityAttestation) -> bool:
    """Verify Android Play Integrity attestation"""
    if not attestation.integrity_verdict:
        return False
    
    # In production, verify the Play Integrity token
    # For now, we'll do basic validation
    required_verdicts = ["MEETS_DEVICE_INTEGRITY", "MEETS_BASIC_INTEGRITY"]
    return any(verdict in attestation.integrity_verdict for verdict in required_verdicts)


def verify_ios_attestation(attestation: SecurityAttestation) -> bool:
    """Verify iOS App Attest attestation"""
    if not attestation.app_attest_token:
        return False
    
    # In production, verify the App Attest token with Apple's servers
    # For now, we'll do basic validation
    return len(attestation.app_attest_token) > 50


def generate_session_id(user_email: str, device_id: str) -> str:
    """Generate a unique session ID"""
    data = f"{user_email}:{device_id}:{datetime.now().isoformat()}"
    return hashlib.sha256(data.encode()).hexdigest()


@router.post("/mobile/register", response_model=MobileRegistrationResponse)
async def mobile_register(
    request: MobileRegistrationRequest,
    db: AsyncSession = Depends(get_db),
    user_agent: Optional[str] = Header(None, alias="User-Agent"),
    x_real_ip: Optional[str] = Header(None, alias="X-Real-IP"),
    http_request: Request = None
):
    """
    Register a new mobile user with enhanced security features
    
    This endpoint creates a new user account with mobile-specific security features
    including device attestation, enhanced password validation, and device registration.
    """
    try:
        # Get client IP
        client_ip = x_real_ip or (http_request.client.host if http_request else "unknown")
        
        # Verify security attestation (optional for registration, but logged)
        attestation_valid = False
        if request.security_attestation:
            attestation_valid = verify_security_attestation(request.security_attestation, request.device_info)
            
        logger.info(
            "mobile_registration_attempt",
            email=request.email,
            device_type=request.device_info.device_type,
            device_model=request.device_info.device_model,
            attestation_valid=attestation_valid,
            client_ip=client_ip
        )
        
        # Register the user
        user_service = UserService(db)
        user = await user_service.register_user(
            email=request.email,
            phone=request.phone,
            first_name=request.first_name,
            last_name=request.last_name,
            password=request.password
        )
        
        # Generate session ID
        session_id = generate_session_id(request.email, request.device_info.device_id)
        
        # Store device information in cache temporarily
        device_data = {
            "device_info": request.device_info.dict(),
            "attestation_valid": attestation_valid,
            "registration_time": datetime.now().isoformat(),
            "client_ip": client_ip,
            "user_agent": user_agent
        }
        
        cache_key = f"mobile_device:{session_id}"
        await cache.set(cache_key, device_data, expire=3600)  # 1 hour expiry
        
        # Generate and send verification email
        verification_otp = await auth_service.account_security.generate_verification_otp(request.email)
        email_sent = await auth_service.otp_delivery.send_verification_email(request.email, verification_otp)
        
        if email_sent:
            logger.info(
                "mobile_user_registered_successfully",
                user_id=str(user.id),
                email=request.email,
                device_id=request.device_info.device_id,
                session_id=session_id
            )
            
            return MobileRegistrationResponse(
                message="Registration successful. Please verify your email to complete the process.",
                user_id=str(user.id),
                email_verification_sent=True,
                session_id=session_id,
                requires_verification=True
            )
        else:
            logger.warning(
                "mobile_user_registered_but_email_failed",
                user_id=str(user.id),
                email=request.email,
                session_id=session_id
            )
            
            return MobileRegistrationResponse(
                message="Registration successful, but verification email could not be sent. Please use resend verification.",
                user_id=str(user.id),
                email_verification_sent=False,
                session_id=session_id,
                requires_verification=True
            )
            
    except ValueError as e:
        logger.warning(
            "mobile_registration_validation_failed",
            email=request.email,
            error=str(e),
            client_ip=client_ip
        )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "mobile_registration_error",
            email=request.email,
            error=str(e),
            client_ip=client_ip,
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed due to internal error"
        )


@router.post("/mobile/verify-email", response_model=Dict[str, Any])
async def mobile_verify_email(
    request: EmailVerificationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify email address for mobile user
    
    This endpoint verifies a user's email address using the verification code
    and completes the mobile registration process.
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
            return {
                "verified": True,
                "message": "Email is already verified",
                "can_login": True
            }
        
        # Verify the OTP
        otp_valid = await auth_service.account_security.verify_verification_otp(
            request.email, 
            request.verification_code
        )
        
        if otp_valid:
            # Mark user as verified
            user.is_verified = True
            await db.commit()
            
            # Get device info from cache
            cache_key = f"mobile_device:{request.session_id}"
            device_data = await cache.get(cache_key)
            
            logger.info(
                "mobile_email_verified_successfully",
                user_id=str(user.id),
                email=request.email,
                session_id=request.session_id,
                has_device_data=device_data is not None
            )
            
            return {
                "verified": True,
                "message": "Email verified successfully. You can now log in.",
                "can_login": True
            }
        else:
            logger.warning(
                "mobile_email_verification_failed",
                email=request.email,
                session_id=request.session_id
            )
            
            return {
                "verified": False,
                "message": "Invalid or expired verification code",
                "can_login": False
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "mobile_email_verification_error",
            email=request.email,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email verification failed due to internal error"
        )


@router.post("/mobile/resend-verification", response_model=Dict[str, Any])
async def mobile_resend_verification(
    request: ResendVerificationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Resend email verification code for mobile user
    
    This endpoint resends the verification email with a new code
    for users who haven't verified their email yet.
    """
    try:
        user_service = UserService(db)
        
        # Check if user exists
        user = await user_service.get_user_by_email(request.email)
        if not user:
            # For security, don't reveal if email exists
            return {
                "sent": True,
                "message": "If the email exists and is not verified, a verification code has been sent",
                "expires_in_minutes": 10
            }
        
        # Check if user is already verified
        if user.is_verified:
            return {
                "sent": False,
                "message": "Email is already verified. You can log in.",
                "expires_in_minutes": None
            }
        
        # Generate new verification OTP
        verification_otp = await auth_service.account_security.generate_verification_otp(request.email)
        
        # Send verification email
        email_sent = await auth_service.otp_delivery.send_verification_email(request.email, verification_otp)
        
        if email_sent:
            logger.info(
                "mobile_verification_resent",
                user_id=str(user.id),
                email=request.email,
                session_id=request.session_id
            )
            
            return {
                "sent": True,
                "message": "Verification code sent to your email",
                "expires_in_minutes": 10
            }
        else:
            logger.error(
                "mobile_verification_resend_failed",
                user_id=str(user.id),
                email=request.email,
                session_id=request.session_id
            )
            
            return {
                "sent": False,
                "message": "Failed to send verification code. Please try again later.",
                "expires_in_minutes": None
            }
            
    except Exception as e:
        logger.error(
            "mobile_resend_verification_error",
            email=request.email,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resend verification code"
        )


@router.post("/mobile/login", response_model=MobileTokenResponse)
async def mobile_login(
    request: MobileLoginRequest,
    db: AsyncSession = Depends(get_db),
    user_agent: Optional[str] = Header(None, alias="User-Agent"),
    x_real_ip: Optional[str] = Header(None, alias="X-Real-IP"),
    http_request: Request = None
):
    """
    Mobile user login with enhanced security features
    
    This endpoint authenticates mobile users with additional security checks
    including device attestation, device fingerprinting, and enhanced logging.
    """
    try:
        # Get client IP
        client_ip = x_real_ip or (http_request.client.host if http_request else "unknown")
        
        # Verify security attestation
        attestation_valid = False
        if request.security_attestation:
            attestation_valid = verify_security_attestation(request.security_attestation, request.device_info)
        
        # Log login attempt
        logger.info(
            "mobile_login_attempt",
            email=request.email,
            device_type=request.device_info.device_type,
            device_id=request.device_info.device_id,
            attestation_valid=attestation_valid,
            has_biometric=request.biometric_hash is not None,
            client_ip=client_ip
        )
        
        # For high-security requirements, you might want to require valid attestation
        if settings.REQUIRE_MOBILE_ATTESTATION and not attestation_valid:
            logger.warning(
                "mobile_login_blocked_invalid_attestation",
                email=request.email,
                device_id=request.device_info.device_id
            )
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Device attestation failed. Please update your app or use a supported device."
            )
        
        # Authenticate user
        detailed_response = await auth_service.authenticate_user_detailed(
            email=request.email,
            password=request.password,
            user_type="registered_user",
            db=db
        )
        
        # Generate session ID
        session_id = generate_session_id(request.email, request.device_info.device_id)
        
        # Store device and session information
        device_session_data = {
            "device_info": request.device_info.dict(),
            "attestation_valid": attestation_valid,
            "login_time": datetime.now().isoformat(),
            "client_ip": client_ip,
            "user_agent": user_agent,
            "user_id": detailed_response.id,
            "biometric_enabled": request.biometric_hash is not None
        }
        
        # Store session data with longer expiry for refresh token validation
        session_cache_key = f"mobile_session:{session_id}"
        await cache.set(session_cache_key, device_session_data, expire=86400 * 7)  # 7 days
        
        # Store device registration
        device_cache_key = f"mobile_device:{detailed_response.id}:{request.device_info.device_id}"
        await cache.set(device_cache_key, device_session_data, expire=86400 * 30)  # 30 days
        
        logger.info(
            "mobile_login_success",
            email=request.email,
            user_id=detailed_response.id,
            device_id=request.device_info.device_id,
            session_id=session_id,
            attestation_valid=attestation_valid
        )
        
        return MobileTokenResponse(
            access_token=detailed_response.access_token,
            refresh_token=detailed_response.refresh_token,
            token_type=detailed_response.token_type,
            expires_in=detailed_response.expires_in,
            user_id=detailed_response.id,
            email=detailed_response.email,
            first_name=detailed_response.first_name,
            last_name=detailed_response.last_name,
            is_verified=True,  # User must be verified to login
            device_registered=True,
            requires_additional_verification=False,
            session_id=session_id
        )
        
    except AuthenticationError as e:
        logger.warning(
            "mobile_login_failed",
            email=request.email,
            device_id=request.device_info.device_id,
            error=str(e),
            client_ip=client_ip
        )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "mobile_login_error",
            email=request.email,
            device_id=request.device_info.device_id,
            error=str(e),
            client_ip=client_ip,
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed due to internal error"
        )


@router.post("/mobile/register-device")
async def mobile_register_device(
    request: DeviceRegistrationRequest,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Register device for push notifications
    
    This endpoint registers a device token for push notifications
    and associates it with the authenticated user.
    """
    try:
        # Store device token in cache
        device_token_key = f"device_token:{current_user.user_id}:{request.device_info.device_id}"
        device_token_data = {
            "device_token": request.device_token,
            "device_info": request.device_info.dict(),
            "registered_at": datetime.now().isoformat(),
            "user_id": str(current_user.user_id)
        }
        
        await cache.set(device_token_key, device_token_data, expire=86400 * 90)  # 90 days
        
        logger.info(
            "device_registered_for_notifications",
            user_id=str(current_user.user_id),
            device_id=request.device_info.device_id,
            device_type=request.device_info.device_type
        )
        
        return {
            "registered": True,
            "message": "Device registered successfully for push notifications",
            "device_id": request.device_info.device_id
        }
        
    except Exception as e:
        logger.error(
            "device_registration_error",
            user_id=str(current_user.user_id),
            device_id=request.device_info.device_id,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Device registration failed"
        )


@router.get("/mobile/security-status")
async def mobile_security_status(
    current_user: UserContext = Depends(get_current_user),
    device_id: Optional[str] = None
):
    """
    Get security status for mobile user
    
    This endpoint returns the security status including device trust level,
    session information, and security recommendations.
    """
    try:
        # Get device information if device_id provided
        device_info = None
        if device_id:
            device_key = f"mobile_device:{current_user.user_id}:{device_id}"
            device_data = await cache.get(device_key)
            if device_data:
                device_info = json.loads(device_data)
        
        # Security status
        security_status = {
            "user_id": str(current_user.user_id),
            "email_verified": True,  # User must be verified to be authenticated
            "device_registered": device_info is not None,
            "attestation_valid": device_info.get("attestation_valid", False) if device_info else False,
            "biometric_enabled": device_info.get("biometric_enabled", False) if device_info else False,
            "last_login": device_info.get("login_time") if device_info else None,
            "security_level": "high" if (device_info and device_info.get("attestation_valid")) else "medium",
            "recommendations": []
        }
        
        # Add security recommendations
        if not security_status["attestation_valid"]:
            security_status["recommendations"].append("Enable device attestation for enhanced security")
        
        if not security_status["biometric_enabled"]:
            security_status["recommendations"].append("Enable biometric authentication for faster and more secure login")
        
        return security_status
        
    except Exception as e:
        logger.error(
            "security_status_error",
            user_id=str(current_user.user_id),
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get security status"
        )


@router.post("/mobile/password-reset/request", response_model=Dict[str, Any])
async def mobile_request_password_reset(
    request: MobilePasswordResetRequest,
    db: AsyncSession = Depends(get_db),
    user_agent: Optional[str] = Header(None, alias="User-Agent"),
    x_real_ip: Optional[str] = Header(None, alias="X-Real-IP"),
    http_request: Request = None
):
    """
    Request password reset for mobile user
    
    This endpoint initiates a password reset process by sending a reset code
    to the user's email address with enhanced security logging.
    """
    try:
        # Get client IP
        client_ip = x_real_ip or (http_request.client.host if http_request else "unknown")
        
        # Log password reset request
        logger.info(
            "mobile_password_reset_requested",
            email=request.email,
            device_type=request.device_info.device_type,
            device_id=request.device_info.device_id,
            client_ip=client_ip
        )
        
        # Request password reset OTP
        result = await auth_service.request_password_reset_otp(
            email=request.email,
            user_type="registered_user",
            db=db
        )
        
        if result["success"]:
            # Generate session ID for tracking
            session_id = generate_session_id(request.email, request.device_info.device_id)
            
            # Store reset session data
            reset_session_data = {
                "device_info": request.device_info.dict(),
                "reset_request_time": datetime.now().isoformat(),
                "client_ip": client_ip,
                "user_agent": user_agent,
                "email": request.email
            }
            
            session_cache_key = f"mobile_reset_session:{session_id}"
            await cache.set(session_cache_key, reset_session_data, expire=1800)  # 30 minutes
            
            logger.info(
                "mobile_password_reset_otp_sent",
                email=request.email,
                device_id=request.device_info.device_id,
                session_id=session_id
            )
            
            return {
                "success": True,
                "message": "Password reset code sent to your email",
                "expires_in_minutes": result.get("expires_in_minutes", 10),
                "session_id": session_id
            }
        else:
            return {
                "success": False,
                "message": result["message"],
                "expires_in_minutes": None
            }
            
    except Exception as e:
        logger.error(
            "mobile_password_reset_request_error",
            email=request.email,
            device_id=request.device_info.device_id,
            error=str(e),
            client_ip=client_ip,
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send password reset code"
        )


@router.post("/mobile/password-reset/verify", response_model=Dict[str, Any])
async def mobile_verify_password_reset(
    request: MobilePasswordResetVerifyRequest,
    db: AsyncSession = Depends(get_db),
    user_agent: Optional[str] = Header(None, alias="User-Agent"),
    x_real_ip: Optional[str] = Header(None, alias="X-Real-IP"),
    http_request: Request = None
):
    """
    Verify password reset code and set new password
    
    This endpoint verifies the reset code and updates the user's password
    with enhanced validation and security logging.
    """
    try:
        # Get client IP
        client_ip = x_real_ip or (http_request.client.host if http_request else "unknown")
        
        # Log password reset attempt
        logger.info(
            "mobile_password_reset_verify_attempt",
            email=request.email,
            device_type=request.device_info.device_type,
            device_id=request.device_info.device_id,
            client_ip=client_ip
        )
        
        # Verify OTP and reset password
        result = await auth_service.verify_password_reset_otp(
            email=request.email,
            otp=request.reset_code,
            new_password=request.new_password,
            user_type="registered_user",
            db=db
        )
        
        if result["success"]:
            # Generate new session ID after password reset
            session_id = generate_session_id(request.email, request.device_info.device_id)
            
            # Store password reset completion data
            reset_completion_data = {
                "device_info": request.device_info.dict(),
                "reset_completion_time": datetime.now().isoformat(),
                "client_ip": client_ip,
                "user_agent": user_agent,
                "email": request.email
            }
            
            completion_cache_key = f"mobile_reset_completed:{session_id}"
            await cache.set(completion_cache_key, reset_completion_data, expire=3600)  # 1 hour
            
            logger.info(
                "mobile_password_reset_completed",
                email=request.email,
                device_id=request.device_info.device_id,
                session_id=session_id
            )
            
            return {
                "success": True,
                "message": "Password reset successfully. You can now log in with your new password.",
                "can_login": True,
                "session_id": session_id
            }
        else:
            logger.warning(
                "mobile_password_reset_verify_failed",
                email=request.email,
                device_id=request.device_info.device_id,
                client_ip=client_ip
            )
            
            return {
                "success": False,
                "message": result["message"],
                "can_login": False
            }
            
    except ValueError as e:
        logger.warning(
            "mobile_password_reset_validation_failed",
            email=request.email,
            device_id=request.device_info.device_id,
            error=str(e),
            client_ip=client_ip
        )
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "mobile_password_reset_verify_error",
            email=request.email,
            device_id=request.device_info.device_id,
            error=str(e),
            client_ip=client_ip,
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify password reset code"
        )


@router.post("/mobile/logout")
async def mobile_logout(
    current_user: UserContext = Depends(get_current_user),
    device_id: Optional[str] = None,
    session_id: Optional[str] = None
):
    """
    Mobile user logout with session cleanup
    
    This endpoint logs out the mobile user and cleans up device sessions.
    """
    try:
        # Clean up device session if provided
        if session_id:
            session_cache_key = f"mobile_session:{session_id}"
            await cache.delete(session_cache_key)
        
        if device_id:
            device_cache_key = f"mobile_device:{current_user.user_id}:{device_id}"
            await cache.delete(device_cache_key)
            
            # Clean up device token
            device_token_key = f"device_token:{current_user.user_id}:{device_id}"
            await cache.delete(device_token_key)
        
        logger.info(
            "mobile_user_logout",
            user_id=str(current_user.user_id),
            email=current_user.email,
            device_id=device_id,
            session_id=session_id
        )
        
        return {
            "logged_out": True,
            "message": "Logged out successfully",
            "session_cleared": session_id is not None,
            "device_cleared": device_id is not None
        }
        
    except Exception as e:
        logger.error(
            "mobile_logout_error",
            user_id=str(current_user.user_id),
            device_id=device_id,
            error=str(e),
            exc_info=True
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )