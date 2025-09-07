"""
Unit tests for log management API endpoints
"""
import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import HTTPException

from app.main import app
from app.services.log_aggregation import LogSearchResult, LogEntry, LogSearchQuery
from app.services.log_retention import LogRetentionService
from app.core.logging import LogLevel, SecurityEventType


client = TestClient(app)


@pytest.fixture
def mock_current_user():
    """Mock current user with admin role"""
    return {
        "user_id": "admin-123",
        "role": "admin",
        "email": "admin@example.com"
    }


@pytest.fixture
def sample_log_entries():
    """Sample log entries for testing"""
    now = datetime.utcnow()
    return [
        LogEntry(
            timestamp=now - timedelta(hours=1),
            level="info",
            logger="app.api.auth",
            message="User login successful",
            service="panic-system-platform",
            version="1.0.0",
            environment="test",
            request_id="req-123",
            user_id="user-456",
            client_ip="192.168.1.1",
            event_type="login_success",
            category="security"
        ),
        LogEntry(
            timestamp=now - timedelta(minutes=30),
            level="error",
            logger="app.services.emergency",
            message="Failed to process panic request",
            service="panic-system-platform",
            version="1.0.0",
            environment="test",
            request_id="req-789",
            user_id="user-123",
            client_ip="192.168.1.2",
            error_type="ValidationError",
            exception="ValidationError: Invalid coordinates"
        )
    ]


