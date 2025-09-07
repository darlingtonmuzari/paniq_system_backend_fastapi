"""
Redis caching layer with decorators, invalidation strategies, and session management
"""
import asyncio
import functools
import hashlib
import json
import pickle
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set, Union
import uuid

import redis.asyncio as redis
import structlog
from pydantic import BaseModel

from app.core.config import settings
from app.core.redis import get_redis

logger = structlog.get_logger()


class CacheKey:
    """Cache key generator and manager"""
    
    @staticmethod
    def generate(prefix: str, *args, **kwargs) -> str:
        """Generate cache key from prefix and arguments"""
        key_parts = [prefix]
        
        # Add positional arguments
        for arg in args:
            if isinstance(arg, (str, int, float, bool)):
                key_parts.append(str(arg))
            elif hasattr(arg, '__dict__'):
                # For objects, use their dict representation
                key_parts.append(hashlib.md5(str(sorted(arg.__dict__.items())).encode()).hexdigest()[:8])
            else:
                key_parts.append(hashlib.md5(str(arg).encode()).hexdigest()[:8])
        
        # Add keyword arguments
        if kwargs:
            sorted_kwargs = sorted(kwargs.items())
            kwargs_str = hashlib.md5(str(sorted_kwargs).encode()).hexdigest()[:8]
            key_parts.append(kwargs_str)
        
        return ":".join(key_parts)
    
    @staticmethod
    def user_subscriptions(user_id: Union[str, uuid.UUID]) -> str:
        return f"user:subscriptions:{user_id}"
    
    @staticmethod
    def coverage_areas(firm_id: Union[str, uuid.UUID]) -> str:
        return f"firm:coverage:{firm_id}"
    
    @staticmethod
    def subscription_product(product_id: Union[str, uuid.UUID]) -> str:
        return f"product:{product_id}"
    
    @staticmethod
    def user_groups(user_id: Union[str, uuid.UUID]) -> str:
        return f"user:groups:{user_id}"
    
    @staticmethod
    def firm_personnel(firm_id: Union[str, uuid.UUID]) -> str:
        return f"firm:personnel:{firm_id}"
    
    @staticmethod
    def session(session_id: str) -> str:
        return f"session:{session_id}"
    
    @staticmethod
    def user_session(user_id: Union[str, uuid.UUID]) -> str:
        return f"user:session:{user_id}"


