"""
Unit tests for metrics API endpoints
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import json

from app.main import app
from app.core.config import settings
from app.api.v1.metrics import router


class TestMetricsAPI:
    """Test metrics API endpoints"""
    
    def setup_method(self):
        """Setup test environment"""
        self.client = TestClient(app)
    
    def test_get_prometheus_metrics_enabled(self):
        """Test Prometheus metrics endpoint when enabled"""
        with patch.object(settings, 'METRICS_ENABLED', True):
            with patch('app.api.v1.metrics.metrics_collector') as mock_collector:
                mock_collector.get_metrics.return_value = """
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",endpoint="/api/v1/users",status_code="200"} 10
"""
                
                response = self.client.get("/api/v1/metrics/prometheus")
                
                assert response.status_code == 200
                assert response.headers["content-type"] == "text/plain; version=0.0.4; charset=utf-8"
                assert "http_requests_total" in response.text
                mock_collector.get_metrics.assert_called_once()
    
    def test_get_prometheus_metrics_disabled(self):
        """Test Prometheus metrics endpoint when disabled"""
        with patch.object(settings, 'METRICS_ENABLED', False):
            response = self.client.get("/api/v1/metrics/prometheus")
            
            assert response.status_code == 404
            assert response.json()["detail"] == "Metrics disabled"
    
    @pytest.mark.asyncio
    async def test_get_system_health_success(self):
        """Test system health endpoint success"""
        mock_db = AsyncMock()
        mock_db.execute.return_value = None
        
        with patch('app.api.v1.metrics.get_db') as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_db
            
            response = self.client.get("/api/v1/metrics/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "timestamp" in data
            assert data["database"]["status"] == "connected"
            assert "latency_ms" in data["database"]
            assert data["metrics"]["enabled"] == settings.METRICS_ENABLED
    
    @pytest.mark.asyncio
    async def test_get_system_health_database_error(self):
        """Test system health endpoint with database error"""
        mock_db = AsyncMock()
        mock_db.execute.side_effect = Exception("Database connection failed")
        
        with patch('app.api.v1.metrics.get_db') as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_db
            
            response = self.client.get("/api/v1/metrics/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "unhealthy"
            assert "error" in data
            assert data["database"]["status"] == "disconnected"
    
    @pytest.mark.asyncio
    async def test_get_business_metrics(self):
        """Test business metrics endpoint"""
        # Mock database results
        mock_panic_row = Mock()
        mock_panic_row.service_type = "security"
        mock_panic_row.status = "completed"
        mock_panic_row.count = 25
        mock_panic_row.avg_response_time = 180.5
        mock_panic_row.avg_completion_time = 600.0
        
        mock_subscription_row = Mock()
        mock_subscription_row.active_subscriptions = 150
        mock_subscription_row.unique_users = 75
        
        mock_prank_row = Mock()
        mock_prank_row.total_prank_flags = 5
        mock_prank_row.users_with_pranks = 3
        
        mock_db = AsyncMock()
        mock_execute_results = [
            AsyncMock(__iter__=lambda x: iter([mock_panic_row])),
            AsyncMock(fetchone=lambda: mock_subscription_row),
            AsyncMock(fetchone=lambda: mock_prank_row)
        ]
        mock_db.execute.side_effect = mock_execute_results
        
        with patch('app.api.v1.metrics.get_db') as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_db
            
            response = self.client.get("/api/v1/metrics/business?hours=24")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["period_hours"] == 24
            assert "timestamp" in data
            assert len(data["panic_requests"]) == 1
            assert data["panic_requests"][0]["service_type"] == "security"
            assert data["panic_requests"][0]["count"] == 25
            assert data["subscriptions"]["active_subscriptions"] == 150
            assert data["prank_detection"]["total_flags"] == 5
    
    @pytest.mark.asyncio
    async def test_get_performance_metrics(self):
        """Test performance metrics endpoint"""
        # Mock database result
        mock_row = Mock()
        mock_row.zone_name = "Downtown"
        mock_row.service_type = "security"
        mock_row.total_requests = 50
        mock_row.avg_response_time = 180.5
        mock_row.avg_completion_time = 600.0
        mock_row.completed_requests = 45
        mock_row.prank_requests = 2
        
        mock_db = AsyncMock()
        mock_db.execute.return_value = AsyncMock(__iter__=lambda x: iter([mock_row]))
        
        with patch('app.api.v1.metrics.get_db') as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_db
            
            response = self.client.get("/api/v1/metrics/performance?hours=24")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["period_hours"] == 24
            assert data["firm_id"] is None
            assert len(data["performance_by_zone"]) == 1
            
            zone_data = data["performance_by_zone"][0]
            assert zone_data["zone_name"] == "Downtown"
            assert zone_data["service_type"] == "security"
            assert zone_data["total_requests"] == 50
            assert zone_data["completion_rate_percent"] == 90.0  # 45/50 * 100
            assert zone_data["prank_rate_percent"] == 4.0       # 2/50 * 100
    
    @pytest.mark.asyncio
    async def test_get_performance_metrics_with_firm_filter(self):
        """Test performance metrics endpoint with firm filter"""
        mock_db = AsyncMock()
        mock_db.execute.return_value = AsyncMock(__iter__=lambda x: iter([]))
        
        with patch('app.api.v1.metrics.get_db') as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_db
            
            response = self.client.get("/api/v1/metrics/performance?firm_id=firm123&hours=12")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["firm_id"] == "firm123"
            assert data["period_hours"] == 12
    
    @pytest.mark.asyncio
    async def test_get_active_alerts(self):
        """Test active alerts endpoint"""
        # Mock slow zones result
        mock_slow_row = Mock()
        mock_slow_row.zone_name = "Uptown"
        mock_slow_row.service_type = "ambulance"
        mock_slow_row.avg_response_time = 450.0  # Above threshold
        mock_slow_row.request_count = 5
        
        # Mock prank rate result
        mock_prank_row = Mock()
        mock_prank_row.zone_name = "Downtown"
        mock_prank_row.total_requests = 20
        mock_prank_row.prank_requests = 5  # 25% prank rate
        
        mock_db = AsyncMock()
        mock_execute_results = [
            AsyncMock(__iter__=lambda x: iter([mock_slow_row])),
            AsyncMock(__iter__=lambda x: iter([mock_prank_row]))
        ]
        mock_db.execute.side_effect = mock_execute_results
        
        with patch('app.api.v1.metrics.get_db') as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_db
            
            response = self.client.get("/api/v1/metrics/alerts")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["alert_count"] == 2
            assert len(data["alerts"]) == 2
            
            # Check slow response alert
            slow_alert = next(a for a in data["alerts"] if a["type"] == "slow_response_time")
            assert slow_alert["zone"] == "Uptown"
            assert slow_alert["service_type"] == "ambulance"
            assert slow_alert["avg_response_time"] == 450.0
            assert slow_alert["severity"] == "warning"
            
            # Check prank rate alert
            prank_alert = next(a for a in data["alerts"] if a["type"] == "high_prank_rate")
            assert prank_alert["zone"] == "Downtown"
            assert prank_alert["prank_rate_percent"] == 25.0
            assert prank_alert["severity"] == "warning"
    
    def test_update_cache_metrics(self):
        """Test cache metrics update endpoint"""
        with patch('app.api.v1.metrics.metrics_collector') as mock_collector:
            response = self.client.post("/api/v1/metrics/update-cache-metrics")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] == "success"
            assert data["message"] == "Cache metrics updated"
            assert "timestamp" in data
            
            # Verify cache metrics were updated
            assert mock_collector.update_cache_hit_rate.call_count == 2
            mock_collector.update_cache_hit_rate.assert_any_call("redis", 85.5)
            mock_collector.update_cache_hit_rate.assert_any_call("application", 92.3)
    
    @pytest.mark.asyncio
    async def test_business_metrics_database_error(self):
        """Test business metrics endpoint with database error"""
        mock_db = AsyncMock()
        mock_db.execute.side_effect = Exception("Database query failed")
        
        with patch('app.api.v1.metrics.get_db') as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_db
            
            response = self.client.get("/api/v1/metrics/business")
            
            assert response.status_code == 500
            assert "Error fetching business metrics" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_performance_metrics_database_error(self):
        """Test performance metrics endpoint with database error"""
        mock_db = AsyncMock()
        mock_db.execute.side_effect = Exception("Database query failed")
        
        with patch('app.api.v1.metrics.get_db') as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_db
            
            response = self.client.get("/api/v1/metrics/performance")
            
            assert response.status_code == 500
            assert "Error fetching performance metrics" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_alerts_database_error(self):
        """Test alerts endpoint with database error"""
        mock_db = AsyncMock()
        mock_db.execute.side_effect = Exception("Database query failed")
        
        with patch('app.api.v1.metrics.get_db') as mock_get_db:
            mock_get_db.return_value.__aenter__.return_value = mock_db
            
            response = self.client.get("/api/v1/metrics/alerts")
            
            assert response.status_code == 500
            assert "Error fetching alerts" in response.json()["detail"]
    
    def test_update_cache_metrics_error(self):
        """Test cache metrics update endpoint with error"""
        with patch('app.api.v1.metrics.metrics_collector') as mock_collector:
            mock_collector.update_cache_hit_rate.side_effect = Exception("Cache update failed")
            
            response = self.client.post("/api/v1/metrics/update-cache-metrics")
            
            assert response.status_code == 500
            assert "Error updating cache metrics" in response.json()["detail"]


class TestMetricsAPIIntegration:
    """Integration tests for metrics API"""
    
    def setup_method(self):
        """Setup test environment"""
        self.client = TestClient(app)
    
    def test_metrics_endpoints_exist(self):
        """Test that all metrics endpoints are properly registered"""
        # Test that endpoints return proper responses (not 404)
        endpoints = [
            "/api/v1/metrics/health",
            "/api/v1/metrics/business",
            "/api/v1/metrics/performance",
            "/api/v1/metrics/alerts"
        ]
        
        for endpoint in endpoints:
            response = self.client.get(endpoint)
            # Should not be 404 (endpoint exists)
            assert response.status_code != 404
    
    def test_prometheus_endpoint_content_type(self):
        """Test Prometheus endpoint returns correct content type"""
        with patch.object(settings, 'METRICS_ENABLED', True):
            with patch('app.api.v1.metrics.metrics_collector') as mock_collector:
                mock_collector.get_metrics.return_value = "# Test metrics\n"
                
                response = self.client.get("/api/v1/metrics/prometheus")
                
                assert response.status_code == 200
                assert "text/plain" in response.headers["content-type"]
                assert "version=0.0.4" in response.headers["content-type"]
    
    def test_health_endpoint_response_structure(self):
        """Test health endpoint returns expected structure"""
        response = self.client.get("/api/v1/metrics/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        required_fields = ["status", "timestamp", "database", "metrics"]
        for field in required_fields:
            assert field in data
        
        # Check database section
        assert "status" in data["database"]
        
        # Check metrics section
        assert "enabled" in data["metrics"]


if __name__ == "__main__":
    pytest.main([__file__])