class TestLogSearchAPI:
    """Test log search API endpoints"""
    
    @patch('app.api.v1.logs.get_current_user')
    @patch('app.api.v1.logs.require_admin_role')
    @patch('app.api.v1.logs.log_aggregation_service.search_logs')
    def test_search_logs_success(self, mock_search, mock_admin, mock_user, mock_current_user, sample_log_entries):
        """Test successful log search"""
        mock_user.return_value = mock_current_user
        mock_admin.return_value = {}
        
        # Mock search result
        mock_result = LogSearchResult(
            entries=sample_log_entries,
            total_count=2,
            query=LogSearchQuery(limit=100),
            execution_time_ms=150
        )
        mock_search.return_value = mock_result
        
        # Make request
        response = client.post(
            "/api/v1/admin/logs/search",
            json={
                "limit": 100,
                "offset": 0,
                "sort_order": "desc"
            },
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_count"] == 2
        assert data["limit"] == 100
        assert data["offset"] == 0
        assert data["execution_time_ms"] == 150
        assert len(data["entries"]) == 2
        
        # Check first entry
        first_entry = data["entries"][0]
        assert first_entry["level"] == "info"
        assert first_entry["message"] == "User login successful"
        assert first_entry["user_id"] == "user-456"
        assert first_entry["event_type"] == "login_success"
    
    @patch('app.api.v1.logs.get_current_user')
    @patch('app.api.v1.logs.require_admin_role')
    def test_search_logs_unauthorized(self, mock_admin, mock_user):
        """Test log search without admin role"""
        mock_user.side_effect = HTTPException(status_code=401, detail="Unauthorized")
        
        response = client.post(
            "/api/v1/admin/logs/search",
            json={"limit": 100},
            headers={"Authorization": "Bearer invalid-token"}
        )
        
        assert response.status_code == 401
    
    @patch('app.api.v1.logs.get_current_user')
    @patch('app.api.v1.logs.require_admin_role')
    @patch('app.api.v1.logs.log_aggregation_service.search_logs')
    def test_search_logs_with_filters(self, mock_search, mock_admin, mock_user, mock_current_user):
        """Test log search with various filters"""
        mock_user.return_value = mock_current_user
        mock_admin.return_value = {}
        
        mock_result = LogSearchResult(
            entries=[],
            total_count=0,
            query=LogSearchQuery(),
            execution_time_ms=50
        )
        mock_search.return_value = mock_result
        
        # Make request with filters
        response = client.post(
            "/api/v1/admin/logs/search",
            json={
                "start_time": "2024-01-01T00:00:00Z",
                "end_time": "2024-01-02T00:00:00Z",
                "level": "error",
                "user_id": "user-123",
                "search_text": "panic request",
                "limit": 50,
                "offset": 10
            },
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200
        
        # Verify search was called with correct parameters
        mock_search.assert_called_once()
        call_args = mock_search.call_args[0][0]
        assert call_args.level == LogLevel.ERROR
        assert call_args.user_id == "user-123"
        assert call_args.search_text == "panic request"
        assert call_args.limit == 50
        assert call_args.offset == 10
    
    @patch('app.api.v1.logs.get_current_user')
    @patch('app.api.v1.logs.require_admin_role')
    @patch('app.api.v1.logs.log_aggregation_service.search_logs')
    def test_search_logs_error(self, mock_search, mock_admin, mock_user, mock_current_user):
        """Test log search with service error"""
        mock_user.return_value = mock_current_user
        mock_admin.return_value = {}
        mock_search.side_effect = Exception("Search failed")
        
        response = client.post(
            "/api/v1/admin/logs/search",
            json={"limit": 100},
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 500
        assert "Failed to search logs" in response.json()["detail"]


class TestLogStatisticsAPI:
    """Test log statistics API endpoints"""
    
    @patch('app.api.v1.logs.get_current_user')
    @patch('app.api.v1.logs.require_admin_role')
    @patch('app.api.v1.logs.log_aggregation_service.get_log_statistics')
    def test_get_log_statistics_success(self, mock_stats, mock_admin, mock_user, mock_current_user):
        """Test successful log statistics retrieval"""
        mock_user.return_value = mock_current_user
        mock_admin.return_value = {}
        
        # Mock statistics result
        mock_stats_result = {
            "total_entries": 1000,
            "time_period": {
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-01-02T00:00:00Z"
            },
            "level_distribution": {
                "info": 700,
                "warning": 200,
                "error": 100
            },
            "event_type_distribution": {
                "login_success": 150,
                "panic_request_submitted": 50
            },
            "error_distribution": {
                "ValidationError": 30,
                "DatabaseError": 20
            },
            "top_users": {
                "user-123": 25,
                "user-456": 20
            },
            "top_ips": {
                "192.168.1.1": 100,
                "192.168.1.2": 80
            }
        }
        mock_stats.return_value = mock_stats_result
        
        # Make request
        response = client.get(
            "/api/v1/admin/logs/statistics",
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_entries"] == 1000
        assert "level_distribution" in data
        assert "event_type_distribution" in data
        assert "error_distribution" in data
        assert "top_users" in data
        assert "top_ips" in data
    
    @patch('app.api.v1.logs.get_current_user')
    @patch('app.api.v1.logs.require_admin_role')
    @patch('app.api.v1.logs.log_aggregation_service.get_log_statistics')
    def test_get_log_statistics_with_time_range(self, mock_stats, mock_admin, mock_user, mock_current_user):
        """Test log statistics with custom time range"""
        mock_user.return_value = mock_current_user
        mock_admin.return_value = {}
        mock_stats.return_value = {"total_entries": 500}
        
        # Make request with time range
        response = client.get(
            "/api/v1/admin/logs/statistics",
            params={
                "start_time": "2024-01-01T00:00:00Z",
                "end_time": "2024-01-02T00:00:00Z"
            },
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200
        
        # Verify statistics was called with correct time range
        mock_stats.assert_called_once()
        call_args = mock_stats.call_args[0]
        assert len(call_args) == 2  # start_time and end_time


class TestLogExportAPI:
    """Test log export API endpoints"""
    
    @patch('app.api.v1.logs.get_current_user')
    @patch('app.api.v1.logs.require_admin_role')
    @patch('app.api.v1.logs.log_aggregation_service.export_logs')
    def test_export_logs_json(self, mock_export, mock_admin, mock_user, mock_current_user):
        """Test log export in JSON format"""
        mock_user.return_value = mock_current_user
        mock_admin.return_value = {}
        
        # Mock export result
        export_data = json.dumps([
            {
                "timestamp": "2024-01-01T12:00:00Z",
                "level": "info",
                "message": "Test message",
                "user_id": "user-123"
            }
        ])
        mock_export.return_value = export_data
        
        # Make request
        response = client.post(
            "/api/v1/admin/logs/export",
            json={"limit": 100},
            params={"format": "json"},
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]
        assert ".json" in response.headers["content-disposition"]
        
        # Verify export was called with correct format
        mock_export.assert_called_once()
        call_args = mock_export.call_args
        assert call_args[0][1] == "json"  # format parameter
    
    @patch('app.api.v1.logs.get_current_user')
    @patch('app.api.v1.logs.require_admin_role')
    @patch('app.api.v1.logs.log_aggregation_service.export_logs')
    def test_export_logs_csv(self, mock_export, mock_admin, mock_user, mock_current_user):
        """Test log export in CSV format"""
        mock_user.return_value = mock_current_user
        mock_admin.return_value = {}
        
        # Mock CSV export result
        csv_data = "timestamp,level,message,user_id\n2024-01-01T12:00:00Z,info,Test message,user-123"
        mock_export.return_value = csv_data
        
        # Make request
        response = client.post(
            "/api/v1/admin/logs/export",
            json={"limit": 100},
            params={"format": "csv"},
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]
        assert ".csv" in response.headers["content-disposition"]
        
        # Verify export was called with correct format
        mock_export.assert_called_once()
        call_args = mock_export.call_args
        assert call_args[0][1] == "csv"  # format parameter


class TestLogRetentionAPI:
    """Test log retention API endpoints"""
    
    @patch('app.api.v1.logs.get_current_user')
    @patch('app.api.v1.logs.require_admin_role')
    @patch('app.api.v1.logs.log_retention_service.run_retention_cleanup')
    def test_run_retention_cleanup(self, mock_cleanup, mock_admin, mock_user, mock_current_user):
        """Test running retention cleanup"""
        mock_user.return_value = mock_current_user
        mock_admin.return_value = {}
        
        # Mock cleanup result
        cleanup_result = {
            "compressed_files": 5,
            "archived_files": 3,
            "deleted_files": 2,
            "errors": 0
        }
        mock_cleanup.return_value = cleanup_result
        
        # Make request
        response = client.post(
            "/api/v1/admin/logs/retention/cleanup",
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "completed"
        assert data["results"] == cleanup_result
        assert "timestamp" in data
    
    @patch('app.api.v1.logs.get_current_user')
    @patch('app.api.v1.logs.require_admin_role')
    @patch('app.api.v1.logs.log_retention_service.get_retention_status')
    def test_get_retention_status(self, mock_status, mock_admin, mock_user, mock_current_user):
        """Test getting retention status"""
        mock_user.return_value = mock_current_user
        mock_admin.return_value = {}
        
        # Mock status result
        status_result = {
            "policies": {
                "application": {
                    "retention_days": 90,
                    "archive_days": 30,
                    "compress_after_days": 7
                }
            },
            "disk_usage": {
                "application": {
                    "size_bytes": 1048576,
                    "size_mb": 1.0
                }
            },
            "file_counts": {
                "application": 10
            },
            "total_disk_usage": {
                "size_bytes": 1048576,
                "size_mb": 1.0,
                "size_gb": 0.001
            },
            "total_file_count": 10
        }
        mock_status.return_value = status_result
        
        # Make request
        response = client.get(
            "/api/v1/admin/logs/retention/status",
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "policies" in data
        assert "disk_usage" in data
        assert "file_counts" in data
        assert "total_disk_usage" in data
        assert "total_file_count" in data
    
    @patch('app.api.v1.logs.get_current_user')
    @patch('app.api.v1.logs.require_admin_role')
    @patch('app.api.v1.logs.log_retention_service.update_retention_policy')
    def test_update_retention_policy(self, mock_update, mock_admin, mock_user, mock_current_user):
        """Test updating retention policy"""
        mock_user.return_value = mock_current_user
        mock_admin.return_value = {}
        
        # Make request
        response = client.put(
            "/api/v1/admin/logs/retention/policy",
            json={
                "log_type": "application",
                "retention_days": 120,
                "archive_days": 45,
                "compress_after_days": 10,
                "max_file_size_mb": 100,
                "max_backup_count": 15
            },
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "updated"
        assert data["log_type"] == "application"
        assert data["policy"]["retention_days"] == 120
        assert data["policy"]["archive_days"] == 45
        assert data["policy"]["compress_after_days"] == 10
        
        # Verify update was called
        mock_update.assert_called_once()
    
    @patch('app.api.v1.logs.get_current_user')
    @patch('app.api.v1.logs.require_admin_role')
    def test_update_retention_policy_validation_error(self, mock_admin, mock_user, mock_current_user):
        """Test retention policy update with validation error"""
        mock_user.return_value = mock_current_user
        mock_admin.return_value = {}
        
        # Make request with invalid policy (archive_days >= retention_days)
        response = client.put(
            "/api/v1/admin/logs/retention/policy",
            json={
                "log_type": "application",
                "retention_days": 30,
                "archive_days": 45,  # Invalid: greater than retention_days
                "compress_after_days": 10,
                "max_file_size_mb": 100,
                "max_backup_count": 15
            },
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 400
        assert "Archive days must be less than retention days" in response.json()["detail"]


class TestLogMonitoringAPI:
    """Test log monitoring API endpoints"""
    
    @patch('app.api.v1.logs.get_current_user')
    @patch('app.api.v1.logs.require_admin_role')
    @patch('app.api.v1.logs.log_aggregation_service.search_logs')
    def test_get_recent_errors(self, mock_search, mock_admin, mock_user, mock_current_user, sample_log_entries):
        """Test getting recent errors"""
        mock_user.return_value = mock_current_user
        mock_admin.return_value = {}
        
        # Filter to only error entries
        error_entries = [entry for entry in sample_log_entries if entry.level == "error"]
        
        mock_result = LogSearchResult(
            entries=error_entries,
            total_count=len(error_entries),
            query=LogSearchQuery(),
            execution_time_ms=100
        )
        mock_search.return_value = mock_result
        
        # Make request
        response = client.get(
            "/api/v1/admin/logs/recent-errors",
            params={"hours": 24, "limit": 50},
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "errors" in data
        assert "total_count" in data
        assert "time_range" in data
        assert data["time_range"]["hours"] == 24
        
        # Verify search was called with error level filter
        mock_search.assert_called_once()
        call_args = mock_search.call_args[0][0]
        assert call_args.level == LogLevel.ERROR
    
    @patch('app.api.v1.logs.get_current_user')
    @patch('app.api.v1.logs.require_admin_role')
    @patch('app.api.v1.logs.log_aggregation_service.search_logs')
    def test_get_security_events(self, mock_search, mock_admin, mock_user, mock_current_user, sample_log_entries):
        """Test getting security events"""
        mock_user.return_value = mock_current_user
        mock_admin.return_value = {}
        
        # Filter to only security entries
        security_entries = [entry for entry in sample_log_entries if entry.category == "security"]
        
        mock_result = LogSearchResult(
            entries=security_entries,
            total_count=len(security_entries),
            query=LogSearchQuery(),
            execution_time_ms=100
        )
        mock_search.return_value = mock_result
        
        # Make request
        response = client.get(
            "/api/v1/admin/logs/security-events",
            params={"hours": 24, "event_type": "login_success"},
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "events" in data
        assert "total_count" in data
        assert "time_range" in data
        assert "event_type_filter" in data
        assert data["event_type_filter"] == "login_success"
        
        # Verify search was called with event type filter
        mock_search.assert_called_once()
        call_args = mock_search.call_args[0][0]
        assert call_args.event_type == "login_success"


class TestLogAPIValidation:
    """Test API input validation"""
    
    @patch('app.api.v1.logs.get_current_user')
    @patch('app.api.v1.logs.require_admin_role')
    def test_search_logs_invalid_sort_order(self, mock_admin, mock_user, mock_current_user):
        """Test log search with invalid sort order"""
        mock_user.return_value = mock_current_user
        mock_admin.return_value = {}
        
        response = client.post(
            "/api/v1/admin/logs/search",
            json={
                "limit": 100,
                "sort_order": "invalid"  # Should be 'asc' or 'desc'
            },
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 422  # Validation error
    
    @patch('app.api.v1.logs.get_current_user')
    @patch('app.api.v1.logs.require_admin_role')
    def test_search_logs_invalid_limit(self, mock_admin, mock_user, mock_current_user):
        """Test log search with invalid limit"""
        mock_user.return_value = mock_current_user
        mock_admin.return_value = {}
        
        response = client.post(
            "/api/v1/admin/logs/search",
            json={
                "limit": 2000  # Exceeds maximum of 1000
            },
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 422  # Validation error
    
    @patch('app.api.v1.logs.get_current_user')
    @patch('app.api.v1.logs.require_admin_role')
    def test_export_logs_invalid_format(self, mock_admin, mock_user, mock_current_user):
        """Test log export with invalid format"""
        mock_user.return_value = mock_current_user
        mock_admin.return_value = {}
        
        response = client.post(
            "/api/v1/admin/logs/export",
            json={"limit": 100},
            params={"format": "xml"},  # Invalid format
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 422  # Validation error


if __name__ == "__main__":
    pytest.main([__file__])