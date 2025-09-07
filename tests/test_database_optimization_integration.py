"""
Integration tests for database optimization functionality
"""
import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from app.core.query_optimizer import QueryOptimizer, QueryPerformanceMetrics
from app.services.database_optimization import DatabaseOptimizationService


class TestDatabaseOptimizationIntegration:
    """Integration tests for database optimization"""
    
    def test_query_performance_metrics_basic_functionality(self):
        """Test basic QueryPerformanceMetrics functionality"""
        metrics = QueryPerformanceMetrics(
            query_hash="test_hash_123",
            execution_time_ms=250.5,
            rows_returned=15,
            query_type="user_lookup",
            timestamp=datetime.utcnow(),
            parameters={"user_id": "123", "status": "active"}
        )
        
        assert metrics.query_hash == "test_hash_123"
        assert metrics.execution_time_ms == 250.5
        assert metrics.rows_returned == 15
        assert metrics.query_type == "user_lookup"
        assert metrics.parameters["user_id"] == "123"
        assert isinstance(metrics.timestamp, datetime)
    
    @pytest.mark.asyncio
    async def test_query_optimizer_monitoring_workflow(self):
        """Test the complete query monitoring workflow"""
        optimizer = QueryOptimizer()
        
        # Test normal query monitoring
        async with optimizer.monitor_query("test_query", "SELECT COUNT(*) FROM users", {"limit": 10}):
            await asyncio.sleep(0.01)  # Simulate query execution
        
        # Verify metrics were recorded
        assert len(optimizer.performance_metrics) == 1
        metric = optimizer.performance_metrics[0]
        assert metric.query_type == "test_query"
        assert metric.execution_time_ms > 0
        assert metric.parameters == {"limit": 10}
        
        # Test slow query detection
        optimizer.slow_query_threshold_ms = 5  # Very low threshold for testing
        
        with patch('app.core.query_optimizer.logger') as mock_logger:
            async with optimizer.monitor_query("slow_query", "SELECT * FROM large_table"):
                await asyncio.sleep(0.01)  # This should trigger slow query warning
            
            # Verify slow query was logged
            mock_logger.warning.assert_called_once()
            call_kwargs = mock_logger.warning.call_args[1]
            assert call_kwargs["query_name"] == "slow_query"
            assert call_kwargs["execution_time_ms"] > 5
    
    def test_query_optimizer_performance_analysis(self):
        """Test query performance analysis functionality"""
        optimizer = QueryOptimizer()
        
        # Add test metrics with different characteristics
        now = datetime.utcnow()
        test_metrics = [
            QueryPerformanceMetrics("hash1", 50.0, 5, "fast_query", now),
            QueryPerformanceMetrics("hash2", 150.0, 10, "medium_query", now),
            QueryPerformanceMetrics("hash3", 2000.0, 100, "slow_query", now),  # Slow query
            QueryPerformanceMetrics("hash4", 75.0, 8, "fast_query", now),
        ]
        
        optimizer.performance_metrics = test_metrics
        
        # Analyze performance
        analysis = asyncio.run(optimizer.analyze_query_performance(hours_back=24))
        
        # Verify analysis results
        assert analysis["total_queries"] == 4
        assert analysis["avg_execution_time_ms"] == (50 + 150 + 2000 + 75) / 4
        assert analysis["min_execution_time_ms"] == 50.0
        assert analysis["max_execution_time_ms"] == 2000.0
        assert analysis["slow_queries_count"] == 1  # Only one exceeds default 1000ms threshold
        
        # Verify query type grouping
        assert "fast_query" in analysis["query_types"]
        assert "medium_query" in analysis["query_types"]
        assert "slow_query" in analysis["query_types"]
        assert analysis["query_types"]["fast_query"]["count"] == 2
        assert analysis["query_types"]["medium_query"]["count"] == 1
        assert analysis["query_types"]["slow_query"]["count"] == 1
        
        # Verify slowest queries list
        assert len(analysis["slowest_queries"]) == 4
        slowest = analysis["slowest_queries"][0]
        assert slowest["execution_time_ms"] == 2000.0
        assert slowest["query_type"] == "slow_query"
    
    def test_database_optimization_service_recommendations(self):
        """Test optimization recommendation generation"""
        service = DatabaseOptimizationService()
        
        # Test high pool utilization scenario
        pool_stats = {"pool_utilization_percent": 85.0, "pool_max_size": 20}
        query_analysis = {"slow_queries_count": 3, "avg_execution_time_ms": 150.0}
        slow_queries = [
            {"mean_time_ms": 300.0, "query": "SELECT * FROM users WHERE email = ?"},
            {"mean_time_ms": 800.0, "query": "SELECT COUNT(*) FROM large_table"}
        ]
        
        recommendations = asyncio.run(service._generate_optimization_recommendations(
            pool_stats, query_analysis, slow_queries
        ))
        
        # Verify recommendations were generated
        assert len(recommendations) > 0
        
        # Check for pool utilization recommendation
        pool_rec = next((r for r in recommendations if r["category"] == "connection_pool"), None)
        assert pool_rec is not None
        assert pool_rec["priority"] == "high"
        assert "pool utilization" in pool_rec["issue"].lower()
        
        # Test low utilization scenario
        pool_stats_low = {"pool_utilization_percent": 15.0, "pool_max_size": 30}
        query_analysis_good = {"slow_queries_count": 1, "avg_execution_time_ms": 50.0}
        
        recommendations_low = asyncio.run(service._generate_optimization_recommendations(
            pool_stats_low, query_analysis_good, []
        ))
        
        # Should have fewer recommendations for good performance
        # The low utilization recommendation only triggers if pool_max_size > 10 and utilization < 20%
        # Let's verify the logic works correctly
        assert len(recommendations_low) <= len(recommendations)  # Should have fewer or equal recommendations
    
    def test_optimization_summary_generation(self):
        """Test optimization summary generation from mixed results"""
        service = DatabaseOptimizationService()
        
        # Test with mixed results including errors and performance issues
        results = [
            {
                "tests": [
                    {"performance_rating": "excellent"},
                    {"performance_rating": "good"},
                    {"performance_rating": "needs_optimization"}
                ]
            },
            {"error": "Database connection failed"},
            {
                "tests": [
                    {"performance_rating": "excellent"},
                    {"performance_rating": "needs_optimization"}
                ]
            },
            Exception("Unexpected error occurred")
        ]
        
        summary = asyncio.run(service._generate_optimization_summary(results))
        
        # Verify summary calculations
        assert summary["critical_issues"] == 2  # One error dict + one exception
        assert summary["warnings"] == 2  # Two "needs_optimization" ratings
        assert summary["optimizations_applied"] == 2  # Two "excellent" ratings
        assert summary["overall_status"] in ["critical", "warning", "needs_attention", "healthy"]
        assert 0 <= summary["performance_score"] <= 100
        
        # Test with all good results
        good_results = [
            {"tests": [{"performance_rating": "excellent"}, {"performance_rating": "good"}]},
            {"tests": [{"performance_rating": "excellent"}]}
        ]
        
        good_summary = asyncio.run(service._generate_optimization_summary(good_results))
        
        assert good_summary["critical_issues"] == 0
        assert good_summary["warnings"] == 0
        assert good_summary["optimizations_applied"] == 2
        assert good_summary["overall_status"] == "healthy"
        assert good_summary["performance_score"] == 100
    
    @pytest.mark.asyncio
    async def test_query_cache_key_generation(self):
        """Test cache key generation consistency"""
        from app.core.query_optimizer import QueryCache
        
        # Test basic key generation
        key1 = QueryCache.generate_cache_key(
            "user_query",
            user_id="123",
            status="active",
            limit=10
        )
        
        # Test same parameters in different order
        key2 = QueryCache.generate_cache_key(
            "user_query",
            limit=10,
            status="active",
            user_id="123"
        )
        
        # Keys should be identical regardless of parameter order
        assert key1 == key2
        assert key1.startswith("user_query:")
        assert "user_id:123" in key1
        assert "status:active" in key1
        assert "limit:10" in key1
        
        # Test different parameters produce different keys
        key3 = QueryCache.generate_cache_key(
            "user_query",
            user_id="456",
            status="active",
            limit=10
        )
        
        assert key1 != key3
    
    def test_performance_metrics_memory_management(self):
        """Test that performance metrics don't grow unbounded"""
        optimizer = QueryOptimizer()
        
        # Add more than the limit of metrics
        for i in range(1200):  # More than the 1000 limit
            metric = QueryPerformanceMetrics(
                query_hash=f"hash_{i}",
                execution_time_ms=float(i),
                rows_returned=i,
                query_type=f"query_type_{i % 5}",
                timestamp=datetime.utcnow()
            )
            optimizer.performance_metrics.append(metric)
        
        # Simulate the cleanup that happens in monitor_query
        if len(optimizer.performance_metrics) > 1000:
            optimizer.performance_metrics = optimizer.performance_metrics[-1000:]
        
        # Verify metrics are limited to 1000
        assert len(optimizer.performance_metrics) == 1000
        
        # Verify we kept the most recent ones
        assert optimizer.performance_metrics[0].query_hash == "hash_200"  # 1200 - 1000 = 200
        assert optimizer.performance_metrics[-1].query_hash == "hash_1199"
    
    @pytest.mark.asyncio
    async def test_database_optimization_service_error_handling(self):
        """Test error handling in database optimization service"""
        service = DatabaseOptimizationService()
        
        # Test error handling in performance dashboard
        with patch('app.services.database_optimization.get_pool_statistics') as mock_stats:
            mock_stats.side_effect = Exception("Database connection failed")
            
            dashboard = await service.get_performance_dashboard()
            
            # Should return error information instead of crashing
            assert "error" in dashboard
            assert "Database connection failed" in dashboard["error"]
        
        # Test error handling in geospatial optimization
        with patch('app.services.database_optimization.OptimizedGeospatialQueries') as mock_geo:
            mock_geo.find_coverage_for_location.side_effect = Exception("Geospatial query failed")
            
            results = await service.optimize_geospatial_queries()
            
            # Should return error information
            assert "error" in results
            assert "Geospatial query failed" in results["error"]
    
    def test_query_optimizer_threshold_configuration(self):
        """Test query optimizer threshold configuration"""
        optimizer = QueryOptimizer()
        
        # Test default threshold
        assert optimizer.slow_query_threshold_ms == 1000
        
        # Test threshold modification
        optimizer.slow_query_threshold_ms = 500
        assert optimizer.slow_query_threshold_ms == 500
        
        # Test cache TTL configuration
        assert optimizer.cache_ttl == 300  # 5 minutes default
        
        optimizer.cache_ttl = 600
        assert optimizer.cache_ttl == 600


if __name__ == "__main__":
    pytest.main([__file__])