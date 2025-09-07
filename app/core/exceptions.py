"""
Custom exceptions and error handling
"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from datetime import datetime
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger()


class APIError(Exception):
    """Base API error"""
    def __init__(self, error_code: str, message: str, details: Optional[Dict[str, Any]] = None):
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ErrorCodes:
    """Error code constants"""
    # Authentication Errors
    INVALID_ATTESTATION = "AUTH_001"
    EXPIRED_TOKEN = "AUTH_002"
    INSUFFICIENT_PERMISSIONS = "AUTH_003"
    ACCOUNT_LOCKED = "AUTH_004"
    TOO_MANY_FAILED_ATTEMPTS = "AUTH_005"
    ACCOUNT_NOT_LOCKED = "AUTH_006"
    INVALID_OTP = "AUTH_007"
    OTP_EXPIRED = "AUTH_008"
    INVALID_DELIVERY_METHOD = "AUTH_009"
    
    # Subscription Errors
    INSUFFICIENT_CREDITS = "SUB_001"
    SUBSCRIPTION_EXPIRED = "SUB_002"
    SUBSCRIPTION_ALREADY_APPLIED = "SUB_003"
    
    # Geographic Errors
    LOCATION_NOT_COVERED = "GEO_001"
    INVALID_COORDINATES = "GEO_002"
    
    # Request Errors
    DUPLICATE_REQUEST = "REQ_001"
    REQUEST_NOT_FOUND = "REQ_002"
    INVALID_SERVICE_TYPE = "REQ_003"
    
    # Validation Errors
    VALIDATION_ERROR = "VAL_001"
    
    # Notification Errors
    NOTIFICATION_FAILED = "NOT_001"
    
    # Silent Mode Errors
    SILENT_MODE_FAILED = "SIL_001"
    
    # Prank Detection and Fine Errors
    PAYMENT_FAILED = "PAYMENT_001"
    FINE_NOT_FOUND = "FINE_001"
    USER_SUSPENDED = "USER_001"
    USER_BANNED = "USER_002"


# Custom exception classes
class AccountLockedException(APIError):
    def __init__(self, message: str = "Account is temporarily locked"):
        super().__init__(ErrorCodes.ACCOUNT_LOCKED, message)


class InvalidCredentialsException(APIError):
    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(ErrorCodes.TOO_MANY_FAILED_ATTEMPTS, message)


class AccountNotLockedException(APIError):
    def __init__(self, message: str = "Account is not locked"):
        super().__init__(ErrorCodes.ACCOUNT_NOT_LOCKED, message)


class InvalidOTPException(APIError):
    def __init__(self, message: str = "Invalid or expired OTP"):
        super().__init__(ErrorCodes.INVALID_OTP, message)


class GeographicCoverageError(APIError):
    def __init__(self, message: str = "Location not covered", alternative_firms: list = None):
        super().__init__(ErrorCodes.LOCATION_NOT_COVERED, message)
        self.alternative_firms = alternative_firms or []


def create_error_response(
    error_code: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """Create standardized error response"""
    return {
        "error_code": error_code,
        "message": message,
        "details": details or {},
        "timestamp": datetime.utcnow().isoformat(),
        "request_id": request_id
    }


def setup_exception_handlers(app: FastAPI):
    """Setup global exception handlers"""
    
    @app.exception_handler(ValidationError)
    async def validation_exception_handler(request: Request, exc: ValidationError):
        logger.warning("Validation error", errors=exc.errors(), path=request.url.path)
        return JSONResponse(
            status_code=422,
            content=create_error_response(
                error_code=ErrorCodes.VALIDATION_ERROR,
                message="Request validation failed",
                details={"errors": exc.errors()},
                request_id=request.headers.get("X-Request-ID")
            )
        )
    
    @app.exception_handler(APIError)
    async def api_exception_handler(request: Request, exc: APIError):
        status_code = 400
        if exc.error_code == ErrorCodes.ACCOUNT_LOCKED:
            status_code = 423  # Locked
        elif exc.error_code in [ErrorCodes.EXPIRED_TOKEN, ErrorCodes.INSUFFICIENT_PERMISSIONS]:
            status_code = 401  # Unauthorized
        
        logger.warning("API error", error_code=exc.error_code, message=exc.message, path=request.url.path)
        return JSONResponse(
            status_code=status_code,
            content=create_error_response(
                error_code=exc.error_code,
                message=exc.message,
                details=exc.details,
                request_id=request.headers.get("X-Request-ID")
            )
        )
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        logger.warning("HTTP error", status_code=exc.status_code, detail=exc.detail, path=request.url.path)
        return JSONResponse(
            status_code=exc.status_code,
            content=create_error_response(
                error_code=f"HTTP_{exc.status_code}",
                message=exc.detail,
                request_id=request.headers.get("X-Request-ID")
            )
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error("Unhandled exception", error=str(exc), path=request.url.path, exc_info=True)
        return JSONResponse(
            status_code=500,
            content=create_error_response(
                error_code="INTERNAL_ERROR",
                message="Internal server error",
                request_id=request.headers.get("X-Request-ID")
            )
        )