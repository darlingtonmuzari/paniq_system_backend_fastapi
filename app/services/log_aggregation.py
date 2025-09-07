"""
Log aggregation and search service for the Panic System Platform
"""
import json
import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import re
import gzip

from app.core.logging import get_logger, LogLevel, SecurityEventType, BusinessEventType

logger = get_logger(__name__)


class LogSearchFilter(str, Enum):
    """Available log search filters"""
    LEVEL = "level"
    EVENT_TYPE = "event_type"
    USER_ID = "user_id"
    REQUEST_ID = "request_id"
    CLIENT_IP = "client_ip"
    SERVICE = "service"
    TIMESTAMP = "timestamp"
    MESSAGE = "message"
    ERROR_TYPE = "error_type"


@dataclass
class LogSearchQuery:
    """Log search query parameters"""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    level: Optional[LogLevel] = None
    event_type: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    client_ip: Optional[str] = None
    search_text: Optional[str] = None
    limit: int = 100
    offset: int = 0
    sort_order: str = "desc"  # desc or asc


@dataclass
class LogEntry:
    """Structured log entry"""
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
    extra_fields: Optional[Dict[str, Any]] = None


@dataclass
class LogSearchResult:
    """Log search result"""
    entries: List[LogEntry]
    total_count: int
    query: LogSearchQuery
    execution_time_ms: int


class LogAggregationService:
    """Service for log aggregation and search capabilities"""
    
    def __init__(self, log_dir: Path = Path("logs")):
        self.log_dir = log_dir
        self.logger = get_logger(__name__)
    
    async def search_logs(self, query: LogSearchQuery) -> LogSearchResult:
        """Search logs based on query parameters"""
        start_time = datetime.now()
        
        try:
            # Get relevant log files
            log_files = await self._get_relevant_log_files(query)
            
            # Search through log files
            entries = []
            total_count = 0
            
            for log_file in log_files:
                file_entries, file_count = await self._search_log_file(log_file, query)
                entries.extend(file_entries)
                total_count += file_count
            
            # Sort entries by timestamp
            entries.sort(
                key=lambda x: x.timestamp,
                reverse=(query.sort_order == "desc")
            )
            
            # Apply pagination
            paginated_entries = entries[query.offset:query.offset + query.limit]
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            self.logger.info(
                "log_search_completed",
                query_params=query.__dict__,
                results_count=len(paginated_entries),
                total_count=total_count,
                execution_time_ms=execution_time
            )
            
            return LogSearchResult(
                entries=paginated_entries,
                total_count=total_count,
                query=query,
                execution_time_ms=int(execution_time)
            )
            
        except Exception as e:
            self.logger.error(
                "log_search_failed",
                query_params=query.__dict__,
                error=str(e),
                exc_info=True
            )
            raise
    
    async def _get_relevant_log_files(self, query: LogSearchQuery) -> List[Path]:
        """Get log files relevant to the search query"""
        log_files = []
        
        # Determine which log files to search based on query
        if query.event_type and query.event_type in [e.value for e in SecurityEventType]:
            log_files.extend(self.log_dir.glob("security.log*"))
        elif query.event_type and query.event_type in [e.value for e in BusinessEventType]:
            log_files.extend(self.log_dir.glob("business.log*"))
        elif query.level and query.level in [LogLevel.ERROR, LogLevel.CRITICAL]:
            log_files.extend(self.log_dir.glob("errors.log*"))
        else:
            # Search all application logs
            log_files.extend(self.log_dir.glob("application.log*"))
            log_files.extend(self.log_dir.glob("security.log*"))
            log_files.extend(self.log_dir.glob("business.log*"))
            log_files.extend(self.log_dir.glob("errors.log*"))
        
        # Filter by date if specified
        if query.start_time or query.end_time:
            filtered_files = []
            for log_file in log_files:
                file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                if query.start_time and file_time < query.start_time:
                    continue
                if query.end_time and file_time > query.end_time + timedelta(days=1):
                    continue
                filtered_files.append(log_file)
            log_files = filtered_files
        
        # Sort by modification time (newest first)
        log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        return log_files
    
    async def _search_log_file(self, log_file: Path, query: LogSearchQuery) -> tuple[List[LogEntry], int]:
        """Search a single log file"""
        entries = []
        total_count = 0
        
        try:
            # Handle compressed files
            if log_file.suffix == '.gz':
                file_opener = gzip.open
                mode = 'rt'
            else:
                file_opener = open
                mode = 'r'
            
            with file_opener(log_file, mode, encoding='utf-8') as f:
                for line in f:
                    try:
                        # Parse JSON log entry
                        log_data = json.loads(line.strip())
                        entry = self._parse_log_entry(log_data)
                        
                        # Apply filters
                        if self._matches_query(entry, query):
                            total_count += 1
                            # Only add to results if within pagination range
                            if len(entries) < query.limit + query.offset:
                                entries.append(entry)
                    
                    except (json.JSONDecodeError, KeyError) as e:
                        # Skip malformed log entries
                        continue
        
        except Exception as e:
            self.logger.error(
                "log_file_search_error",
                log_file=str(log_file),
                error=str(e)
            )
        
        return entries, total_count
    
    def _parse_log_entry(self, log_data: Dict[str, Any]) -> LogEntry:
        """Parse log data into LogEntry object"""
        # Parse timestamp
        timestamp_str = log_data.get('timestamp', '')
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except ValueError:
            timestamp = datetime.now(timezone.utc)
        
        # Extract extra fields
        extra_fields = {}
        standard_fields = {
            'timestamp', 'level', 'logger', 'message', 'service', 'version',
            'environment', 'request_id', 'user_id', 'client_ip', 'event_type',
            'category', 'error_type', 'exception'
        }
        
        for key, value in log_data.items():
            if key not in standard_fields:
                extra_fields[key] = value
        
        return LogEntry(
            timestamp=timestamp,
            level=log_data.get('level', ''),
            logger=log_data.get('logger', ''),
            message=log_data.get('message', ''),
            service=log_data.get('service', ''),
            version=log_data.get('version', ''),
            environment=log_data.get('environment', ''),
            request_id=log_data.get('request_id'),
            user_id=log_data.get('user_id'),
            client_ip=log_data.get('client_ip'),
            event_type=log_data.get('event_type'),
            category=log_data.get('category'),
            error_type=log_data.get('error_type'),
            exception=log_data.get('exception'),
            extra_fields=extra_fields if extra_fields else None
        )
    
    def _matches_query(self, entry: LogEntry, query: LogSearchQuery) -> bool:
        """Check if log entry matches search query"""
        # Time range filter
        if query.start_time and entry.timestamp < query.start_time:
            return False
        if query.end_time and entry.timestamp > query.end_time:
            return False
        
        # Level filter
        if query.level and entry.level != query.level.value:
            return False
        
        # Event type filter
        if query.event_type and entry.event_type != query.event_type:
            return False
        
        # User ID filter
        if query.user_id and entry.user_id != query.user_id:
            return False
        
        # Request ID filter
        if query.request_id and entry.request_id != query.request_id:
            return False
        
        # Client IP filter
        if query.client_ip and entry.client_ip != query.client_ip:
            return False
        
        # Text search filter
        if query.search_text:
            search_text = query.search_text.lower()
            searchable_text = f"{entry.message} {entry.logger} {entry.exception or ''}".lower()
            if entry.extra_fields:
                searchable_text += " " + " ".join(str(v) for v in entry.extra_fields.values()).lower()
            
            if search_text not in searchable_text:
                return False
        
        return True
    
    async def get_log_statistics(self, start_time: datetime, end_time: datetime) -> Dict[str, Any]:
        """Get log statistics for a time period"""
        try:
            query = LogSearchQuery(
                start_time=start_time,
                end_time=end_time,
                limit=10000  # Large limit to get all entries for stats
            )
            
            result = await self.search_logs(query)
            
            # Calculate statistics
            stats = {
                'total_entries': result.total_count,
                'time_period': {
                    'start': start_time.isoformat(),
                    'end': end_time.isoformat()
                },
                'level_distribution': {},
                'event_type_distribution': {},
                'error_distribution': {},
                'top_users': {},
                'top_ips': {}
            }
            
            # Analyze entries
            for entry in result.entries:
                # Level distribution
                level = entry.level
                stats['level_distribution'][level] = stats['level_distribution'].get(level, 0) + 1
                
                # Event type distribution
                if entry.event_type:
                    event_type = entry.event_type
                    stats['event_type_distribution'][event_type] = stats['event_type_distribution'].get(event_type, 0) + 1
                
                # Error distribution
                if entry.error_type:
                    error_type = entry.error_type
                    stats['error_distribution'][error_type] = stats['error_distribution'].get(error_type, 0) + 1
                
                # User activity
                if entry.user_id:
                    user_id = entry.user_id
                    stats['top_users'][user_id] = stats['top_users'].get(user_id, 0) + 1
                
                # IP activity
                if entry.client_ip:
                    client_ip = entry.client_ip
                    stats['top_ips'][client_ip] = stats['top_ips'].get(client_ip, 0) + 1
            
            # Sort top lists
            stats['top_users'] = dict(sorted(stats['top_users'].items(), key=lambda x: x[1], reverse=True)[:10])
            stats['top_ips'] = dict(sorted(stats['top_ips'].items(), key=lambda x: x[1], reverse=True)[:10])
            
            self.logger.info(
                "log_statistics_generated",
                time_period=f"{start_time} to {end_time}",
                total_entries=stats['total_entries']
            )
            
            return stats
            
        except Exception as e:
            self.logger.error(
                "log_statistics_failed",
                start_time=start_time.isoformat(),
                end_time=end_time.isoformat(),
                error=str(e),
                exc_info=True
            )
            raise
    
    async def export_logs(self, query: LogSearchQuery, format: str = "json") -> str:
        """Export logs matching query to specified format"""
        try:
            result = await self.search_logs(query)
            
            if format.lower() == "json":
                return self._export_to_json(result.entries)
            elif format.lower() == "csv":
                return self._export_to_csv(result.entries)
            else:
                raise ValueError(f"Unsupported export format: {format}")
                
        except Exception as e:
            self.logger.error(
                "log_export_failed",
                query_params=query.__dict__,
                format=format,
                error=str(e),
                exc_info=True
            )
            raise
    
    def _export_to_json(self, entries: List[LogEntry]) -> str:
        """Export log entries to JSON format"""
        export_data = []
        for entry in entries:
            entry_dict = {
                'timestamp': entry.timestamp.isoformat(),
                'level': entry.level,
                'logger': entry.logger,
                'message': entry.message,
                'service': entry.service,
                'version': entry.version,
                'environment': entry.environment
            }
            
            # Add optional fields
            if entry.request_id:
                entry_dict['request_id'] = entry.request_id
            if entry.user_id:
                entry_dict['user_id'] = entry.user_id
            if entry.client_ip:
                entry_dict['client_ip'] = entry.client_ip
            if entry.event_type:
                entry_dict['event_type'] = entry.event_type
            if entry.category:
                entry_dict['category'] = entry.category
            if entry.error_type:
                entry_dict['error_type'] = entry.error_type
            if entry.exception:
                entry_dict['exception'] = entry.exception
            if entry.extra_fields:
                entry_dict.update(entry.extra_fields)
            
            export_data.append(entry_dict)
        
        return json.dumps(export_data, indent=2, default=str)
    
    def _export_to_csv(self, entries: List[LogEntry]) -> str:
        """Export log entries to CSV format"""
        import csv
        import io
        
        output = io.StringIO()
        
        if not entries:
            return ""
        
        # Determine all possible fields
        all_fields = set(['timestamp', 'level', 'logger', 'message', 'service', 'version', 'environment'])
        for entry in entries:
            if entry.request_id:
                all_fields.add('request_id')
            if entry.user_id:
                all_fields.add('user_id')
            if entry.client_ip:
                all_fields.add('client_ip')
            if entry.event_type:
                all_fields.add('event_type')
            if entry.category:
                all_fields.add('category')
            if entry.error_type:
                all_fields.add('error_type')
            if entry.exception:
                all_fields.add('exception')
            if entry.extra_fields:
                all_fields.update(entry.extra_fields.keys())
        
        fieldnames = sorted(all_fields)
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for entry in entries:
            row = {
                'timestamp': entry.timestamp.isoformat(),
                'level': entry.level,
                'logger': entry.logger,
                'message': entry.message,
                'service': entry.service,
                'version': entry.version,
                'environment': entry.environment
            }
            
            # Add optional fields
            if entry.request_id:
                row['request_id'] = entry.request_id
            if entry.user_id:
                row['user_id'] = entry.user_id
            if entry.client_ip:
                row['client_ip'] = entry.client_ip
            if entry.event_type:
                row['event_type'] = entry.event_type
            if entry.category:
                row['category'] = entry.category
            if entry.error_type:
                row['error_type'] = entry.error_type
            if entry.exception:
                row['exception'] = entry.exception
            if entry.extra_fields:
                row.update(entry.extra_fields)
            
            writer.writerow(row)
        
        return output.getvalue()


# Global service instance
log_aggregation_service = LogAggregationService()