"""
Metrics middleware for automatic HTTP request tracking
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
from typing import Callable
from app.core.metrics import metrics_collector


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to automatically collect HTTP request metrics"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip metrics endpoint to avoid recursion
        if request.url.path == "/metrics":
            return await call_next(request)
        
        start_time = time.time()
        
        # Extract endpoint pattern for better grouping
        endpoint = self._get_endpoint_pattern(request)
        method = request.method
        
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            # Record error metrics
            status_code = 500
            # Re-raise the exception
            raise e
        finally:
            # Calculate request duration
            duration = time.time() - start_time
            
            # Record metrics
            metrics_collector.record_http_request(
                method=method,
                endpoint=endpoint,
                status_code=status_code,
                duration=duration
            )
        
        return response
    
    def _get_endpoint_pattern(self, request: Request) -> str:
        """Extract endpoint pattern from request for better metric grouping"""
        path = request.url.path
        
        # Group common patterns to avoid high cardinality
        if path.startswith("/api/v1/"):
            # Extract the main resource
            parts = path.split("/")
            if len(parts) >= 4:
                base_path = f"/api/v1/{parts[3]}"
                # Handle ID patterns
                if len(parts) > 4 and self._is_uuid_or_id(parts[4]):
                    return f"{base_path}/{{id}}"
                return base_path
        
        # Handle other common patterns
        if path == "/":
            return "/"
        elif path == "/health":
            return "/health"
        elif path == "/docs":
            return "/docs"
        elif path == "/openapi.json":
            return "/openapi.json"
        
        return path
    
    def _is_uuid_or_id(self, value: str) -> bool:
        """Check if a path segment looks like an ID"""
        # Check for UUID pattern
        if len(value) == 36 and value.count("-") == 4:
            return True
        # Check for numeric ID
        if value.isdigit():
            return True
        return False