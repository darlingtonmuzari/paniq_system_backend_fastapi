"""
Background tasks for log maintenance and retention
"""
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any

from app.core.logging import get_logger
from app.services.log_retention import log_retention_service
from app.core.celery import celery_app

logger = get_logger(__name__)


@celery_app.task(name="log_retention_cleanup")
def run_log_retention_cleanup() -> Dict[str, Any]:
    """
    Celery task for automated log retention cleanup
    
    This task should be scheduled to run daily to maintain log storage.
    """
    try:
        logger.info("automated_log_retention_started")
        
        # Run the async cleanup in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            results = loop.run_until_complete(log_retention_service.run_retention_cleanup())
            
            logger.info(
                "automated_log_retention_completed",
                **results
            )
            
            return {
                "status": "success",
                "timestamp": datetime.utcnow().isoformat(),
                "results": results
            }
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(
            "automated_log_retention_failed",
            error=str(e),
            exc_info=True
        )
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


@celery_app.task(name="log_archive_cleanup")
def run_log_archive_cleanup() -> Dict[str, Any]:
    """
    Celery task for cleaning up empty archive directories
    
    This task should be scheduled to run weekly.
    """
    try:
        logger.info("automated_archive_cleanup_started")
        
        # Run the async cleanup in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            cleaned_count = loop.run_until_complete(log_retention_service.cleanup_empty_archives())
            
            logger.info(
                "automated_archive_cleanup_completed",
                cleaned_directories=cleaned_count
            )
            
            return {
                "status": "success",
                "timestamp": datetime.utcnow().isoformat(),
                "cleaned_directories": cleaned_count
            }
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(
            "automated_archive_cleanup_failed",
            error=str(e),
            exc_info=True
        )
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


@celery_app.task(name="log_health_check")
def run_log_health_check() -> Dict[str, Any]:
    """
    Celery task for checking log system health
    
    This task should be scheduled to run hourly to monitor log system health.
    """
    try:
        logger.info("log_health_check_started")
        
        # Run the async health check in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            status = loop.run_until_complete(log_retention_service.get_retention_status())
            
            # Check for potential issues
            issues = []
            warnings = []
            
            # Check total disk usage
            total_size_gb = status["total_disk_usage"]["size_gb"]
            if total_size_gb > 10:  # More than 10GB
                warnings.append(f"High disk usage: {total_size_gb:.2f} GB")
            if total_size_gb > 50:  # More than 50GB
                issues.append(f"Very high disk usage: {total_size_gb:.2f} GB")
            
            # Check for very old files
            for log_type, oldest_info in status["oldest_files"].items():
                if oldest_info["date"]:
                    oldest_date = datetime.fromisoformat(oldest_info["date"])
                    age_days = (datetime.now() - oldest_date.replace(tzinfo=None)).days
                    
                    if age_days > 365:  # Older than 1 year
                        issues.append(f"Very old {log_type} logs: {age_days} days old")
                    elif age_days > 180:  # Older than 6 months
                        warnings.append(f"Old {log_type} logs: {age_days} days old")
            
            # Check file counts
            if status["total_file_count"] > 1000:
                warnings.append(f"High file count: {status['total_file_count']} files")
            if status["total_file_count"] > 5000:
                issues.append(f"Very high file count: {status['total_file_count']} files")
            
            health_status = "healthy"
            if issues:
                health_status = "critical"
            elif warnings:
                health_status = "warning"
            
            result = {
                "status": "success",
                "timestamp": datetime.utcnow().isoformat(),
                "health_status": health_status,
                "issues": issues,
                "warnings": warnings,
                "disk_usage_gb": total_size_gb,
                "total_files": status["total_file_count"]
            }
            
            # Log health status
            if health_status == "critical":
                logger.error(
                    "log_system_health_critical",
                    issues=issues,
                    warnings=warnings,
                    disk_usage_gb=total_size_gb
                )
            elif health_status == "warning":
                logger.warning(
                    "log_system_health_warning",
                    warnings=warnings,
                    disk_usage_gb=total_size_gb
                )
            else:
                logger.info(
                    "log_system_health_good",
                    disk_usage_gb=total_size_gb,
                    total_files=status["total_file_count"]
                )
            
            return result
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(
            "log_health_check_failed",
            error=str(e),
            exc_info=True
        )
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


# Schedule configuration for Celery Beat
# Add this to your celery beat schedule configuration
CELERY_BEAT_SCHEDULE = {
    'log-retention-cleanup': {
        'task': 'log_retention_cleanup',
        'schedule': 86400.0,  # Run daily (24 hours)
        'options': {'queue': 'maintenance'}
    },
    'log-archive-cleanup': {
        'task': 'log_archive_cleanup',
        'schedule': 604800.0,  # Run weekly (7 days)
        'options': {'queue': 'maintenance'}
    },
    'log-health-check': {
        'task': 'log_health_check',
        'schedule': 3600.0,  # Run hourly
        'options': {'queue': 'monitoring'}
    }
}