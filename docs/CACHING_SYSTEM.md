# Redis Caching System Documentation

## Overview

The Panic System Platform implements a comprehensive Redis-based caching layer that provides:

- **Caching Decorators** for easy function result caching
- **Cache Invalidation Strategies** for maintaining data consistency
- **Session Management** with Redis for user sessions
- **Cache Warming** for pre-populating critical data
- **Performance Optimization** for frequently accessed data

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                        │
├─────────────────────────────────────────────────────────────┤
│  @cache_result    │  @cache_invalidate  │  Manual Cache Ops │
├─────────────────────────────────────────────────────────────┤
│                Enhanced Cache Service                       │
├─────────────────────────────────────────────────────────────┤
│ Invalidation │ Session Manager │ Cache Warmer │ Key Manager │
├─────────────────────────────────────────────────────────────┤
│                      Redis Client                          │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Enhanced Cache Service

The main caching service that provides:

```python
from app.core.cache import enhanced_cache

# Basic operations
await enhanced_cache.get(key, default=None)
await enhanced_cache.set(key, value, expire=3600)
await enhanced_cache.delete(*keys)
await enhanced_cache.exists(key)
await enhanced_cache.expire(key, seconds)
await enhanced_cache.ttl(key)
```

### 2. Caching Decorators

#### @cache_result

Automatically cache function results:

```python
from app.core.cache import cache_result

@cache_result(expire=3600, key_prefix="user_profile")
async def get_user_profile(user_id: str):
    # Expensive database operation
    return user_data
```

#### @cache_invalidate

Automatically invalidate cache patterns after function execution:

```python
from app.core.cache import cache_invalidate

@cache_invalidate("user_profile:*", "user_subscriptions:*")
async def update_user_profile(user_id: str, updates: dict):
    # Update database
    # Cache patterns are automatically invalidated
    return updated_user
```

### 3. Cache Key Management

Standardized cache key generation:

```python
from app.core.cache import CacheKey

# Predefined key patterns
user_key = CacheKey.user_subscriptions(user_id)
firm_key = CacheKey.coverage_areas(firm_id)
session_key = CacheKey.session(session_id)

# Dynamic key generation
custom_key = CacheKey.generate("prefix", arg1, arg2, param1="value1")
```

### 4. Cache Invalidation Strategies

#### Pattern-based Invalidation

```python
from app.core.cache import enhanced_cache

# Invalidate all keys matching pattern
await enhanced_cache.invalidation.invalidate_pattern("user:*")
```

#### Dependency-based Invalidation

```python
# Add cache dependencies
enhanced_cache.invalidation.add_dependency(
    "user:profile:123", 
    ["user:subscriptions:123", "user:groups:123"]
)

# Invalidate dependencies
await enhanced_cache.invalidation.invalidate_dependencies("user:profile:123")
```

#### Entity-specific Invalidation

```python
from app.core.cache import invalidate_user_cache, invalidate_firm_cache

# Invalidate all user-related cache
await invalidate_user_cache(user_id)

# Invalidate all firm-related cache
await invalidate_firm_cache(firm_id)
```

### 5. Session Management

Redis-based session management:

```python
from app.core.cache import enhanced_cache

session_manager = enhanced_cache.session_manager

# Create session
session_id = await session_manager.create_session(user_id, session_data)

# Get session
session_data = await session_manager.get_session(session_id)

# Update session
await session_manager.update_session(session_id, updates)

# Delete session
await session_manager.delete_session(session_id)
```

### 6. Cache Warming

Pre-populate critical data:

```python
from app.services.cache_warming import cache_warming_service

# Warm specific cache
await cache_warming_service.warm_specific_cache("active_products")

# Warm all caches
await cache_warming_service.warm_all_caches()

# Get cache statistics
stats = await cache_warming_service.get_cache_statistics()
```

## Configuration

### Redis Settings

Configure Redis connection in `app/core/config.py`:

```python
class Settings(BaseSettings):
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 3600  # Default TTL in seconds
```

### Cache TTL Guidelines

- **User profiles**: 1 hour (3600s)
- **User groups**: 30 minutes (1800s)
- **Active products**: 30 minutes (1800s)
- **Coverage areas**: 1 hour (3600s)
- **Session data**: 30 minutes (1800s)
- **Temporary data**: 15 minutes (900s)

## Usage Patterns

### 1. Service Layer Caching

```python
from app.core.cache import cache_result, invalidate_user_cache

class UserService:
    @cache_result(expire=3600, key_prefix="user_by_id")
    async def get_user_by_id(self, user_id: UUID):
        # Database query
        return user
    
    async def update_user_profile(self, user_id: UUID, updates: dict):
        # Update database
        result = await self._update_user_in_db(user_id, updates)
        
        # Invalidate user cache
        await invalidate_user_cache(user_id)
        
        return result
```

