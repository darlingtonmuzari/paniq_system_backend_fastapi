"""
Tests for metrics service
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.functions import ST_GeomFromText

from app.services.metrics import MetricsService, MetricsError
from app.models.emergency import PanicRequest
from app.models.metrics import ResponseTimeMetric, PerformanceAlert
from app.models.security_firm import SecurityFirm, CoverageArea
from app.models.user import UserGroup, RegisteredUser
from app.models.subscription import StoredSubscription, SubscriptionProduct


@pytest.fixture
def mock_db():
    """Mock database session"""
    return AsyncMock(spec=AsyncSession)

@pytest.fixture
def metrics_service(mock_db):
    """Create metrics service instance"""
    return MetricsService(mock_db)


@pytest.fixture
def sample_firm():
    """Create sample security firm"""
    firm = SecurityFirm(
        id=uuid4(),
        name="Test Security Firm",
        registration_number="TSF001",
        email="test@security.com",
        phone="+1234567890",
        address="123 Security St",
        verification_status="approved",
        credit_balance=1000
    )
    return firm


@pytest.fixture
def sample_coverage_area(sample_firm):
    """Create sample coverage area"""
    coverage_area = CoverageArea(
        id=uuid4(),
        firm_id=sample_firm.id,
        name="Downtown Zone",
        boundary=ST_GeomFromText("POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))", 4326)
    )
    return coverage_area


@pytest.fixture
def sample_user_and_group(sample_firm):
    """Create sample user and group with subscription"""
    user = RegisteredUser(
        id=uuid4(),
        email="test@user.com",
        phone="+1987654321",
        first_name="Test",
        last_name="User",
        is_verified=True
    )
    
    product = SubscriptionProduct(
        id=uuid4(),
        firm_id=sample_firm.id,
        name="Basic Security",
        description="Basic security service",
        max_users=10,
        price=99.99,
        credit_cost=100
    )
    product.firm = sample_firm
    
    subscription = StoredSubscription(
        id=uuid4(),
        user_id=user.id,
        product_id=product.id,
        is_applied=True
    )
    subscription.product = product
    
    group = UserGroup(
        id=uuid4(),
        user_id=user.id,
        name="Test Group",
        address="123 Test St",
        location=ST_GeomFromText("POINT(0.5 0.5)", 4326),
        subscription_id=subscription.id,
        subscription_expires_at=datetime.utcnow() + timedelta(days=30)
    )
    group.stored_subscription = subscription
    
    return user, group, product


@pytest.fixture
def sample_panic_request(sample_user_and_group):
    """Create sample panic request"""
    user, group, product = sample_user_and_group
    
    panic_request = PanicRequest(
        id=uuid4(),
        group_id=group.id,
        requester_phone="+1987654321",
        service_type="security",
        location=ST_GeomFromText("POINT(0.5 0.5)", 4326),
        address="123 Emergency St",
        description="Test emergency",
        status="pending"
    )
    panic_request.group = group
    return panic_request


class TestMetricsService:
    """Test metrics service functionality"""
    
    async def test_record_request_lifecycle_event_accepted(
        self, 
        metrics_service: MetricsService,
        sample_panic_request: PanicRequest,
        mock_db: AsyncSession
    ):
        """Test recording accepted event"""
        request_id = sample_panic_request.id
        timestamp = datetime.utcnow()
        
        # Mock database query to return the panic request
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_panic_request
        mock_db.execute.return_value = mock_result
        
        result = await metrics_service.record_request_lifecycle_event(
            request_id, "accepted", timestamp
        )
        
        assert result is True
        
        # Verify timestamp was set
        assert sample_panic_request.accepted_at == timestamp
        
        # Verify database operations were called
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()
    
    async def test_record_request_lifecycle_event_arrived(
        self, 
        metrics_service: MetricsService,
        sample_panic_request: PanicRequest,
        mock_db: AsyncSession
    ):
        """Test recording arrived event"""
        request_id = sample_panic_request.id
        timestamp = datetime.utcnow()
        
        # Mock database query to return the panic request
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_panic_request
        mock_db.execute.return_value = mock_result
        
        result = await metrics_service.record_request_lifecycle_event(
            request_id, "arrived", timestamp
        )
        
        assert result is True
        
        # Verify timestamp was set
        assert sample_panic_request.arrived_at == timestamp
    
    async def test_record_request_lifecycle_event_completed(
        self, 
        metrics_service: MetricsService,
        sample_panic_request: PanicRequest,
        sample_user_and_group,
        db_session: AsyncSession
    ):
        """Test recording completed event and metrics calculation"""
        user, group, product = sample_user_and_group
        request_id = sample_panic_request.id
        
        # Set up timestamps for a complete request lifecycle
        now = datetime.utcnow()
        sample_panic_request.accepted_at = now - timedelta(minutes=10)
        sample_panic_request.arrived_at = now - timedelta(minutes=5)
        
        # Mock the group relationship loading
        with patch.object(metrics_service, '_determine_zone_name', return_value="Test Zone"):
            result = await metrics_service.record_request_lifecycle_event(
                request_id, "completed", now
            )
        
        assert result is True
        
        # Verify timestamp was recorded
        await db_session.refresh(sample_panic_request)
        assert sample_panic_request.completed_at == now
    
    async def test_record_request_lifecycle_event_nonexistent_request(
        self, 
        metrics_service: MetricsService
    ):
        """Test recording event for nonexistent request"""
        fake_request_id = uuid4()
        
        result = await metrics_service.record_request_lifecycle_event(
            fake_request_id, "accepted"
        )
        
        assert result is False
    
    async def test_calculate_zone_metrics_with_data(
        self,
        metrics_service: MetricsService,
        sample_firm: SecurityFirm,
        db_session: AsyncSession
    ):
        """Test calculating zone metrics with sample data"""
        firm_id = sample_firm.id
        zone_name = "Test Zone"
        service_type = "security"
        
        # Create sample metrics
        base_time = datetime.utcnow() - timedelta(days=5)
        for i in range(5):
            metric = ResponseTimeMetric(
                request_id=uuid4(),
                firm_id=firm_id,
                service_type=service_type,
                zone_name=zone_name,
                response_time=300 + (i * 60),  # 5-9 minutes in seconds
                arrival_time=600 + (i * 60),   # 10-14 minutes in seconds
                total_time=900 + (i * 120),    # 15-23 minutes in seconds
                request_location=ST_GeomFromText("POINT(0.5 0.5)", 4326),
                created_at=base_time + timedelta(hours=i)
            )
            db_session.add(metric)
        
        await db_session.commit()
        
        # Calculate metrics
        result = await metrics_service.calculate_zone_metrics(
            firm_id, zone_name, service_type
        )
        
        assert result["zone_name"] == zone_name
        assert result["service_type"] == service_type
        assert result["total_requests"] == 5
        assert result["avg_response_time"] == 7.0  # (5+6+7+8+9)/5 minutes
        assert result["min_response_time"] == 5.0
        assert result["max_response_time"] == 9.0
        assert result["avg_arrival_time"] == 12.0  # (10+11+12+13+14)/5 minutes
    
    async def test_calculate_zone_metrics_no_data(
        self,
        metrics_service: MetricsService,
        sample_firm: SecurityFirm
    ):
        """Test calculating zone metrics with no data"""
        firm_id = sample_firm.id
        zone_name = "Empty Zone"
        service_type = "security"
        
        result = await metrics_service.calculate_zone_metrics(
            firm_id, zone_name, service_type
        )
        
        assert result["zone_name"] == zone_name
        assert result["service_type"] == service_type
        assert result["total_requests"] == 0
        assert result["avg_response_time"] is None
        assert result["min_response_time"] is None
        assert result["max_response_time"] is None
    
    async def test_get_service_type_performance(
        self,
        metrics_service: MetricsService,
        sample_firm: SecurityFirm,
        db_session: AsyncSession
    ):
        """Test getting service type performance across zones"""
        firm_id = sample_firm.id
        service_type = "security"
        
        # Create metrics for multiple zones
        zones = ["Zone A", "Zone B", "Zone C"]
        base_time = datetime.utcnow() - timedelta(days=5)
        
        for zone_idx, zone_name in enumerate(zones):
            for i in range(3):  # 3 requests per zone
                metric = ResponseTimeMetric(
                    request_id=uuid4(),
                    firm_id=firm_id,
                    service_type=service_type,
                    zone_name=zone_name,
                    response_time=300 + (zone_idx * 120) + (i * 60),  # Varying response times
                    total_time=900 + (zone_idx * 240) + (i * 120),    # Varying total times
                    request_location=ST_GeomFromText("POINT(0.5 0.5)", 4326),
                    created_at=base_time + timedelta(hours=zone_idx * 3 + i)
                )
                db_session.add(metric)
        
        await db_session.commit()
        
        result = await metrics_service.get_service_type_performance(
            firm_id, service_type
        )
        
        assert result["service_type"] == service_type
        assert result["total_requests"] == 9  # 3 zones * 3 requests
        assert len(result["zones"]) == 3
        assert result["overall_performance"]["status"] in ["good", "warning", "critical"]
        
        # Verify zones are sorted by request count (descending)
        zone_counts = [zone["request_count"] for zone in result["zones"]]
        assert zone_counts == sorted(zone_counts, reverse=True)
    
    async def test_generate_performance_report(
        self,
        metrics_service: MetricsService,
        sample_firm: SecurityFirm,
        db_session: AsyncSession
    ):
        """Test generating comprehensive performance report"""
        firm_id = sample_firm.id
        
        # Create diverse metrics data
        service_types = ["security", "ambulance", "fire"]
        zones = ["Downtown", "Uptown"]
        base_time = datetime.utcnow() - timedelta(days=10)
        
        for service_idx, service_type in enumerate(service_types):
            for zone_idx, zone_name in enumerate(zones):
                for i in range(2):  # 2 requests per service-zone combination
                    metric = ResponseTimeMetric(
                        request_id=uuid4(),
                        firm_id=firm_id,
                        service_type=service_type,
                        zone_name=zone_name,
                        response_time=300 + (service_idx * 180) + (i * 60),
                        total_time=900 + (service_idx * 360) + (i * 120),
                        request_location=ST_GeomFromText("POINT(0.5 0.5)", 4326),
                        created_at=base_time + timedelta(hours=service_idx * 4 + zone_idx * 2 + i)
                    )
                    db_session.add(metric)
        
        # Create a performance alert
        alert = PerformanceAlert(
            firm_id=firm_id,
            alert_type="slow_response",
            severity="medium",
            zone_name="Downtown",
            service_type="security",
            message="Response times above threshold",
            metric_value=25.5,
            threshold_value=20.0,
            created_at=base_time + timedelta(days=1)
        )
        db_session.add(alert)
        
        await db_session.commit()
        
        # Generate report
        date_from = base_time
        date_to = datetime.utcnow()
        
        result = await metrics_service.generate_performance_report(
            firm_id, date_from, date_to
        )
        
        assert result["firm_id"] == str(firm_id)
        assert result["total_requests"] == 12  # 3 services * 2 zones * 2 requests
        assert len(result["service_types"]) == 3
        assert len(result["zones"]) == 2
        assert len(result["alerts"]) == 1
        
        # Verify service types are sorted by request count
        service_counts = [st["request_count"] for st in result["service_types"]]
        assert service_counts == sorted(service_counts, reverse=True)
        
        # Verify alert data
        alert_data = result["alerts"][0]
        assert alert_data["alert_type"] == "slow_response"
        assert alert_data["severity"] == "medium"
        assert alert_data["zone_name"] == "Downtown"
    
    async def test_detect_performance_degradation(
        self,
        metrics_service: MetricsService,
        sample_firm: SecurityFirm,
        db_session: AsyncSession
    ):
        """Test detecting performance degradation"""
        firm_id = sample_firm.id
        service_type = "security"
        zone_name = "Test Zone"
        
        now = datetime.utcnow()
        
        # Create historical metrics (good performance)
        historical_start = now - timedelta(days=28)
        for i in range(10):
            metric = ResponseTimeMetric(
                request_id=uuid4(),
                firm_id=firm_id,
                service_type=service_type,
                zone_name=zone_name,
                total_time=600 + (i * 60),  # 10-19 minutes (good performance)
                request_location=ST_GeomFromText("POINT(0.5 0.5)", 4326),
                created_at=historical_start + timedelta(hours=i * 2)
            )
            db_session.add(metric)
        
        # Create recent metrics (degraded performance)
        recent_start = now - timedelta(days=7)
        for i in range(5):
            metric = ResponseTimeMetric(
                request_id=uuid4(),
                firm_id=firm_id,
                service_type=service_type,
                zone_name=zone_name,
                total_time=1800 + (i * 120),  # 30-38 minutes (degraded performance)
                request_location=ST_GeomFromText("POINT(0.5 0.5)", 4326),
                created_at=recent_start + timedelta(hours=i * 12)
            )
            db_session.add(metric)
        
        await db_session.commit()
        
        # Detect degradation
        alerts = await metrics_service.detect_performance_degradation(firm_id)
        
        assert len(alerts) == 1
        alert = alerts[0]
        assert alert["alert_type"] == "performance_degradation"
        assert alert["service_type"] == service_type
        assert alert["zone_name"] == zone_name
        assert alert["severity"] in ["medium", "high"]
        assert alert["recent_avg_time"] > alert["historical_avg_time"]
        assert alert["degradation_percentage"] > 25
    
    async def test_create_performance_alert(
        self,
        metrics_service: MetricsService,
        sample_firm: SecurityFirm,
        db_session: AsyncSession
    ):
        """Test creating performance alert"""
        firm_id = sample_firm.id
        
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
    
    async def test_determine_zone_name_with_coverage_area(
        self,
        metrics_service: MetricsService,
        sample_coverage_area: CoverageArea,
        db_session: AsyncSession
    ):
        """Test determining zone name from coverage area"""
        location_geom = ST_GeomFromText("POINT(0.5 0.5)", 4326)
        
        zone_name = await metrics_service._determine_zone_name(
            location_geom, sample_coverage_area.firm_id
        )
        
        assert zone_name == "Downtown Zone"
    
    async def test_determine_zone_name_outside_coverage(
        self,
        metrics_service: MetricsService,
        sample_coverage_area: CoverageArea,
        db_session: AsyncSession
    ):
        """Test determining zone name for location outside coverage areas"""
        # Point outside the coverage area polygon
        location_geom = ST_GeomFromText("POINT(2.0 2.0)", 4326)
        
        zone_name = await metrics_service._determine_zone_name(
            location_geom, sample_coverage_area.firm_id
        )
        
        # Should return coordinate-based zone name
        assert zone_name.startswith("Zone_2.000_2.000")
    
    def test_get_performance_status(self, metrics_service: MetricsService):
        """Test performance status determination"""
        # Test good performance
        status = metrics_service._get_performance_status("security", 10.0)
        assert status == "good"
        
        # Test warning performance
        status = metrics_service._get_performance_status("security", 20.0)
        assert status == "warning"
        
        # Test critical performance
        status = metrics_service._get_performance_status("security", 40.0)
        assert status == "critical"
        
        # Test unknown service type
        status = metrics_service._get_performance_status("unknown", 10.0)
        assert status == "unknown"
        
        # Test None time
        status = metrics_service._get_performance_status("security", None)
        assert status == "unknown"
    
    def test_group_metrics_by_service_and_zone(self, metrics_service: MetricsService):
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
    
    def test_calculate_average_total_time(self, metrics_service: MetricsService):
        """Test calculating average total time"""
        # Test with valid metrics
        metrics = [
            ResponseTimeMetric(total_time=600),  # 10 minutes
            ResponseTimeMetric(total_time=900),  # 15 minutes
            ResponseTimeMetric(total_time=1200)  # 20 minutes
        ]
        
        avg_time = metrics_service._calculate_average_total_time(metrics)
        assert avg_time == 15.0  # (10+15+20)/3
        
        # Test with None values
        metrics_with_none = [
            ResponseTimeMetric(total_time=600),
            ResponseTimeMetric(total_time=None),
            ResponseTimeMetric(total_time=900)
        ]
        
        avg_time = metrics_service._calculate_average_total_time(metrics_with_none)
        assert avg_time == 12.5  # (10+15)/2
        
        # Test with all None values
        metrics_all_none = [
            ResponseTimeMetric(total_time=None),
            ResponseTimeMetric(total_time=None)
        ]
        
        avg_time = metrics_service._calculate_average_total_time(metrics_all_none)
        assert avg_time is None