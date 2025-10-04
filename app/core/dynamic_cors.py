"""
Dynamic CORS middleware that handles credentials properly
"""
import re
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from typing import List
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class DynamicCORSMiddleware(BaseHTTPMiddleware):
    """
    Dynamic CORS middleware that can handle wildcard origins with credentials
    by dynamically setting the Access-Control-Allow-Origin header to the requesting origin
    """
    
    def __init__(self, app, **kwargs):
        super().__init__(app)
        
        # Development environment patterns
        self.dev_patterns = [
            r'https://.*\.cloudworkstations\.dev',
            r'https://.*\.gitpod\.io', 
            r'https://.*\.github\.dev',
            r'https://.*\.codespaces\.github\.com',
            r'https://.*\.replit\.com',
            r'https://.*\.stackblitz\.com',
            r'http://localhost:\d+',
            r'https://localhost:\d+',
            r'http://127\.0\.0\.1:\d+',
            r'https://127\.0\.0\.1:\d+'
        ]
        
        # Compile patterns for performance
        self.compiled_patterns = [re.compile(pattern) for pattern in self.dev_patterns]
        
        # Static allowed origins
        self.static_origins = set(settings.ALLOWED_ORIGINS + settings.ADMIN_ALLOWED_ORIGINS)
    
    def is_allowed_origin(self, origin: str) -> bool:
        """Check if origin is allowed"""
        if not origin:
            return False
        
        # Check static origins first
        if origin in self.static_origins:
            return True
        
        # In development, check dynamic patterns
        if settings.DEBUG:
            for pattern in self.compiled_patterns:
                if pattern.match(origin):
                    return True
        
        return False
    
    def is_preflight_request(self, request: Request) -> bool:
        """Check if this is a CORS preflight request"""
        return (
            request.method == "OPTIONS" and
            "origin" in request.headers and
            "access-control-request-method" in request.headers
        )
    
    async def dispatch(self, request: Request, call_next):
        """Handle CORS for all requests"""
        origin = request.headers.get("origin")
        
        # Handle preflight requests
        if self.is_preflight_request(request):
            if origin and self.is_allowed_origin(origin):
                response = Response(status_code=200)
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
                response.headers["Access-Control-Allow-Headers"] = (
                    "Accept, Accept-Language, Content-Language, Content-Type, Authorization, "
                    "X-Requested-With, X-Platform, X-App-Version, X-Device-ID, X-Real-IP, User-Agent, "
                    "X-Client-Type"
                )
                response.headers["Access-Control-Max-Age"] = "86400"
                
                logger.debug(
                    "cors_preflight_allowed",
                    origin=origin,
                    path=request.url.path
                )
                
                return response
            else:
                logger.warning(
                    "cors_preflight_blocked",
                    origin=origin,
                    path=request.url.path
                )
                return Response(status_code=403, content="CORS: Origin not allowed")
        
        # Handle actual requests
        response = await call_next(request)
        
        # Add CORS headers to response if origin is allowed
        if origin and self.is_allowed_origin(origin):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Expose-Headers"] = (
                "Content-Length, Content-Range, X-Total-Count, X-Page-Count, "
                "X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset"
            )
            
            logger.debug(
                "cors_headers_added",
                origin=origin,
                path=request.url.path,
                status_code=response.status_code
            )
        
        return response