"""
Unit tests for structured logging functionality
"""
import pytest
import json
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock
import gzip

from app.core.logging import (
    StructuredLogger,
    get_logger,
    setup_logging,
    LogLevel,
    SecurityEventType,
    BusinessEventType,
    set_request_context,
    clear_request_context,
    get_request_context,
    LogRetentionManager,
    filter_sensitive_data,
    add_timestamp,
    add_service_context,
    JSONFormatter
)


class TestStructuredLogger:
    """Test structured logger functionality"""
    
    def test_logger_creation(self):
        """Test logger creation and basic functionality"""
        logger = get_logger("test_logger")
        assert isinstance(logger, StructuredLogger)
        assert logger.logger is not None
    
    def test_logger_binding(self):
        """Test logger context binding"""
        logger = get_logger("test_logger")
        bound_logger = logger.bind(user_id="123", request_id="abc")
        
        assert isinstance(bound_logger, StructuredLogger)
        assert bound_logger._context == {"user_id": "123", "request_id": "abc"}
    
    def test_logger_with_context(self):
        """Test logger with_context method (alias for bind)"""
        logger = get_logger("test_logger")
        context_logger = logger.with_context(session_id="xyz", action="test")
        
        assert isinstance(context_logger, StructuredLogger)
        assert context_logger._context == {"session_id": "xyz", "action": "test"}
    
    @patch('logging.getLogger')
    def test_security_event_logging(self, mock_get_logger):
        """Test security event logging"""
        mock_security_logger = MagicMock()
        mock_get_logger.return_value = mock_security_logger
        
        logger = get_logger("test_logger")
        logger.security_event(
            SecurityEventType.LOGIN_SUCCESS,
            user_id="123",
            client_ip="192.168.1.1"
        )
        
        mock_get_logger.assert_called_with("security")
        mock_security_logger.info.assert_called_once()
        
        # Check the logged data structure
        call_args = mock_security_logger.info.call_args[0][0]
        logged_data = json.loads(call_args)
        
        assert logged_data["event_type"] == SecurityEventType.LOGIN_SUCCESS.value
        assert logged_data["category"] == "security"
        assert logged_data["user_id"] == "123"
        assert logged_data["client_ip"] == "192.168.1.1"
        assert "timestamp" in logged_data
    
    @patch('logging.getLogger')
    def test_business_event_logging(self, mock_get_logger):
        """Test business event logging"""
        mock_business_logger = MagicMock()
        mock_get_logger.return_value = mock_business_logger
        
        logger = get_logger("test_logger")
        logger.business_event(
            BusinessEventType.PANIC_REQUEST_SUBMITTED,
            user_id="456",
            request_id="req-789",
            service_type="security"
        )
        
        mock_get_logger.assert_called_with("business")
        mock_business_logger.info.assert_called_once()
        
        # Check the logged data structure
        call_args = mock_business_logger.info.call_args[0][0]
        logged_data = json.loads(call_args)
        
        assert logged_data["event_type"] == BusinessEventType.PANIC_REQUEST_SUBMITTED.value
        assert logged_data["category"] == "business"
        assert logged_data["user_id"] == "456"
        assert logged_data["request_id"] == "req-789"
        assert logged_data["service_type"] == "security"


class TestRequestContext:
    """Test request context management"""
    
    def test_set_and_get_request_context(self):
        """Test setting and getting request context"""
        request_id = "test-request-123"
        user_id = "user-456"
        
        set_request_context(request_id, user_id)
        context = get_request_context()
        
        assert context["request_id"] == request_id
        assert context["user_id"] == user_id
    
    def test_clear_request_context(self):
        """Test clearing request context"""
        set_request_context("test-request", "test-user")
        clear_request_context()
        
        context = get_request_context()
        assert context["request_id"] is None
        assert context["user_id"] is None
    
    def test_partial_context(self):
        """Test setting partial context (only request_id)"""
        request_id = "test-request-only"
        
        set_request_context(request_id)
        context = get_request_context()
        
        assert context["request_id"] == request_id
        assert context["user_id"] is None


