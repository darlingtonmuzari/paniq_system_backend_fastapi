"""
Unit tests for log retention service
"""
import pytest
import tempfile
import shutil
import gzip
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.services.log_retention import (
    LogRetentionService,
    LogType,
    RetentionPolicy
)


@pytest.fixture
def temp_log_dir():
    """Fixture for temporary log directory"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def log_retention_service(temp_log_dir):
    """Fixture for log retention service"""
    return LogRetentionService(temp_log_dir)


class TestLogRetentionService:
    """Test log retention service functionality"""
    
    def test_service_initialization(self, temp_log_dir):
        """Test service initialization"""
        service = LogRetentionService(temp_log_dir)
        
        assert service.log_dir == temp_log_dir
        assert service.archive_dir == temp_log_dir / "archive"
        assert service.archive_dir.exists()
        assert len(service.policies) == 4  # Four default policies
        assert LogType.APPLICATION in service.policies
        assert LogType.SECURITY in service.policies
        assert LogType.BUSINESS in service.policies
        assert LogType.ERROR in service.policies
    
    def test_default_retention_policies(self, log_retention_service):
        """Test default retention policies"""
        app_policy = log_retention_service.policies[LogType.APPLICATION]
        assert app_policy.retention_days == 90
        assert app_policy.archive_days == 30
        assert app_policy.compress_after_days == 7
        
        security_policy = log_retention_service.policies[LogType.SECURITY]
        assert security_policy.retention_days == 365  # Longer for security
        assert security_policy.archive_days == 90
        assert security_policy.compress_after_days == 7
        
        business_policy = log_retention_service.policies[LogType.BUSINESS]
        assert business_policy.retention_days == 180
        assert business_policy.archive_days == 60
        assert business_policy.compress_after_days == 7
        
        error_policy = log_retention_service.policies[LogType.ERROR]
        assert error_policy.retention_days == 180
        assert error_policy.archive_days == 60
        assert error_policy.compress_after_days == 7
    
    def test_update_retention_policy(self, log_retention_service):
        """Test updating retention policy"""
        new_policy = RetentionPolicy(
            log_type=LogType.APPLICATION,
            retention_days=120,
            archive_days=45,
            compress_after_days=10,
            max_file_size_mb=100,
            max_backup_count=15
        )
        
        log_retention_service.update_retention_policy(LogType.APPLICATION, new_policy)
        
        updated_policy = log_retention_service.policies[LogType.APPLICATION]
        assert updated_policy.retention_days == 120
        assert updated_policy.archive_days == 45
        assert updated_policy.compress_after_days == 10
        assert updated_policy.max_file_size_mb == 100
        assert updated_policy.max_backup_count == 15
    
    def test_get_log_files_by_type(self, log_retention_service, temp_log_dir):
        """Test getting log files by type"""
        # Create test log files
        (temp_log_dir / "application.log").touch()
        (temp_log_dir / "application.log.1").touch()
        (temp_log_dir / "security.log").touch()
        (temp_log_dir / "business.log").touch()
        (temp_log_dir / "errors.log").touch()
        (temp_log_dir / "other.log").touch()  # Should not be included
        
        # Test application logs
        app_files = log_retention_service._get_log_files_by_type(LogType.APPLICATION)
        app_file_names = [f.name for f in app_files]
        assert "application.log" in app_file_names
        assert "application.log.1" in app_file_names
        assert "security.log" not in app_file_names
        
        # Test security logs
        security_files = log_retention_service._get_log_files_by_type(LogType.SECURITY)
        security_file_names = [f.name for f in security_files]
        assert "security.log" in security_file_names
        assert "application.log" not in security_file_names
        
        # Test business logs
        business_files = log_retention_service._get_log_files_by_type(LogType.BUSINESS)
        business_file_names = [f.name for f in business_files]
        assert "business.log" in business_file_names
        
        # Test error logs
        error_files = log_retention_service._get_log_files_by_type(LogType.ERROR)
        error_file_names = [f.name for f in error_files]
        assert "errors.log" in error_file_names
    
    @pytest.mark.asyncio
    async def test_compress_log_file(self, log_retention_service, temp_log_dir):
        """Test log file compression"""
        # Create test log file
        log_file = temp_log_dir / "test.log"
        test_content = "This is test log content\nLine 2\nLine 3"
        log_file.write_text(test_content)
        
        # Compress the file
        result = await log_retention_service._compress_log_file(log_file)
        
        assert result == True
        assert not log_file.exists()  # Original file should be removed
        
        compressed_file = temp_log_dir / "test.log.gz"
        assert compressed_file.exists()
        
        # Verify compressed content
        with gzip.open(compressed_file, 'rt') as f:
            decompressed_content = f.read()
            assert decompressed_content == test_content
    
    @pytest.mark.asyncio
    async def test_compress_already_compressed_file(self, log_retention_service, temp_log_dir):
        """Test compressing already compressed file"""
        # Create compressed log file
        log_file = temp_log_dir / "test.log.gz"
        with gzip.open(log_file, 'wt') as f:
            f.write("Test content")
        
        # Try to compress again
        result = await log_retention_service._compress_log_file(log_file)
        
        assert result == False  # Should not compress already compressed file
        assert log_file.exists()  # File should still exist
    
    @pytest.mark.asyncio
    async def test_archive_log_file(self, log_retention_service, temp_log_dir):
        """Test log file archival"""
        # Create test log file
        log_file = temp_log_dir / "application.log"
        test_content = "Test log content for archival"
        log_file.write_text(test_content)
        
        # Set file modification time to 40 days ago
        old_time = (datetime.now() - timedelta(days=40)).timestamp()
        log_file.touch(times=(old_time, old_time))
        
        # Archive the file
        result = await log_retention_service._archive_log_file(log_file, LogType.APPLICATION)
        
        assert result == True
        assert not log_file.exists()  # Original file should be moved
        
        # Check archive directory
        archive_dir = temp_log_dir / "archive" / "application"
        assert archive_dir.exists()
        
        # Check for archived file (should be compressed)
        archive_files = list(archive_dir.glob("*.gz"))
        assert len(archive_files) == 1
        
        # Verify archived content
        with gzip.open(archive_files[0], 'rt') as f:
            archived_content = f.read()
            assert archived_content == test_content
    
    @pytest.mark.asyncio
    async def test_delete_log_file(self, log_retention_service, temp_log_dir):
        """Test log file deletion"""
        # Create test log file
        log_file = temp_log_dir / "old.log"
        log_file.write_text("Old log content")
        
        # Delete the file
        result = await log_retention_service._delete_log_file(log_file)
        
        assert result == True
        assert not log_file.exists()
    
    @pytest.mark.asyncio
    async def test_process_log_type(self, log_retention_service, temp_log_dir):
        """Test processing logs for a specific type"""
        # Create test files with different ages
        now = datetime.now()
        
        # File to be deleted (older than retention)
        old_file = temp_log_dir / "application.log.old"
        old_file.write_text("Very old content")
        very_old_time = (now - timedelta(days=100)).timestamp()
        old_file.touch(times=(very_old_time, very_old_time))
        
        # File to be archived (older than archive threshold)
        archive_file = temp_log_dir / "application.log.archive"
        archive_file.write_text("Archive content")
        archive_time = (now - timedelta(days=40)).timestamp()
        archive_file.touch(times=(archive_time, archive_time))
        
        # File to be compressed (older than compress threshold)
        compress_file = temp_log_dir / "application.log.compress"
        compress_file.write_text("Compress content")
        compress_time = (now - timedelta(days=10)).timestamp()
        compress_file.touch(times=(compress_time, compress_time))
        
        # Recent file (should not be touched)
        recent_file = temp_log_dir / "application.log.recent"
        recent_file.write_text("Recent content")
        recent_time = (now - timedelta(days=1)).timestamp()
        recent_file.touch(times=(recent_time, recent_time))
        
        # Process application logs
        policy = log_retention_service.policies[LogType.APPLICATION]
        results = await log_retention_service._process_log_type(LogType.APPLICATION, policy)
        
        # Check results
        assert results["deleted_files"] == 1
        assert results["archived_files"] == 1
        assert results["compressed_files"] == 1
        assert results["errors"] == 0
        
        # Verify file states
        assert not old_file.exists()  # Should be deleted
        assert not archive_file.exists()  # Should be archived
        assert not compress_file.exists()  # Should be compressed
        assert recent_file.exists()  # Should remain unchanged
        
        # Check compressed file exists
        compressed_file = temp_log_dir / "application.log.compress.gz"
        assert compressed_file.exists()
        
        # Check archive directory
        archive_dir = temp_log_dir / "archive" / "application"
        assert archive_dir.exists()
        archive_files = list(archive_dir.glob("*.gz"))
        assert len(archive_files) == 1
    
    @pytest.mark.asyncio
    async def test_run_retention_cleanup(self, log_retention_service, temp_log_dir):
        """Test complete retention cleanup process"""
        # Create test files for different log types
        now = datetime.now()
        
        # Application log files
        app_old = temp_log_dir / "application.log.old"
        app_old.write_text("Old app log")
        old_time = (now - timedelta(days=100)).timestamp()
        app_old.touch(times=(old_time, old_time))
        
        # Security log files
        sec_archive = temp_log_dir / "security.log.archive"
        sec_archive.write_text("Archive security log")
        archive_time = (now - timedelta(days=100)).timestamp()  # Should be archived for security
        sec_archive.touch(times=(archive_time, archive_time))
        
        # Business log files
        bus_compress = temp_log_dir / "business.log.compress"
        bus_compress.write_text("Compress business log")
        compress_time = (now - timedelta(days=10)).timestamp()
        bus_compress.touch(times=(compress_time, compress_time))
        
        # Run cleanup
        results = await log_retention_service.run_retention_cleanup()
        
        # Check overall results
        assert "compressed_files" in results
        assert "archived_files" in results
        assert "deleted_files" in results
        assert "errors" in results
        
        # Should have processed files
        assert results["deleted_files"] >= 1
        assert results["archived_files"] >= 1
        assert results["compressed_files"] >= 1
    
    @pytest.mark.asyncio
    async def test_get_retention_status(self, log_retention_service, temp_log_dir):
        """Test getting retention status"""
        # Create test log files
        app_log = temp_log_dir / "application.log"
        app_log.write_text("Application log content")
        
        sec_log = temp_log_dir / "security.log"
        sec_log.write_text("Security log content")
        
        # Create archive files
        archive_dir = temp_log_dir / "archive" / "application"
        archive_dir.mkdir(parents=True)
        archive_file = archive_dir / "archived.log.gz"
        with gzip.open(archive_file, 'wt') as f:
            f.write("Archived content")
        
        # Get status
        status = await log_retention_service.get_retention_status()
        
        # Check status structure
        assert "policies" in status
        assert "disk_usage" in status
        assert "file_counts" in status
        assert "oldest_files" in status
        assert "archive_status" in status
        assert "total_disk_usage" in status
        assert "total_file_count" in status
        
        # Check policies
        assert "application" in status["policies"]
        assert "security" in status["policies"]
        assert "business" in status["policies"]
        assert "error" in status["policies"]
        
        # Check disk usage
        assert "application" in status["disk_usage"]
        assert "security" in status["disk_usage"]
        
        # Check file counts
        assert status["file_counts"]["application"] >= 1
        assert status["file_counts"]["security"] >= 1
        
        # Check archive status
        assert "application" in status["archive_status"]
        assert status["archive_status"]["application"]["file_count"] >= 1
    
    @pytest.mark.asyncio
    async def test_cleanup_empty_archives(self, log_retention_service, temp_log_dir):
        """Test cleanup of empty archive directories"""
        # Create empty archive directories
        empty_dir1 = temp_log_dir / "archive" / "empty1"
        empty_dir1.mkdir(parents=True)
        
        empty_dir2 = temp_log_dir / "archive" / "empty2"
        empty_dir2.mkdir(parents=True)
        
        # Create non-empty archive directory
        non_empty_dir = temp_log_dir / "archive" / "nonempty"
        non_empty_dir.mkdir(parents=True)
        (non_empty_dir / "file.log").touch()
        
        # Run cleanup
        cleaned_count = await log_retention_service.cleanup_empty_archives()
        
        # Should have cleaned 2 empty directories
        assert cleaned_count == 2
        
        # Empty directories should be gone
        assert not empty_dir1.exists()
        assert not empty_dir2.exists()
        
        # Non-empty directory should remain
        assert non_empty_dir.exists()


class TestRetentionPolicy:
    """Test retention policy model"""
    
    def test_retention_policy_creation(self):
        """Test retention policy creation"""
        policy = RetentionPolicy(
            log_type=LogType.APPLICATION,
            retention_days=90,
            archive_days=30,
            compress_after_days=7,
            max_file_size_mb=50,
            max_backup_count=10
        )
        
        assert policy.log_type == LogType.APPLICATION
        assert policy.retention_days == 90
        assert policy.archive_days == 30
        assert policy.compress_after_days == 7
        assert policy.max_file_size_mb == 50
        assert policy.max_backup_count == 10


class TestLogType:
    """Test log type enumeration"""
    
    def test_log_type_values(self):
        """Test log type enumeration values"""
        assert LogType.APPLICATION == "application"
        assert LogType.SECURITY == "security"
        assert LogType.BUSINESS == "business"
        assert LogType.ERROR == "error"


class TestLogRetentionIntegration:
    """Integration tests for log retention"""
    
    @pytest.mark.asyncio
    async def test_full_retention_cycle(self, temp_log_dir):
        """Test complete retention lifecycle"""
        service = LogRetentionService(temp_log_dir)
        
        # Create files at different lifecycle stages
        now = datetime.now()
        
        # Create files for each stage
        files_to_create = [
            ("application.log.delete", 100, "delete"),  # Should be deleted
            ("application.log.archive", 40, "archive"),  # Should be archived
            ("application.log.compress", 10, "compress"),  # Should be compressed
            ("application.log.keep", 1, "keep"),  # Should be kept as-is
        ]
        
        for filename, age_days, expected_action in files_to_create:
            file_path = temp_log_dir / filename
            file_path.write_text(f"Content for {expected_action}")
            
            # Set file age
            file_time = (now - timedelta(days=age_days)).timestamp()
            file_path.touch(times=(file_time, file_time))
        
        # Run retention cleanup
        results = await service.run_retention_cleanup()
        
        # Verify results
        assert results["deleted_files"] >= 1
        assert results["archived_files"] >= 1
        assert results["compressed_files"] >= 1
        
        # Verify file states
        assert not (temp_log_dir / "application.log.delete").exists()
        assert not (temp_log_dir / "application.log.archive").exists()
        assert not (temp_log_dir / "application.log.compress").exists()
        assert (temp_log_dir / "application.log.keep").exists()
        
        # Verify compressed file exists
        assert (temp_log_dir / "application.log.compress.gz").exists()
        
        # Verify archive exists
        archive_dir = temp_log_dir / "archive" / "application"
        assert archive_dir.exists()
        archive_files = list(archive_dir.glob("*.gz"))
        assert len(archive_files) >= 1
        
        # Get final status
        status = await service.get_retention_status()
        assert status["total_file_count"] >= 2  # Keep file + compressed file


if __name__ == "__main__":
    pytest.main([__file__])