"""
Prometheus metrics collection and monitoring
"""
from prometheus_client import Counter, Histogram, Gauge, Info, CollectorRegistry, generate_latest
from prometheus_client.multiprocess import MultiProcessCollector
from typing import Dict, Any, Optional
import time
import functools
import asyncio
from contextlib import asynccontextmanager

# Create a custom registry for the application
REGISTRY = CollectorRegistry()

# Application Info
app_info = Info('panic_system_app', 'Application information', registry=REGISTRY)
app_info.info({
    'version': '1.0.0',
    'name': 'Panic System Platform'
})

# HTTP Request Metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code'],
    registry=REGISTRY
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    registry=REGISTRY
)

# Authentication Metrics
auth_attempts_total = Counter(
    'auth_attempts_total',
    'Total authentication attempts',
    ['status', 'user_type'],
    registry=REGISTRY
)

failed_login_attempts = Counter(
    'failed_login_attempts_total',
    'Total failed login attempts',
    ['user_type'],
    registry=REGISTRY
)

account_lockouts_total = Counter(
    'account_lockouts_total',
    'Total account lockouts',
    ['user_type'],
    registry=REGISTRY
)

# Business Metrics
panic_requests_total = Counter(
    'panic_requests_total',
    'Total panic requests',
    ['service_type', 'status', 'firm_id'],
    registry=REGISTRY
)

panic_request_response_time = Histogram(
    'panic_request_response_time_seconds',
    'Panic request response time from submission to acceptance',
    ['service_type', 'zone'],
    buckets=[30, 60, 120, 300, 600, 1200, 3600],  # 30s to 1h
    registry=REGISTRY
)

panic_request_completion_time = Histogram(
    'panic_request_completion_time_seconds',
    'Panic request completion time from submission to completion',
    ['service_type', 'zone'],
    buckets=[300, 600, 1200, 1800, 3600, 7200],  # 5min to 2h
    registry=REGISTRY
)

# Subscription Metrics
active_subscriptions = Gauge(
    'active_subscriptions_total',
    'Total active subscriptions',
    ['firm_id'],
    registry=REGISTRY
)

subscription_purchases_total = Counter(
    'subscription_purchases_total',
    'Total subscription purchases',
    ['product_id', 'firm_id'],
    registry=REGISTRY
)

credit_transactions_total = Counter(
    'credit_transactions_total',
    'Total credit transactions',
    ['transaction_type', 'firm_id'],
    registry=REGISTRY
)

# Prank Detection Metrics
prank_flags_total = Counter(
    'prank_flags_total',
    'Total prank flags',
    ['user_id', 'firm_id'],
    registry=REGISTRY
)

user_fines_total = Counter(
    'user_fines_total',
    'Total user fines issued',
    ['user_id', 'fine_amount'],
    registry=REGISTRY
)

# System Health Metrics
database_connections = Gauge(
    'database_connections_active',
    'Active database connections',
    registry=REGISTRY
)

redis_connections = Gauge(
    'redis_connections_active',
    'Active Redis connections',
    registry=REGISTRY
)

cache_hit_rate = Gauge(
    'cache_hit_rate',
    'Cache hit rate percentage',
    ['cache_type'],
    registry=REGISTRY
)

# WebSocket Metrics
websocket_connections = Gauge(
    'websocket_connections_active',
    'Active WebSocket connections',
    ['connection_type'],
    registry=REGISTRY
)

# Notification Metrics
notifications_sent_total = Counter(
    'notifications_sent_total',
    'Total notifications sent',
    ['type', 'status'],
    registry=REGISTRY
)

# Performance Metrics
zone_performance = Gauge(
    'zone_average_response_time_seconds',
    'Average response time per zone',
    ['zone_id', 'service_type'],
    registry=REGISTRY
)

firm_performance = Gauge(
    'firm_average_response_time_seconds',
    'Average response time per firm',
    ['firm_id', 'service_type'],
    registry=REGISTRY
)