class TestLogProcessors:
    """Test log processors"""
    
    def test_filter_sensitive_data(self):
        """Test sensitive data filtering"""
        event_dict = {
            "message": "User login",
            "password": "secret123",
            "email": "user@example.com",
            "phone": "1234567890",
            "token": "jwt-token-here",
            "user_data": {
                "name": "John Doe",
                "credit_card": "4111-1111-1111-1111"
            },
            "safe_field": "safe_value"
        }
        
        filtered = filter_sensitive_data(None, None, event_dict)
        
        assert filtered["password"] == "***"
        assert filtered["email"] == "us***@example.com"
        assert filtered["phone"] == "***7890"
        assert filtered["token"] == "***"
        assert filtered["user_data"]["credit_card"] == "***"
        assert filtered["user_data"]["name"] == "John Doe"  # Safe field unchanged
        assert filtered["safe_field"] == "safe_value"
    
    def test_add_timestamp(self):
        """Test timestamp addition"""
        event_dict = {"message": "test"}
        
        result = add_timestamp(None, None, event_dict)
        
        assert "timestamp" in result
        # Verify timestamp is valid ISO format
        datetime.fromisoformat(result["timestamp"].replace('Z', '+00:00'))
    
    def test_add_service_context(self):
        """Test service context addition"""
        event_dict = {"message": "test"}
        
        result = add_service_context(None, None, event_dict)
        
        assert result["service"] == "panic-system-platform"
        assert result["version"] == "1.0.0"
        assert "environment" in result


class TestJSONFormatter:
    """Test JSON formatter"""
    
    def test_json_formatter_basic(self):
        """Test basic JSON formatting"""
        import logging
        
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        data = json.loads(formatted)
        
        assert data["level"] == "info"
        assert data["logger"] == "test_logger"
        assert data["message"] == "Test message"
        assert data["service"] == "panic-system-platform"
        assert "timestamp" in data
    
    def test_json_formatter_with_exception(self):
        """Test JSON formatting with exception"""
        import logging
        
        formatter = JSONFormatter()
        
        try:
            raise ValueError("Test exception")
        except ValueError:
            import sys
            record = logging.LogRecord(
                name="test_logger",
                level=logging.ERROR,
                pathname="test.py",
                lineno=10,
                msg="Error occurred",
                args=(),
                exc_info=sys.exc_info()
            )
        
        formatted = formatter.format(record)
        data = json.loads(formatted)
        
        assert data["level"] == "error"
        assert data["message"] == "Error occurred"
        assert "exception" in data
        assert "ValueError: Test exception" in data["exception"]


class TestLogRetentionManager:
    """Test log retention manager"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.retention_manager = LogRetentionManager(self.temp_dir)
    
    def tearDown(self):
        """Clean up test environment"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_cleanup_old_logs(self):
        """Test cleanup of old log files"""
        self.setUp()
        
        try:
            # Create test log files with different ages
            old_log = self.temp_dir / "old.log"
            recent_log = self.temp_dir / "recent.log"
            
            old_log.write_text("old log content")
            recent_log.write_text("recent log content")
            
            # Set old file modification time to 100 days ago
            old_time = (datetime.now() - timedelta(days=100)).timestamp()
            import os
            os.utime(old_log, (old_time, old_time))
            
            # Run cleanup with 90 day retention
            self.retention_manager.cleanup_old_logs(retention_days=90)
            
            # Old file should be removed, recent file should remain
            assert not old_log.exists()
            assert recent_log.exists()
            
        finally:
            self.tearDown()
    
    def test_archive_logs(self):
        """Test log archival"""
        self.setUp()
        
        try:
            # Create test log file
            log_file = self.temp_dir / "test.log"
            log_file.write_text("test log content")
            
            # Set file modification time to 40 days ago
            old_time = (datetime.now() - timedelta(days=40)).timestamp()
            import os
            os.utime(log_file, (old_time, old_time))
            
            # Run archival with 30 day threshold
            self.retention_manager.archive_logs(archive_days=30)
            
            # Original file should be gone, archived file should exist
            assert not log_file.exists()
            
            archive_dir = self.temp_dir / "archive"
            assert archive_dir.exists()
            
            # Check for compressed archive file
            archive_files = list(archive_dir.glob("*.gz"))
            assert len(archive_files) > 0
            
            # Verify archived content
            with gzip.open(archive_files[0], 'rt') as f:
                content = f.read()
                assert "test log content" in content
                
        finally:
            self.tearDown()