class CacheInvalidationStrategy:
    """Cache invalidation strategies"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.dependency_map: Dict[str, Set[str]] = {}
    
    def add_dependency(self, cache_key: str, dependent_keys: List[str]):
        """Add cache dependencies"""
        if cache_key not in self.dependency_map:
            self.dependency_map[cache_key] = set()
        self.dependency_map[cache_key].update(dependent_keys)
    
    async def invalidate_pattern(self, pattern: str):
        """Invalidate all keys matching pattern"""
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
                logger.info("Cache invalidated", pattern=pattern, count=len(keys))
        except Exception as e:
            logger.error("Cache invalidation failed", pattern=pattern, error=str(e))
    
    async def invalidate_dependencies(self, cache_key: str):
        """Invalidate dependent cache keys"""
        if cache_key in self.dependency_map:
            dependent_keys = list(self.dependency_map[cache_key])
            if dependent_keys:
                await self.redis.delete(*dependent_keys)
                logger.info("Dependent cache keys invalidated", 
                          cache_key=cache_key, 
                          dependent_count=len(dependent_keys))
    
    async def invalidate_user_data(self, user_id: Union[str, uuid.UUID]):
        """Invalidate all user-related cache"""
        patterns = [
            f"user:*:{user_id}",
            f"user:{user_id}:*"
        ]
        for pattern in patterns:
            await self.invalidate_pattern(pattern)
    
    async def invalidate_firm_data(self, firm_id: Union[str, uuid.UUID]):
        """Invalidate all firm-related cache"""
        patterns = [
            f"firm:*:{firm_id}",
            f"firm:{firm_id}:*"
        ]
        for pattern in patterns:
            await self.invalidate_pattern(pattern)


class SessionManager:
    """Redis-based session management"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.session_ttl = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    
    async def create_session(self, user_id: Union[str, uuid.UUID], 
                           session_data: Dict[str, Any]) -> str:
        """Create a new session"""
        session_id = str(uuid.uuid4())
        session_key = CacheKey.session(session_id)
        user_session_key = CacheKey.user_session(user_id)
        
        # Store session data
        session_info = {
            "user_id": str(user_id),
            "created_at": datetime.utcnow().isoformat(),
            "last_accessed": datetime.utcnow().isoformat(),
            **session_data
        }
        
        await self.redis.setex(session_key, self.session_ttl, json.dumps(session_info))
        await self.redis.setex(user_session_key, self.session_ttl, session_id)
        
        logger.info("Session created", user_id=str(user_id), session_id=session_id)
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        session_key = CacheKey.session(session_id)
        session_data = await self.redis.get(session_key)
        
        if session_data:
            try:
                data = json.loads(session_data)
                # Update last accessed time
                data["last_accessed"] = datetime.utcnow().isoformat()
                await self.redis.setex(session_key, self.session_ttl, json.dumps(data))
                return data
            except json.JSONDecodeError:
                logger.error("Invalid session data", session_id=session_id)
        
        return None
    
    async def update_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """Update session data"""
        session_data = await self.get_session(session_id)
        if session_data:
            session_data.update(updates)
            session_key = CacheKey.session(session_id)
            await self.redis.setex(session_key, self.session_ttl, json.dumps(session_data))
            return True
        return False
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete session"""
        session_data = await self.get_session(session_id)
        if session_data:
            user_id = session_data.get("user_id")
            session_key = CacheKey.session(session_id)
            user_session_key = CacheKey.user_session(user_id)
            
            await self.redis.delete(session_key, user_session_key)
            logger.info("Session deleted", session_id=session_id, user_id=user_id)
            return True
        return False
    
    async def get_user_session(self, user_id: Union[str, uuid.UUID]) -> Optional[str]:
        """Get active session ID for user"""
        user_session_key = CacheKey.user_session(user_id)
        return await self.redis.get(user_session_key)
    
    async def delete_user_sessions(self, user_id: Union[str, uuid.UUID]) -> bool:
        """Delete all sessions for user"""
        session_id = await self.get_user_session(user_id)
        if session_id:
            return await self.delete_session(session_id)
        return False


class CacheWarmer:
    """Cache warming for critical data"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.warming_tasks: Dict[str, Callable] = {}
    
    def register_warmer(self, cache_key_pattern: str, warmer_func: Callable):
        """Register a cache warming function"""
        self.warming_tasks[cache_key_pattern] = warmer_func
    
    async def warm_cache(self, cache_key_pattern: str = None):
        """Warm cache for specific pattern or all registered patterns"""
        if cache_key_pattern:
            if cache_key_pattern in self.warming_tasks:
                await self.warming_tasks[cache_key_pattern]()
                logger.info("Cache warmed", pattern=cache_key_pattern)
        else:
            # Warm all registered caches
            for pattern, warmer_func in self.warming_tasks.items():
                try:
                    await warmer_func()
                    logger.info("Cache warmed", pattern=pattern)
                except Exception as e:
                    logger.error("Cache warming failed", pattern=pattern, error=str(e))
    
    async def schedule_warming(self, interval_seconds: int = 3600):
        """Schedule periodic cache warming"""
        while True:
            await asyncio.sleep(interval_seconds)
            await self.warm_cache()


