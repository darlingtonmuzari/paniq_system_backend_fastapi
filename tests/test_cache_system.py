"""
Unit tests for Redis caching system
"""
import asyncio
import json
import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.cache import (
    CacheKey,
    CacheInvalidationStrategy,
    SessionManager,
    CacheWarmer,
    EnhancedCacheService,
    cache_result,
    cache_invalidate,
    initialize_cache_system,
    enhanced_cache
)


class TestCacheKey:
    """Test cache key generation"""
    
    def test_generate_simple_key(self):
        """Test simple cache key generation"""
        key = CacheKey.generate("test", "arg1", "arg2")
        assert key == "test:arg1:arg2"
    
    def test_generate_key_with_kwargs(self):
        """Test cache key generation with keyword arguments"""
        key = CacheKey.generate("test", "arg1", param1="value1", param2="value2")
        # Should include a hash of the sorted kwargs
        assert key.startswith("test:arg1:")
        assert len(key.split(":")) == 3
    
    def test_generate_key_with_objects(self):
        """Test cache key generation with objects"""
        class TestObj:
            def __init__(self):
                self.attr1 = "value1"
                self.attr2 = "value2"
        
        obj = TestObj()
        key = CacheKey.generate("test", obj)
        assert key.startswith("test:")
        assert len(key.split(":")) == 2
    
    def test_user_subscriptions_key(self):
        """Test user subscriptions cache key"""
        user_id = uuid.uuid4()
        key = CacheKey.user_subscriptions(user_id)
        assert key == f"user:subscriptions:{user_id}"
    
    def test_coverage_areas_key(self):
        """Test coverage areas cache key"""
        firm_id = uuid.uuid4()
        key = CacheKey.coverage_areas(firm_id)
        assert key == f"firm:coverage:{firm_id}"
    
    def test_session_key(self):
        """Test session cache key"""
        session_id = "test-session-123"
        key = CacheKey.session(session_id)
        assert key == f"session:{session_id}"


