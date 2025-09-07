"""
Unit tests for metrics collection system
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import asyncio

from app.core.metrics import (
    MetricsCollector,
    metrics_collector,
    track_time,
    track_request_time
)
from app.services.metrics import MetricsService, metrics_service
from app.core.metrics_middleware import MetricsMiddleware
from fastapi import Request, Response
from fastapi.testclient import TestClient


class TestMetricsCollector:
    """Test the core metrics collector"""
    
    def setup_method(self):
        """Setup test environment"""
        self.collector = MetricsCollector()
    
    def test_record_http_request(self):
        """Test HTTP request metrics recording"""
        # Record a request
        self.collector.record_http_request("GET", "/api/v1/users", 200, 0.5)
        
        # Get metrics and verify
        metrics = self.collector.get_metrics()
        assert "http_requests_total" in metrics
        assert "http_request_duration_seconds" in metrics
        assert 'method="GET"' in metrics
        assert 'endpoint="/api/v1/users"' in metrics
        assert 'status_code="200"' in metrics
    
    def test_record_auth_attempt(self):
        """Test authentication metrics recording"""
        # Record successful auth
        self.collector.record_auth_attempt("success", "registered_user")
        
        # Record failed auth
        self.collector.record_failed_login("registered_user")
        
        # Record account lockout
        self.collector.record_account_lockout("registered_user")
        
        metrics = self.collector.get_metrics()
        assert "auth_attempts_total" in metrics
        assert "failed_login_attempts_total" in metrics
        assert "account_lockouts_total" in metrics
        assert 'user_type="registered_user"' in metrics
    
    def test_record_panic_request(self):
        """Test panic request metrics recording"""
        # Record panic request
        self.collector.record_panic_request("security", "submitted", "firm123")
        
        # Record response time
        self.collector.record_panic_response_time("security", "zone1", 120.5)
        
        # Record completion time
        self.collector.record_panic_completion_time("security", "zone1", 600.0)
        
        metrics = self.collector.get_metrics()
        assert "panic_requests_total" in metrics
        assert "panic_request_response_time_seconds" in metrics
        assert "panic_request_completion_time_seconds" in metrics
        assert 'service_type="security"' in metrics
        assert 'firm_id="firm123"' in metrics
        assert 'zone="zone1"' in metrics
    
    def test_record_subscription_metrics(self):
        """Test subscription metrics recording"""
        # Update active subscriptions
        self.collector.update_active_subscriptions("firm123", 50)
        
        # Record purchase
        self.collector.record_subscription_purchase("product456", "firm123")
        
        # Record credit transaction
        self.collector.record_credit_transaction("purchase", "firm123")
        
        metrics = self.collector.get_metrics()
        assert "active_subscriptions_total" in metrics
        assert "subscription_purchases_total" in metrics
        assert "credit_transactions_total" in metrics
    
    def test_record_prank_detection(self):
        """Test prank detection metrics recording"""
        # Record prank flag
        self.collector.record_prank_flag("user123", "firm456")
        
        # Record fine
        self.collector.record_user_fine("user123", "50.00")
        
        metrics = self.collector.get_metrics()
        assert "prank_flags_total" in metrics
        assert "user_fines_total" in metrics
        assert 'user_id="user123"' in metrics
        assert 'firm_id="firm456"' in metrics
    
    def test_system_health_metrics(self):
        """Test system health metrics"""
        # Update system metrics
        self.collector.update_database_connections(25)
        self.collector.update_redis_connections(15)
        self.collector.update_cache_hit_rate("redis", 85.5)
        self.collector.update_websocket_connections("user", 100)
        
        metrics = self.collector.get_metrics()
        assert "database_connections_active" in metrics
        assert "redis_connections_active" in metrics
        assert "cache_hit_rate" in metrics
        assert "websocket_connections_active" in metrics
    
    def test_notification_metrics(self):
        """Test notification metrics recording"""
        # Record successful notification
        self.collector.record_notification_sent("push", "success")
        
        # Record failed notification
        self.collector.record_notification_sent("sms", "failed")
        
        metrics = self.collector.get_metrics()
        assert "notifications_sent_total" in metrics
        assert 'type="push"' in metrics
        assert 'status="success"' in metrics
        assert 'type="sms"' in metrics
        assert 'status="failed"' in metrics
    
    def test_performance_metrics(self):
        """Test performance metrics updates"""
        # Update zone performance
        self.collector.update_zone_performance("zone1", "security", 180.5)
        
        # Update firm performance
        self.collector.update_firm_performance("firm123", "ambulance", 240.0)
        
        metrics = self.collector.get_metrics()
        assert "zone_average_response_time_seconds" in metrics
        assert "firm_average_response_time_seconds" in metrics
        assert 'zone_id="zone1"' in metrics
        assert 'firm_id="firm123"' in metrics


class TestMetricsService:
    """Test the metrics service"""
    
    def setup_method(self):
        """Setup test environment"""
        self.service = MetricsService()
    
    @pytest.mark.asyncio
    async def test_record_panic_request_submitted(self):
        """Test panic request submission recording"""
        with patch.object(self.service.metrics_collector, 'record_panic_request') as mock_record:
            await self.service.record_panic_request_submitted("security", "firm123", "zone1")
            
            mock_record.assert_called_once_with(
                service_type="security",
                status="submitted",
                firm_id="firm123"
            )
    
    @pytest.mark.asyncio
    async def test_record_panic_request_accepted(self):
        """Test panic request acceptance recording"""
        with patch.object(self.service.metrics_collector, 'record_panic_request') as mock_record, \
             patch.object(self.service.metrics_collector, 'record_panic_response_time') as mock_response:
            
            await self.service.record_panic_request_accepted(
                "req123", "security", "firm123", "zone1", 120.5
            )
            
            mock_record.assert_called_once_with(
                service_type="security",
                status="accepted",
                firm_id="firm123"
            )
            mock_response.assert_called_once_with(
                service_type="security",
                zone="zone1",
                response_time=120.5
            )
    
    @pytest.mark.asyncio
    async def test_record_authentication_metrics(self):
        """Test authentication metrics recording"""
        with patch.object(self.service.metrics_collector, 'record_auth_attempt') as mock_auth, \
             patch.object(self.service.metrics_collector, 'record_failed_login') as mock_failed, \
             patch.object(self.service.metrics_collector, 'record_account_lockout') as mock_lockout:
            
            # Test successful auth
            await self.service.record_authentication_metrics("registered_user", True, False)
            mock_auth.assert_called_with("success", "registered_user")
            
            # Test failed auth with lockout
            await self.service.record_authentication_metrics("registered_user", False, True)
            mock_auth.assert_called_with("failed", "registered_user")
            mock_failed.assert_called_with("registered_user")
            mock_lockout.assert_called_with("registered_user")
    
    @pytest.mark.asyncio
    async def test_update_system_health_metrics(self):
        """Test system health metrics update"""
        mock_db = AsyncMock()
        
        with patch.object(self.service.metrics_collector, 'update_database_connections') as mock_db_conn, \
             patch.object(self.service.metrics_collector, 'update_redis_connections') as mock_redis_conn:
            
            await self.service.update_system_health_metrics(mock_db)
            
            mock_db_conn.assert_called_once()
            mock_redis_conn.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_performance_metrics(self):
        """Test performance metrics update"""
        mock_db = AsyncMock()
        
        # Mock database query results
        zone_result = Mock()
        zone_result.zone_id = "zone1"
        zone_result.zone_name = "Downtown"
        zone_result.service_type = "security"
        zone_result.avg_response_time = 180.5
        
        firm_result = Mock()
        firm_result.firm_id = "firm123"
        firm_result.service_type = "ambulance"
        firm_result.avg_response_time = 240.0
        
        mock_db.execute.return_value = AsyncMock()
        mock_db.execute.return_value.__aiter__ = AsyncMock(return_value=iter([zone_result]))
        
        with patch.object(self.service.metrics_collector, 'update_zone_performance') as mock_zone, \
             patch.object(self.service.metrics_collector, 'update_firm_performance') as mock_firm:
            
            await self.service.update_performance_metrics(mock_db)
            
            # Verify database was queried
            assert mock_db.execute.call_count >= 1


class TestMetricsMiddleware:
    """Test the metrics middleware"""
    
    def setup_method(self):
        """Setup test environment"""
        self.middleware = MetricsMiddleware(Mock())
    
    @pytest.mark.asyncio
    async def test_dispatch_records_metrics(self):
        """Test that middleware records HTTP metrics"""
        # Create mock request and response
        request = Mock(spec=Request)
        request.method = "GET"
        request.url.path = "/api/v1/users"
        
        response = Mock(spec=Response)
        response.status_code = 200
        
        # Mock the call_next function
        async def mock_call_next(req):
            return response
        
        with patch.object(metrics_collector, 'record_http_request') as mock_record:
            result = await self.middleware.dispatch(request, mock_call_next)
            
            assert result == response
            mock_record.assert_called_once()
            
            # Verify the call arguments
            call_args = mock_record.call_args
            assert call_args[1]['method'] == "GET"
            assert call_args[1]['endpoint'] == "/api/v1/users"
            assert call_args[1]['status_code'] == 200
            assert 'duration' in call_args[1]
    
    @pytest.mark.asyncio
    async def test_dispatch_handles_exceptions(self):
        """Test that middleware handles exceptions properly"""
        request = Mock(spec=Request)
        request.method = "POST"
        request.url.path = "/api/v1/emergency"
        
        # Mock call_next to raise an exception
        async def mock_call_next(req):
            raise ValueError("Test error")
        
        with patch.object(metrics_collector, 'record_http_request') as mock_record:
            with pytest.raises(ValueError):
                await self.middleware.dispatch(request, mock_call_next)
            
            # Should still record metrics with 500 status
            mock_record.assert_called_once()
            call_args = mock_record.call_args
            assert call_args[1]['status_code'] == 500
    
    def test_get_endpoint_pattern(self):
        """Test endpoint pattern extraction"""
        # Test API endpoint with ID
        request = Mock()
        request.url.path = "/api/v1/users/123e4567-e89b-12d3-a456-426614174000"
        pattern = self.middleware._get_endpoint_pattern(request)
        assert pattern == "/api/v1/users/{id}"
        
        # Test API endpoint without ID
        request.url.path = "/api/v1/users"
        pattern = self.middleware._get_endpoint_pattern(request)
        assert pattern == "/api/v1/users"
        
        # Test root endpoint
        request.url.path = "/"
        pattern = self.middleware._get_endpoint_pattern(request)
        assert pattern == "/"
        
        # Test health endpoint
        request.url.path = "/health"
        pattern = self.middleware._get_endpoint_pattern(request)
        assert pattern == "/health"
    
    def test_is_uuid_or_id(self):
        """Test UUID and ID detection"""
        # Test UUID
        assert self.middleware._is_uuid_or_id("123e4567-e89b-12d3-a456-426614174000") == True
        
        # Test numeric ID
        assert self.middleware._is_uuid_or_id("12345") == True
        
        # Test non-ID string
        assert self.middleware._is_uuid_or_id("users") == False
        assert self.middleware._is_uuid_or_id("emergency") == False


class TestMetricsDecorators:
    """Test metrics decorators and context managers"""
    
    @pytest.mark.asyncio
    async def test_track_time_decorator_async(self):
        """Test track_time decorator with async function"""
        
        @track_time("panic_response_time", {"service_type": "security", "zone": "zone1"})
        async def mock_async_function():
            await asyncio.sleep(0.1)
            return "result"
        
        with patch.object(metrics_collector, 'record_panic_response_time') as mock_record:
            result = await mock_async_function()
            
            assert result == "result"
            mock_record.assert_called_once()
            
            # Verify timing was recorded
            call_args = mock_record.call_args
            assert call_args[0][0] == "security"  # service_type
            assert call_args[0][1] == "zone1"     # zone
            assert call_args[0][2] >= 0.1         # duration should be at least 0.1s
    
    def test_track_time_decorator_sync(self):
        """Test track_time decorator with sync function"""
        
        @track_time("panic_response_time", {"service_type": "ambulance", "zone": "zone2"})
        def mock_sync_function():
            import time
            time.sleep(0.1)
            return "sync_result"
        
        with patch.object(metrics_collector, 'record_panic_response_time') as mock_record:
            result = mock_sync_function()
            
            assert result == "sync_result"
            mock_record.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_track_request_time_context_manager(self):
        """Test track_request_time context manager"""
        
        with patch.object(metrics_collector, 'record_panic_response_time') as mock_record:
            async with track_request_time("fire", "zone3"):
                await asyncio.sleep(0.05)
            
            mock_record.assert_called_once()
            call_args = mock_record.call_args
            assert call_args[0][0] == "fire"      # service_type
            assert call_args[0][1] == "zone3"     # zone
            assert call_args[0][2] >= 0.05        # duration


class TestMetricsIntegration:
    """Integration tests for metrics system"""
    
    @pytest.mark.asyncio
    async def test_metrics_service_integration(self):
        """Test metrics service integration"""
        service = MetricsService()
        
        # Test recording various metrics
        await service.record_panic_request_submitted("security", "firm123")
        await service.record_authentication_metrics("registered_user", True)
        await service.record_subscription_purchase("product456", "firm123")
        await service.record_prank_detection("user789", "firm123", 25.0)
        await service.record_notification_sent("push", True)
        
        # Verify metrics were recorded (by checking the collector has data)
        metrics = metrics_collector.get_metrics()
        assert len(metrics) > 0
    
    def test_global_metrics_collector_singleton(self):
        """Test that global metrics collector is a singleton"""
        from app.core.metrics import metrics_collector as collector1
        from app.core.metrics import metrics_collector as collector2
        
        assert collector1 is collector2
    
    def test_global_metrics_service_singleton(self):
        """Test that global metrics service is a singleton"""
        from app.services.metrics import metrics_service as service1
        from app.services.metrics import metrics_service as service2
        
        assert service1 is service2


if __name__ == "__main__":
    pytest.main([__file__])