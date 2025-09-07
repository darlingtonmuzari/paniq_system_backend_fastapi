"""
Redis configuration and connection management
"""
import redis.asyncio as redis
from typing import Optional, Any
import json
import structlog

from app.core.config import settings

logger = structlog.get_logger()

# Redis connection pool
redis_pool: Optional[redis.ConnectionPool] = None
redis_client: Optional[redis.Redis] = None


async def init_redis():
    """Initialize Redis connection"""
    global redis_pool, redis_client
    
    try:
        redis_pool = redis.ConnectionPool.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=20
        )
        redis_client = redis.Redis(connection_pool=redis_pool)
        
        # Test connection
        await redis_client.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.error("Failed to connect to Redis", error=str(e))
        raise


async def get_redis() -> redis.Redis:
    """Get Redis client"""
    if redis_client is None:
        raise RuntimeError("Redis not initialized")
    return redis_client


class CacheService:
    """Redis caching service"""
    
    def __init__(self):
        self.client = None
    
    async def get_client(self) -> redis.Redis:
        if self.client is None:
            self.client = await get_redis()
        return self.client
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        client = await self.get_client()
        value = await client.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None
    
    async def set(self, key: str, value: Any, expire: int = None) -> bool:
        """Set value in cache"""
        client = await self.get_client()
        if expire is None:
            expire = settings.REDIS_CACHE_TTL
        
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        
        return await client.setex(key, expire, value)
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        client = await self.get_client()
        return bool(await client.delete(key))
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        client = await self.get_client()
        return bool(await client.exists(key))


# Global cache service instance
cache = CacheService()