class TestCacheInvalidationStrategy:
    """Test cache invalidation strategies"""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client"""
        redis_mock = AsyncMock()
        return redis_mock
    
    @pytest.fixture
    def invalidation_strategy(self, mock_redis):
        """Create invalidation strategy with mock Redis"""
        return CacheInvalidationStrategy(mock_redis)
    
    @pytest.mark.asyncio
    async def test_add_dependency(self, invalidation_strategy):
        """Test adding cache dependencies"""
        cache_key = "test:key"
        dependent_keys = ["dep1", "dep2"]
        
        invalidation_strategy.add_dependency(cache_key, dependent_keys)
        
        assert cache_key in invalidation_strategy.dependency_map
        assert invalidation_strategy.dependency_map[cache_key] == set(dependent_keys)
    
    @pytest.mark.asyncio
    async def test_invalidate_pattern(self, invalidation_strategy, mock_redis):
        """Test pattern-based cache invalidation"""
        pattern = "user:*"
        keys = ["user:123", "user:456"]
        mock_redis.keys.return_value = keys
        mock_redis.delete.return_value = len(keys)
        
        await invalidation_strategy.invalidate_pattern(pattern)
        
        mock_redis.keys.assert_called_once_with(pattern)
        mock_redis.delete.assert_called_once_with(*keys)
    
    @pytest.mark.asyncio
    async def test_invalidate_dependencies(self, invalidation_strategy, mock_redis):
        """Test dependency-based cache invalidation"""
        cache_key = "test:key"
        dependent_keys = ["dep1", "dep2"]
        invalidation_strategy.add_dependency(cache_key, dependent_keys)
        
        await invalidation_strategy.invalidate_dependencies(cache_key)
        
        # Check that delete was called once with the dependent keys (order may vary)
        mock_redis.delete.assert_called_once()
        call_args = mock_redis.delete.call_args[0]
        assert set(call_args) == set(dependent_keys)
    
    @pytest.mark.asyncio
    async def test_invalidate_user_data(self, invalidation_strategy, mock_redis):
        """Test user data invalidation"""
        user_id = uuid.uuid4()
        mock_redis.keys.return_value = []
        
        await invalidation_strategy.invalidate_user_data(user_id)
        
        # Should call keys twice for both patterns
        assert mock_redis.keys.call_count == 2
        expected_patterns = [f"user:*:{user_id}", f"user:{user_id}:*"]
        actual_patterns = [call[0][0] for call in mock_redis.keys.call_args_list]
        assert set(actual_patterns) == set(expected_patterns)
    
    @pytest.mark.asyncio
    async def test_invalidate_firm_data(self, invalidation_strategy, mock_redis):
        """Test firm data invalidation"""
        firm_id = uuid.uuid4()
        mock_redis.keys.return_value = []
        
        await invalidation_strategy.invalidate_firm_data(firm_id)
        
        # Should call keys twice for both patterns
        assert mock_redis.keys.call_count == 2
        expected_patterns = [f"firm:*:{firm_id}", f"firm:{firm_id}:*"]
        actual_patterns = [call[0][0] for call in mock_redis.keys.call_args_list]
        assert set(actual_patterns) == set(expected_patterns)


class TestSessionManager:
    """Test Redis session management"""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client"""
        redis_mock = AsyncMock()
        return redis_mock
    
    @pytest.fixture
    def session_manager(self, mock_redis):
        """Create session manager with mock Redis"""
        return SessionManager(mock_redis)
    
    @pytest.mark.asyncio
    async def test_create_session(self, session_manager, mock_redis):
        """Test session creation"""
        user_id = uuid.uuid4()
        session_data = {"role": "user", "permissions": ["read"]}
        
        mock_redis.setex.return_value = True
        
        session_id = await session_manager.create_session(user_id, session_data)
        
        assert isinstance(session_id, str)
        assert len(session_id) == 36  # UUID length
        
        # Should call setex twice (session and user_session)
        assert mock_redis.setex.call_count == 2
    
    @pytest.mark.asyncio
    async def test_get_session(self, session_manager, mock_redis):
        """Test getting session data"""
        session_id = str(uuid.uuid4())
        session_data = {
            "user_id": str(uuid.uuid4()),
            "created_at": datetime.utcnow().isoformat(),
            "last_accessed": datetime.utcnow().isoformat(),
            "role": "user"
        }
        
        mock_redis.get.return_value = json.dumps(session_data)
        mock_redis.setex.return_value = True
        
        result = await session_manager.get_session(session_id)
        
        assert result is not None
        assert result["user_id"] == session_data["user_id"]
        assert result["role"] == session_data["role"]
        
        # Should update last_accessed time
        mock_redis.setex.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_session(self, session_manager, mock_redis):
        """Test getting non-existent session"""
        session_id = str(uuid.uuid4())
        mock_redis.get.return_value = None
        
        result = await session_manager.get_session(session_id)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_update_session(self, session_manager, mock_redis):
        """Test updating session data"""
        session_id = str(uuid.uuid4())
        existing_data = {
            "user_id": str(uuid.uuid4()),
            "created_at": datetime.utcnow().isoformat(),
            "last_accessed": datetime.utcnow().isoformat(),
            "role": "user"
        }
        updates = {"role": "admin", "new_field": "value"}
        
        mock_redis.get.return_value = json.dumps(existing_data)
        mock_redis.setex.return_value = True
        
        result = await session_manager.update_session(session_id, updates)
        
        assert result is True
        # Should call setex twice (once for get_session, once for update)
        assert mock_redis.setex.call_count == 2
    
    @pytest.mark.asyncio
    async def test_delete_session(self, session_manager, mock_redis):
        """Test session deletion"""
        session_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        session_data = {
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "last_accessed": datetime.utcnow().isoformat()
        }
        
        mock_redis.get.return_value = json.dumps(session_data)
        mock_redis.setex.return_value = True
        mock_redis.delete.return_value = 2
        
        result = await session_manager.delete_session(session_id)
        
        assert result is True
        mock_redis.delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_user_session(self, session_manager, mock_redis):
        """Test getting user's active session"""
        user_id = uuid.uuid4()
        session_id = str(uuid.uuid4())
        
        mock_redis.get.return_value = session_id
        
        result = await session_manager.get_user_session(user_id)
        
        assert result == session_id
        mock_redis.get.assert_called_once_with(f"user:session:{user_id}")


