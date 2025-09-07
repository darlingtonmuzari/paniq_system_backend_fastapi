"""
Cache management API endpoints
"""
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel

from app.core.cache import enhanced_cache, invalidate_user_cache, invalidate_firm_cache
from app.services.cache_warming import cache_warming_service
from app.core.auth import get_current_user
from app.models.user import RegisteredUser
import structlog

logger = structlog.get_logger()

router = APIRouter(prefix="/cache", tags=["cache"])


class CacheInvalidationRequest(BaseModel):
    """Request model for cache invalidation"""
    patterns: List[str]
    user_id: Optional[str] = None
    firm_id: Optional[str] = None


class CacheWarmingRequest(BaseModel):
    """Request model for cache warming"""
    cache_names: Optional[List[str]] = None  # If None, warm all caches


class CacheStatsResponse(BaseModel):
    """Response model for cache statistics"""
    cache_keys_count: int
    memory_usage: str
    connected_clients: int
    total_commands_processed: int
    warming_functions: List[str]


@router.get("/stats", response_model=CacheStatsResponse)
async def get_cache_statistics(
    current_user: RegisteredUser = Depends(get_current_user)
):
    """
    Get cache statistics and health information
    
    Requires authentication.
    """
    try:
        stats = await cache_warming_service.get_cache_statistics()
        return CacheStatsResponse(**stats)
    except Exception as e:
        logger.error("Failed to get cache statistics", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cache statistics"
        )


@router.post("/invalidate")
async def invalidate_cache(
    request: CacheInvalidationRequest,
    current_user: RegisteredUser = Depends(get_current_user)
):
    """
    Invalidate cache patterns or user/firm specific caches
    
    Requires authentication.
    """
    try:
        invalidated_count = 0
        
        # Invalidate specific patterns
        if request.patterns:
            for pattern in request.patterns:
                await enhanced_cache.invalidation.invalidate_pattern(pattern)
                invalidated_count += 1
        
        # Invalidate user-specific cache
        if request.user_id:
            await invalidate_user_cache(request.user_id)
            invalidated_count += 1
        
        # Invalidate firm-specific cache
        if request.firm_id:
            await invalidate_firm_cache(request.firm_id)
            invalidated_count += 1
        
        logger.info("Cache invalidation completed", 
                   patterns=request.patterns,
                   user_id=request.user_id,
                   firm_id=request.firm_id,
                   invalidated_count=invalidated_count)
        
        return {
            "success": True,
            "message": f"Invalidated {invalidated_count} cache patterns/entities",
            "invalidated_patterns": request.patterns,
            "user_id": request.user_id,
            "firm_id": request.firm_id
        }
    
    except Exception as e:
        logger.error("Cache invalidation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cache invalidation failed"
        )


@router.post("/warm")
async def warm_cache(
    request: CacheWarmingRequest,
    current_user: RegisteredUser = Depends(get_current_user)
):
    """
    Warm specific caches or all caches
    
    Requires authentication.
    """
    try:
        if request.cache_names:
            # Warm specific caches
            warmed_caches = []
            for cache_name in request.cache_names:
                try:
                    await cache_warming_service.warm_specific_cache(cache_name)
                    warmed_caches.append(cache_name)
                except ValueError as e:
                    logger.warning("Unknown cache name", cache_name=cache_name, error=str(e))
                except Exception as e:
                    logger.error("Cache warming failed", cache_name=cache_name, error=str(e))
            
            return {
                "success": True,
                "message": f"Warmed {len(warmed_caches)} caches",
                "warmed_caches": warmed_caches,
                "failed_caches": list(set(request.cache_names) - set(warmed_caches))
            }
        else:
            # Warm all caches
            await cache_warming_service.warm_all_caches()
            
            return {
                "success": True,
                "message": "All caches warmed successfully",
                "warmed_caches": list(cache_warming_service.warming_functions.keys())
            }
    
    except Exception as e:
        logger.error("Cache warming failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cache warming failed"
        )


@router.get("/keys/{pattern}")
async def get_cache_keys(
    pattern: str,
    current_user: RegisteredUser = Depends(get_current_user)
):
    """
    Get cache keys matching a pattern
    
    Requires authentication.
    Use with caution in production as this can be expensive.
    """
    try:
        if not enhanced_cache.client:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Cache service not available"
            )
        
        keys = await enhanced_cache.client.keys(pattern)
        
        return {
            "pattern": pattern,
            "keys": keys[:100],  # Limit to first 100 keys
            "total_count": len(keys),
            "truncated": len(keys) > 100
        }
    
    except Exception as e:
        logger.error("Failed to get cache keys", pattern=pattern, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cache keys"
        )


@router.get("/key/{key}")
async def get_cache_value(
    key: str,
    current_user: RegisteredUser = Depends(get_current_user)
):
    """
    Get value for a specific cache key
    
    Requires authentication.
    """
    try:
        value = await enhanced_cache.get(key)
        ttl = await enhanced_cache.ttl(key)
        
        return {
            "key": key,
            "value": value,
            "exists": value is not None,
            "ttl": ttl,
            "expires_in_seconds": ttl if ttl > 0 else None
        }
    
    except Exception as e:
        logger.error("Failed to get cache value", key=key, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cache value"
        )


@router.delete("/key/{key}")
async def delete_cache_key(
    key: str,
    current_user: RegisteredUser = Depends(get_current_user)
):
    """
    Delete a specific cache key
    
    Requires authentication.
    """
    try:
        deleted_count = await enhanced_cache.delete(key)
        
        return {
            "key": key,
            "deleted": deleted_count > 0,
            "message": f"Key {'deleted' if deleted_count > 0 else 'not found'}"
        }
    
    except Exception as e:
        logger.error("Failed to delete cache key", key=key, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete cache key"
        )


@router.get("/health")
async def cache_health_check():
    """
    Check cache system health
    
    Public endpoint for health monitoring.
    """
    try:
        if not enhanced_cache.client:
            return {
                "status": "unhealthy",
                "message": "Cache client not initialized"
            }
        
        # Test basic Redis operations
        test_key = "health_check_test"
        test_value = "ok"
        
        # Test set
        set_result = await enhanced_cache.set(test_key, test_value, expire=60)
        if not set_result:
            return {
                "status": "unhealthy",
                "message": "Failed to set test key"
            }
        
        # Test get
        get_result = await enhanced_cache.get(test_key)
        if get_result != test_value:
            return {
                "status": "unhealthy",
                "message": "Failed to get test key"
            }
        
        # Test delete
        delete_result = await enhanced_cache.delete(test_key)
        if delete_result == 0:
            return {
                "status": "unhealthy",
                "message": "Failed to delete test key"
            }
        
        return {
            "status": "healthy",
            "message": "Cache system is operational",
            "components": {
                "redis_client": "ok",
                "invalidation_strategy": "ok" if enhanced_cache.invalidation else "not_initialized",
                "session_manager": "ok" if enhanced_cache.session_manager else "not_initialized",
                "cache_warmer": "ok" if enhanced_cache.cache_warmer else "not_initialized"
            }
        }
    
    except Exception as e:
        logger.error("Cache health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "message": f"Cache health check failed: {str(e)}"
        }