"""
Unit tests for database optimization functionality
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from uuid import uuid4

from app.core.query_optimizer import (
    QueryOptimizer,
    QueryPerformanceMetrics,
    OptimizedGeospatialQueries,
    OptimizedUserQueries,
    OptimizedEmergencyQueries,
    ConnectionPoolOptimizer,
    QueryCache
)
from app.services.database_optimization import DatabaseOptimizationService


class TestQueryOptimizer:
    """Test query optimizer functionality"""
    
    def test_query_performance_metrics_creation(self):
        """Test QueryPerformanceMetrics data class"""
        metrics = QueryPerformanceMetrics(
            query_hash="test_hash",
            execution_time_ms=150.5,
            rows_returned=10,
            query_type="test_query",
            timestamp=datetime.utcnow(),
            parameters={"param1": "value1"}
        )
        
        assert metrics.query_hash == "test_hash"
        assert metrics.execution_time_ms == 150.5
        assert metrics.rows_returned == 10
        assert metrics.query_type == "test_query"
        assert metrics.parameters == {"param1": "value1"}
    
    @pytest.mark.asyncio
    async def test_query_optimizer_monitor_query(self):
        """Test query monitoring context manager"""
        optimizer = QueryOptimizer()
        
        async with optimizer.monitor_query("test_query", "SELECT 1", {"param": "value"}):
            # Simulate some work
            await asyncio.sleep(0.01)
        
        # Check that metrics were recorded
        assert len(optimizer.performance_metrics) == 1
        metric = optimizer.performance_metrics[0]
        assert metric.query_type == "test_query"
        assert metric.execution_time_ms > 0
        assert metric.parameters == {"param": "value"}
    
    @pytest.mark.asyncio
    async def test_query_optimizer_slow_query_detection(self):
        """Test slow query detection and logging"""
        optimizer = QueryOptimizer()
        optimizer.slow_query_threshold_ms = 50  # Lower threshold for testing
        
        with patch('app.core.query_optimizer.logger') as mock_logger:
            async with optimizer.monitor_query("slow_query", "SELECT pg_sleep(0.1)"):
                await asyncio.sleep(0.06)  # Simulate slow query
            
            # Check that slow query was logged
            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args[1]
            assert call_args["query_name"] == "slow_query"
            assert call_args["execution_time_ms"] > 50
    
    def test_query_optimizer_analyze_performance(self):
        """Test query performance analysis"""
        optimizer = QueryOptimizer()
        
        # Add some test metrics
        now = datetime.utcnow()
        test_metrics = [
            QueryPerformanceMetrics("hash1", 100.0, 5, "query1", now),
            QueryPerformanceMetrics("hash2", 200.0, 10, "query1", now),
            QueryPerformanceMetrics("hash3", 50.0, 3, "query2", now),
            QueryPerformanceMetrics("hash4", 1500.0, 20, "query2", now - timedelta(hours=25))  # Old metric
        ]
        
        optimizer.performance_metrics = test_metrics
        
        # Analyze performance for last 24 hours
        analysis = asyncio.run(optimizer.analyze_query_performance(hours_back=24))
        
        assert analysis["total_queries"] == 3  # Excludes old metric
        assert analysis["avg_execution_time_ms"] == (100 + 200 + 50) / 3
        assert analysis["slow_queries_count"] == 0  # None exceed default threshold
        assert "query1" in analysis["query_types"]
        assert "query2" in analysis["query_types"]
        assert analysis["query_types"]["query1"]["count"] == 2
        assert analysis["query_types"]["query2"]["count"] == 1
    
    @pytest.mark.asyncio
    async def test_query_optimizer_explain_plan(self):
        """Test EXPLAIN plan generation"""
        optimizer = QueryOptimizer()
        
        with patch('app.core.query_optimizer.get_db_pool') as mock_pool:
            mock_conn = AsyncMock()
            mock_conn.fetchval.return_value = [{"Plan": {"Node Type": "Seq Scan"}}]
            
            # Properly mock the async context manager
            mock_pool.return_value.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_pool.return_value.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
            
            explain_plan = await optimizer.get_query_explain_plan(
                "SELECT * FROM test_table",
                {"param1": "value1"}
            )
            
            assert explain_plan is not None
            mock_conn.fetchval.assert_called_once()


class TestOptimizedQueries:
    """Test optimized query implementations"""
    
    @pytest.mark.asyncio
    async def test_optimized_geospatial_find_coverage(self):
        """Test optimized coverage area lookup"""
        with patch('app.core.query_optimizer.get_db_pool') as mock_pool:
            mock_conn = AsyncMock()
            mock_conn.fetch.return_value = [
                {
                    "id": uuid4(),
                    "firm_id": uuid4(),
                    "name": "Test Coverage",
                    "firm_name": "Test Firm",
                    "verification_status": "approved",
                    "distance_km": 0.5
                }
            ]
            mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn
            
            results = await OptimizedGeospatialQueries.find_coverage_for_location(
                40.7128, -74.0060
            )
            
            assert len(results) == 1
            assert results[0]["firm_name"] == "Test Firm"
            assert results[0]["distance_km"] == 0.5
            
            # Verify the query was called with correct parameters
            mock_conn.fetch.assert_called_once()
            call_args = mock_conn.fetch.call_args[0]
            assert "ST_Contains" in call_args[0]
            assert "POINT(-74.0060 40.7128)" in call_args[1]
    
    @pytest.mark.asyncio
    async def test_optimized_geospatial_nearest_providers(self):
        """Test optimized service provider lookup"""
        firm_id = uuid4()
        
        with patch('app.core.query_optimizer.get_db_pool') as mock_pool:
            mock_conn = AsyncMock()
            mock_conn.fetch.return_value = [
                {
                    "id": uuid4(),
                    "name": "Test Ambulance",
                    "service_type": "ambulance",
                    "email": "test@example.com",
                    "phone": "123-456-7890",
                    "address": "123 Test St",
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "distance_km": 2.5
                }
            ]
            mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn
            
            results = await OptimizedGeospatialQueries.find_nearest_service_providers(
                40.7128, -74.0060, "ambulance", firm_id, max_distance_km=10.0, limit=5
            )
            
            assert len(results) == 1
            assert results[0]["name"] == "Test Ambulance"
            assert results[0]["service_type"] == "ambulance"
            assert results[0]["distance_km"] == 2.5
            
            # Verify query parameters
            mock_conn.fetch.assert_called_once()
            call_args = mock_conn.fetch.call_args[0]
            assert "ST_DWithin" in call_args[0]
            assert str(firm_id) in call_args[2]
            assert "ambulance" in call_args[3]
    
    @pytest.mark.asyncio
    async def test_optimized_user_subscriptions(self):
        """Test optimized user subscription queries"""
        user_id = uuid4()
        
        with patch('app.core.query_optimizer.get_db_pool') as mock_pool:
            mock_conn = AsyncMock()
            mock_conn.fetch.return_value = [
                {
                    "subscription_id": uuid4(),
                    "purchased_at": datetime.utcnow(),
                    "applied_at": datetime.utcnow(),
                    "product_name": "Premium Security",
                    "price": 99.99,
                    "max_users": 10,
                    "firm_name": "SecureCorp",
                    "firm_id": uuid4(),
                    "group_id": uuid4(),
                    "group_name": "My Family",
                    "group_address": "123 Home St",
                    "subscription_expires_at": datetime.utcnow() + timedelta(days=30),
                    "group_latitude": 40.7128,
                    "group_longitude": -74.0060,
                    "mobile_numbers_count": 3
                }
            ]
            mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn
            
            results = await OptimizedUserQueries.get_user_active_subscriptions_with_groups(user_id)
            
            assert len(results) == 1
            subscription = results[0]
            assert subscription["product"]["name"] == "Premium Security"
            assert subscription["firm"]["name"] == "SecureCorp"
            assert subscription["group"]["name"] == "My Family"
            assert subscription["group"]["mobile_numbers_count"] == 3
            
            # Verify query was called with user_id
            mock_conn.fetch.assert_called_once()
            call_args = mock_conn.fetch.call_args[0]
            assert str(user_id) in call_args[1]
    
    @pytest.mark.asyncio
    async def test_optimized_emergency_requests(self):
        """Test optimized emergency request queries"""
        firm_id = uuid4()
        
        with patch('app.core.query_optimizer.get_db_pool') as mock_pool:
            mock_conn = AsyncMock()
            mock_conn.fetch.return_value = [
                {
                    "id": uuid4(),
                    "requester_phone": "+1234567890",
                    "service_type": "security",
                    "status": "completed",
                    "address": "123 Emergency St",
                    "created_at": datetime.utcnow(),
                    "accepted_at": datetime.utcnow(),
                    "arrived_at": datetime.utcnow(),
                    "completed_at": datetime.utcnow(),
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "group_name": "Test Group",
                    "user_first_name": "John",
                    "user_last_name": "Doe",
                    "assigned_team_name": "Alpha Team",
                    "service_provider_name": None,
                    "response_time_minutes": 15.5
                }
            ]
            mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn
            
            results = await OptimizedEmergencyQueries.get_recent_requests_with_metrics(
                firm_id, hours_back=24, limit=50
            )
            
            assert "requests" in results
            assert "metrics" in results
            assert len(results["requests"]) == 1
            
            request = results["requests"][0]
            assert request["service_type"] == "security"
            assert request["status"] == "completed"
            assert request["response_time_minutes"] == 15.5
            
            metrics = results["metrics"]
            assert metrics["total_requests"] == 1
            assert metrics["avg_response_time_minutes"] == 15.5
            assert metrics["completed_requests"] == 1


class TestConnectionPoolOptimizer:
    """Test connection pool optimization"""
    
    @pytest.mark.asyncio
    async def test_get_pool_stats(self):
        """Test pool statistics retrieval"""
        with patch('app.core.query_optimizer.get_db_pool') as mock_pool:
            mock_pool_instance = Mock()
            mock_pool_instance.get_size.return_value = 20
            mock_pool_instance.get_min_size.return_value = 5
            mock_pool_instance.get_max_size.return_value = 30
            mock_pool_instance.get_idle_size.return_value = 15
            mock_pool.return_value = mock_pool_instance
            
            stats = await ConnectionPoolOptimizer.get_pool_stats()
            
            assert stats["pool_size"] == 20
            assert stats["pool_min_size"] == 5
            assert stats["pool_max_size"] == 30
            assert stats["pool_idle_size"] == 15
            assert stats["pool_used_size"] == 5
            assert stats["pool_utilization_percent"] == (5 / 30) * 100
    
    @pytest.mark.asyncio
    async def test_optimize_pool_settings_high_utilization(self):
        """Test pool optimization recommendations for high utilization"""
        with patch.object(ConnectionPoolOptimizer, 'get_pool_stats') as mock_stats:
            mock_stats.return_value = {
                "pool_size": 25,
                "pool_max_size": 30,
                "pool_utilization_percent": 85.0,
                "pool_idle_size": 5
            }
            
            recommendations = await ConnectionPoolOptimizer.optimize_pool_settings()
            
            assert "recommendations" in recommendations
            assert len(recommendations["recommendations"]) > 0
            
            high_util_rec = next(
                (r for r in recommendations["recommendations"] if "High pool utilization" in r["message"]),
                None
            )
            assert high_util_rec is not None
            assert high_util_rec["type"] == "warning"
    
    @pytest.mark.asyncio
    async def test_optimize_pool_settings_low_utilization(self):
        """Test pool optimization recommendations for low utilization"""
        with patch.object(ConnectionPoolOptimizer, 'get_pool_stats') as mock_stats:
            mock_stats.return_value = {
                "pool_size": 15,
                "pool_max_size": 30,
                "pool_utilization_percent": 15.0,
                "pool_idle_size": 12
            }
            
            recommendations = await ConnectionPoolOptimizer.optimize_pool_settings()
            
            assert "recommendations" in recommendations
            low_util_rec = next(
                (r for r in recommendations["recommendations"] if "Low pool utilization" in r["message"]),
                None
            )
            assert low_util_rec is not None
            assert low_util_rec["type"] == "info"


class TestQueryCache:
    """Test query caching functionality"""
    
    @pytest.mark.asyncio
    async def test_cache_hit(self):
        """Test cache hit scenario"""
        with patch('app.core.query_optimizer.cache') as mock_cache:
            mock_cache.get.return_value = {"cached": "result"}
            
            async def dummy_query():
                return {"fresh": "result"}
            
            result = await QueryCache.get_or_execute(
                "test_key", dummy_query, ttl=300
            )
            
            assert result == {"cached": "result"}
            mock_cache.get.assert_called_once_with("test_key")
            mock_cache.set.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_cache_miss(self):
        """Test cache miss scenario"""
        with patch('app.core.query_optimizer.cache') as mock_cache:
            mock_cache.get.return_value = None
            
            async def dummy_query():
                return {"fresh": "result"}
            
            result = await QueryCache.get_or_execute(
                "test_key", dummy_query, ttl=300
            )
            
            assert result == {"fresh": "result"}
            mock_cache.get.assert_called_once_with("test_key")
            mock_cache.set.assert_called_once_with("test_key", {"fresh": "result"}, expire=300)
    
    def test_generate_cache_key(self):
        """Test cache key generation"""
        key = QueryCache.generate_cache_key(
            "test_prefix",
            param1="value1",
            param2="value2",
            param3=123
        )
        
        assert key.startswith("test_prefix:")
        assert "param1:value1" in key
        assert "param2:value2" in key
        assert "param3:123" in key
        
        # Test consistent key generation
        key2 = QueryCache.generate_cache_key(
            "test_prefix",
            param2="value2",  # Different order
            param1="value1",
            param3=123
        )
        
        assert key == key2  # Should be the same regardless of parameter order


class TestDatabaseOptimizationService:
    """Test database optimization service"""
    
    @pytest.mark.asyncio
    async def test_get_performance_dashboard(self):
        """Test performance dashboard generation"""
        service = DatabaseOptimizationService()
        
        with patch.multiple(
            'app.services.database_optimization',
            get_pool_statistics=AsyncMock(return_value={"pool_size": 20}),
            analyze_slow_queries=AsyncMock(return_value=[]),
            optimize_database_settings=AsyncMock(return_value={"settings": "optimized"})
        ):
            with patch.object(service, '_get_cache_statistics') as mock_cache_stats:
                mock_cache_stats.return_value = {"hit_rate_percent": 85.0}
                
                with patch.object(service, '_generate_optimization_recommendations') as mock_recommendations:
                    mock_recommendations.return_value = []
                    
                    dashboard = await service.get_performance_dashboard()
                    
                    assert "timestamp" in dashboard
                    assert "pool_statistics" in dashboard
                    assert "query_performance" in dashboard
                    assert "slow_queries" in dashboard
                    assert "database_optimization" in dashboard
                    assert "cache_statistics" in dashboard
                    assert "recommendations" in dashboard
    
    @pytest.mark.asyncio
    async def test_optimize_geospatial_queries(self):
        """Test geospatial query optimization"""
        service = DatabaseOptimizationService()
        
        with patch('app.services.database_optimization.OptimizedGeospatialQueries') as mock_geo:
            mock_geo.find_coverage_for_location.return_value = [{"coverage": "result"}]
            
            with patch('app.services.database_optimization.execute_optimized_query') as mock_execute:
                mock_execute.return_value = [{"count": 5}]
                
                results = await service.optimize_geospatial_queries()
                
                assert "timestamp" in results
                assert "tests" in results
                assert "overall_performance" in results
                assert len(results["tests"]) > 0
                
                # Check that coverage tests were performed
                coverage_tests = [t for t in results["tests"] if t["test_type"] == "coverage_lookup"]
                assert len(coverage_tests) == 3  # Three test locations
    
    @pytest.mark.asyncio
    async def test_run_comprehensive_optimization(self):
        """Test comprehensive optimization run"""
        service = DatabaseOptimizationService()
        
        with patch.object(service, 'get_performance_dashboard') as mock_dashboard:
            mock_dashboard.return_value = {"dashboard": "data"}
            
            with patch.object(service, 'optimize_geospatial_queries') as mock_geo:
                mock_geo.return_value = {"geospatial": "results"}
                
                with patch.object(service, 'optimize_user_queries') as mock_user:
                    mock_user.return_value = {"user": "results"}
                    
                    with patch.object(service, 'optimize_emergency_queries') as mock_emergency:
                        mock_emergency.return_value = {"emergency": "results"}
                        
                        with patch('app.services.database_optimization.cache') as mock_cache:
                            report = await service.run_comprehensive_optimization()
                            
                            assert report["status"] == "completed"
                            assert "optimization_id" in report
                            assert "performance_dashboard" in report
                            assert "geospatial_optimization" in report
                            assert "user_optimization" in report
                            assert "emergency_optimization" in report
                            assert "summary" in report
                            
                            # Verify cache was called
                            mock_cache.set.assert_called_once()
    
    def test_generate_optimization_recommendations(self):
        """Test optimization recommendation generation"""
        service = DatabaseOptimizationService()
        
        pool_stats = {"pool_utilization_percent": 85.0}
        query_analysis = {"slow_queries_count": 15, "avg_execution_time_ms": 250.0}
        slow_queries = [{"mean_time_ms": 600.0, "query": "SELECT * FROM large_table"}]
        
        recommendations = asyncio.run(service._generate_optimization_recommendations(
            pool_stats, query_analysis, slow_queries
        ))
        
        assert len(recommendations) >= 3  # Should have multiple recommendations
        
        # Check for high pool utilization recommendation
        pool_rec = next((r for r in recommendations if r["category"] == "connection_pool"), None)
        assert pool_rec is not None
        assert pool_rec["priority"] == "high"
        
        # Check for slow query recommendation
        slow_rec = next((r for r in recommendations if r["category"] == "slow_query"), None)
        assert slow_rec is not None
        assert slow_rec["priority"] == "high"
    
    def test_generate_optimization_summary(self):
        """Test optimization summary generation"""
        service = DatabaseOptimizationService()
        
        # Test with mixed results
        results = [
            {"tests": [{"performance_rating": "excellent"}, {"performance_rating": "needs_optimization"}]},
            {"error": "Some error occurred"},
            {"tests": [{"performance_rating": "good"}]}
        ]
        
        summary = asyncio.run(service._generate_optimization_summary(results))
        
        assert summary["critical_issues"] == 1  # One error
        assert summary["warnings"] == 1  # One needs_optimization
        assert summary["optimizations_applied"] == 1  # One excellent
        assert summary["overall_status"] in ["critical", "warning", "needs_attention", "healthy"]
        assert 0 <= summary["performance_score"] <= 100


if __name__ == "__main__":
    pytest.main([__file__])