class TestCacheWarmer:
    """Test cache warming functionality"""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client"""
        return AsyncMock()
    
    @pytest.fixture
    def cache_warmer(self, mock_redis):
        """Create cache warmer with mock Redis"""
        return CacheWarmer(mock_redis)
    
    def test_register_warmer(self, cache_warmer):
        """Test registering cache warmer function"""
        async def test_warmer():
            pass
        
        cache_warmer.register_warmer("test:*", test_warmer)
        
        assert "test:*" in cache_warmer.warming_tasks
        assert cache_warmer.warming_tasks["test:*"] == test_warmer
    
    @pytest.mark.asyncio
    async def test_warm_specific_cache(self, cache_warmer):
        """Test warming specific cache pattern"""
        warmer_called = False
        
        async def test_warmer():
            nonlocal warmer_called
            warmer_called = True
        
        cache_warmer.register_warmer("test:*", test_warmer)
        
        await cache_warmer.warm_cache("test:*")
        
        assert warmer_called is True
    
    @pytest.mark.asyncio
    async def test_warm_all_caches(self, cache_warmer):
        """Test warming all registered caches"""
        warmer1_called = False
        warmer2_called = False
        
        async def test_warmer1():
            nonlocal warmer1_called
            warmer1_called = True
        
        async def test_warmer2():
            nonlocal warmer2_called
            warmer2_called = True
        
        cache_warmer.register_warmer("test1:*", test_warmer1)
        cache_warmer.register_warmer("test2:*", test_warmer2)
        
        await cache_warmer.warm_cache()
        
        assert warmer1_called is True
        assert warmer2_called is True


class TestEnhancedCacheService:
    """Test enhanced cache service"""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client"""
        return AsyncMock()
    
    @pytest.fixture
    def cache_service(self, mock_redis):
        """Create cache service with mock Redis"""
        service = EnhancedCacheService()
        service.client = mock_redis
        service.invalidation = CacheInvalidationStrategy(mock_redis)
        service.session_manager = SessionManager(mock_redis)
        service.cache_warmer = CacheWarmer(mock_redis)
        return service
    
    @pytest.mark.asyncio
    async def test_get_json_value(self, cache_service, mock_redis):
        """Test getting JSON value from cache"""
        key = "test:key"
        value = {"data": "test"}
        mock_redis.get.return_value = json.dumps(value)
        
        result = await cache_service.get(key)
        
        assert result == value
        mock_redis.get.assert_called_once_with(key)
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self, cache_service, mock_redis):
        """Test getting non-existent key with default"""
        key = "test:key"
        default = "default_value"
        mock_redis.get.return_value = None
        
        result = await cache_service.get(key, default)
        
        assert result == default
    
    @pytest.mark.asyncio
    async def test_set_json_value(self, cache_service, mock_redis):
        """Test setting JSON value in cache"""
        key = "test:key"
        value = {"data": "test"}
        expire = 3600
        mock_redis.setex.return_value = True
        
        result = await cache_service.set(key, value, expire)
        
        assert result is True
        mock_redis.setex.assert_called_once_with(key, expire, json.dumps(value))
    
    @pytest.mark.asyncio
    async def test_delete_keys(self, cache_service, mock_redis):
        """Test deleting keys from cache"""
        keys = ["key1", "key2", "key3"]
        mock_redis.delete.return_value = len(keys)
        
        result = await cache_service.delete(*keys)
        
        assert result == len(keys)
        mock_redis.delete.assert_called_once_with(*keys)
    
    @pytest.mark.asyncio
    async def test_exists_key(self, cache_service, mock_redis):
        """Test checking if key exists"""
        key = "test:key"
        mock_redis.exists.return_value = 1
        
        result = await cache_service.exists(key)
        
        assert result is True
        mock_redis.exists.assert_called_once_with(key)
    
    @pytest.mark.asyncio
    async def test_expire_key(self, cache_service, mock_redis):
        """Test setting expiration for key"""
        key = "test:key"
        seconds = 3600
        mock_redis.expire.return_value = True
        
        result = await cache_service.expire(key, seconds)
        
        assert result is True
        mock_redis.expire.assert_called_once_with(key, seconds)
    
    @pytest.mark.asyncio
    async def test_ttl_key(self, cache_service, mock_redis):
        """Test getting TTL for key"""
        key = "test:key"
        ttl_value = 1800
        mock_redis.ttl.return_value = ttl_value
        
        result = await cache_service.ttl(key)
        
        assert result == ttl_value
        mock_redis.ttl.assert_called_once_with(key)


