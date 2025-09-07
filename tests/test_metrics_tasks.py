"""
Unit tests for metrics background tasks
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio

from app.tasks.metrics import (
    update_all_metrics,
    update_performance_metrics,
    cleanup_old_metrics,
    record_panic_request_metrics,
    record_auth_metrics,
    record_notification_metrics
)


class TestMetricsTasks:
    """Test metrics background tasks"""
    
    def test_update_all_metrics_success(self):
        """Test successful metrics update task"""
        with patch('app.tasks.metrics.get_db') as mock_get_db, \
             patch('app.tasks.metrics.metrics_service') as mock_service:
            
            # Mock async generator for database session
            async def mock_db_generator():
                yield AsyncMock()
            
            mock_get_db.return_value = mock_db_generator()
            mock_service.run_periodic_metrics_update = AsyncMock()
            
            result = update_all_metrics()
            
            assert result["status"] == "success"
            assert result["message"] == "All metrics updated"
    
    def test_update_all_metrics_error(self):
        """Test metrics update task with error"""
        with patch('app.tasks.metrics.get_db') as mock_get_db:
            mock_get_db.side_effect = Exception("Database connection failed")
            
            result = update_all_metrics()
            
            assert result["status"] == "error"
            assert "Database connection failed" in result["message"]
    
    def test_update_performance_metrics_success(self):
        """Test successful performance metrics update"""
        with patch('app.tasks.metrics.get_db') as mock_get_db, \
             patch('app.tasks.metrics.metrics_service') as mock_service:
            
            # Mock async generator for database session
            async def mock_db_generator():
                yield AsyncMock()
            
            mock_get_db.return_value = mock_db_generator()
            mock_service.update_performance_metrics = AsyncMock()
            
            result = update_performance_metrics()
            
            assert result["status"] == "success"
            assert result["message"] == "Performance metrics updated"
    
    def test_update_performance_metrics_error(self):
        """Test performance metrics update with error"""
        with patch('app.tasks.metrics.get_db') as mock_get_db:
            mock_get_db.side_effect = Exception("Performance update failed")
            
            result = update_performance_metrics()
            
            assert result["status"] == "error"
            assert "Performance update failed" in result["message"]
    
    def test_cleanup_old_metrics_success(self):
        """Test successful metrics cleanup"""
        result = cleanup_old_metrics()
        
        assert result["status"] == "success"
        assert result["message"] == "Metrics cleanup completed"
    
    def test_cleanup_old_metrics_error(self):
        """Test metrics cleanup with error"""
        with patch('app.tasks.metrics.logger') as mock_logger:
            # Simulate an error during cleanup
            mock_logger.info.side_effect = Exception("Cleanup failed")
            
            result = cleanup_old_metrics()
            
            assert result["status"] == "error"
            assert "Cleanup failed" in result["message"]
    
    def test_record_panic_request_metrics_submitted(self):
        """Test recording panic request submission metrics"""
        with patch('app.tasks.metrics.metrics_service') as mock_service:
            mock_service.record_panic_request_submitted = AsyncMock()
            
            result = record_panic_request_metrics(
                service_type="security",
                status="submitted",
                firm_id="firm123",
                zone="zone1"
            )
            
            assert result["status"] == "success"
            assert result["message"] == "Panic request metrics recorded"
    
    def test_record_panic_request_metrics_accepted(self):
        """Test recording panic request acceptance metrics"""
        with patch('app.tasks.metrics.metrics_service') as mock_service:
            mock_service.record_panic_request_accepted = AsyncMock()
            
            result = record_panic_request_metrics(
                service_type="ambulance",
                status="accepted",
                firm_id="firm456",
                zone="zone2",
                response_time=180.5
            )
            
            assert result["status"] == "success"
            assert result["message"] == "Panic request metrics recorded"
    
    def test_record_panic_request_metrics_completed(self):
        """Test recording panic request completion metrics"""
        with patch('app.tasks.metrics.metrics_service') as mock_service:
            mock_service.record_panic_request_completed = AsyncMock()
            
            result = record_panic_request_metrics(
                service_type="fire",
                status="completed",
                firm_id="firm789",
                zone="zone3",
                completion_time=600.0
            )
            
            assert result["status"] == "success"
            assert result["message"] == "Panic request metrics recorded"
    
    def test_record_panic_request_metrics_error(self):
        """Test recording panic request metrics with error"""
        with patch('app.tasks.metrics.metrics_service') as mock_service:
            mock_service.record_panic_request_submitted = AsyncMock(
                side_effect=Exception("Metrics recording failed")
            )
            
            result = record_panic_request_metrics(
                service_type="security",
                status="submitted",
                firm_id="firm123"
            )
            
            assert result["status"] == "error"
            assert "Metrics recording failed" in result["message"]
    
    def test_record_auth_metrics_success(self):
        """Test recording authentication metrics"""
        with patch('app.tasks.metrics.metrics_service') as mock_service:
            mock_service.record_authentication_metrics = AsyncMock()
            
            result = record_auth_metrics(
                user_type="registered_user",
                success=True,
                account_locked=False
            )
            
            assert result["status"] == "success"
            assert result["message"] == "Auth metrics recorded"
    
    def test_record_auth_metrics_failed_with_lockout(self):
        """Test recording failed auth with account lockout"""
        with patch('app.tasks.metrics.metrics_service') as mock_service:
            mock_service.record_authentication_metrics = AsyncMock()
            
            result = record_auth_metrics(
                user_type="field_agent",
                success=False,
                account_locked=True
            )
            
            assert result["status"] == "success"
            assert result["message"] == "Auth metrics recorded"
    
    def test_record_auth_metrics_error(self):
        """Test recording auth metrics with error"""
        with patch('app.tasks.metrics.metrics_service') as mock_service:
            mock_service.record_authentication_metrics = AsyncMock(
                side_effect=Exception("Auth metrics failed")
            )
            
            result = record_auth_metrics(
                user_type="registered_user",
                success=True
            )
            
            assert result["status"] == "error"
            assert "Auth metrics failed" in result["message"]
    
    def test_record_notification_metrics_success(self):
        """Test recording notification metrics"""
        with patch('app.tasks.metrics.metrics_service') as mock_service:
            mock_service.record_notification_sent = AsyncMock()
            
            result = record_notification_metrics(
                notification_type="push",
                success=True
            )
            
            assert result["status"] == "success"
            assert result["message"] == "Notification metrics recorded"
    
    def test_record_notification_metrics_failed(self):
        """Test recording failed notification metrics"""
        with patch('app.tasks.metrics.metrics_service') as mock_service:
            mock_service.record_notification_sent = AsyncMock()
            
            result = record_notification_metrics(
                notification_type="sms",
                success=False
            )
            
            assert result["status"] == "success"
            assert result["message"] == "Notification metrics recorded"
    
    def test_record_notification_metrics_error(self):
        """Test recording notification metrics with error"""
        with patch('app.tasks.metrics.metrics_service') as mock_service:
            mock_service.record_notification_sent = AsyncMock(
                side_effect=Exception("Notification metrics failed")
            )
            
            result = record_notification_metrics(
                notification_type="email",
                success=True
            )
            
            assert result["status"] == "error"
            assert "Notification metrics failed" in result["message"]


class TestCeleryConfiguration:
    """Test Celery configuration for metrics tasks"""
    
    def test_celery_app_configuration(self):
        """Test Celery app is properly configured"""
        from app.tasks.metrics import celery_app
        
        # Check basic configuration
        assert celery_app.conf.task_serializer == 'json'
        assert celery_app.conf.accept_content == ['json']
        assert celery_app.conf.result_serializer == 'json'
        assert celery_app.conf.timezone == 'UTC'
        assert celery_app.conf.enable_utc is True
    
    def test_celery_beat_schedule(self):
        """Test Celery beat schedule is configured"""
        from app.tasks.metrics import celery_app
        
        beat_schedule = celery_app.conf.beat_schedule
        
        # Check scheduled tasks exist
        assert 'update-metrics-every-minute' in beat_schedule
        assert 'update-performance-metrics-every-5-minutes' in beat_schedule
        assert 'cleanup-old-metrics-daily' in beat_schedule
        
        # Check task schedules
        assert beat_schedule['update-metrics-every-minute']['schedule'] == 60.0
        assert beat_schedule['update-performance-metrics-every-5-minutes']['schedule'] == 300.0
        assert beat_schedule['cleanup-old-metrics-daily']['schedule'] == 86400.0
        
        # Check task names
        assert beat_schedule['update-metrics-every-minute']['task'] == 'app.tasks.metrics.update_all_metrics'
        assert beat_schedule['update-performance-metrics-every-5-minutes']['task'] == 'app.tasks.metrics.update_performance_metrics'
        assert beat_schedule['cleanup-old-metrics-daily']['task'] == 'app.tasks.metrics.cleanup_old_metrics'


class TestAsyncTaskExecution:
    """Test async task execution within Celery tasks"""
    
    def test_async_function_execution_in_sync_task(self):
        """Test that async functions are properly executed in sync Celery tasks"""
        
        # Mock async function
        async def mock_async_function():
            return "async_result"
        
        # Test the pattern used in the tasks
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(mock_async_function())
        loop.close()
        
        assert result == "async_result"
    
    def test_async_generator_handling(self):
        """Test async generator handling in tasks"""
        
        async def mock_async_generator():
            yield "item1"
            yield "item2"
        
        # Test the pattern used for database sessions
        async def process_generator():
            async for item in mock_async_generator():
                return item  # Return first item like in the tasks
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(process_generator())
        loop.close()
        
        assert result == "item1"


if __name__ == "__main__":
    pytest.main([__file__])