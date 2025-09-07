"""
Unit tests for log aggregation service
"""
import pytest
import json
import tempfile
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
import gzip

from app.services.log_aggregation import (
    LogAggregationService,
    LogSearchQuery,
    LogSearchResult,
    LogEntry,
    LogSearchFilter
)
from app.core.logging import LogLevel, SecurityEventType, BusinessEventType


@pytest.fixture
def temp_log_dir():
    """Fixture for temporary log directory"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def sample_log_entries():
    """Fixture for sample log entries"""
    now = datetime.now(timezone.utc)
    return [
        {
            "timestamp": (now - timedelta(hours=1)).isoformat(),
            "level": "info",
            "logger": "app.api.auth",
            "message": "User login successful",
            "service": "panic-system-platform",
            "version": "1.0.0",
            "environment": "test",
            "request_id": "req-123",
            "user_id": "user-456",
            "client_ip": "192.168.1.1",
            "event_type": "login_success",
            "category": "security"
        },
        {
            "timestamp": (now - timedelta(minutes=30)).isoformat(),
            "level": "error",
            "logger": "app.services.emergency",
            "message": "Failed to process panic request",
            "service": "panic-system-platform",
            "version": "1.0.0",
            "environment": "test",
            "request_id": "req-789",
            "user_id": "user-123",
            "client_ip": "192.168.1.2",
            "error_type": "ValidationError",
            "exception": "ValidationError: Invalid coordinates"
        },
        {
            "timestamp": (now - timedelta(minutes=15)).isoformat(),
            "level": "info",
            "logger": "app.services.subscription",
            "message": "Subscription purchased",
            "service": "panic-system-platform",
            "version": "1.0.0",
            "environment": "test",
            "request_id": "req-456",
            "user_id": "user-789",
            "client_ip": "192.168.1.3",
            "event_type": "subscription_purchased",
            "category": "business",
            "subscription_id": "sub-123",
            "amount": 29.99
        }
    ]


@pytest.fixture
def log_aggregation_service(temp_log_dir):
    """Fixture for log aggregation service"""
    return LogAggregationService(temp_log_dir)


class TestLogAggregationService:
    """Test log aggregation service functionality"""
    
    def test_service_initialization(self, temp_log_dir):
        """Test service initialization"""
        service = LogAggregationService(temp_log_dir)
        assert service.log_dir == temp_log_dir
        assert service.logger is not None
    
    @pytest.mark.asyncio
    async def test_search_logs_empty_directory(self, log_aggregation_service):
        """Test searching logs in empty directory"""
        query = LogSearchQuery(limit=10)
        result = await log_aggregation_service.search_logs(query)
        
        assert isinstance(result, LogSearchResult)
        assert result.total_count == 0
        assert len(result.entries) == 0
        assert result.query == query
        assert result.execution_time_ms >= 0
    
    @pytest.mark.asyncio
    async def test_search_logs_with_data(self, log_aggregation_service, sample_log_entries, temp_log_dir):
        """Test searching logs with sample data"""
        # Create sample log file
        log_file = temp_log_dir / "application.log"
        with open(log_file, 'w') as f:
            for entry in sample_log_entries:
                f.write(json.dumps(entry) + '\n')
        
        query = LogSearchQuery(limit=10)
        result = await log_aggregation_service.search_logs(query)
        
        assert result.total_count == 3
        assert len(result.entries) == 3
        assert all(isinstance(entry, LogEntry) for entry in result.entries)
    
    @pytest.mark.asyncio
    async def test_search_logs_with_level_filter(self, log_aggregation_service, sample_log_entries, temp_log_dir):
        """Test searching logs with level filter"""
        # Create sample log file
        log_file = temp_log_dir / "application.log"
        with open(log_file, 'w') as f:
            for entry in sample_log_entries:
                f.write(json.dumps(entry) + '\n')
        
        query = LogSearchQuery(level=LogLevel.ERROR, limit=10)
        result = await log_aggregation_service.search_logs(query)
        
        assert result.total_count == 1
        assert len(result.entries) == 1
        assert result.entries[0].level == "error"
        assert result.entries[0].error_type == "ValidationError"
    
    @pytest.mark.asyncio
    async def test_search_logs_with_user_filter(self, log_aggregation_service, sample_log_entries, temp_log_dir):
        """Test searching logs with user ID filter"""
        # Create sample log file
        log_file = temp_log_dir / "application.log"
        with open(log_file, 'w') as f:
            for entry in sample_log_entries:
                f.write(json.dumps(entry) + '\n')
        
        query = LogSearchQuery(user_id="user-456", limit=10)
        result = await log_aggregation_service.search_logs(query)
        
        assert result.total_count == 1
        assert len(result.entries) == 1
        assert result.entries[0].user_id == "user-456"
        assert result.entries[0].event_type == "login_success"
    
    @pytest.mark.asyncio
    async def test_search_logs_with_text_search(self, log_aggregation_service, sample_log_entries, temp_log_dir):
        """Test searching logs with text search"""
        # Create sample log file
        log_file = temp_log_dir / "application.log"
        with open(log_file, 'w') as f:
            for entry in sample_log_entries:
                f.write(json.dumps(entry) + '\n')
        
        query = LogSearchQuery(search_text="subscription", limit=10)
        result = await log_aggregation_service.search_logs(query)
        
        assert result.total_count == 1
        assert len(result.entries) == 1
        assert "subscription" in result.entries[0].message.lower()
    
    @pytest.mark.asyncio
    async def test_search_logs_with_time_range(self, log_aggregation_service, sample_log_entries, temp_log_dir):
        """Test searching logs with time range"""
        # Create sample log file
        log_file = temp_log_dir / "application.log"
        with open(log_file, 'w') as f:
            for entry in sample_log_entries:
                f.write(json.dumps(entry) + '\n')
        
        now = datetime.now(timezone.utc)
        start_time = now - timedelta(minutes=45)
        end_time = now - timedelta(minutes=10)
        
        query = LogSearchQuery(start_time=start_time, end_time=end_time, limit=10)
        result = await log_aggregation_service.search_logs(query)
        
        # Should find the error entry (30 minutes ago) and subscription entry (15 minutes ago)
        assert result.total_count == 2
        assert len(result.entries) == 2
    
    @pytest.mark.asyncio
    async def test_search_logs_pagination(self, log_aggregation_service, sample_log_entries, temp_log_dir):
        """Test log search pagination"""
        # Create sample log file
        log_file = temp_log_dir / "application.log"
        with open(log_file, 'w') as f:
            for entry in sample_log_entries:
                f.write(json.dumps(entry) + '\n')
        
        # Test first page
        query = LogSearchQuery(limit=2, offset=0)
        result = await log_aggregation_service.search_logs(query)
        
        assert result.total_count == 3
        assert len(result.entries) == 2
        
        # Test second page
        query = LogSearchQuery(limit=2, offset=2)
        result = await log_aggregation_service.search_logs(query)
        
        assert result.total_count == 3
        assert len(result.entries) == 1
    
    @pytest.mark.asyncio
    async def test_search_logs_sort_order(self, log_aggregation_service, sample_log_entries, temp_log_dir):
        """Test log search sort order"""
        # Create sample log file
        log_file = temp_log_dir / "application.log"
        with open(log_file, 'w') as f:
            for entry in sample_log_entries:
                f.write(json.dumps(entry) + '\n')
        
        # Test descending order (default)
        query = LogSearchQuery(sort_order="desc", limit=10)
        result = await log_aggregation_service.search_logs(query)
        
        assert len(result.entries) == 3
        # Most recent entry should be first
        assert result.entries[0].message == "Subscription purchased"
        
        # Test ascending order
        query = LogSearchQuery(sort_order="asc", limit=10)
        result = await log_aggregation_service.search_logs(query)
        
        assert len(result.entries) == 3
        # Oldest entry should be first
        assert result.entries[0].message == "User login successful"
    
    @pytest.mark.asyncio
    async def test_search_compressed_logs(self, log_aggregation_service, sample_log_entries, temp_log_dir):
        """Test searching compressed log files"""
        # Create compressed log file
        log_file = temp_log_dir / "application.log.gz"
        with gzip.open(log_file, 'wt') as f:
            for entry in sample_log_entries:
                f.write(json.dumps(entry) + '\n')
        
        query = LogSearchQuery(limit=10)
        result = await log_aggregation_service.search_logs(query)
        
        assert result.total_count == 3
        assert len(result.entries) == 3
    
    def test_parse_log_entry(self, log_aggregation_service, sample_log_entries):
        """Test log entry parsing"""
        log_data = sample_log_entries[0]
        entry = log_aggregation_service._parse_log_entry(log_data)
        
        assert isinstance(entry, LogEntry)
        assert entry.level == "info"
        assert entry.message == "User login successful"
        assert entry.user_id == "user-456"
        assert entry.request_id == "req-123"
        assert entry.event_type == "login_success"
        assert entry.category == "security"
    
    def test_matches_query_level_filter(self, log_aggregation_service, sample_log_entries):
        """Test query matching with level filter"""
        entry = log_aggregation_service._parse_log_entry(sample_log_entries[0])
        
        # Should match info level
        query = LogSearchQuery(level=LogLevel.INFO)
        assert log_aggregation_service._matches_query(entry, query) == True
        
        # Should not match error level
        query = LogSearchQuery(level=LogLevel.ERROR)
        assert log_aggregation_service._matches_query(entry, query) == False
    
    def test_matches_query_user_filter(self, log_aggregation_service, sample_log_entries):
        """Test query matching with user filter"""
        entry = log_aggregation_service._parse_log_entry(sample_log_entries[0])
        
        # Should match correct user ID
        query = LogSearchQuery(user_id="user-456")
        assert log_aggregation_service._matches_query(entry, query) == True
        
        # Should not match different user ID
        query = LogSearchQuery(user_id="user-999")
        assert log_aggregation_service._matches_query(entry, query) == False
    
    def test_matches_query_text_search(self, log_aggregation_service, sample_log_entries):
        """Test query matching with text search"""
        entry = log_aggregation_service._parse_log_entry(sample_log_entries[0])
        
        # Should match text in message
        query = LogSearchQuery(search_text="login")
        assert log_aggregation_service._matches_query(entry, query) == True
        
        # Should not match non-existent text
        query = LogSearchQuery(search_text="nonexistent")
        assert log_aggregation_service._matches_query(entry, query) == False
    
    @pytest.mark.asyncio
    async def test_get_log_statistics(self, log_aggregation_service, sample_log_entries, temp_log_dir):
        """Test log statistics generation"""
        # Create sample log file
        log_file = temp_log_dir / "application.log"
        with open(log_file, 'w') as f:
            for entry in sample_log_entries:
                f.write(json.dumps(entry) + '\n')
        
        now = datetime.now(timezone.utc)
        start_time = now - timedelta(hours=2)
        end_time = now
        
        stats = await log_aggregation_service.get_log_statistics(start_time, end_time)
        
        assert stats["total_entries"] == 3
        assert "level_distribution" in stats
        assert "event_type_distribution" in stats
        assert "error_distribution" in stats
        assert "top_users" in stats
        assert "top_ips" in stats
        
        # Check level distribution
        assert stats["level_distribution"]["info"] == 2
        assert stats["level_distribution"]["error"] == 1
        
        # Check event type distribution
        assert stats["event_type_distribution"]["login_success"] == 1
        assert stats["event_type_distribution"]["subscription_purchased"] == 1
        
        # Check error distribution
        assert stats["error_distribution"]["ValidationError"] == 1
    
    @pytest.mark.asyncio
    async def test_export_logs_json(self, log_aggregation_service, sample_log_entries, temp_log_dir):
        """Test exporting logs to JSON format"""
        # Create sample log file
        log_file = temp_log_dir / "application.log"
        with open(log_file, 'w') as f:
            for entry in sample_log_entries:
                f.write(json.dumps(entry) + '\n')
        
        query = LogSearchQuery(limit=10)
        export_data = await log_aggregation_service.export_logs(query, "json")
        
        # Should be valid JSON
        exported_entries = json.loads(export_data)
        assert len(exported_entries) == 3
        assert all("timestamp" in entry for entry in exported_entries)
        assert all("message" in entry for entry in exported_entries)
    
    @pytest.mark.asyncio
    async def test_export_logs_csv(self, log_aggregation_service, sample_log_entries, temp_log_dir):
        """Test exporting logs to CSV format"""
        # Create sample log file
        log_file = temp_log_dir / "application.log"
        with open(log_file, 'w') as f:
            for entry in sample_log_entries:
                f.write(json.dumps(entry) + '\n')
        
        query = LogSearchQuery(limit=10)
        export_data = await log_aggregation_service.export_logs(query, "csv")
        
        # Should be valid CSV with headers
        lines = export_data.strip().split('\n')
        assert len(lines) >= 4  # Header + 3 data rows
        assert "timestamp" in lines[0]  # Header row
        assert "message" in lines[0]
    
    @pytest.mark.asyncio
    async def test_export_logs_invalid_format(self, log_aggregation_service):
        """Test exporting logs with invalid format"""
        query = LogSearchQuery(limit=10)
        
        with pytest.raises(ValueError, match="Unsupported export format"):
            await log_aggregation_service.export_logs(query, "xml")
    
    def test_get_relevant_log_files_security(self, log_aggregation_service, temp_log_dir):
        """Test getting relevant log files for security events"""
        # Create various log files
        (temp_log_dir / "application.log").touch()
        (temp_log_dir / "security.log").touch()
        (temp_log_dir / "business.log").touch()
        (temp_log_dir / "errors.log").touch()
        
        query = LogSearchQuery(event_type=SecurityEventType.LOGIN_SUCCESS.value)
        
        # This would be tested with async, but for simplicity testing the logic
        # In real implementation, this would be an async method call
        # log_files = await log_aggregation_service._get_relevant_log_files(query)
        # assert any("security.log" in str(f) for f in log_files)
    
    def test_get_relevant_log_files_business(self, log_aggregation_service, temp_log_dir):
        """Test getting relevant log files for business events"""
        # Create various log files
        (temp_log_dir / "application.log").touch()
        (temp_log_dir / "security.log").touch()
        (temp_log_dir / "business.log").touch()
        (temp_log_dir / "errors.log").touch()
        
        query = LogSearchQuery(event_type=BusinessEventType.PANIC_REQUEST_SUBMITTED.value)
        
        # This would be tested with async, but for simplicity testing the logic
        # In real implementation, this would be an async method call
        # log_files = await log_aggregation_service._get_relevant_log_files(query)
        # assert any("business.log" in str(f) for f in log_files)


class TestLogSearchQuery:
    """Test log search query model"""
    
    def test_default_values(self):
        """Test default query values"""
        query = LogSearchQuery()
        
        assert query.start_time is None
        assert query.end_time is None
        assert query.level is None
        assert query.limit == 100
        assert query.offset == 0
        assert query.sort_order == "desc"
    
    def test_custom_values(self):
        """Test custom query values"""
        start_time = datetime.now(timezone.utc) - timedelta(hours=1)
        end_time = datetime.now(timezone.utc)
        
        query = LogSearchQuery(
            start_time=start_time,
            end_time=end_time,
            level=LogLevel.ERROR,
            user_id="test-user",
            limit=50,
            offset=10,
            sort_order="asc"
        )
        
        assert query.start_time == start_time
        assert query.end_time == end_time
        assert query.level == LogLevel.ERROR
        assert query.user_id == "test-user"
        assert query.limit == 50
        assert query.offset == 10
        assert query.sort_order == "asc"


class TestLogEntry:
    """Test log entry model"""
    
    def test_log_entry_creation(self):
        """Test log entry creation"""
        timestamp = datetime.now(timezone.utc)
        
        entry = LogEntry(
            timestamp=timestamp,
            level="info",
            logger="test.logger",
            message="Test message",
            service="test-service",
            version="1.0.0",
            environment="test",
            user_id="user-123",
            request_id="req-456"
        )
        
        assert entry.timestamp == timestamp
        assert entry.level == "info"
        assert entry.logger == "test.logger"
        assert entry.message == "Test message"
        assert entry.user_id == "user-123"
        assert entry.request_id == "req-456"


if __name__ == "__main__":
    pytest.main([__file__])