class TestCacheDecorators:
    """Test caching decorators"""
    
    @pytest.fixture
    def mock_enhanced_cache(self):
        """Mock enhanced cache service"""
        cache_mock = AsyncMock()
        cache_mock.get.return_value = None
        cache_mock.set.return_value = True
        cache_mock.invalidation = AsyncMock()
        return cache_mock
    
    @pytest.mark.asyncio
    async def test_cache_result_decorator_miss(self, mock_enhanced_cache):
        """Test cache result decorator on cache miss"""
        with patch('app.core.cache.enhanced_cache', mock_enhanced_cache):
            @cache_result(expire=3600, key_prefix="test")
            async def test_function(arg1, arg2):
                return f"result_{arg1}_{arg2}"
            
            result = await test_function("a", "b")
            
            assert result == "result_a_b"
            mock_enhanced_cache.get.assert_called_once()
            mock_enhanced_cache.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cache_result_decorator_hit(self, mock_enhanced_cache):
        """Test cache result decorator on cache hit"""
        cached_result = "cached_result"
        mock_enhanced_cache.get.return_value = cached_result
        
        with patch('app.core.cache.enhanced_cache', mock_enhanced_cache):
            @cache_result(expire=3600, key_prefix="test")
            async def test_function(arg1, arg2):
                return f"result_{arg1}_{arg2}"
            
            result = await test_function("a", "b")
            
            assert result == cached_result
            mock_enhanced_cache.get.assert_called_once()
            mock_enhanced_cache.set.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_cache_invalidate_decorator(self, mock_enhanced_cache):
        """Test cache invalidate decorator"""
        with patch('app.core.cache.enhanced_cache', mock_enhanced_cache):
            @cache_invalidate("pattern1:*", "pattern2:*")
            async def test_function():
                return "result"
            
            result = await test_function()
            
            assert result == "result"
            # Should call invalidate_pattern for each pattern
            assert mock_enhanced_cache.invalidation.invalidate_pattern.call_count == 2


class TestCacheIntegration:
    """Integration tests for cache system"""
    
    @pytest.mark.asyncio
    async def test_cache_system_initialization(self):
        """Test cache system initialization"""
        with patch('app.core.cache.get_redis') as mock_get_redis:
            mock_redis = AsyncMock()
            mock_get_redis.return_value = mock_redis
            
            await initialize_cache_system()
            
            assert enhanced_cache.client is not None
            assert enhanced_cache.invalidation is not None
            assert enhanced_cache.session_manager is not None
            assert enhanced_cache.cache_warmer is not None
    
    @pytest.mark.asyncio
    async def test_user_cache_operations(self):
        """Test user-specific cache operations"""
        user_id = uuid.uuid4()
        user_data = {"name": "Test User", "email": "test@example.com"}
        
        with patch('app.core.cache.enhanced_cache') as mock_cache:
            mock_cache.set = AsyncMock(return_value=True)
            mock_cache.invalidation = AsyncMock()
            mock_cache.invalidation.invalidate_user_data = AsyncMock()
            
            from app.core.cache import cache_user_data, invalidate_user_cache
            
            # Test caching user data
            await cache_user_data(user_id, user_data)
            mock_cache.set.assert_called_once()
            
            # Test invalidating user cache
            await invalidate_user_cache(user_id)
            mock_cache.invalidation.invalidate_user_data.assert_called_once_with(user_id)
    
    @pytest.mark.asyncio
    async def test_firm_cache_operations(self):
        """Test firm-specific cache operations"""
        firm_id = uuid.uuid4()
        firm_data = {"name": "Test Firm", "coverage_areas": []}
        
        with patch('app.core.cache.enhanced_cache') as mock_cache:
            mock_cache.set = AsyncMock(return_value=True)
            mock_cache.invalidation = AsyncMock()
            mock_cache.invalidation.invalidate_firm_data = AsyncMock()
            
            from app.core.cache import cache_firm_data, invalidate_firm_cache
            
            # Test caching firm data
            await cache_firm_data(firm_id, firm_data)
            mock_cache.set.assert_called_once()
            
            # Test invalidating firm cache
            await invalidate_firm_cache(firm_id)
            mock_cache.invalidation.invalidate_firm_data.assert_called_once_with(firm_id)


class TestCacheErrorHandling:
    """Test cache error handling"""
    
    @pytest.fixture
    def cache_service_with_errors(self):
        """Create cache service that raises errors"""
        service = EnhancedCacheService()
        service.client = AsyncMock()
        return service
    
    @pytest.mark.asyncio
    async def test_get_with_redis_error(self, cache_service_with_errors):
        """Test get operation with Redis error"""
        cache_service_with_errors.client.get.side_effect = Exception("Redis error")
        
        result = await cache_service_with_errors.get("test:key", "default")
        
        assert result == "default"
    
    @pytest.mark.asyncio
    async def test_set_with_redis_error(self, cache_service_with_errors):
        """Test set operation with Redis error"""
        cache_service_with_errors.client.setex.side_effect = Exception("Redis error")
        
        result = await cache_service_with_errors.set("test:key", "value")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_delete_with_redis_error(self, cache_service_with_errors):
        """Test delete operation with Redis error"""
        cache_service_with_errors.client.delete.side_effect = Exception("Redis error")
        
        result = await cache_service_with_errors.delete("test:key")
        
        assert result == 0


if __name__ == "__main__":
    pytest.main([__file__])