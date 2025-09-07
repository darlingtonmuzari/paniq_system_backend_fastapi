"""
Log retention and archival service for the Panic System Platform
"""
import asyncio
import gzip
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)


class LogType(str, Enum):
    """Types of logs with different retention policies"""
    APPLICATION = "application"
    SECURITY = "security"
    BUSINESS = "business"
    ERROR = "error"


@dataclass
class RetentionPolicy:
    """Log retention policy configuration"""
    log_type: LogType
    retention_days: int
    archive_days: int
    compress_after_days: int
    max_file_size_mb: int = 50
    max_backup_count: int = 10


class LogRetentionService:
    """Service for managing log retention and archival"""
    
    # Default retention policies (using settings)
    @property
    def DEFAULT_POLICIES(self):
        return {
            LogType.APPLICATION: RetentionPolicy(
                log_type=LogType.APPLICATION,
                retention_days=settings.LOG_RETENTION_DAYS,
                archive_days=settings.LOG_ARCHIVE_DAYS,
                compress_after_days=settings.LOG_COMPRESS_AFTER_DAYS,
                max_file_size_mb=settings.LOG_MAX_FILE_SIZE_MB,
                max_backup_count=settings.LOG_MAX_BACKUP_COUNT
            ),
            LogType.SECURITY: RetentionPolicy(
                log_type=LogType.SECURITY,
                retention_days=settings.SECURITY_LOG_RETENTION_DAYS,
                archive_days=settings.SECURITY_LOG_ARCHIVE_DAYS,
                compress_after_days=settings.LOG_COMPRESS_AFTER_DAYS,
                max_file_size_mb=settings.LOG_MAX_FILE_SIZE_MB,
                max_backup_count=settings.SECURITY_LOG_MAX_BACKUP_COUNT
            ),
            LogType.BUSINESS: RetentionPolicy(
                log_type=LogType.BUSINESS,
                retention_days=settings.LOG_RETENTION_DAYS,
                archive_days=settings.LOG_ARCHIVE_DAYS,
                compress_after_days=settings.LOG_COMPRESS_AFTER_DAYS,
                max_file_size_mb=settings.LOG_MAX_FILE_SIZE_MB,
                max_backup_count=settings.LOG_MAX_BACKUP_COUNT
            ),
            LogType.ERROR: RetentionPolicy(
                log_type=LogType.ERROR,
                retention_days=settings.LOG_RETENTION_DAYS,
                archive_days=settings.LOG_ARCHIVE_DAYS,
                compress_after_days=settings.LOG_COMPRESS_AFTER_DAYS,
                max_file_size_mb=settings.LOG_MAX_FILE_SIZE_MB,
                max_backup_count=settings.LOG_MAX_BACKUP_COUNT
            )
        }
    
    def __init__(self, log_dir: Path = None):
        if log_dir is None:
            log_dir = Path(settings.LOG_DIR)
        self.log_dir = log_dir
        self.archive_dir = log_dir / "archive"
        self.archive_dir.mkdir(exist_ok=True)
        self.policies = self.DEFAULT_POLICIES.copy()
        self.logger = get_logger(__name__)
    
    def update_retention_policy(self, log_type: LogType, policy: RetentionPolicy):
        """Update retention policy for a specific log type"""
        self.policies[log_type] = policy
        self.logger.info(
            "retention_policy_updated",
            log_type=log_type.value,
            retention_days=policy.retention_days,
            archive_days=policy.archive_days,
            compress_after_days=policy.compress_after_days
        )
    
    async def run_retention_cleanup(self) -> Dict[str, int]:
        """Run complete retention cleanup process"""
        try:
            self.logger.info("retention_cleanup_started")
            
            results = {
                "compressed_files": 0,
                "archived_files": 0,
                "deleted_files": 0,
                "errors": 0
            }
            
            # Process each log type
            for log_type, policy in self.policies.items():
                try:
                    type_results = await self._process_log_type(log_type, policy)
                    for key, value in type_results.items():
                        results[key] += value
                except Exception as e:
                    self.logger.error(
                        "retention_cleanup_error",
                        log_type=log_type.value,
                        error=str(e),
                        exc_info=True
                    )
                    results["errors"] += 1
            
            self.logger.info(
                "retention_cleanup_completed",
                **results
            )
            
            return results
            
        except Exception as e:
            self.logger.error(
                "retention_cleanup_failed",
                error=str(e),
                exc_info=True
            )
            raise
    
    async def _process_log_type(self, log_type: LogType, policy: RetentionPolicy) -> Dict[str, int]:
        """Process retention for a specific log type"""
        results = {
            "compressed_files": 0,
            "archived_files": 0,
            "deleted_files": 0,
            "errors": 0
        }
        
        # Get log files for this type
        log_files = self._get_log_files_by_type(log_type)
        
        now = datetime.now()
        
        for log_file in log_files:
            try:
                file_age_days = (now - datetime.fromtimestamp(log_file.stat().st_mtime)).days
                
                # Delete old files
                if file_age_days > policy.retention_days:
                    await self._delete_log_file(log_file)
                    results["deleted_files"] += 1
                
                # Archive files
                elif file_age_days > policy.archive_days:
                    if await self._archive_log_file(log_file, log_type):
                        results["archived_files"] += 1
                
                # Compress files
                elif file_age_days > policy.compress_after_days and not log_file.name.endswith('.gz'):
                    if await self._compress_log_file(log_file):
                        results["compressed_files"] += 1
                
            except Exception as e:
                self.logger.error(
                    "log_file_processing_error",
                    log_file=str(log_file),
                    error=str(e)
                )
                results["errors"] += 1
        
        return results
    
    def _get_log_files_by_type(self, log_type: LogType) -> List[Path]:
        """Get log files for a specific log type"""
        patterns = {
            LogType.APPLICATION: ["application.log*"],
            LogType.SECURITY: ["security.log*"],
            LogType.BUSINESS: ["business.log*"],
            LogType.ERROR: ["errors.log*", "error.log*"]
        }
        
        log_files = []
        for pattern in patterns.get(log_type, []):
            log_files.extend(self.log_dir.glob(pattern))
        
        # Sort by modification time (oldest first)
        log_files.sort(key=lambda x: x.stat().st_mtime)
        
        return log_files
    
    async def _compress_log_file(self, log_file: Path) -> bool:
        """Compress a log file"""
        try:
            compressed_path = log_file.with_suffix(log_file.suffix + '.gz')
            
            # Don't compress if already compressed or if compressed version exists
            if log_file.suffix == '.gz' or compressed_path.exists():
                return False
            
            # Compress the file
            with open(log_file, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Verify compression was successful
            if compressed_path.exists() and compressed_path.stat().st_size > 0:
                log_file.unlink()  # Remove original file
                self.logger.info(
                    "log_file_compressed",
                    original_file=str(log_file),
                    compressed_file=str(compressed_path),
                    original_size=log_file.stat().st_size,
                    compressed_size=compressed_path.stat().st_size
                )
                return True
            else:
                # Compression failed, remove compressed file if it exists
                if compressed_path.exists():
                    compressed_path.unlink()
                return False
                
        except Exception as e:
            self.logger.error(
                "log_compression_failed",
                log_file=str(log_file),
                error=str(e)
            )
            return False
    
    async def _archive_log_file(self, log_file: Path, log_type: LogType) -> bool:
        """Archive a log file"""
        try:
            # Create archive subdirectory for log type
            type_archive_dir = self.archive_dir / log_type.value
            type_archive_dir.mkdir(exist_ok=True)
            
            # Generate archive filename with timestamp
            timestamp = datetime.fromtimestamp(log_file.stat().st_mtime).strftime('%Y%m%d')
            archive_name = f"{log_file.stem}_{timestamp}{log_file.suffix}"
            archive_path = type_archive_dir / archive_name
            
            # Don't archive if already exists
            if archive_path.exists():
                return False
            
            # Move file to archive
            shutil.move(str(log_file), str(archive_path))
            
            # Compress archived file if not already compressed
            if not archive_path.suffix.endswith('.gz'):
                compressed_archive = archive_path.with_suffix(archive_path.suffix + '.gz')
                with open(archive_path, 'rb') as f_in:
                    with gzip.open(compressed_archive, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                archive_path.unlink()
                archive_path = compressed_archive
            
            self.logger.info(
                "log_file_archived",
                original_file=str(log_file),
                archive_file=str(archive_path),
                log_type=log_type.value
            )
            return True
            
        except Exception as e:
            self.logger.error(
                "log_archival_failed",
                log_file=str(log_file),
                log_type=log_type.value,
                error=str(e)
            )
            return False
    
    async def _delete_log_file(self, log_file: Path) -> bool:
        """Delete an old log file"""
        try:
            file_size = log_file.stat().st_size
            log_file.unlink()
            
            self.logger.info(
                "log_file_deleted",
                log_file=str(log_file),
                file_size=file_size,
                age_days=(datetime.now() - datetime.fromtimestamp(log_file.stat().st_mtime)).days
            )
            return True
            
        except Exception as e:
            self.logger.error(
                "log_deletion_failed",
                log_file=str(log_file),
                error=str(e)
            )
            return False
    
    async def get_retention_status(self) -> Dict[str, any]:
        """Get current retention status and statistics"""
        try:
            status = {
                "policies": {},
                "disk_usage": {},
                "file_counts": {},
                "oldest_files": {},
                "archive_status": {}
            }
            
            total_size = 0
            total_files = 0
            
            for log_type, policy in self.policies.items():
                log_files = self._get_log_files_by_type(log_type)
                
                # Calculate size and count
                type_size = sum(f.stat().st_size for f in log_files)
                type_count = len(log_files)
                
                total_size += type_size
                total_files += type_count
                
                # Find oldest file
                oldest_file = None
                oldest_date = None
                if log_files:
                    oldest_file_path = min(log_files, key=lambda x: x.stat().st_mtime)
                    oldest_file = str(oldest_file_path)
                    oldest_date = datetime.fromtimestamp(oldest_file_path.stat().st_mtime).isoformat()
                
                # Archive statistics
                archive_dir = self.archive_dir / log_type.value
                archive_files = list(archive_dir.glob("*")) if archive_dir.exists() else []
                archive_size = sum(f.stat().st_size for f in archive_files if f.is_file())
                
                status["policies"][log_type.value] = {
                    "retention_days": policy.retention_days,
                    "archive_days": policy.archive_days,
                    "compress_after_days": policy.compress_after_days
                }
                
                status["disk_usage"][log_type.value] = {
                    "size_bytes": type_size,
                    "size_mb": round(type_size / (1024 * 1024), 2)
                }
                
                status["file_counts"][log_type.value] = type_count
                
                status["oldest_files"][log_type.value] = {
                    "file": oldest_file,
                    "date": oldest_date
                }
                
                status["archive_status"][log_type.value] = {
                    "file_count": len(archive_files),
                    "size_bytes": archive_size,
                    "size_mb": round(archive_size / (1024 * 1024), 2)
                }
            
            status["total_disk_usage"] = {
                "size_bytes": total_size,
                "size_mb": round(total_size / (1024 * 1024), 2),
                "size_gb": round(total_size / (1024 * 1024 * 1024), 2)
            }
            
            status["total_file_count"] = total_files
            
            return status
            
        except Exception as e:
            self.logger.error(
                "retention_status_failed",
                error=str(e),
                exc_info=True
            )
            raise
    
    async def cleanup_empty_archives(self) -> int:
        """Clean up empty archive directories"""
        cleaned_count = 0
        
        try:
            for archive_subdir in self.archive_dir.iterdir():
                if archive_subdir.is_dir():
                    # Check if directory is empty
                    if not any(archive_subdir.iterdir()):
                        archive_subdir.rmdir()
                        cleaned_count += 1
                        self.logger.info(
                            "empty_archive_directory_removed",
                            directory=str(archive_subdir)
                        )
            
            return cleaned_count
            
        except Exception as e:
            self.logger.error(
                "archive_cleanup_failed",
                error=str(e),
                exc_info=True
            )
            return cleaned_count


# Global service instance
log_retention_service = LogRetentionService()