"""
Custom CORS middleware for role-based origin access
"""
from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse
from typing import List
import re

from app.core.config import settings


class RoleBasedCORSMiddleware(BaseHTTPMiddleware):
    """
    Custom CORS middleware that allows different origins based on the endpoint being accessed
    """
    
    def __init__(self, app, **kwargs):
        super().__init__(app)
        self.default_origins = settings.ALLOWED_ORIGINS
        self.admin_origins = settings.ADMIN_ALLOWED_ORIGINS
        self.all_origins = list(set(self.default_origins + self.admin_origins))
        
        # Patterns for admin/office staff endpoints
        self.admin_patterns = [
            r'/api/v1/admin/.*',
            r'/api/v1/auth/.*',  # Auth endpoints for admin login
            r'/api/v1/security-firms/.*',
            r'/api/v1/prank-detection/.*',
            r'/api/v1/cache-management/.*',
            r'/api/v1/database-optimization/.*',
            r'/api/v1/feedback/.*',
            r'/api/v1/credits/.*'
        ]
    
    def is_admin_endpoint(self, path: str) -> bool:
        """Check if the path is an admin endpoint"""
        for pattern in self.admin_patterns:
            if re.match(pattern, path):
                return True
        return False
    
    def get_allowed_origins(self, request: Request) -> List[str]:
        """Get allowed origins based on the request path"""
        if self.is_admin_endpoint(request.url.path):
            return self.all_origins  # Allow both regular and admin origins
        return self.default_origins  # Only allow regular origins
    
    def is_cors_preflight(self, request: Request) -> bool:
        """Check if this is a CORS preflight request"""
        return (
            request.method == "OPTIONS" and
            "origin" in request.headers and
            "access-control-request-method" in request.headers
        )
    
    def add_cors_headers(self, response: StarletteResponse, origin: str, is_preflight: bool = False) -> None:
        """Add CORS headers to response"""
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        
        if is_preflight:
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            response.headers["Access-Control-Allow-Headers"] = (
                "Accept, Accept-Language, Content-Language, Content-Type, Authorization, "
                "X-Requested-With, X-Platform, X-App-Version, X-Device-ID"
            )
            response.headers["Access-Control-Max-Age"] = "86400"  # 24 hours
        else:
            response.headers["Access-Control-Expose-Headers"] = (
                "Content-Length, Content-Range, X-Total-Count, X-Page-Count"
            )
    
    async def dispatch(self, request: Request, call_next):
        """Process the request and add appropriate CORS headers"""
        origin = request.headers.get("origin")
        
        if origin:
            allowed_origins = self.get_allowed_origins(request)
            
            # Check if origin is allowed
            if origin in allowed_origins:
                # Handle preflight requests
                if self.is_cors_preflight(request):
                    response = StarletteResponse(status_code=200)
                    self.add_cors_headers(response, origin, is_preflight=True)
                    return response
                
                # Handle actual requests
                response = await call_next(request)
                self.add_cors_headers(response, origin, is_preflight=False)
                return response
            else:
                # Origin not allowed
                if self.is_cors_preflight(request):
                    return StarletteResponse(status_code=403, content="CORS: Origin not allowed")
        
        # No origin header or origin not in allowed list, proceed normally
        response = await call_next(request)
        return response


def setup_cors_middleware(app):
    """Setup CORS middleware for the application"""
    # Add our custom role-based CORS middleware
    app.add_middleware(RoleBasedCORSMiddleware)
    
    # Also add the standard CORS middleware as fallback
    # This will handle cases where our custom middleware doesn't apply
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS + settings.ADMIN_ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )