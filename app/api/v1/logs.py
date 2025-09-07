"""
Log management API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.security import HTTPBearer
from typing import Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from app.core.auth import get_current_user, require_admin
from app.services.log_aggregation import (
    log_aggregation_service,
    LogSearchQuery,
    LogSearchResult,
    LogEntry,
    LogLevel
)
from app.services.log_retention import log_retention_service, LogType, RetentionPolicy
from app.core.logging import get_logger, SecurityEventType

logger = get_logger(__name__)
router = APIRouter(prefix="/logs", tags=["Log Management"])
security = HTTPBearer()


class LogSearchRequest(BaseModel):
    """Log search request model"""
    start_time: Optional[datetime] = Field(None, description="Start time for log search")
    end_time: Optional[datetime] = Field(None, description="End time for log search")
    level: Optional[LogLevel] = Field(None, description="Log level filter")
    event_type: Optional[str] = Field(None, description="Event type filter")
    user_id: Optional[str] = Field(None, description="User ID filter")
    request_id: Optional[str] = Field(None, description="Request ID filter")
    client_ip: Optional[str] = Field(None, description="Client IP filter")
    search_text: Optional[str] = Field(None, description="Text search in log messages")
    limit: int = Field(100, ge=1, le=1000, description="Maximum number of results")
    offset: int = Field(0, ge=0, description="Offset for pagination")
    sort_order: str = Field("desc", pattern="^(asc|desc)$", description="Sort order")


class LogEntryResponse(BaseModel):
    """Log entry response model"""
    timestamp: datetime
    level: str
    logger: str
    message: str
    service: str
    version: str
    environment: str
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    client_ip: Optional[str] = None
    event_type: Optional[str] = None
    category: Optional[str] = None
    error_type: Optional[str] = None
    exception: Optional[str] = None
    extra_fields: Optional[dict] = None


class LogSearchResponse(BaseModel):
    """Log search response model"""
    entries: List[LogEntryResponse]
    total_count: int
    limit: int
    offset: int
    execution_time_ms: int


class LogStatisticsResponse(BaseModel):
    """Log statistics response model"""
    total_entries: int
    time_period: dict
    level_distribution: dict
    event_type_distribution: dict
    error_distribution: dict
    top_users: dict
    top_ips: dict


@router.post("/search", response_model=LogSearchResponse)
async def search_logs(
    search_request: LogSearchRequest,
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_admin)
):
    """
    Search logs with various filters
    
    Requires admin role for access to log data.
    """
    try:
        # Log the search request for audit purposes
        logger.security_event(
            SecurityEventType.DATA_ACCESS,
            user_id=current_user.get("user_id"),
            action="log_search",
            search_params=search_request.dict(exclude_none=True)
        )
        
        # Convert request to query object
        query = LogSearchQuery(
            start_time=search_request.start_time,
            end_time=search_request.end_time,
            level=search_request.level,
            event_type=search_request.event_type,
            user_id=search_request.user_id,
            request_id=search_request.request_id,
            client_ip=search_request.client_ip,
            search_text=search_request.search_text,
            limit=search_request.limit,
            offset=search_request.offset,
            sort_order=search_request.sort_order
        )
        
        # Perform search
        result = await log_aggregation_service.search_logs(query)
        
        # Convert entries to response format
        entries = [
            LogEntryResponse(
                timestamp=entry.timestamp,
                level=entry.level,
                logger=entry.logger,
                message=entry.message,
                service=entry.service,
                version=entry.version,
                environment=entry.environment,
                request_id=entry.request_id,
                user_id=entry.user_id,
                client_ip=entry.client_ip,
                event_type=entry.event_type,
                category=entry.category,
                error_type=entry.error_type,
                exception=entry.exception,
                extra_fields=entry.extra_fields
            )
            for entry in result.entries
        ]
        
        return LogSearchResponse(
            entries=entries,
            total_count=result.total_count,
            limit=search_request.limit,
            offset=search_request.offset,
            execution_time_ms=result.execution_time_ms
        )
        
    except Exception as e:
        logger.error(
            "log_search_api_error",
            user_id=current_user.get("user_id"),
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to search logs"
        )


@router.get("/statistics", response_model=LogStatisticsResponse)
async def get_log_statistics(
    start_time: Optional[datetime] = Query(None, description="Start time for statistics"),
    end_time: Optional[datetime] = Query(None, description="End time for statistics"),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_admin)
):
    """
    Get log statistics for a time period
    
    Requires admin role for access to log statistics.
    """
    try:
        # Default to last 24 hours if no time range specified
        if not start_time:
            start_time = datetime.utcnow() - timedelta(hours=24)
        if not end_time:
            end_time = datetime.utcnow()
        
        # Log the statistics request
        logger.security_event(
            SecurityEventType.DATA_ACCESS,
            user_id=current_user.get("user_id"),
            action="log_statistics",
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat()
        )
        
        # Get statistics
        stats = await log_aggregation_service.get_log_statistics(start_time, end_time)
        
        return LogStatisticsResponse(**stats)
        
    except Exception as e:
        logger.error(
            "log_statistics_api_error",
            user_id=current_user.get("user_id"),
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to get log statistics"
        )


@router.post("/export")
async def export_logs(
    search_request: LogSearchRequest,
    format: str = Query("json", pattern="^(json|csv)$", description="Export format"),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_admin)
):
    """
    Export logs matching search criteria
    
    Requires admin role for log export functionality.
    """
    try:
        # Log the export request
        logger.security_event(
            SecurityEventType.DATA_ACCESS,
            user_id=current_user.get("user_id"),
            action="log_export",
            format=format,
            search_params=search_request.dict(exclude_none=True)
        )
        
        # Convert request to query object
        query = LogSearchQuery(
            start_time=search_request.start_time,
            end_time=search_request.end_time,
            level=search_request.level,
            event_type=search_request.event_type,
            user_id=search_request.user_id,
            request_id=search_request.request_id,
            client_ip=search_request.client_ip,
            search_text=search_request.search_text,
            limit=min(search_request.limit, 10000),  # Cap export limit
            offset=search_request.offset,
            sort_order=search_request.sort_order
        )
        
        # Export logs
        export_data = await log_aggregation_service.export_logs(query, format)
        
        # Set appropriate content type and filename
        if format == "json":
            media_type = "application/json"
            filename = f"logs_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        else:  # csv
            media_type = "text/csv"
            filename = f"logs_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return Response(
            content=export_data,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(
            "log_export_api_error",
            user_id=current_user.get("user_id"),
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to export logs"
        )


@router.get("/recent-errors")
async def get_recent_errors(
    hours: int = Query(24, ge=1, le=168, description="Hours to look back"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of errors"),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_admin)
):
    """
    Get recent error logs for monitoring
    
    Requires admin role for error log access.
    """
    try:
        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        # Search for error logs
        query = LogSearchQuery(
            start_time=start_time,
            end_time=end_time,
            level=LogLevel.ERROR,
            limit=limit,
            sort_order="desc"
        )
        
        result = await log_aggregation_service.search_logs(query)
        
        # Convert to response format
        errors = [
            {
                "timestamp": entry.timestamp.isoformat(),
                "message": entry.message,
                "logger": entry.logger,
                "error_type": entry.error_type,
                "request_id": entry.request_id,
                "user_id": entry.user_id,
                "exception": entry.exception
            }
            for entry in result.entries
        ]
        
        return {
            "errors": errors,
            "total_count": result.total_count,
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "hours": hours
            }
        }
        
    except Exception as e:
        logger.error(
            "recent_errors_api_error",
            user_id=current_user.get("user_id"),
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to get recent errors"
        )


@router.get("/security-events")
async def get_security_events(
    hours: int = Query(24, ge=1, le=168, description="Hours to look back"),
    event_type: Optional[str] = Query(None, description="Specific security event type"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of events"),
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_admin)
):
    """
    Get recent security events for monitoring
    
    Requires admin role for security event access.
    """
    try:
        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        # Search for security events
        query = LogSearchQuery(
            start_time=start_time,
            end_time=end_time,
            event_type=event_type,
            limit=limit,
            sort_order="desc"
        )
        
        result = await log_aggregation_service.search_logs(query)
        
        # Filter for security category events
        security_events = [
            entry for entry in result.entries
            if entry.category == "security"
        ]
        
        # Convert to response format
        events = [
            {
                "timestamp": entry.timestamp.isoformat(),
                "event_type": entry.event_type,
                "message": entry.message,
                "user_id": entry.user_id,
                "client_ip": entry.client_ip,
                "request_id": entry.request_id,
                "extra_fields": entry.extra_fields
            }
            for entry in security_events
        ]
        
        return {
            "events": events,
            "total_count": len(security_events),
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "hours": hours
            },
            "event_type_filter": event_type
        }
        
    except Exception as e:
        logger.error(
            "security_events_api_error",
            user_id=current_user.get("user_id"),
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to get security events"
        )


class RetentionPolicyRequest(BaseModel):
    """Retention policy update request"""
    log_type: LogType
    retention_days: int = Field(ge=1, le=3650, description="Days to retain logs")
    archive_days: int = Field(ge=1, le=365, description="Days before archiving")
    compress_after_days: int = Field(ge=1, le=30, description="Days before compression")
    max_file_size_mb: int = Field(ge=1, le=1000, description="Maximum file size in MB")
    max_backup_count: int = Field(ge=1, le=100, description="Maximum backup files")


@router.post("/retention/cleanup")
async def run_retention_cleanup(
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_admin)
):
    """
    Run log retention cleanup process
    
    Requires admin role for log retention management.
    """
    try:
        # Log the cleanup request
        logger.security_event(
            SecurityEventType.ADMIN_ACTION,
            user_id=current_user.get("user_id"),
            action="log_retention_cleanup"
        )
        
        # Run cleanup
        results = await log_retention_service.run_retention_cleanup()
        
        return {
            "status": "completed",
            "results": results,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(
            "retention_cleanup_api_error",
            user_id=current_user.get("user_id"),
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to run retention cleanup"
        )


@router.get("/retention/status")
async def get_retention_status(
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_admin)
):
    """
    Get current log retention status and statistics
    
    Requires admin role for retention status access.
    """
    try:
        status = await log_retention_service.get_retention_status()
        return status
        
    except Exception as e:
        logger.error(
            "retention_status_api_error",
            user_id=current_user.get("user_id"),
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to get retention status"
        )


@router.put("/retention/policy")
async def update_retention_policy(
    policy_request: RetentionPolicyRequest,
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_admin)
):
    """
    Update retention policy for a log type
    
    Requires admin role for retention policy management.
    """
    try:
        # Validate policy
        if policy_request.archive_days >= policy_request.retention_days:
            raise HTTPException(
                status_code=400,
                detail="Archive days must be less than retention days"
            )
        
        if policy_request.compress_after_days >= policy_request.archive_days:
            raise HTTPException(
                status_code=400,
                detail="Compress after days must be less than archive days"
            )
        
        # Log the policy update
        logger.security_event(
            SecurityEventType.ADMIN_ACTION,
            user_id=current_user.get("user_id"),
            action="retention_policy_update",
            log_type=policy_request.log_type.value,
            retention_days=policy_request.retention_days,
            archive_days=policy_request.archive_days
        )
        
        # Create and update policy
        policy = RetentionPolicy(
            log_type=policy_request.log_type,
            retention_days=policy_request.retention_days,
            archive_days=policy_request.archive_days,
            compress_after_days=policy_request.compress_after_days,
            max_file_size_mb=policy_request.max_file_size_mb,
            max_backup_count=policy_request.max_backup_count
        )
        
        log_retention_service.update_retention_policy(policy_request.log_type, policy)
        
        return {
            "status": "updated",
            "log_type": policy_request.log_type.value,
            "policy": {
                "retention_days": policy.retention_days,
                "archive_days": policy.archive_days,
                "compress_after_days": policy.compress_after_days,
                "max_file_size_mb": policy.max_file_size_mb,
                "max_backup_count": policy.max_backup_count
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "retention_policy_update_error",
            user_id=current_user.get("user_id"),
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to update retention policy"
        )


@router.delete("/retention/archives/cleanup")
async def cleanup_empty_archives(
    current_user: dict = Depends(get_current_user),
    _: dict = Depends(require_admin)
):
    """
    Clean up empty archive directories
    
    Requires admin role for archive management.
    """
    try:
        # Log the cleanup request
        logger.security_event(
            SecurityEventType.ADMIN_ACTION,
            user_id=current_user.get("user_id"),
            action="archive_cleanup"
        )
        
        # Clean up empty archives
        cleaned_count = await log_retention_service.cleanup_empty_archives()
        
        return {
            "status": "completed",
            "cleaned_directories": cleaned_count,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(
            "archive_cleanup_api_error",
            user_id=current_user.get("user_id"),
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to cleanup archives"
        )