class EnhancedCacheService:
    """Enhanced Redis caching service with advanced features"""
    
    def __init__(self):
        self.client: Optional[redis.Redis] = None
        self.invalidation: Optional[CacheInvalidationStrategy] = None
        self.session_manager: Optional[SessionManager] = None
        self.cache_warmer: Optional[CacheWarmer] = None
    
    async def initialize(self):
        """Initialize cache service components"""
        self.client = await get_redis()
        self.invalidation = CacheInvalidationStrategy(self.client)
        self.session_manager = SessionManager(self.client)
        self.cache_warmer = CacheWarmer(self.client)
        
        # Register cache warming functions
        await self._register_warmers()
    
    async def _register_warmers(self):
        """Register cache warming functions"""
        # These will be implemented based on actual service functions
        pass
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache with optional default"""
        try:
            value = await self.client.get(key)
            if value is not None:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    # Try pickle for complex objects
                    try:
                        return pickle.loads(value.encode('latin1'))
                    except:
                        return value
            return default
        except Exception as e:
            logger.error("Cache get failed", key=key, error=str(e))
            return default
    
    async def set(self, key: str, value: Any, expire: int = None, 
                  serialize_method: str = "json") -> bool:
        """Set value in cache with serialization options"""
        try:
            if expire is None:
                expire = settings.REDIS_CACHE_TTL
            
            if serialize_method == "json":
                if isinstance(value, (dict, list, str, int, float, bool, type(None))):
                    serialized_value = json.dumps(value)
                else:
                    # Fallback to pickle for complex objects
                    serialized_value = pickle.dumps(value).decode('latin1')
            else:
                serialized_value = pickle.dumps(value).decode('latin1')
            
            result = await self.client.setex(key, expire, serialized_value)
            return bool(result)
        except Exception as e:
            logger.error("Cache set failed", key=key, error=str(e))
            return False
    
    async def delete(self, *keys: str) -> int:
        """Delete one or more keys from cache"""
        try:
            return await self.client.delete(*keys)
        except Exception as e:
            logger.error("Cache delete failed", keys=keys, error=str(e))
            return 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            return bool(await self.client.exists(key))
        except Exception as e:
            logger.error("Cache exists check failed", key=key, error=str(e))
            return False
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration time for key"""
        try:
            return bool(await self.client.expire(key, seconds))
        except Exception as e:
            logger.error("Cache expire failed", key=key, error=str(e))
            return False
    
    async def ttl(self, key: str) -> int:
        """Get time to live for key"""
        try:
            return await self.client.ttl(key)
        except Exception as e:
            logger.error("Cache TTL check failed", key=key, error=str(e))
            return -1


# Global enhanced cache service instance
enhanced_cache = EnhancedCacheService()


def cache_result(expire: int = None, key_prefix: str = None, 
                invalidate_on: List[str] = None):
    """
    Decorator for caching function results
    
    Args:
        expire: Cache expiration time in seconds
        key_prefix: Custom prefix for cache key
        invalidate_on: List of events that should invalidate this cache
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            if key_prefix:
                cache_key = CacheKey.generate(key_prefix, *args, **kwargs)
            else:
                cache_key = CacheKey.generate(func.__name__, *args, **kwargs)
            
            # Try to get from cache first
            cached_result = await enhanced_cache.get(cache_key)
            if cached_result is not None:
                logger.debug("Cache hit", function=func.__name__, key=cache_key)
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            if result is not None:
                await enhanced_cache.set(cache_key, result, expire)
                logger.debug("Cache set", function=func.__name__, key=cache_key)
                
                # Register invalidation dependencies
                if invalidate_on and enhanced_cache.invalidation:
                    enhanced_cache.invalidation.add_dependency(cache_key, invalidate_on)
            
            return result
        
        return wrapper
    return decorator


def cache_invalidate(*patterns: str):
    """
    Decorator for invalidating cache patterns after function execution
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            
            # Invalidate cache patterns
            if enhanced_cache.invalidation:
                for pattern in patterns:
                    await enhanced_cache.invalidation.invalidate_pattern(pattern)
            
            return result
        
        return wrapper
    return decorator


async def initialize_cache_system():
    """Initialize the enhanced cache system"""
    await enhanced_cache.initialize()
    logger.info("Enhanced cache system initialized")


# Convenience functions for common cache operations
async def cache_user_data(user_id: Union[str, uuid.UUID], data: Dict[str, Any], 
                         expire: int = 3600):
    """Cache user-related data"""
    key = CacheKey.user_subscriptions(user_id)
    await enhanced_cache.set(key, data, expire)


async def invalidate_user_cache(user_id: Union[str, uuid.UUID]):
    """Invalidate all user-related cache"""
    if enhanced_cache.invalidation:
        await enhanced_cache.invalidation.invalidate_user_data(user_id)


async def cache_firm_data(firm_id: Union[str, uuid.UUID], data: Dict[str, Any], 
                         expire: int = 3600):
    """Cache firm-related data"""
    key = CacheKey.coverage_areas(firm_id)
    await enhanced_cache.set(key, data, expire)


async def invalidate_firm_cache(firm_id: Union[str, uuid.UUID]):
    """Invalidate all firm-related cache"""
    if enhanced_cache.invalidation:
        await enhanced_cache.invalidation.invalidate_firm_data(firm_id)