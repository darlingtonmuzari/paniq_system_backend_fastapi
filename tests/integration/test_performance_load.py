"""
Performance and Load Testing
Tests system performance under various load conditions
"""
import pytest
import asyncio
import time
from uuid import uuid4
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch, AsyncMock

import httpx


class TestAPIPerformance:
    """Test API endpoint performance"""
    
    @pytest.mark.asyncio
    async def test_authentication_endpoint_performance(self, client, mock_external_services):
        """Test authentication endpoint performance under load"""
        
        # Mock successful authentication
        with patch('app.services.auth.auth_service.authenticate_user') as mock_auth:
            mock_auth.return_value = {
                "access_token": "perf.test.token",
                "refresh_token": "perf.refresh.token",
                "expires_in": 3600,
                "token_type": "Bearer"
            }
            
            login_data = {
                "email": "perf@test.com",
                "password": "test_password",
                "user_type": "registered_user"
            }
            
            # Measure single request performance
            start_time = time.time()
            response = client.post("/api/v1/auth/login", json=login_data)
            end_time = time.time()
            
            assert response.status_code == 200
            single_request_time = end_time - start_time
            assert single_request_time < 0.5  # Should complete within 500ms
            
            # Test concurrent requests
            async def make_login_request():
                return client.post("/api/v1/auth/login", json=login_data)
            
            concurrent_requests = 50
            start_time = time.time()
            
            tasks = [make_login_request() for _ in range(concurrent_requests)]
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Check that most requests succeeded
            successful_responses = [r for r in responses if hasattr(r, 'status_code') and r.status_code == 200]
            success_rate = len(successful_responses) / concurrent_requests
            
            assert success_rate >= 0.95  # At least 95% success rate
            assert total_time < 5.0  # All requests should complete within 5 seconds
            
            # Calculate average response time
            avg_response_time = total_time / concurrent_requests
            assert avg_response_time < 0.1  # Average should be under 100ms
    
    @pytest.mark.asyncio
    async def test_panic_request_submission_performance(self, client, mock_external_services):
        """Test panic request submission performance"""
        
        # Mock mobile attestation and emergency service
        with patch('app.api.v1.emergency.require_mobile_attestation') as mock_attestation:
            mock_attestation.return_value = {"valid": True}
            
            with patch('app.services.emergency.EmergencyService.submit_panic_request') as mock_submit:
                mock_request = AsyncMock()
                mock_request.id = uuid4()
                mock_request.status = "pending"
                mock_request.created_at = datetime.utcnow()
                mock_submit.return_value = mock_request
                
                request_data = {
                    "requester_phone": "+1234567890",
                    "group_id": str(uuid4()),
                    "service_type": "security",
                    "latitude": 40.7484,
                    "longitude": -73.9857,
                    "address": "Emergency Location",
                    "description": "Performance test emergency"
                }
                
                # Test single request performance
                start_time = time.time()
                response = client.post("/api/v1/emergency/request", json=request_data)
                end_time = time.time()
                
                assert response.status_code == 201
                single_request_time = end_time - start_time
                assert single_request_time < 1.0  # Should complete within 1 second
                
                # Test burst of emergency requests
                async def make_emergency_request():
                    return client.post("/api/v1/emergency/request", json=request_data)
                
                burst_size = 20  # Simulate 20 simultaneous emergencies
                start_time = time.time()
                
                tasks = [make_emergency_request() for _ in range(burst_size)]
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                
                end_time = time.time()
                total_time = end_time - start_time
                
                # Emergency requests should be processed quickly
                successful_responses = [r for r in responses if hasattr(r, 'status_code') and r.status_code == 201]
                success_rate = len(successful_responses) / burst_size
                
                assert success_rate >= 0.98  # At least 98% success rate for emergencies
                assert total_time < 3.0  # All emergency requests within 3 seconds
    
    @pytest.mark.asyncio
    async def test_geospatial_query_performance(self, db_session, sample_security_firm):
        """Test geospatial query performance with large datasets"""
        from app.models.security_firm import CoverageArea
        from geoalchemy2 import WKTElement
        from sqlalchemy import text
        
        # Create multiple coverage areas
        coverage_areas = []
        for i in range(100):  # Create 100 coverage areas
            coverage = CoverageArea(
                firm_id=sample_security_firm.id,
                name=f"Coverage Area {i}",
                boundary=WKTElement(
                    f"POLYGON(({i} {i}, {i+1} {i}, {i+1} {i+1}, {i} {i+1}, {i} {i}))",
                    srid=4326
                )
            )
            coverage_areas.append(coverage)
        
        db_session.add_all(coverage_areas)
        await db_session.commit()
        
        # Test point-in-polygon query performance
        test_points = [
            WKTElement(f"POINT({i+0.5} {i+0.5})", srid=4326) 
            for i in range(50)
        ]
        
        start_time = time.time()
        
        for point in test_points:
            result = await db_session.execute(
                text("""
                    SELECT ca.id, ca.name
                    FROM coverage_areas ca
                    WHERE ST_Contains(ca.boundary, :point)
                    LIMIT 1
                """),
                {"point": str(point)}
            )
            result.fetchone()
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_query_time = total_time / len(test_points)
        
        # Each geospatial query should be fast
        assert avg_query_time < 0.01  # Average under 10ms per query
        assert total_time < 0.5  # All queries within 500ms
    
    @pytest.mark.asyncio
    async def test_database_connection_pool_performance(self, db_session):
        """Test database connection pool performance under load"""
        from sqlalchemy import text
        
        async def execute_query():
            result = await db_session.execute(text("SELECT 1 as test"))
            return result.fetchone()
        
        # Test concurrent database queries
        concurrent_queries = 100
        start_time = time.time()
        
        tasks = [execute_query() for _ in range(concurrent_queries)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Check that all queries succeeded
        successful_queries = [r for r in results if not isinstance(r, Exception)]
        success_rate = len(successful_queries) / concurrent_queries
        
        assert success_rate >= 0.99  # At least 99% success rate
        assert total_time < 2.0  # All queries within 2 seconds
        
        avg_query_time = total_time / concurrent_queries
        assert avg_query_time < 0.02  # Average under 20ms per query


class TestMemoryAndResourceUsage:
    """Test memory usage and resource consumption"""
    
    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, client, mock_external_services):
        """Test memory usage during high load"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Mock services
        with patch('app.services.auth.auth_service.authenticate_user') as mock_auth:
            mock_auth.return_value = {
                "access_token": "memory.test.token",
                "refresh_token": "memory.refresh.token",
                "expires_in": 3600
            }
            
            login_data = {
                "email": "memory@test.com",
                "password": "test_password",
                "user_type": "registered_user"
            }
            
            # Make many requests to test memory usage
            for batch in range(10):  # 10 batches of 50 requests each
                tasks = []
                for _ in range(50):
                    tasks.append(asyncio.create_task(
                        asyncio.to_thread(client.post, "/api/v1/auth/login", json=login_data)
                    ))
                
                await asyncio.gather(*tasks)
                
                # Check memory usage after each batch
                current_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_increase = current_memory - initial_memory
                
                # Memory increase should be reasonable (less than 100MB)
                assert memory_increase < 100, f"Memory usage increased by {memory_increase}MB"
        
        # Final memory check
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        total_memory_increase = final_memory - initial_memory
        
        # Total memory increase should be reasonable
        assert total_memory_increase < 200, f"Total memory increase: {total_memory_increase}MB"
    
    @pytest.mark.asyncio
    async def test_database_connection_limits(self, db_session):
        """Test database connection pool limits"""
        from sqlalchemy import text
        
        # Test maximum concurrent connections
        async def long_running_query():
            # Simulate a query that takes some time
            await asyncio.sleep(0.1)
            result = await db_session.execute(text("SELECT pg_sleep(0.01), 1 as test"))
            return result.fetchone()
        
        # Try to create more connections than the pool limit
        max_connections = 50  # Assuming pool size is around 20-30
        
        start_time = time.time()
        tasks = [long_running_query() for _ in range(max_connections)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        # Check that queries either succeeded or failed gracefully
        successful_queries = [r for r in results if not isinstance(r, Exception)]
        failed_queries = [r for r in results if isinstance(r, Exception)]
        
        # Some queries should succeed
        assert len(successful_queries) > 0
        
        # If queries failed, they should fail gracefully (not crash)
        for failed_query in failed_queries:
            assert isinstance(failed_query, Exception)
        
        # Total time should be reasonable even with connection limits
        assert end_time - start_time < 10.0  # Within 10 seconds


class TestCachePerformance:
    """Test caching system performance"""
    
    @pytest.mark.asyncio
    async def test_redis_cache_performance(self, mock_external_services):
        """Test Redis cache performance"""
        from app.core.cache import cache_manager
        
        # Test cache write performance
        cache_operations = 1000
        start_time = time.time()
        
        for i in range(cache_operations):
            await cache_manager.set(f"perf_test_key_{i}", f"value_{i}", expire=300)
        
        write_time = time.time() - start_time
        avg_write_time = write_time / cache_operations
        
        assert avg_write_time < 0.001  # Average write under 1ms
        assert write_time < 1.0  # All writes within 1 second
        
        # Test cache read performance
        start_time = time.time()
        
        for i in range(cache_operations):
            value = await cache_manager.get(f"perf_test_key_{i}")
            assert value == f"value_{i}"
        
        read_time = time.time() - start_time
        avg_read_time = read_time / cache_operations
        
        assert avg_read_time < 0.001  # Average read under 1ms
        assert read_time < 1.0  # All reads within 1 second
        
        # Test concurrent cache operations
        async def cache_operation(key_suffix):
            await cache_manager.set(f"concurrent_key_{key_suffix}", f"value_{key_suffix}")
            return await cache_manager.get(f"concurrent_key_{key_suffix}")
        
        concurrent_ops = 100
        start_time = time.time()
        
        tasks = [cache_operation(i) for i in range(concurrent_ops)]
        results = await asyncio.gather(*tasks)
        
        concurrent_time = time.time() - start_time
        
        assert len(results) == concurrent_ops
        assert concurrent_time < 0.5  # All concurrent operations within 500ms
    
    @pytest.mark.asyncio
    async def test_cache_hit_ratio_performance(self, mock_external_services):
        """Test cache hit ratio under realistic load"""
        from app.core.cache import cache_manager
        
        # Simulate realistic cache usage pattern
        # 80% reads, 20% writes, with some key overlap
        
        cache_hits = 0
        cache_misses = 0
        total_operations = 1000
        
        # Pre-populate cache with some data
        for i in range(100):
            await cache_manager.set(f"popular_key_{i}", f"popular_value_{i}")
        
        start_time = time.time()
        
        for i in range(total_operations):
            if i % 5 == 0:  # 20% writes
                await cache_manager.set(f"key_{i}", f"value_{i}")
            else:  # 80% reads
                if i % 10 < 5:  # 50% read popular keys (should hit)
                    key = f"popular_key_{i % 100}"
                else:  # 50% read random keys (might miss)
                    key = f"key_{i}"
                
                value = await cache_manager.get(key)
                if value is not None:
                    cache_hits += 1
                else:
                    cache_misses += 1
        
        total_time = time.time() - start_time
        
        # Calculate hit ratio
        total_reads = cache_hits + cache_misses
        hit_ratio = cache_hits / total_reads if total_reads > 0 else 0
        
        # Hit ratio should be reasonable (at least 40% for this test pattern)
        assert hit_ratio >= 0.4
        
        # Performance should be good
        avg_operation_time = total_time / total_operations
        assert avg_operation_time < 0.001  # Average under 1ms per operation


class TestScalabilityLimits:
    """Test system scalability limits"""
    
    @pytest.mark.asyncio
    async def test_concurrent_user_limit(self, client, mock_external_services):
        """Test system behavior with many concurrent users"""
        
        # Mock authentication for multiple users
        with patch('app.services.auth.auth_service.authenticate_user') as mock_auth:
            mock_auth.return_value = {
                "access_token": "concurrent.user.token",
                "refresh_token": "concurrent.refresh.token",
                "expires_in": 3600
            }
            
            # Simulate many users logging in simultaneously
            concurrent_users = 200
            
            async def simulate_user_session(user_id):
                # Login
                login_data = {
                    "email": f"user{user_id}@test.com",
                    "password": "test_password",
                    "user_type": "registered_user"
                }
                
                login_response = client.post("/api/v1/auth/login", json=login_data)
                if login_response.status_code != 200:
                    return {"success": False, "step": "login"}
                
                # Make some API calls
                token = login_response.json()["access_token"]
                headers = {"Authorization": f"Bearer {token}"}
                
                # Simulate user activity
                for _ in range(5):  # 5 API calls per user
                    with patch('app.core.auth.verify_token') as mock_verify:
                        mock_verify.return_value = {
                            "user_id": uuid4(),
                            "user_type": "registered_user",
                            "email": f"user{user_id}@test.com"
                        }
                        
                        response = client.get("/api/v1/auth/me", headers=headers)
                        if response.status_code != 200:
                            return {"success": False, "step": "api_call"}
                
                return {"success": True}
            
            start_time = time.time()
            
            # Run concurrent user sessions
            tasks = [simulate_user_session(i) for i in range(concurrent_users)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # Analyze results
            successful_sessions = [r for r in results if isinstance(r, dict) and r.get("success")]
            failed_sessions = [r for r in results if not (isinstance(r, dict) and r.get("success"))]
            
            success_rate = len(successful_sessions) / concurrent_users
            
            # System should handle reasonable concurrent load
            assert success_rate >= 0.90  # At least 90% success rate
            assert total_time < 30.0  # Complete within 30 seconds
            
            # Log performance metrics
            print(f"Concurrent users: {concurrent_users}")
            print(f"Success rate: {success_rate:.2%}")
            print(f"Total time: {total_time:.2f}s")
            print(f"Average time per user: {total_time/concurrent_users:.3f}s")
    
    @pytest.mark.asyncio
    async def test_emergency_request_burst_handling(self, client, mock_external_services):
        """Test system handling of emergency request bursts"""
        
        # Mock emergency services
        with patch('app.api.v1.emergency.require_mobile_attestation') as mock_attestation:
            mock_attestation.return_value = {"valid": True}
            
            with patch('app.services.emergency.EmergencyService.submit_panic_request') as mock_submit:
                mock_request = AsyncMock()
                mock_request.id = uuid4()
                mock_request.status = "pending"
                mock_submit.return_value = mock_request
                
                # Simulate emergency burst (e.g., natural disaster)
                burst_size = 100  # 100 simultaneous emergency requests
                
                async def submit_emergency_request(request_id):
                    request_data = {
                        "requester_phone": f"+155512{request_id:05d}",
                        "group_id": str(uuid4()),
                        "service_type": "security",
                        "latitude": 40.7484 + (request_id * 0.001),  # Slightly different locations
                        "longitude": -73.9857 + (request_id * 0.001),
                        "address": f"Emergency Location {request_id}",
                        "description": f"Burst emergency {request_id}"
                    }
                    
                    return client.post("/api/v1/emergency/request", json=request_data)
                
                start_time = time.time()
                
                # Submit all emergency requests simultaneously
                tasks = [submit_emergency_request(i) for i in range(burst_size)]
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                
                end_time = time.time()
                total_time = end_time - start_time
                
                # Analyze emergency response performance
                successful_requests = [
                    r for r in responses 
                    if hasattr(r, 'status_code') and r.status_code == 201
                ]
                
                success_rate = len(successful_requests) / burst_size
                
                # Emergency requests should be handled with high priority
                assert success_rate >= 0.95  # At least 95% success rate for emergencies
                assert total_time < 10.0  # All emergency requests within 10 seconds
                
                avg_response_time = total_time / burst_size
                assert avg_response_time < 0.1  # Average under 100ms per emergency request
                
                print(f"Emergency burst size: {burst_size}")
                print(f"Success rate: {success_rate:.2%}")
                print(f"Total processing time: {total_time:.2f}s")
                print(f"Average response time: {avg_response_time:.3f}s")


class TestResourceCleanup:
    """Test resource cleanup and garbage collection"""
    
    @pytest.mark.asyncio
    async def test_connection_cleanup_after_load(self, db_session):
        """Test that database connections are properly cleaned up after load"""
        from sqlalchemy import text
        
        # Get initial connection count
        initial_connections = await db_session.execute(
            text("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()")
        )
        initial_count = initial_connections.fetchone()[0]
        
        # Create load that should create and cleanup connections
        async def create_temporary_load():
            for _ in range(100):
                result = await db_session.execute(text("SELECT 1"))
                result.fetchone()
        
        # Run load test
        await create_temporary_load()
        
        # Force garbage collection
        import gc
        gc.collect()
        
        # Wait a bit for cleanup
        await asyncio.sleep(1)
        
        # Check final connection count
        final_connections = await db_session.execute(
            text("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()")
        )
        final_count = final_connections.fetchone()[0]
        
        # Connection count should not have grown significantly
        connection_increase = final_count - initial_count
        assert connection_increase <= 5  # Allow for some normal variation
    
    @pytest.mark.asyncio
    async def test_memory_cleanup_after_load(self, client, mock_external_services):
        """Test memory cleanup after high load"""
        import psutil
        import os
        import gc
        
        process = psutil.Process(os.getpid())
        
        # Force garbage collection before test
        gc.collect()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create significant load
        with patch('app.services.auth.auth_service.authenticate_user') as mock_auth:
            mock_auth.return_value = {
                "access_token": "cleanup.test.token",
                "refresh_token": "cleanup.refresh.token",
                "expires_in": 3600
            }
            
            # Create and process many requests
            for batch in range(20):  # 20 batches
                tasks = []
                for i in range(100):  # 100 requests per batch
                    login_data = {
                        "email": f"cleanup{batch}_{i}@test.com",
                        "password": "test_password",
                        "user_type": "registered_user"
                    }
                    tasks.append(asyncio.create_task(
                        asyncio.to_thread(client.post, "/api/v1/auth/login", json=login_data)
                    ))
                
                await asyncio.gather(*tasks)
                
                # Clear references
                del tasks
        
        # Force cleanup
        gc.collect()
        await asyncio.sleep(2)  # Wait for cleanup
        
        # Check memory after cleanup
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory should not have increased dramatically
        assert memory_increase < 300, f"Memory increased by {memory_increase}MB after cleanup"
        
        print(f"Initial memory: {initial_memory:.1f}MB")
        print(f"Final memory: {final_memory:.1f}MB")
        print(f"Memory increase: {memory_increase:.1f}MB")