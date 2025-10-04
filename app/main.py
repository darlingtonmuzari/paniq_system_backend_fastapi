"""
Panic System Platform - Main FastAPI Application
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
# from app.core.cors_middleware import setup_cors_middleware
# from app.core.dynamic_cors import DynamicCORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_db
from app.core.redis import init_redis
from app.core.cache import initialize_cache_system
from app.services.cache_warming import warm_critical_caches, start_cache_warming_background_task
from app.api.v1.router import api_router
from app.core.exceptions import setup_exception_handlers
from app.core.middleware import (
    RequestLoggingMiddleware,
    MobileAttestationMiddleware,
    SecurityHeadersMiddleware
)
from app.core.rate_limiter import RateLimitMiddleware, SecurityHeadersMiddleware as RateLimitSecurityMiddleware
from app.core.metrics_middleware import MetricsMiddleware
from app.core.logging import get_logger, setup_logging

# Initialize logging system
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting Panic System Platform API")
    await init_db()
    await init_redis()
    await initialize_cache_system()
    await warm_critical_caches()
    await start_cache_warming_background_task()
    logger.info("API startup complete")

    yield

    # Shutdown
    logger.info("Shutting down Panic System Platform API")


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    app = FastAPI(
        title="Panic System Platform API",
        description="""
        ## Emergency Response Platform API
        
        The Panic System Platform connects security firms, emergency service providers, and end users 
        through a comprehensive emergency response system. This API enables:
        
        - **Security Firm Management**: Registration, verification, and service area definition
        - **User Registration**: Mobile number verification and group management
        - **Subscription System**: Credit-based subscription products and purchases
        - **Emergency Services**: Real-time panic request processing and coordination
        - **Mobile App Integration**: Secure mobile app attestation and authentication
        - **Performance Monitoring**: Response time tracking and analytics
        
        ### Authentication
        
        The API uses JWT tokens for authentication with mobile app attestation for enhanced security.
        All mobile endpoints require valid app attestation tokens from Google Play Integrity API (Android) 
        or Apple App Attest (iOS).
        
        ### Rate Limiting
        
        API endpoints are rate-limited to prevent abuse. Standard limits apply unless otherwise specified.
        
        ### Error Handling
        
        All errors follow a consistent format with error codes, messages, and contextual details.
        """,
        version="1.0.0",
        contact={
            "name": "Panic System Platform Support",
            "email": "support@panicsystem.com",
            "url": "https://panicsystem.com/support"
        },
        license_info={
            "name": "Proprietary",
            "url": "https://panicsystem.com/license"
        },
        terms_of_service="https://panicsystem.com/terms",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_tags=[
            {
                "name": "authentication",
                "description": "User authentication and token management with account protection"
            },
            {
                "name": "attestation", 
                "description": "Mobile app integrity verification"
            },
            {
                "name": "security-firms",
                "description": "Security firm registration and management"
            },
            {
                "name": "users",
                "description": "Registered user management and profiles"
            },
            {
                "name": "mobile-users",
                "description": "Mobile user operations with attestation"
            },
            {
                "name": "personnel",
                "description": "Firm personnel and team management"
            },
            {
                "name": "credits",
                "description": "Credit purchase and management system"
            },
            {
                "name": "mobile-subscriptions",
                "description": "Mobile subscription management with attestation"
            },
            {
                "name": "emergency",
                "description": "Emergency request processing and coordination"
            },
            {
                "name": "emergency-dashboard",
                "description": "Emergency dashboard for supervisors and office staff (no mobile attestation required)"
            },
            {
                "name": "feedback",
                "description": "Service feedback and prank detection"
            },
            {
                "name": "websocket",
                "description": "Real-time communication and updates"
            },
            {
                "name": "mobile-silent-mode",
                "description": "Mobile device ringer control for call services"
            },
            {
                "name": "prank-detection",
                "description": "Administrative prank detection and user fining"
            },
            {
                "name": "metrics",
                "description": "Performance metrics and analytics"
            },
            {
                "name": "cache-management",
                "description": "Administrative cache management"
            },
            {
                "name": "database-optimization",
                "description": "Administrative database optimization"
            },
            {
                "name": "log-management",
                "description": "Administrative log management and retention"
            }
        ],
        lifespan=lifespan,
    )

    # Middleware (order matters - last added is executed first)
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Use standard CORS middleware for development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:4010",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:4010",
            "https://localhost:3000",
            "https://localhost:4010",
            "https://127.0.0.1:3000", 
            "https://127.0.0.1:4010"
        ] + [f"http://localhost:{port}" for port in range(3000, 5000)] + [f"http://localhost:{port}" for port in range(8000, 8100)],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
    )
    
    # Security and rate limiting middleware  
    # app.add_middleware(RateLimitSecurityMiddleware)
    # app.add_middleware(RateLimitMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    # app.add_middleware(MobileAttestationMiddleware)  # Disable for CORS testing
    app.add_middleware(RequestLoggingMiddleware)
    
    # Metrics middleware (if enabled)
    if settings.METRICS_ENABLED:
        app.add_middleware(MetricsMiddleware)

    # Exception handlers
    setup_exception_handlers(app)

    # Routes
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "panic-system-platform"}

    @app.get("/api/v1/openapi.json", include_in_schema=False)
    async def get_openapi():
        """Get OpenAPI specification"""
        from fastapi.openapi.utils import get_openapi
        return get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )

    @app.get("/api/v1/docs", include_in_schema=False)
    async def get_documentation():
        """Redirect to interactive API documentation"""
        from fastapi.responses import HTMLResponse
        return HTMLResponse("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Panic System Platform API Documentation</title>
            <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@3.52.5/swagger-ui.css" />
            <style>
                html { box-sizing: border-box; overflow: -moz-scrollbars-vertical; overflow-y: scroll; }
                *, *:before, *:after { box-sizing: inherit; }
                body { margin:0; background: #fafafa; }
            </style>
        </head>
        <body>
            <div id="swagger-ui"></div>
            <script src="https://unpkg.com/swagger-ui-dist@3.52.5/swagger-ui-bundle.js"></script>
            <script>
                const ui = SwaggerUIBundle({
                    url: '/api/v1/openapi.json',
                    dom_id: '#swagger-ui',
                    presets: [
                        SwaggerUIBundle.presets.apis,
                        SwaggerUIBundle.presets.standalone
                    ],
                    layout: "StandaloneLayout",
                    deepLinking: true,
                    showExtensions: true,
                    showCommonExtensions: true,
                    tryItOutEnabled: true,
                    requestInterceptor: (request) => {
                        // Add custom headers for mobile endpoints
                        if (request.url.includes('/mobile/')) {
                            request.headers['X-Platform'] = 'web';
                            request.headers['X-Attestation-Token'] = 'demo-token';
                        }
                        return request;
                    }
                });
            </script>
        </body>
        </html>
        """)

    return app


app = create_app()