@pytest.fixture
def temp_log_dir():
    """Fixture for temporary log directory"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


class TestLogSetup:
    """Test log setup and configuration"""
    
    @patch('app.core.logging.settings')
    @patch('structlog.configure')
    @patch('logging.basicConfig')
    def test_setup_logging(self, mock_basic_config, mock_structlog_configure, mock_settings):
        """Test logging setup"""
        # Mock settings
        mock_settings.LOG_DIR = "/tmp/test_logs"
        mock_settings.LOG_LEVEL = "INFO"
        mock_settings.LOG_MAX_FILE_SIZE_MB = 50
        mock_settings.LOG_MAX_BACKUP_COUNT = 10
        mock_settings.SECURITY_LOG_MAX_BACKUP_COUNT = 20
        
        with patch('app.core.logging.Path') as mock_path:
            mock_log_dir = MagicMock()
            mock_path.return_value = mock_log_dir
            
            setup_logging()
            
            # Verify log directory creation
            mock_log_dir.mkdir.assert_called_with(exist_ok=True)
            
            # Verify structlog configuration
            mock_structlog_configure.assert_called_once()
            
            # Verify basic logging configuration
            mock_basic_config.assert_called_once()
    
    def test_log_levels(self):
        """Test log level enumeration"""
        assert LogLevel.DEBUG == "debug"
        assert LogLevel.INFO == "info"
        assert LogLevel.WARNING == "warning"
        assert LogLevel.ERROR == "error"
        assert LogLevel.CRITICAL == "critical"
    
    def test_security_event_types(self):
        """Test security event type enumeration"""
        assert SecurityEventType.LOGIN_SUCCESS == "login_success"
        assert SecurityEventType.LOGIN_FAILURE == "login_failure"
        assert SecurityEventType.ACCOUNT_LOCKED == "account_locked"
        assert SecurityEventType.ATTESTATION_FAILURE == "attestation_failure"
    
    def test_business_event_types(self):
        """Test business event type enumeration"""
        assert BusinessEventType.PANIC_REQUEST_SUBMITTED == "panic_request_submitted"
        assert BusinessEventType.SUBSCRIPTION_PURCHASED == "subscription_purchased"
        assert BusinessEventType.CREDIT_PURCHASED == "credit_purchased"


class TestLogIntegration:
    """Integration tests for logging system"""
    
    def test_end_to_end_logging(self, temp_log_dir):
        """Test end-to-end logging functionality"""
        # This would be an integration test that verifies the entire logging pipeline
        # from log generation to file output and processing
        
        # Set up logging with temp directory
        with patch('app.core.logging.Path') as mock_path:
            mock_path.return_value = temp_log_dir
            
            logger = get_logger("integration_test")
            
            # Test various log levels
            logger.debug("Debug message", test_field="debug_value")
            logger.info("Info message", test_field="info_value")
            logger.warning("Warning message", test_field="warning_value")
            logger.error("Error message", test_field="error_value")
            
            # Test security event
            logger.security_event(
                SecurityEventType.LOGIN_SUCCESS,
                user_id="test_user",
                client_ip="127.0.0.1"
            )
            
            # Test business event
            logger.business_event(
                BusinessEventType.PANIC_REQUEST_SUBMITTED,
                request_id="test_request",
                service_type="security"
            )
            
            # In a real integration test, we would verify that:
            # 1. Log files are created in the correct location
            # 2. Log entries have the correct format
            # 3. Sensitive data is properly filtered
            # 4. Context information is included
            
            # For now, we just verify the logger works without errors
            assert True  # If we get here, logging didn't crash


if __name__ == "__main__":
    pytest.main([__file__])