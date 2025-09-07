"""
Simple tests for metrics service core functionality
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.metrics import MetricsService
from app.models.emergency import PanicRequest
from app.models.metrics import ResponseTimeMetric


class TestMetricsServiceCore:
    """Test core metrics service functionality"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def metrics_service(self, mock_db):
        """Create metrics service instance"""
        return MetricsService(mock_db)
    
    def test_get_performance_status_good(self, metrics_service):
        """Test performance status determination - good performance"""
        status = metrics_service._get_performance_status("security", 10.0)
        assert status == "good"
    
    def test_get_performance_status_warning(self, metrics_service):
        """Test performance status determination - warning performance"""
        status = metrics_service._get_performance_status("security", 20.0)
        assert status == "warning"
    
    def test_get_performance_status_critical(self, metrics_service):
        """Test performance status determination - critical performance"""
        status = metrics_service._get_performance_status("security", 40.0)
        assert status == "critical"
    
    def test_get_performance_status_unknown_service(self, metrics_service):
        """Test performance status determination - unknown service type"""
        status = metrics_service._get_performance_status("unknown", 10.0)
        assert status == "unknown"
    
    def test_get_performance_status_none_time(self, metrics_service):
        """Test performance status determination - None time"""
        status = metrics_service._get_performance_status("security", None)
        assert status == "unknown"
    
    def test_group_metrics_by_service_and_zone(self, metrics_service):
        """Test grouping metrics by service type and zone"""
        # Create sample metrics
        metrics = [
            ResponseTimeMetric(
                service_type="security", zone_name="Zone A", total_time=600
            ),
            ResponseTimeMetric(
                service_type="security", zone_name="Zone A", total_time=700
            ),
            ResponseTimeMetric(
                service_type="ambulance", zone_name="Zone B", total_time=500
            )
        ]
        
        groups = metrics_service._group_metrics_by_service_and_zone(metrics)
        
        assert len(groups) == 2
        assert ("security", "Zone A") in groups
        assert ("ambulance", "Zone B") in groups
        assert len(groups[("security", "Zone A")]) == 2
        assert len(groups[("ambulance", "Zone B")]) == 1
    
    def test_calculate_average_total_time_valid_metrics(self, metrics_service):
        """Test calculating average total time with valid metrics"""
        metrics = [
            ResponseTimeMetric(total_time=600),  # 10 minutes
            ResponseTimeMetric(total_time=900),  # 15 minutes
            ResponseTimeMetric(total_time=1200)  # 20 minutes
        ]
        
        avg_time = metrics_service._calculate_average_total_time(metrics)
        assert avg_time == 15.0  # (10+15+20)/3
    
    def test_calculate_average_total_time_with_none_values(self, metrics_service):
        """Test calculating average total time with None values"""
        metrics = [
            ResponseTimeMetric(total_time=600),
            ResponseTimeMetric(total_time=None),
            ResponseTimeMetric(total_time=900)
        ]
        
        avg_time = metrics_service._calculate_average_total_time(metrics)
        assert avg_time == 12.5  # (10+15)/2
    
    def test_calculate_average_total_time_all_none(self, metrics_service):
        """Test calculating average total time with all None values"""
        metrics = [
            ResponseTimeMetric(total_time=None),
            ResponseTimeMetric(total_time=None)
        ]
        
        avg_time = metrics_service._calculate_average_total_time(metrics)
        assert avg_time is None
    
    async def test_record_request_lifecycle_event_nonexistent_request(
        self, 
        metrics_service: MetricsService,
        mock_db: AsyncSession
    ):
        """Test recording event for nonexistent request"""
        fake_request_id = uuid4()
        
        # Mock database query to return None (request not found)
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        result = await metrics_service.record_request_lifecycle_event(
            fake_request_id, "accepted"
        )
        
        assert result is False
    
    async def test_record_request_lifecycle_event_accepted(
        self, 
        metrics_service: MetricsService,
        mock_db: AsyncSession
    ):
        """Test recording accepted event"""
        request_id = uuid4()
        timestamp = datetime.utcnow()
        
        # Create a mock panic request
        mock_panic_request = PanicRequest(
            id=request_id,
            group_id=uuid4(),
            requester_phone="+1234567890",
            service_type="security",
            address="Test Address",
            status="pending"
        )
        
        # Mock database query to return the panic request
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = mock_panic_request
        mock_db.execute.return_value = mock_result
        
        result = await metrics_service.record_request_lifecycle_event(
            request_id, "accepted", timestamp
        )
        
        assert result is True
        assert mock_panic_request.accepted_at == timestamp
        mock_db.commit.assert_called_once()
    
    async def test_create_performance_alert(
        self,
        metrics_service: MetricsService,
        mock_db: AsyncSession
    ):
        """Test creating performance alert"""
        firm_id = uuid4()
        
        # Mock the database operations
        mock_alert = MagicMock()
        mock_alert.firm_id = firm_id
        mock_alert.alert_type = "slow_response"
        mock_alert.severity = "high"
        mock_alert.zone_name = "Downtown"
        mock_alert.service_type = "security"
        mock_alert.metric_value = 35.5
        mock_alert.threshold_value = 25.0
        mock_alert.is_resolved = False
        
        # Mock database session methods
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Mock the PerformanceAlert constructor to return our mock
        with patch('app.services.metrics.PerformanceAlert', return_value=mock_alert):
            alert = await metrics_service.create_performance_alert(
                firm_id=firm_id,
                alert_type="slow_response",
                severity="high",
                message="Response times critically high",
                zone_name="Downtown",
                service_type="security",
                metric_value=35.5,
                threshold_value=25.0
            )
        
        assert alert.firm_id == firm_id
        assert alert.alert_type == "slow_response"
        assert alert.severity == "high"
        assert alert.zone_name == "Downtown"
        assert alert.service_type == "security"
        assert alert.metric_value == 35.5
        assert alert.threshold_value == 25.0
        assert not alert.is_resolved
        
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
    
    def test_response_time_thresholds_exist(self, metrics_service):
        """Test that response time thresholds are properly defined"""
        thresholds = metrics_service.RESPONSE_TIME_THRESHOLDS
        
        # Check that all expected service types have thresholds
        expected_services = ["security", "ambulance", "fire", "towing", "call"]
        for service in expected_services:
            assert service in thresholds
            assert "good" in thresholds[service]
            assert "warning" in thresholds[service]
            assert "critical" in thresholds[service]
            
            # Verify threshold values are reasonable
            assert thresholds[service]["good"] < thresholds[service]["warning"]
            assert thresholds[service]["warning"] < thresholds[service]["critical"]