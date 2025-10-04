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
        
        # Patterns for development environment detection
        self.dev_origin_patterns = [
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
        
        # Patterns for admin/office staff endpoints
        self.admin_patterns = [
            r'/api/v1/admin/.*',
            r'/api/v1/auth/.*',  # Auth endpoints for admin login
            r'/api/v1/security-firms/.*',
            r'/api/v1/prank-detection/.*',
            r'/api/v1/cache-management/.*',
            r'/api/v1/database-optimization/.*',
            r'/api/v1/feedback/.*',
            r'/api/v1/credits/.*',
            r'/api/v1/emergency/.*',  # Emergency endpoints
            r'/api/v1/subscription-products/.*',  # Subscription product endpoints
            r'/api/v1/personnel/.*'  # Personnel endpoints
        ]
    
    def is_admin_endpoint(self, path: str) -> bool:
        """Check if the path is an admin endpoint"""
        for pattern in self.admin_patterns:
            if re.match(pattern, path):
                return True
        return False
    
    def is_dev_origin(self, origin: str) -> bool:
        """Check if origin matches development environment patterns"""
        if not origin:
            return False
        
        for pattern in self.dev_origin_patterns:
            if re.match(pattern, origin):
                return True
        return False
    
    def get_allowed_origins(self, request: Request) -> List[str]:
        """Get allowed origins based on the request path"""
        # In development mode, be more permissive
        if settings.DEBUG:
            origin = request.headers.get("origin", "")
            
            # Check if origin matches development patterns
            if self.is_dev_origin(origin):
                return self.all_origins + [origin]
        
        # Always return all origins to ensure access
        return self.all_origins
    
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
    # In development mode, use simple CORS setup that allows all localhost origins
    if settings.DEBUG:
        all_localhost_origins = (
            [f"http://localhost:{port}" for port in range(3000, 4000)] +
            [f"http://localhost:{port}" for port in range(4000, 4100)] +
            [f"https://localhost:{port}" for port in range(3000, 4000)] +
            [f"https://localhost:{port}" for port in range(4000, 4100)] +
            [f"http://127.0.0.1:{port}" for port in range(3000, 4000)] +
            [f"http://127.0.0.1:{port}" for port in range(4000, 4100)] +
            ["http://localhost:8080", "http://localhost:5173", "https://localhost:8080", "https://localhost:5173",
             "http://localhost:4010", "http://127.0.0.1:4010"]  # Explicitly add port 4010
        )
        
        # Add specific development environment origins
        dev_origins = [
            # Cloud Workstations
            "https://6000-firebase-studio-1758341768037.cluster-64pjnskmlbaxowh5lzq6i7v4ra.cloudworkstations.dev",
            # Add other common patterns - you can expand this as needed
            "https://codespaces.githubusercontent.com",
            "https://github.dev",
        ]
        
        # Combine all allowed origins
        all_origins = all_localhost_origins + dev_origins + settings.ALLOWED_ORIGINS + settings.ADMIN_ALLOWED_ORIGINS
        
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Allow all origins in development
            allow_credentials=False,  # Must be False when using "*"
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        # Add our custom role-based CORS middleware for production
        app.add_middleware(RoleBasedCORSMiddleware)
        
        # Also add the standard CORS middleware as fallback
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.ALLOWED_ORIGINS + settings.ADMIN_ALLOWED_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )