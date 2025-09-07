"""
Structured logging configuration and utilities for the Panic System Platform
"""
import structlog
import logging
import logging.handlers
import json
import sys
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union
from pathlib import Path
from enum import Enum

from app.core.config import settings


class LogLevel(str, Enum):
    """Log levels for structured logging"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class SecurityEventType(str, Enum):
    """Security event types for audit logging"""
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_UNLOCKED = "account_unlocked"
    ATTESTATION_FAILURE = "attestation_failure"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    PERMISSION_DENIED = "permission_denied"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    ADMIN_ACTION = "admin_action"
    PASSWORD_RESET = "password_reset"
    OTP_GENERATED = "otp_generated"
    OTP_VERIFIED = "otp_verified"
    TOKEN_ISSUED = "token_issued"
    TOKEN_REVOKED = "token_revoked"


class BusinessEventType(str, Enum):
    """Business event types for operational logging"""
    PANIC_REQUEST_SUBMITTED = "panic_request_submitted"
    PANIC_REQUEST_ALLOCATED = "panic_request_allocated"
    PANIC_REQUEST_ACCEPTED = "panic_request_accepted"
    PANIC_REQUEST_COMPLETED = "panic_request_completed"
    SUBSCRIPTION_PURCHASED = "subscription_purchased"
    SUBSCRIPTION_APPLIED = "subscription_applied"
    CREDIT_PURCHASED = "credit_purchased"
    FINE_APPLIED = "fine_applied"
    USER_BANNED = "user_banned"
    FIRM_REGISTERED = "firm_registered"
    FIRM_APPROVED = "firm_approved"
    PRANK_DETECTED = "prank_detected"


def add_request_context(logger, method_name, event_dict):
    """Add request context to log entries"""
    # Try to get request context from contextvars or thread local
    try:
        import contextvars
        request_id = contextvars.copy_context().get('request_id', None)
        user_id = contextvars.copy_context().get('user_id', None)
        
        if request_id:
            event_dict['request_id'] = request_id
        if user_id:
            event_dict['user_id'] = user_id
    except:
        pass
    
    return event_dict


def add_timestamp(logger, method_name, event_dict):
    """Add ISO timestamp to log entries"""
    event_dict['timestamp'] = datetime.now(timezone.utc).isoformat()
    return event_dict


def add_service_context(logger, method_name, event_dict):
    """Add service context to log entries"""
    event_dict['service'] = 'panic-system-platform'
    event_dict['version'] = '1.0.0'
    event_dict['environment'] = 'development' if settings.DEBUG else 'production'
    return event_dict


def filter_sensitive_data(logger, method_name, event_dict):
    """Filter sensitive data from log entries"""
    sensitive_keys = {
        'password', 'token', 'secret', 'key', 'authorization',
        'credit_card', 'ssn', 'phone', 'email', 'address'
    }
    
    def _filter_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        filtered = {}
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                if key.lower() in ['phone', 'email']:
                    # Partially mask phone and email
                    if isinstance(value, str):
                        if '@' in value:  # Email
                            parts = value.split('@')
                            filtered[key] = f"{parts[0][:2]}***@{parts[1]}"
                        elif len(value) >= 4:  # Phone
                            filtered[key] = f"***{value[-4:]}"
                        else:
                            filtered[key] = "***"
                    else:
                        filtered[key] = "***"
                else:
                    filtered[key] = "***"
            elif isinstance(value, dict):
                filtered[key] = _filter_dict(value)
            elif isinstance(value, list):
                filtered[key] = [_filter_dict(item) if isinstance(item, dict) else item for item in value]
            else:
                filtered[key] = value
        return filtered
    
    # Filter the event_dict itself
    return _filter_dict(event_dict)


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            'level': record.levelname.lower(),
            'logger': record.name,
            'message': record.getMessage(),
            'service': 'panic-system-platform',
            'version': '1.0.0',
            'environment': 'development' if settings.DEBUG else 'production'
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'lineno', 'funcName', 'created',
                          'msecs', 'relativeCreated', 'thread', 'threadName',
                          'processName', 'process', 'getMessage', 'exc_info',
                          'exc_text', 'stack_info']:
                log_entry[key] = value
        
        return json.dumps(log_entry)


def setup_logging():
    """Configure structured logging for the application"""
    
    # Create logs directory
    log_dir = Path(settings.LOG_DIR)
    log_dir.mkdir(exist_ok=True)
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            add_service_context,
            add_request_context,
            add_timestamp,
            filter_sensitive_data,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.DEBUG if settings.DEBUG else logging.INFO
        ),
        logger_factory=structlog.WriteLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )
    
    # Suppress verbose AWS/boto3 debug logging to improve performance
    logging.getLogger('botocore').setLevel(logging.WARNING)
    logging.getLogger('boto3').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('s3transfer').setLevel(logging.WARNING)
    
    # Suppress other noisy third-party loggers
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)
    
    # Create file handlers for different log types
    
    # Application logs
    app_handler = logging.handlers.RotatingFileHandler(
        log_dir / "application.log",
        maxBytes=settings.LOG_MAX_FILE_SIZE_MB * 1024 * 1024,
        backupCount=settings.LOG_MAX_BACKUP_COUNT
    )
    app_handler.setFormatter(JSONFormatter())
    
    # Security logs
    security_handler = logging.handlers.RotatingFileHandler(
        log_dir / "security.log",
        maxBytes=settings.LOG_MAX_FILE_SIZE_MB * 1024 * 1024,
        backupCount=settings.SECURITY_LOG_MAX_BACKUP_COUNT
    )
    security_handler.setFormatter(JSONFormatter())
    
    # Business logs
    business_handler = logging.handlers.RotatingFileHandler(
        log_dir / "business.log",
        maxBytes=settings.LOG_MAX_FILE_SIZE_MB * 1024 * 1024,
        backupCount=settings.LOG_MAX_BACKUP_COUNT
    )
    business_handler.setFormatter(JSONFormatter())
    
    # Error logs
    error_handler = logging.handlers.RotatingFileHandler(
        log_dir / "errors.log",
        maxBytes=settings.LOG_MAX_FILE_SIZE_MB * 1024 * 1024,
        backupCount=settings.LOG_MAX_BACKUP_COUNT
    )
    error_handler.setFormatter(JSONFormatter())
    error_handler.setLevel(logging.ERROR)
    
    # Add handlers to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(app_handler)
    root_logger.addHandler(security_handler)
    root_logger.addHandler(business_handler)
    root_logger.addHandler(error_handler)
    
    # Configure specific loggers
    
    # Security logger
    security_logger = logging.getLogger("security")
    security_logger.addHandler(security_handler)
    security_logger.setLevel(logging.INFO)
    
    # Business logger
    business_logger = logging.getLogger("business")
    business_logger.addHandler(business_handler)
    business_logger.setLevel(logging.INFO)
    
    # Disable propagation to avoid duplicate logs
    security_logger.propagate = False
    business_logger.propagate = False


class StructuredLogger:
    """Enhanced structured logger with context management"""
    
    def __init__(self, name: str = None):
        self.logger = structlog.get_logger(name)
        self._context = {}
    
    def bind(self, **kwargs) -> 'StructuredLogger':
        """Bind context to logger"""
        new_logger = StructuredLogger()
        new_logger.logger = self.logger.bind(**kwargs)
        new_logger._context = {**self._context, **kwargs}
        return new_logger
    
    def with_context(self, **kwargs) -> 'StructuredLogger':
        """Add context to logger (alias for bind)"""
        return self.bind(**kwargs)
    
    def debug(self, event: str, **kwargs):
        """Log debug message"""
        self.logger.debug(event, **kwargs)
    
    def info(self, event: str, **kwargs):
        """Log info message"""
        self.logger.info(event, **kwargs)
    
    def warning(self, event: str, **kwargs):
        """Log warning message"""
        self.logger.warning(event, **kwargs)
    
    def error(self, event: str, **kwargs):
        """Log error message"""
        self.logger.error(event, **kwargs)
    
    def critical(self, event: str, **kwargs):
        """Log critical message"""
        self.logger.critical(event, **kwargs)
    
    def security_event(self, event_type: SecurityEventType, **kwargs):
        """Log security event"""
        security_logger = logging.getLogger("security")
        security_logger.info(
            json.dumps({
                'event_type': event_type.value,
                'category': 'security',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                **kwargs
            })
        )
    
    def business_event(self, event_type: BusinessEventType, **kwargs):
        """Log business event"""
        business_logger = logging.getLogger("business")
        business_logger.info(
            json.dumps({
                'event_type': event_type.value,
                'category': 'business',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                **kwargs
            })
        )


def get_logger(name: str = None) -> StructuredLogger:
    """Get a structured logger instance"""
    return StructuredLogger(name)


# Context managers for request and user context
import contextvars

request_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar('request_id', default=None)
user_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar('user_id', default=None)


def set_request_context(request_id: str, user_id: Optional[str] = None):
    """Set request context for logging"""
    request_id_var.set(request_id)
    if user_id:
        user_id_var.set(user_id)


def clear_request_context():
    """Clear request context"""
    request_id_var.set(None)
    user_id_var.set(None)


def get_request_context() -> Dict[str, Optional[str]]:
    """Get current request context"""
    return {
        'request_id': request_id_var.get(),
        'user_id': user_id_var.get()
    }


# Log retention and archival utilities
class LogRetentionManager:
    """Manages log retention and archival policies"""
    
    def __init__(self, log_dir: Path = Path("logs")):
        self.log_dir = log_dir
    
    def cleanup_old_logs(self, retention_days: int = 90):
        """Remove log files older than retention period"""
        cutoff_time = datetime.now().timestamp() - (retention_days * 24 * 60 * 60)
        
        for log_file in self.log_dir.glob("*.log*"):
            if log_file.stat().st_mtime < cutoff_time:
                try:
                    log_file.unlink()
                    print(f"Removed old log file: {log_file}")
                except OSError as e:
                    print(f"Error removing log file {log_file}: {e}")
    
    def archive_logs(self, archive_days: int = 30):
        """Archive logs older than specified days"""
        import gzip
        import shutil
        
        cutoff_time = datetime.now().timestamp() - (archive_days * 24 * 60 * 60)
        archive_dir = self.log_dir / "archive"
        archive_dir.mkdir(exist_ok=True)
        
        for log_file in self.log_dir.glob("*.log"):
            if log_file.stat().st_mtime < cutoff_time:
                try:
                    # Compress and move to archive
                    archive_path = archive_dir / f"{log_file.name}.gz"
                    with open(log_file, 'rb') as f_in:
                        with gzip.open(archive_path, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    
                    log_file.unlink()
                    print(f"Archived log file: {log_file} -> {archive_path}")
                except OSError as e:
                    print(f"Error archiving log file {log_file}: {e}")


# Initialize logging when module is imported
setup_logging()