class MetricsCollector:
    """Centralized metrics collection service"""
    
    def __init__(self):
        self.registry = REGISTRY
    
    def record_http_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metrics"""
        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()
        
        http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    def record_auth_attempt(self, status: str, user_type: str):
        """Record authentication attempt"""
        auth_attempts_total.labels(
            status=status,
            user_type=user_type
        ).inc()
    
    def record_failed_login(self, user_type: str):
        """Record failed login attempt"""
        failed_login_attempts.labels(user_type=user_type).inc()
    
    def record_account_lockout(self, user_type: str):
        """Record account lockout"""
        account_lockouts_total.labels(user_type=user_type).inc()
    
    def record_panic_request(self, service_type: str, status: str, firm_id: str):
        """Record panic request"""
        panic_requests_total.labels(
            service_type=service_type,
            status=status,
            firm_id=firm_id
        ).inc()
    
    def record_panic_response_time(self, service_type: str, zone: str, response_time: float):
        """Record panic request response time"""
        panic_request_response_time.labels(
            service_type=service_type,
            zone=zone
        ).observe(response_time)
    
    def record_panic_completion_time(self, service_type: str, zone: str, completion_time: float):
        """Record panic request completion time"""
        panic_request_completion_time.labels(
            service_type=service_type,
            zone=zone
        ).observe(completion_time)
    
    def update_active_subscriptions(self, firm_id: str, count: int):
        """Update active subscriptions count"""
        active_subscriptions.labels(firm_id=firm_id).set(count)
    
    def record_subscription_purchase(self, product_id: str, firm_id: str):
        """Record subscription purchase"""
        subscription_purchases_total.labels(
            product_id=product_id,
            firm_id=firm_id
        ).inc()
    
    def record_credit_transaction(self, transaction_type: str, firm_id: str):
        """Record credit transaction"""
        credit_transactions_total.labels(
            transaction_type=transaction_type,
            firm_id=firm_id
        ).inc()
    
    def record_prank_flag(self, user_id: str, firm_id: str):
        """Record prank flag"""
        prank_flags_total.labels(
            user_id=user_id,
            firm_id=firm_id
        ).inc()
    
    def record_user_fine(self, user_id: str, fine_amount: str):
        """Record user fine"""
        user_fines_total.labels(
            user_id=user_id,
            fine_amount=fine_amount
        ).inc()
    
    def update_database_connections(self, count: int):
        """Update database connections count"""
        database_connections.set(count)
    
    def update_redis_connections(self, count: int):
        """Update Redis connections count"""
        redis_connections.set(count)
    
    def update_cache_hit_rate(self, cache_type: str, hit_rate: float):
        """Update cache hit rate"""
        cache_hit_rate.labels(cache_type=cache_type).set(hit_rate)
    
    def update_websocket_connections(self, connection_type: str, count: int):
        """Update WebSocket connections count"""
        websocket_connections.labels(connection_type=connection_type).set(count)
    
    def record_notification_sent(self, notification_type: str, status: str):
        """Record notification sent"""
        notifications_sent_total.labels(
            type=notification_type,
            status=status
        ).inc()
    
    def update_zone_performance(self, zone_id: str, service_type: str, avg_response_time: float):
        """Update zone performance metrics"""
        zone_performance.labels(
            zone_id=zone_id,
            service_type=service_type
        ).set(avg_response_time)
    
    def update_firm_performance(self, firm_id: str, service_type: str, avg_response_time: float):
        """Update firm performance metrics"""
        firm_performance.labels(
            firm_id=firm_id,
            service_type=service_type
        ).set(avg_response_time)
    
    def get_metrics(self) -> str:
        """Get all metrics in Prometheus format"""
        return generate_latest(self.registry).decode('utf-8')


# Global metrics collector instance
metrics_collector = MetricsCollector()


def track_time(metric_name: str, labels: Optional[Dict[str, str]] = None):
    """Decorator to track execution time of functions"""
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                # Record the timing metric based on metric_name
                if metric_name == "panic_response_time" and labels:
                    metrics_collector.record_panic_response_time(
                        labels.get('service_type', 'unknown'),
                        labels.get('zone', 'unknown'),
                        duration
                    )
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                # Record the timing metric based on metric_name
                if metric_name == "panic_response_time" and labels:
                    metrics_collector.record_panic_response_time(
                        labels.get('service_type', 'unknown'),
                        labels.get('zone', 'unknown'),
                        duration
                    )
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


@asynccontextmanager
async def track_request_time(service_type: str, zone: str):
    """Context manager to track request processing time"""
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        metrics_collector.record_panic_response_time(service_type, zone, duration)