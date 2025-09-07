"""
Application configuration settings
"""
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Optional, Union
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    DEBUG: bool = False
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:4010"]
    ADMIN_ALLOWED_ORIGINS: List[str] = [f"http://localhost:{port}" for port in range(4000, 4021)]
    
    @field_validator('ALLOWED_ORIGINS', 'ADMIN_ALLOWED_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            # Handle comma-separated string
            return [origin.strip() for origin in v.split(',') if origin.strip()]
        return v
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/panic_system"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 30
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 3600
    
    # JWT
    JWT_SECRET_KEY: str = "jwt-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Mobile App Attestation
    GOOGLE_PLAY_INTEGRITY_PACKAGE_NAME: str = "za.co.paniq"
    GOOGLE_PLAY_INTEGRITY_API_KEY: Optional[str] = None
    APPLE_APP_ATTEST_TEAM_ID: str = "YOUR_TEAM_ID"
    APPLE_APP_ATTEST_BUNDLE_ID: str = "za.co.paniq.client"
    
    # External Services
    SMS_PROVIDER_API_KEY: Optional[str] = None
    SMS_PROVIDER_URL: Optional[str] = None
    PUSH_NOTIFICATION_FCM_KEY: Optional[str] = None
    PAYMENT_GATEWAY_API_KEY: Optional[str] = None
    
    # Email/SMTP Settings
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    FROM_EMAIL: str = "noreply@panicsystem.com"
    
    # Notification Services
    FCM_SERVER_KEY: Optional[str] = None
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None
    SENDGRID_API_KEY: Optional[str] = None
    FROM_NAME: str = "Panic System Platform"
    
    # SMS Settings (alternative names for compatibility)
    SMS_API_KEY: Optional[str] = None
    SMS_API_URL: Optional[str] = None
    
    # Security
    ACCOUNT_LOCKOUT_DURATION_MINUTES: int = 30
    MAX_FAILED_LOGIN_ATTEMPTS: int = 5
    OTP_EXPIRY_MINUTES: int = 10
    OTP_MAX_ATTEMPTS: int = 3
    
    # File Storage
    FILE_STORAGE_PATH: str = "./uploads"
    MAX_FILE_SIZE_MB: int = 10
    
    # AWS S3 Configuration
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION_NAME: str = "us-east-1"
    AWS_S3_BUCKET: Optional[str] = None
    USE_S3_STORAGE: bool = False
    
    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "./logs"
    LOG_RETENTION_DAYS: int = 90
    LOG_ARCHIVE_DAYS: int = 30
    LOG_COMPRESS_AFTER_DAYS: int = 7
    LOG_MAX_FILE_SIZE_MB: int = 50
    LOG_MAX_BACKUP_COUNT: int = 10
    
    # Security Log Retention (longer for compliance)
    SECURITY_LOG_RETENTION_DAYS: int = 365
    SECURITY_LOG_ARCHIVE_DAYS: int = 90
    SECURITY_LOG_MAX_BACKUP_COUNT: int = 20
    
    # Metrics and Monitoring
    METRICS_ENABLED: bool = True
    METRICS_PORT: int = 8001
    METRICS_PATH: str = "/metrics"
    PROMETHEUS_MULTIPROC_DIR: Optional[str] = None
    
    # Alerting Configuration
    ALERT_WEBHOOK_URL: Optional[str] = None
    ALERT_EMAIL_RECIPIENTS: List[str] = []
    RESPONSE_TIME_ALERT_THRESHOLD_SECONDS: int = 300  # 5 minutes
    ERROR_RATE_ALERT_THRESHOLD_PERCENT: float = 5.0
    
    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # Feature Flags
    RATE_LIMIT_ENABLED: bool = True
    CACHE_ENABLED: bool = True
    
    # OZOW Payment Configuration - using live API
    OZOW_BASE_URL: str = "https://great-utterly-owl.ngrok-free.app"
    OZOW_SITE_CODE: str = "MOF-MOF-002"
    OZOW_PRIVATE_KEY: str = "40481eb78f0648f0894dd394f87a9cf2"
    OZOW_API_KEY: str = "d1784bcb43db4869b786901bc7a87577"
    OZOW_POST_URL: str = "https://api.ozow.com/postpaymentrequest"
    OZOW_POST_LIVE_URL: str = "https://api.ozow.com/postpaymentrequest"
    OZOW_IS_TEST: bool = True
    OZOW_SUCCESS_URL: str = OZOW_BASE_URL + "/api/ozow/payments/status"
    OZOW_CANCEL_URL: str = OZOW_BASE_URL + "/api/ozow/payments/status"
    OZOW_ERROR_URL: str = OZOW_BASE_URL + "/api/ozow/payments/status"
    OZOW_NOTIFY_URL: str = OZOW_BASE_URL + "/api/v1/payments/ozow/webhooks"
    OZOW_VERIFY_TRANS_URL: str = "https://api.ozow.com"
    OZOW_VERIFY_TRANS_LIVE_URL: str = "https://api.ozow.com"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()