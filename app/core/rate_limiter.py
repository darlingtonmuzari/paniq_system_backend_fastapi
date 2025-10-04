"""
Rate limiting middleware for mobile authentication endpoints
"""
import json
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse
import structlog

from app.core.redis import cache
from app.core.config import settings

logger = structlog.get_logger()


class RateLimitExceeded(Exception):
    """Rate limit exceeded exception"""
    def __init__(self, retry_after: int, limit: int, window: int):
        self.retry_after = retry_after
        self.limit = limit
        self.window = window
        super().__init__(f"Rate limit exceeded. Limit: {limit} requests per {window} seconds")


class MobileAuthRateLimiter:
    """Rate limiter for mobile authentication endpoints"""
    
    # Rate limiting rules for different endpoints
    RATE_LIMITS = {
        "/auth/mobile/register": {"limit": 3, "window": 300},  # 3 registrations per 5 minutes
        "/auth/mobile/login": {"limit": 10, "window": 300},    # 10 login attempts per 5 minutes
        "/auth/mobile/verify-email": {"limit": 5, "window": 300},  # 5 verification attempts per 5 minutes
        "/auth/mobile/resend-verification": {"limit": 3, "window": 600},  # 3 resends per 10 minutes
        "/auth/mobile/password-reset/request": {"limit": 3, "window": 600},  # 3 reset requests per 10 minutes
        "/auth/mobile/password-reset/verify": {"limit": 5, "window": 300},  # 5 reset attempts per 5 minutes
    }
    
    # Global rate limits (per IP)
    GLOBAL_LIMITS = {
        "requests_per_minute": {"limit": 60, "window": 60},
        "auth_requests_per_hour": {"limit": 100, "window": 3600},
    }
    
    @staticmethod
    def get_client_key(request: Request, endpoint: str) -> str:
        """Get unique client key for rate limiting"""
        # Get client IP
        client_ip = request.headers.get("X-Real-IP") or request.client.host
        
        # Get additional identifying information
        user_agent = request.headers.get("User-Agent", "")
        device_id = None
        
        # Try to extract device ID from request body for mobile endpoints
        if hasattr(request, "_json") and request._json:
            if isinstance(request._json, dict):
                device_info = request._json.get("device_info", {})
                if isinstance(device_info, dict):
                    device_id = device_info.get("device_id")
        
        # Create composite key
        key_parts = [client_ip, endpoint]
        if device_id:
            key_parts.append(device_id)
        else:
            # Use hash of user agent as fallback
            key_parts.append(hashlib.md5(user_agent.encode()).hexdigest()[:8])
        
        return ":".join(key_parts)
    
    @staticmethod
    async def check_rate_limit(
        key: str, 
        limit: int, 
        window: int,
        endpoint: str = None
    ) -> Dict[str, Any]:
        """Check if request is within rate limits"""
        try:
            current_time = datetime.now()
            window_start = current_time - timedelta(seconds=window)
            
            # Get current request count
            cache_key = f"rate_limit:{key}"
            request_data = await cache.get(cache_key)
            
            if request_data:
                requests = request_data  # Cache service already decoded JSON
                # Filter requests within current window
                valid_requests = [
                    req_time for req_time in requests 
                    if datetime.fromisoformat(req_time) > window_start
                ]
            else:
                valid_requests = []
            
            # Check if limit exceeded
            if len(valid_requests) >= limit:
                # Calculate retry after time
                oldest_request = min(valid_requests)
                retry_after = int((datetime.fromisoformat(oldest_request) + timedelta(seconds=window) - current_time).total_seconds())
                
                logger.warning(
                    "rate_limit_exceeded",
                    key=key,
                    endpoint=endpoint,
                    current_count=len(valid_requests),
                    limit=limit,
                    window=window,
                    retry_after=retry_after
                )
                
                return {
                    "allowed": False,
                    "current_count": len(valid_requests),
                    "limit": limit,
                    "window": window,
                    "retry_after": retry_after
                }
            
            # Add current request
            valid_requests.append(current_time.isoformat())
            
            # Store updated request list
            await cache.set(cache_key, valid_requests, expire=window)
            
            logger.debug(
                "rate_limit_check_passed",
                key=key,
                endpoint=endpoint,
                current_count=len(valid_requests),
                limit=limit,
                window=window
            )
            
            return {
                "allowed": True,
                "current_count": len(valid_requests),
                "limit": limit,
                "window": window,
                "remaining": limit - len(valid_requests)
            }
            
        except Exception as e:
            logger.error(
                "rate_limit_check_error",
                key=key,
                endpoint=endpoint,
                error=str(e),
                exc_info=True
            )
            # Allow request on error (fail open)
            return {
                "allowed": True,
                "current_count": 0,
                "limit": limit,
                "window": window,
                "remaining": limit,
                "error": str(e)
            }
    
    @classmethod
    async def check_endpoint_rate_limit(cls, request: Request, endpoint: str) -> Dict[str, Any]:
        """Check rate limit for specific endpoint"""
        rate_config = cls.RATE_LIMITS.get(endpoint)
        if not rate_config:
            return {"allowed": True, "current_count": 0, "limit": 0, "window": 0}
        
        client_key = cls.get_client_key(request, endpoint)
        return await cls.check_rate_limit(
            key=client_key,
            limit=rate_config["limit"],
            window=rate_config["window"],
            endpoint=endpoint
        )
    
    @classmethod
    async def check_global_rate_limits(cls, request: Request) -> Dict[str, Any]:
        """Check global rate limits"""
        client_ip = request.headers.get("X-Real-IP") or request.client.host
        
        # Check requests per minute
        rpm_result = await cls.check_rate_limit(
            key=f"global:rpm:{client_ip}",
            limit=cls.GLOBAL_LIMITS["requests_per_minute"]["limit"],
            window=cls.GLOBAL_LIMITS["requests_per_minute"]["window"],
            endpoint="global_rpm"
        )
        
        if not rpm_result["allowed"]:
            return rpm_result
        
        # Check auth requests per hour for auth endpoints
        if "/auth/" in str(request.url):
            auth_result = await cls.check_rate_limit(
                key=f"global:auth:{client_ip}",
                limit=cls.GLOBAL_LIMITS["auth_requests_per_hour"]["limit"],
                window=cls.GLOBAL_LIMITS["auth_requests_per_hour"]["window"],
                endpoint="global_auth_hourly"
            )
            
            if not auth_result["allowed"]:
                return auth_result
        
        return {"allowed": True}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware for FastAPI"""
    
    async def dispatch(self, request: Request, call_next):
        # Handle CORS preflight requests for mobile endpoints
        if request.method == "OPTIONS" and "/auth/mobile/" in request.url.path:
            response = Response(status_code=200)
            origin = request.headers.get("origin", "*")
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            response.headers["Access-Control-Allow-Headers"] = (
                "Accept, Accept-Language, Content-Language, Content-Type, Authorization, "
                "X-Requested-With, X-Platform, X-App-Version, X-Device-ID, X-Real-IP"
            )
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Max-Age"] = "86400"
            return response
        
        # Skip rate limiting for non-mobile auth endpoints
        path = request.url.path
        
        # Store request body for device ID extraction
        if request.method == "POST" and "/auth/mobile/" in path:
            try:
                body = await request.body()
                if body:
                    request._json = json.loads(body.decode())
                # Recreate request with body
                request._stream = iter([body])
            except:
                request._json = None
        
        # Check global rate limits first
        global_limit_result = await MobileAuthRateLimiter.check_global_rate_limits(request)
        if not global_limit_result["allowed"]:
            logger.warning(
                "global_rate_limit_exceeded",
                path=path,
                client_ip=request.headers.get("X-Real-IP") or request.client.host,
                limit_info=global_limit_result
            )
            
            return StarletteResponse(
                content=json.dumps({
                    "error": "Too many requests",
                    "message": "Global rate limit exceeded",
                    "retry_after": global_limit_result.get("retry_after", 60),
                    "limit": global_limit_result.get("limit"),
                    "window": global_limit_result.get("window")
                }),
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={
                    "Content-Type": "application/json",
                    "Retry-After": str(global_limit_result.get("retry_after", 60)),
                    "X-RateLimit-Limit": str(global_limit_result.get("limit", 0)),
                    "X-RateLimit-Remaining": str(global_limit_result.get("remaining", 0)),
                    "X-RateLimit-Reset": str(global_limit_result.get("window", 60))
                }
            )
        
        # Check endpoint-specific rate limits for mobile auth endpoints
        if "/auth/mobile/" in path:
            endpoint_limit_result = await MobileAuthRateLimiter.check_endpoint_rate_limit(request, path)
            
            if not endpoint_limit_result["allowed"]:
                logger.warning(
                    "endpoint_rate_limit_exceeded",
                    path=path,
                    client_ip=request.headers.get("X-Real-IP") or request.client.host,
                    limit_info=endpoint_limit_result
                )
                
                return StarletteResponse(
                    content=json.dumps({
                        "error": "Too many requests",
                        "message": f"Rate limit exceeded for {path}",
                        "retry_after": endpoint_limit_result.get("retry_after", 60),
                        "limit": endpoint_limit_result.get("limit"),
                        "window": endpoint_limit_result.get("window")
                    }),
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    headers={
                        "Content-Type": "application/json",
                        "Retry-After": str(endpoint_limit_result.get("retry_after", 60)),
                        "X-RateLimit-Limit": str(endpoint_limit_result.get("limit", 0)),
                        "X-RateLimit-Remaining": str(endpoint_limit_result.get("remaining", 0)),
                        "X-RateLimit-Reset": str(endpoint_limit_result.get("window", 60))
                    }
                )
        
        # Proceed with request
        response = await call_next(request)
        
        # Add rate limit headers to successful responses
        if "/auth/mobile/" in path and hasattr(request, "_rate_limit_info"):
            info = request._rate_limit_info
            response.headers["X-RateLimit-Limit"] = str(info.get("limit", 0))
            response.headers["X-RateLimit-Remaining"] = str(info.get("remaining", 0))
            response.headers["X-RateLimit-Reset"] = str(info.get("window", 60))
        
        return response


# Security headers middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=self"
        
        # Add CSP for mobile auth endpoints
        if "/auth/mobile/" in request.url.path:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "connect-src 'self'; "
                "font-src 'self'; "
                "object-src 'none'; "
                "base-uri 'self';"
            )
        
        return response


# Audit logging for sensitive operations
async def log_sensitive_operation(
    operation: str,
    user_id: Optional[str] = None,
    email: Optional[str] = None,
    device_id: Optional[str] = None,
    client_ip: Optional[str] = None,
    success: bool = True,
    additional_data: Optional[Dict[str, Any]] = None
):
    """Log sensitive authentication operations for audit trail"""
    try:
        audit_data = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "user_id": user_id,
            "email": email,
            "device_id": device_id,
            "client_ip": client_ip,
            "success": success,
            "additional_data": additional_data or {}
        }
        
        # Store in Redis with longer TTL for audit purposes
        audit_key = f"audit:{operation}:{datetime.now().strftime('%Y%m%d')}:{hashlib.md5(str(audit_data).encode()).hexdigest()[:8]}"
        await cache.set(audit_key, audit_data, expire=86400 * 30)  # 30 days
        
        logger.info(
            "sensitive_operation_logged",
            operation=operation,
            user_id=user_id,
            email=email,
            device_id=device_id,
            success=success
        )
        
    except Exception as e:
        logger.error(
            "audit_logging_failed",
            operation=operation,
            error=str(e),
            exc_info=True
        )