"""
Examples of how to use the Redis caching system in the Panic System Platform
"""
import asyncio
import uuid
from typing import List, Dict, Any

from app.core.cache import (
    cache_result, 
    cache_invalidate, 
    enhanced_cache,
    invalidate_user_cache,
    invalidate_firm_cache,
    CacheKey
)


# Example 1: Using the @cache_result decorator
@cache_result(expire=3600, key_prefix="user_profile")
async def get_user_profile(user_id: str) -> Dict[str, Any]:
    """
    Example function that caches user profile data for 1 hour
    """
    # Simulate database query
    await asyncio.sleep(0.1)  # Simulate DB latency
    
    return {
        "user_id": user_id,
        "name": "John Doe",
        "email": "john@example.com",
        "subscription_count": 3,
        "last_login": "2024-08-24T10:00:00Z"
    }


# Example 2: Using cache invalidation decorator
@cache_invalidate("user_profile:*", "user_subscriptions:*")
async def update_user_profile(user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Example function that invalidates related caches after updating user profile
    """
    # Simulate database update
    await asyncio.sleep(0.05)
    
    # After updating, invalidate related caches
    await invalidate_user_cache(user_id)
    
    return {"user_id": user_id, "updated": True, **updates}


# Example 3: Manual cache operations
async def get_security_firm_coverage_areas(firm_id: str) -> List[Dict[str, Any]]:
    """
    Example of manual cache operations for complex data
    """
    cache_key = CacheKey.coverage_areas(firm_id)
    
    # Try to get from cache first
    cached_areas = await enhanced_cache.get(cache_key)
    if cached_areas is not None:
        print(f"Cache hit for firm {firm_id}")
        return cached_areas
    
    print(f"Cache miss for firm {firm_id}, fetching from database")
    
    # Simulate database query
    await asyncio.sleep(0.2)
    coverage_areas = [
        {
            "id": str(uuid.uuid4()),
            "name": "Downtown Area",
            "boundary": "POLYGON((...))"
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Suburban Area", 
            "boundary": "POLYGON((...))"
        }
    ]
    
    # Cache the result for 30 minutes
    await enhanced_cache.set(cache_key, coverage_areas, expire=1800)
    
    return coverage_areas


# Example 4: Session management
async def create_user_session_example(user_id: str) -> str:
    """
    Example of creating and managing user sessions
    """
    session_data = {
        "role": "user",
        "permissions": ["read_profile", "create_emergency_request"],
        "firm_id": str(uuid.uuid4()),
        "login_time": "2024-08-24T10:00:00Z"
    }
    
    session_id = await enhanced_cache.session_manager.create_session(user_id, session_data)
    print(f"Created session {session_id} for user {user_id}")
    
    return session_id


async def get_user_session_example(session_id: str) -> Dict[str, Any]:
    """
    Example of retrieving session data
    """
    session_data = await enhanced_cache.session_manager.get_session(session_id)
    if session_data:
        print(f"Retrieved session data: {session_data}")
        return session_data
    else:
        print("Session not found or expired")
        return {}


# Example 5: Cache warming
async def warm_critical_data_example():
    """
    Example of warming critical cache data
    """
    # Warm active subscription products
    products = [
        {"id": str(uuid.uuid4()), "name": "Basic Security", "price": 29.99},
        {"id": str(uuid.uuid4()), "name": "Premium Security", "price": 49.99},
        {"id": str(uuid.uuid4()), "name": "Enterprise Security", "price": 99.99}
    ]
    
    cache_key = CacheKey.generate("active_products")
    await enhanced_cache.set(cache_key, products, expire=1800)
    print(f"Warmed cache with {len(products)} products")
    
    # Warm user groups for a specific user
    user_id = str(uuid.uuid4())
    user_groups = [
        {"id": str(uuid.uuid4()), "name": "Home", "address": "123 Main St"},
        {"id": str(uuid.uuid4()), "name": "Office", "address": "456 Business Ave"}
    ]
    
    cache_key = CacheKey.user_groups(user_id)
    await enhanced_cache.set(cache_key, user_groups, expire=1800)
    print(f"Warmed user groups cache for user {user_id}")


# Example 6: Cache invalidation patterns
async def invalidate_cache_patterns_example():
    """
    Example of invalidating cache using patterns
    """
    # Invalidate all user-related cache for a specific user
    user_id = str(uuid.uuid4())
    await invalidate_user_cache(user_id)
    print(f"Invalidated all cache for user {user_id}")
    
    # Invalidate all firm-related cache for a specific firm
    firm_id = str(uuid.uuid4())
    await invalidate_firm_cache(firm_id)
    print(f"Invalidated all cache for firm {firm_id}")
    
    # Invalidate specific patterns
    await enhanced_cache.invalidation.invalidate_pattern("product:*")
    print("Invalidated all product cache")
    
    await enhanced_cache.invalidation.invalidate_pattern("session:*")
    print("Invalidated all session cache")


# Example 7: Error handling with cache
async def cache_with_error_handling_example(user_id: str) -> Dict[str, Any]:
    """
    Example of proper error handling with cache operations
    """
    cache_key = CacheKey.generate("user_stats", user_id)
    
    try:
        # Try to get from cache
        cached_stats = await enhanced_cache.get(cache_key)
        if cached_stats is not None:
            return cached_stats
        
        # Simulate database query that might fail
        if user_id == "error_user":
            raise Exception("Database connection failed")
        
        # Generate stats
        user_stats = {
            "user_id": user_id,
            "total_requests": 15,
            "active_subscriptions": 2,
            "last_request": "2024-08-24T09:30:00Z"
        }
        
        # Cache the result
        await enhanced_cache.set(cache_key, user_stats, expire=900)
        
        return user_stats
        
    except Exception as e:
        print(f"Error getting user stats: {e}")
        # Return default stats if both cache and database fail
        return {
            "user_id": user_id,
            "total_requests": 0,
            "active_subscriptions": 0,
            "last_request": None,
            "error": "Data temporarily unavailable"
        }


# Example 8: Performance monitoring
async def cache_performance_example():
    """
    Example of monitoring cache performance
    """
    # Get cache statistics
    if enhanced_cache.client:
        try:
            info = await enhanced_cache.client.info()
            print("Redis Info:")
            print(f"  Memory usage: {info.get('used_memory_human', 'unknown')}")
            print(f"  Connected clients: {info.get('connected_clients', 0)}")
            print(f"  Total commands: {info.get('total_commands_processed', 0)}")
            
            # Count cache keys (be careful in production)
            keys = await enhanced_cache.client.keys("*")
            print(f"  Total cache keys: {len(keys)}")
            
        except Exception as e:
            print(f"Failed to get cache statistics: {e}")


async def main():
    """
    Run all cache examples
    """
    print("=== Redis Caching System Examples ===\n")
    
    # Initialize cache system (normally done in main.py)
    from app.core.cache import initialize_cache_system
    await initialize_cache_system()
    
    print("1. Cache result decorator example:")
    user_id = str(uuid.uuid4())
    
    # First call - cache miss
    profile1 = await get_user_profile(user_id)
    print(f"First call result: {profile1}")
    
    # Second call - cache hit
    profile2 = await get_user_profile(user_id)
    print(f"Second call result: {profile2}")
    print()
    
    print("2. Cache invalidation example:")
    await update_user_profile(user_id, {"name": "Jane Doe"})
    print()
    
    print("3. Manual cache operations example:")
    firm_id = str(uuid.uuid4())
    areas1 = await get_security_firm_coverage_areas(firm_id)
    areas2 = await get_security_firm_coverage_areas(firm_id)  # Should be cached
    print()
    
    print("4. Session management example:")
    session_id = await create_user_session_example(user_id)
    await get_user_session_example(session_id)
    print()
    
    print("5. Cache warming example:")
    await warm_critical_data_example()
    print()
    
    print("6. Cache invalidation patterns example:")
    await invalidate_cache_patterns_example()
    print()
    
    print("7. Error handling example:")
    stats1 = await cache_with_error_handling_example(user_id)
    print(f"Normal user stats: {stats1}")
    
    stats2 = await cache_with_error_handling_example("error_user")
    print(f"Error user stats: {stats2}")
    print()
    
    print("8. Performance monitoring example:")
    await cache_performance_example()
    print()
    
    print("=== Examples completed ===")


if __name__ == "__main__":
    asyncio.run(main())