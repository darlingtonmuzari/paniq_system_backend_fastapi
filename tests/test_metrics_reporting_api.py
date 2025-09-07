"""
Tests for metrics reporting and alerting API endpoints
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.security_firm import FirmPersonnel, SecurityFirm
from app.models.metrics import PerformanceAlert, ResponseTimeMetric
from app.core.auth import get_current_user


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def sample_firm():
    """Create sample security firm"""
    return SecurityFirm(
        id=uuid4(),
        name="Test Security Firm",
        registration_number="TSF001",
        email="test@security.com",
        phone="+1234567890",
        address="123 Security St",
        verification_status="approved",
        credit_balance=1000
    )


@pytest.fixture
def sample_office_staff(sample_firm):
    """Create sample office staff user"""
    return FirmPersonnel(
        id=uuid4(),
        firm_id=sample_firm.id,
        email="office@security.com",
        phone="+1234567891",
        first_name="Office",
        last_name="Staff",
        role="office_staff",
        is_active=True
    )


@pytest.fixture
def sample_team_leader(sample_firm):
    """Create sample team leader user"""
    return FirmPersonnel(
        id=uuid4(),
        firm_id=sample_firm.id,
        email="leader@security.com",
        phone="+1234567892",
        first_name="Team",
        last_name="Leader",
        role="team_leader",
        is_active=True
    )


class TestStatisticalReportingAPI:
    """Test statistical reporting API endpoints"""
    
    def test_generate_statistical_performance_report_success(
        self, 
        client: TestClient,
        sample_office_staff: FirmPersonnel
    ):
        """Test successful statistical report generation"""
        # Mock authentication
        app.dependency_overrides[get_current_user] = lambda: sample_office_staff
        
        # Mock the service response
        mock_report = {
            "firm_id": str(sample_office_staff.firm_id),
            "total_requests": 100,
            "statistical_analysis": {
                "response_time": {
                    "mean": 12.5,
                    "median": 11.0,
                    "p90": 18.0,
                    "p95": 22.0
                },
                "total_time": {
                    "mean": 25.3,
                    "median": 23.0,
                    "p90": 35.0,
                    "p95": 40.0
                }
            },
            "trend_analysis": {
                "trend_direction": "stable",
                "daily_averages": []
            },
            "service_type_comparison": {
                "best_performing": "fire",
                "worst_performing": "towing"
            },
            "zone_performance_ranking": []
        }
        
        with patch("app.services.metrics.MetricsService.generate_statistical_performance_report") as mock_service:
            mock_service.return_value = mock_report
            
            response = client.get(
                "/api/v1/metrics/statistical-report",
                params={
                    "date_from": "2024-01-01T00:00:00",
                    "date_to": "2024-01-31T23:59:59",
                    "include_percentiles": True
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["firm_id"] == str(sample_office_staff.firm_id)
        assert data["total_requests"] == 100
        assert "statistical_analysis" in data
        assert "trend_analysis" in data
        assert "service_type_comparison" in data
        assert "zone_performance_ranking" in data
        
        # Clean up
        app.dependency_overrides.clear()
    
    def test_generate_statistical_performance_report_invalid_date_range(
        self, 
        client: TestClient,
        sample_office_staff: FirmPersonnel
    ):
        """Test statistical report with invalid date range"""
        app.dependency_overrides[get_current_user] = lambda: sample_office_staff
        
        # End date before start date
        response = client.get(
            "/api/v1/metrics/statistical-report",
            params={
                "date_from": "2024-01-31T00:00:00",
                "date_to": "2024-01-01T23:59:59"
            }
        )
        
        assert response.status_code == 400
        assert "End date must be after start date" in response.json()["detail"]
        
        app.dependency_overrides.clear()
    
    def test_generate_statistical_performance_report_date_range_too_large(
        self, 
        client: TestClient,
        sample_office_staff: FirmPersonnel
    ):
        """Test statistical report with date range too large"""
        app.dependency_overrides[get_current_user] = lambda: sample_office_staff
        
        # Date range > 180 days
        response = client.get(
            "/api/v1/metrics/statistical-report",
            params={
                "date_from": "2024-01-01T00:00:00",
                "date_to": "2024-08-01T23:59:59"
            }
        )
        
        assert response.status_code == 400
        assert "Date range cannot exceed 180 days" in response.json()["detail"]
        
        app.dependency_overrides.clear()
    
    def test_generate_statistical_performance_report_unauthorized(
        self, 
        client: TestClient,
        sample_team_leader: FirmPersonnel
    ):
        """Test statistical report with insufficient permissions"""
        # Team leader should not have access to statistical reports
        app.dependency_overrides[get_current_user] = lambda: sample_team_leader
        
        response = client.get(
            "/api/v1/metrics/statistical-report",
            params={
                "date_from": "2024-01-01T00:00:00",
                "date_to": "2024-01-31T23:59:59"
            }
        )
        
        # Should require office_staff role
        assert response.status_code == 403
        
        app.dependency_overrides.clear()


class TestAutomatedAlertingAPI:
    """Test automated alerting API endpoints"""
    
    def test_create_automated_alerts_success(
        self, 
        client: TestClient,
        sample_office_staff: FirmPersonnel
    ):
        """Test successful automated alert creation"""
        app.dependency_overrides[get_current_user] = lambda: sample_office_staff
        
        # Mock alerts creation
        mock_alerts = [
            PerformanceAlert(
                id=uuid4(),
                firm_id=sample_office_staff.firm_id,
                alert_type="threshold_violation",
                severity="high",
                zone_name="Critical Zone",
                service_type="security",
                message="Response times critically high",
                created_at=datetime.utcnow()
            )
        ]
        
        with patch("app.services.metrics.MetricsService.create_automated_performance_alerts") as mock_service:
            mock_service.return_value = mock_alerts
            
            response = client.post(
                "/api/v1/metrics/automated-alerts",
                params={"check_period_hours": 24}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["message"] == "Created 1 automated alerts"
        assert data["alerts_created"] == 1
        assert len(data["alerts"]) == 1
        
        alert = data["alerts"][0]
        assert alert["alert_type"] == "threshold_violation"
        assert alert["severity"] == "high"
        assert alert["zone_name"] == "Critical Zone"
        assert alert["service_type"] == "security"
        
        app.dependency_overrides.clear()
    
    def test_create_automated_alerts_no_alerts(
        self, 
        client: TestClient,
        sample_office_staff: FirmPersonnel
    ):
        """Test automated alert creation with no alerts needed"""
        app.dependency_overrides[get_current_user] = lambda: sample_office_staff
        
        with patch("app.services.metrics.MetricsService.create_automated_performance_alerts") as mock_service:
            mock_service.return_value = []
            
            response = client.post(
                "/api/v1/metrics/automated-alerts",
                params={"check_period_hours": 12}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["message"] == "Created 0 automated alerts"
        assert data["alerts_created"] == 0
        assert len(data["alerts"]) == 0
        
        app.dependency_overrides.clear()
    
    def test_create_automated_alerts_invalid_period(
        self, 
        client: TestClient,
        sample_office_staff: FirmPersonnel
    ):
        """Test automated alert creation with invalid check period"""
        app.dependency_overrides[get_current_user] = lambda: sample_office_staff
        
        # Period too large (> 168 hours)
        response = client.post(
            "/api/v1/metrics/automated-alerts",
            params={"check_period_hours": 200}
        )
        
        assert response.status_code == 422  # Validation error
        
        app.dependency_overrides.clear()


class TestMetricsExportAPI:
    """Test metrics export API endpoints"""
    
    def test_export_metrics_json_format(
        self, 
        client: TestClient,
        sample_office_staff: FirmPersonnel
    ):
        """Test exporting metrics in JSON format"""
        app.dependency_overrides[get_current_user] = lambda: sample_office_staff
        
        mock_export_data = {
            "format": "json",
            "firm_id": str(sample_office_staff.firm_id),
            "total_records": 5,
            "metrics": [
                {
                    "timestamp": "2024-01-15T10:00:00",
                    "service_type": "security",
                    "zone_name": "Downtown",
                    "response_time_minutes": 12.5,
                    "total_time_minutes": 25.0
                }
            ]
        }
        
        with patch("app.services.metrics.MetricsService.export_metrics_for_monitoring") as mock_service:
            mock_service.return_value = mock_export_data
            
            response = client.get(
                "/api/v1/metrics/export",
                params={"export_format": "json"}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["format"] == "json"
        assert data["firm_id"] == str(sample_office_staff.firm_id)
        assert data["total_records"] == 5
        assert len(data["metrics"]) == 1
        
        app.dependency_overrides.clear()
    
    def test_export_metrics_prometheus_format(
        self, 
        client: TestClient,
        sample_office_staff: FirmPersonnel
    ):
        """Test exporting metrics in Prometheus format"""
        app.dependency_overrides[get_current_user] = lambda: sample_office_staff
        
        mock_export_data = {
            "format": "prometheus",
            "metrics": [
                f'panic_system_response_time_minutes{{firm_id="{sample_office_staff.firm_id}",service_type="security",zone="Downtown"}} 12.50',
                f'panic_system_request_count{{firm_id="{sample_office_staff.firm_id}",service_type="security",zone="Downtown"}} 5'
            ]
        }
        
        with patch("app.services.metrics.MetricsService.export_metrics_for_monitoring") as mock_service:
            mock_service.return_value = mock_export_data
            
            response = client.get(
                "/api/v1/metrics/export",
                params={"export_format": "prometheus"}
            )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; version=0.0.4; charset=utf-8"
        
        content = response.text
        assert "panic_system_response_time_minutes" in content
        assert "panic_system_request_count" in content
        assert str(sample_office_staff.firm_id) in content
        
        app.dependency_overrides.clear()
    
    def test_export_metrics_csv_format(
        self, 
        client: TestClient,
        sample_office_staff: FirmPersonnel
    ):
        """Test exporting metrics in CSV format"""
        app.dependency_overrides[get_current_user] = lambda: sample_office_staff
        
        mock_export_data = {
            "format": "csv",
            "headers": ["timestamp", "firm_id", "service_type", "zone_name", "response_time_minutes"],
            "rows": [
                ["2024-01-15T10:00:00", str(sample_office_staff.firm_id), "security", "Downtown", "12.50"]
            ]
        }
        
        with patch("app.services.metrics.MetricsService.export_metrics_for_monitoring") as mock_service:
            mock_service.return_value = mock_export_data
            
            response = client.get(
                "/api/v1/metrics/export",
                params={"export_format": "csv"}
            )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]
        
        content = response.text
        assert "timestamp,firm_id,service_type,zone_name,response_time_minutes" in content
        assert str(sample_office_staff.firm_id) in content
        
        app.dependency_overrides.clear()
    
    def test_export_metrics_invalid_format(
        self, 
        client: TestClient,
        sample_office_staff: FirmPersonnel
    ):
        """Test exporting metrics with invalid format"""
        app.dependency_overrides[get_current_user] = lambda: sample_office_staff
        
        response = client.get(
            "/api/v1/metrics/export",
            params={"export_format": "invalid"}
        )
        
        assert response.status_code == 422  # Validation error
        
        app.dependency_overrides.clear()
    
    def test_export_metrics_team_leader_access(
        self, 
        client: TestClient,
        sample_team_leader: FirmPersonnel
    ):
        """Test that team leaders can access metrics export"""
        app.dependency_overrides[get_current_user] = lambda: sample_team_leader
        
        mock_export_data = {
            "format": "json",
            "firm_id": str(sample_team_leader.firm_id),
            "total_records": 0,
            "metrics": []
        }
        
        with patch("app.services.metrics.MetricsService.export_metrics_for_monitoring") as mock_service:
            mock_service.return_value = mock_export_data
            
            response = client.get(
                "/api/v1/metrics/export",
                params={"export_format": "json"}
            )
        
        assert response.status_code == 200
        
        app.dependency_overrides.clear()


class TestDashboardAPI:
    """Test dashboard API endpoints"""
    
    def test_get_zone_performance_dashboard(
        self, 
        client: TestClient,
        sample_office_staff: FirmPersonnel
    ):
        """Test zone performance dashboard"""
        app.dependency_overrides[get_current_user] = lambda: sample_office_staff
        
        # Mock statistical report
        mock_report = {
            "zone_performance_ranking": [
                {
                    "zone_name": "Downtown",
                    "request_count": 50,
                    "avg_total_time": 15.5,
                    "performance_score": 85.2,
                    "service_types": ["security", "ambulance"]
                },
                {
                    "zone_name": "Uptown",
                    "request_count": 30,
                    "avg_total_time": 22.1,
                    "performance_score": 72.8,
                    "service_types": ["security"]
                }
            ]
        }
        
        # Mock alerts query
        mock_alerts = [
            PerformanceAlert(
                zone_name="Downtown",
                severity="medium",
                message="Moderate performance degradation",
                service_type="security",
                created_at=datetime.utcnow()
            )
        ]
        
        with patch("app.services.metrics.MetricsService.generate_statistical_performance_report") as mock_service:
            mock_service.return_value = mock_report
            
            with patch("app.api.v1.metrics.select") as mock_select:
                mock_result = AsyncMock()
                mock_result.scalars.return_value.all.return_value = mock_alerts
                mock_db = AsyncMock()
                mock_db.execute.return_value = mock_result
                
                with patch("app.api.v1.metrics.get_db", return_value=mock_db):
                    response = client.get(
                        "/api/v1/metrics/dashboard/zones",
                        params={"days": 30}
                    )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["firm_id"] == str(sample_office_staff.firm_id)
        assert data["dashboard_period_days"] == 30
        assert data["total_zones"] == 2
        assert data["zones_with_alerts"] >= 0
        assert len(data["zones"]) == 2
        
        # Verify zone data structure
        zone = data["zones"][0]
        assert "zone_name" in zone
        assert "request_count" in zone
        assert "avg_total_time" in zone
        assert "performance_score" in zone
        assert "active_alerts" in zone
        assert "alert_count" in zone
        
        app.dependency_overrides.clear()
    
    def test_get_service_type_performance_dashboard(
        self, 
        client: TestClient,
        sample_team_leader: FirmPersonnel
    ):
        """Test service type performance dashboard"""
        app.dependency_overrides[get_current_user] = lambda: sample_team_leader
        
        # Mock statistical report
        mock_report = {
            "service_type_comparison": {
                "best_performing": "fire",
                "worst_performing": "towing",
                "performance_ranking": [
                    {
                        "service_type": "fire",
                        "request_count": 25,
                        "avg_total_time": 8.5,
                        "performance_status": "good"
                    },
                    {
                        "service_type": "security",
                        "request_count": 75,
                        "avg_total_time": 18.2,
                        "performance_status": "warning"
                    }
                ]
            },
            "trend_analysis": {
                "trend_direction": "stable",
                "daily_averages": []
            }
        }
        
        with patch("app.services.metrics.MetricsService.generate_statistical_performance_report") as mock_service:
            mock_service.return_value = mock_report
            
            with patch("app.api.v1.metrics.select") as mock_select:
                mock_result = AsyncMock()
                mock_result.scalars.return_value.all.return_value = []
                mock_db = AsyncMock()
                mock_db.execute.return_value = mock_result
                
                with patch("app.api.v1.metrics.get_db", return_value=mock_db):
                    response = client.get(
                        "/api/v1/metrics/dashboard/service-types",
                        params={"days": 30}
                    )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["firm_id"] == str(sample_team_leader.firm_id)
        assert data["dashboard_period_days"] == 30
        assert data["best_performing"] == "fire"
        assert data["worst_performing"] == "towing"
        assert "trend_analysis" in data
        assert len(data["services"]) == 2
        
        # Verify service data structure
        service = data["services"][0]
        assert "service_type" in service
        assert "request_count" in service
        assert "avg_total_time" in service
        assert "performance_status" in service
        assert "active_alerts" in service
        assert "alert_count" in service
        
        app.dependency_overrides.clear()
    
    def test_dashboard_invalid_days_parameter(
        self, 
        client: TestClient,
        sample_office_staff: FirmPersonnel
    ):
        """Test dashboard with invalid days parameter"""
        app.dependency_overrides[get_current_user] = lambda: sample_office_staff
        
        # Days parameter too large (> 90)
        response = client.get(
            "/api/v1/metrics/dashboard/zones",
            params={"days": 100}
        )
        
        assert response.status_code == 422  # Validation error
        
        app.dependency_overrides.clear()


class TestErrorHandling:
    """Test error handling in API endpoints"""
    
    def test_service_error_handling(
        self, 
        client: TestClient,
        sample_office_staff: FirmPersonnel
    ):
        """Test handling of service errors"""
        app.dependency_overrides[get_current_user] = lambda: sample_office_staff
        
        with patch("app.services.metrics.MetricsService.generate_statistical_performance_report") as mock_service:
            mock_service.side_effect = Exception("Database connection failed")
            
            response = client.get(
                "/api/v1/metrics/statistical-report",
                params={
                    "date_from": "2024-01-01T00:00:00",
                    "date_to": "2024-01-31T23:59:59"
                }
            )
        
        assert response.status_code == 500
        assert "Failed to generate statistical report" in response.json()["detail"]
        
        app.dependency_overrides.clear()
    
    def test_export_service_error_handling(
        self, 
        client: TestClient,
        sample_office_staff: FirmPersonnel
    ):
        """Test handling of export service errors"""
        app.dependency_overrides[get_current_user] = lambda: sample_office_staff
        
        with patch("app.services.metrics.MetricsService.export_metrics_for_monitoring") as mock_service:
            mock_service.side_effect = ValueError("Invalid export format")
            
            response = client.get(
                "/api/v1/metrics/export",
                params={"export_format": "json"}
            )
        
        assert response.status_code == 400
        assert "Invalid export format" in response.json()["detail"]
        
        app.dependency_overrides.clear()