### 2. API Endpoint Caching

```python
from fastapi import APIRouter
from app.core.cache import enhanced_cache, CacheKey

router = APIRouter()

@router.get("/products")
async def get_active_products():
    cache_key = CacheKey.generate("active_products")
    
    # Try cache first
    cached_products = await enhanced_cache.get(cache_key)
    if cached_products:
        return cached_products
    
    # Fetch from database
    products = await fetch_products_from_db()
    
    # Cache for 30 minutes
    await enhanced_cache.set(cache_key, products, expire=1800)
    
    return products
```

### 3. Complex Data Caching

```python
async def get_user_dashboard_data(user_id: str):
    cache_key = CacheKey.generate("user_dashboard", user_id)
    
    cached_data = await enhanced_cache.get(cache_key)
    if cached_data:
        return cached_data
    
    # Aggregate data from multiple sources
    dashboard_data = {
        "user_profile": await get_user_profile(user_id),
        "active_subscriptions": await get_user_subscriptions(user_id),
        "recent_requests": await get_recent_emergency_requests(user_id),
        "statistics": await get_user_statistics(user_id)
    }
    
    # Cache for 15 minutes
    await enhanced_cache.set(cache_key, dashboard_data, expire=900)
    
    return dashboard_data
```

## Cache Management API

The system provides REST endpoints for cache management:

### Get Cache Statistics

```http
GET /api/v1/admin/cache/stats
```

### Invalidate Cache

```http
POST /api/v1/admin/cache/invalidate
Content-Type: application/json

{
  "patterns": ["user:*", "product:*"],
  "user_id": "user-uuid",
  "firm_id": "firm-uuid"
}
```

### Warm Cache

```http
POST /api/v1/admin/cache/warm
Content-Type: application/json

{
  "cache_names": ["active_products", "coverage_areas"]
}
```

### Health Check

```http
GET /api/v1/admin/cache/health
```

## Performance Considerations

### Cache Hit Rates

Monitor cache hit rates to optimize caching strategies:

```python
# Log cache hits/misses
@cache_result(expire=3600, key_prefix="expensive_operation")
async def expensive_operation(param):
    logger.info("Cache miss - executing expensive operation", param=param)
    return result
```

### Memory Usage

- Monitor Redis memory usage
- Set appropriate TTL values
- Use cache warming for critical data
- Implement cache eviction policies

### Key Naming Conventions

- Use consistent prefixes: `user:`, `firm:`, `product:`
- Include entity IDs: `user:profile:123`
- Use descriptive names: `user:active_subscriptions:123`
- Avoid special characters in keys

## Error Handling

The caching system includes comprehensive error handling:

```python
async def get_data_with_fallback(key: str):
    try:
        # Try cache first
        cached_data = await enhanced_cache.get(key)
        if cached_data:
            return cached_data
        
        # Fetch from database
        data = await fetch_from_database()
        
        # Cache the result
        await enhanced_cache.set(key, data, expire=3600)
        
        return data
        
    except Exception as e:
        logger.error("Cache operation failed", error=str(e))
        # Fallback to database only
        return await fetch_from_database()
```

## Monitoring and Alerting

### Key Metrics to Monitor

- Cache hit rate
- Memory usage
- Connection count
- Command processing rate
- Key expiration rate

### Alerting Rules

- Memory usage > 80%
- Cache hit rate < 70%
- Connection failures
- High command latency

## Best Practices

1. **Use appropriate TTL values** based on data volatility
2. **Implement cache warming** for critical data
3. **Monitor cache performance** regularly
4. **Use consistent key naming** conventions
5. **Handle cache failures gracefully** with fallbacks
6. **Invalidate cache** when data changes
7. **Avoid caching large objects** (>1MB)
8. **Use compression** for large cached data
9. **Implement circuit breakers** for cache operations
10. **Test cache behavior** in your unit tests

## Troubleshooting

### Common Issues

1. **Cache misses**: Check TTL values and key generation
2. **Memory issues**: Monitor Redis memory usage and implement eviction
3. **Stale data**: Ensure proper cache invalidation
4. **Connection errors**: Check Redis connectivity and configuration
5. **Performance issues**: Monitor cache hit rates and optimize keys

### Debug Commands

```python
# Check if key exists
exists = await enhanced_cache.exists("user:profile:123")

# Get TTL for key
ttl = await enhanced_cache.ttl("user:profile:123")

# Get cache statistics
stats = await cache_warming_service.get_cache_statistics()
```

## Testing

The caching system includes comprehensive unit tests:

```bash
# Run cache system tests
python -m pytest tests/test_cache_system.py -v

# Run with coverage
python -m pytest tests/test_cache_system.py --cov=app.core.cache
```

## Examples

See `examples/cache_usage_examples.py` for complete usage examples demonstrating all caching features.