"""
Middleware for request processing and security
"""
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable, Optional
import time
import uuid

from app.services.attestation import attestation_service, AttestationError
from app.core.exceptions import create_error_response, ErrorCodes
from app.core.logging import get_logger, set_request_context, clear_request_context, SecurityEventType

logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request logging and timing"""
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Set request context for logging
        set_request_context(request_id)
        
        # Add request ID to headers for response
        start_time = time.time()
        
        # Create request logger with context
        request_logger = logger.bind(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            content_length=request.headers.get("content-length")
        )
        
        # Log request
        request_logger.info("request_started")
        
        try:
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Add headers to response
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(process_time)
            
            # Log response
            request_logger.info(
                "request_completed",
                status_code=response.status_code,
                process_time=process_time,
                response_size=response.headers.get("content-length")
            )
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            request_logger.error(
                "request_failed",
                error=str(e),
                error_type=type(e).__name__,
                process_time=process_time,
                exc_info=True
            )
            raise
        finally:
            # Clear request context
            clear_request_context()


class MobileAttestationMiddleware(BaseHTTPMiddleware):
    """Middleware to validate mobile app attestation on mobile endpoints"""
    
    MOBILE_ENDPOINTS = [
        "/api/v1/mobile/",
        "/api/v1/auth/mobile/",
        "/api/v1/emergency/",
        "/api/v1/agent/",
    ]
    
    EXEMPT_PATHS = [
        "/api/v1/mobile/auth/register",
        "/api/v1/mobile/auth/request-challenge",  # For initial attestation setup
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json"
    ]
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Check if this is a mobile endpoint that requires attestation
        if not self._requires_attestation(request):
            return await call_next(request)
        
        try:
            # Verify attestation based on platform
            await self._verify_request_attestation(request)
            return await call_next(request)
            
        except AttestationError as e:
            # Log security event
            logger.security_event(
                SecurityEventType.ATTESTATION_FAILURE,
                path=request.url.path,
                error=str(e),
                client_ip=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                platform=request.headers.get("X-Platform")
            )
            
            logger.warning(
                "attestation_verification_failed",
                path=request.url.path,
                error=str(e),
                client_ip=request.client.host if request.client else None
            )
            
            return JSONResponse(
                status_code=401,
                content=create_error_response(
                    error_code=ErrorCodes.INVALID_ATTESTATION,
                    message="Mobile app attestation verification failed",
                    details={"reason": str(e)},
                    request_id=getattr(request.state, 'request_id', None)
                )
            )
        
        except Exception as e:
            logger.error(
                "attestation_middleware_error",
                path=request.url.path,
                error=str(e),
                exc_info=True
            )
            
            # Convert general exceptions to AttestationError for consistency
            return JSONResponse(
                status_code=401,
                content=create_error_response(
                    error_code=ErrorCodes.INVALID_ATTESTATION,
                    message="Mobile app attestation verification failed",
                    details={"reason": str(e)},
                    request_id=getattr(request.state, 'request_id', None)
                )
            )
    
    def _requires_attestation(self, request: Request) -> bool:
        """Check if the request path requires attestation"""
        path = request.url.path
        
        # Check if path is exempt
        if any(path.startswith(exempt) for exempt in self.EXEMPT_PATHS):
            return False
        
        # Check if path is a mobile endpoint
        return any(path.startswith(mobile_path) for mobile_path in self.MOBILE_ENDPOINTS)
    
    async def _verify_request_attestation(self, request: Request):
        """Verify attestation based on platform headers"""
        # Get platform from headers
        platform = request.headers.get("X-Platform", "").lower()
        
        if platform == "android":
            await self._verify_android_attestation(request)
        elif platform == "ios":
            await self._verify_ios_attestation(request)
        else:
            raise AttestationError("Missing or invalid platform header")
    
    async def _verify_android_attestation(self, request: Request):
        """Verify Android Play Integrity attestation"""
        # Get integrity token from headers
        integrity_token = request.headers.get("X-Integrity-Token")
        if not integrity_token:
            raise AttestationError("Missing Android integrity token")
        
        # Get optional nonce
        nonce = request.headers.get("X-Nonce")
        
        # Verify with Google Play Integrity API
        is_valid = await attestation_service.verify_android_integrity(integrity_token, nonce)
        
        if not is_valid:
            raise AttestationError("Android integrity verification failed")
        
        # Store verification result in request state
        request.state.attestation_verified = True
        request.state.platform = "android"
    
    async def _verify_ios_attestation(self, request: Request):
        """Verify iOS App Attest attestation"""
        # Check if this is initial attestation or ongoing assertion
        attestation_object = request.headers.get("X-Attestation-Object")
        assertion = request.headers.get("X-Assertion")
        
        if attestation_object:
            # Initial attestation
            await self._verify_ios_initial_attestation(request, attestation_object)
        elif assertion:
            # Ongoing assertion
            await self._verify_ios_assertion(request, assertion)
        else:
            raise AttestationError("Missing iOS attestation data")
        
        # Store verification result in request state
        request.state.attestation_verified = True
        request.state.platform = "ios"
    
    async def _verify_ios_initial_attestation(self, request: Request, attestation_object: str):
        """Verify iOS initial attestation"""
        key_id = request.headers.get("X-Key-ID")
        challenge = request.headers.get("X-Challenge")
        
        if not key_id or not challenge:
            raise AttestationError("Missing iOS attestation parameters")
        
        # Verify with Apple App Attest
        is_valid = await attestation_service.verify_ios_attestation(
            attestation_object, key_id, challenge
        )
        
        if not is_valid:
            raise AttestationError("iOS attestation verification failed")
    
    async def _verify_ios_assertion(self, request: Request, assertion: str):
        """Verify iOS ongoing assertion"""
        key_id = request.headers.get("X-Key-ID")
        client_data_hash = request.headers.get("X-Client-Data-Hash")
        
        if not key_id or not client_data_hash:
            raise AttestationError("Missing iOS assertion parameters")
        
        # Verify with Apple App Attest
        is_valid = await attestation_service.verify_ios_assertion(
            assertion, key_id, client_data_hash
        )
        
        if not is_valid:
            raise AttestationError("iOS assertion verification failed")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers"""
    
    async def dispatch(self, request: Request, call_next: Callable):
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Remove server header for security
        if "server" in response.headers:
            del response.headers["server"]
        
        return response


async def require_mobile_attestation(request: Request) -> dict:
    """
    Dependency function to require mobile attestation for endpoints
    
    Returns:
        dict: Attestation verification details
        
    Raises:
        HTTPException: If attestation is not verified
    """
    # Check if attestation was verified by middleware
    if not getattr(request.state, 'attestation_verified', False):
        raise HTTPException(
            status_code=401,
            detail="Mobile app attestation required"
        )
    
    return {
        "platform": getattr(request.state, 'platform', None),
        "verified": True
    }