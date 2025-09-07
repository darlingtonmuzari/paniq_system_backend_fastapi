# Panic System Platform - Monitoring and Metrics

This directory contains the complete monitoring and metrics collection setup for the Panic System Platform, including Prometheus metrics collection, Grafana dashboards, and alerting configuration.

## Overview

The monitoring system provides:

- **Prometheus Metrics Collection**: Custom business metrics and system health metrics
- **Grafana Dashboards**: Visual monitoring of system performance and business KPIs
- **Alerting**: Automated alerts for system health and performance issues
- **Background Tasks**: Automated metrics collection and updates

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Application   │───▶│   Prometheus    │───▶│    Grafana      │
│                 │    │                 │    │                 │
│ - HTTP Metrics  │    │ - Scrapes /metrics │ │ - Dashboards    │
│ - Business KPIs │    │ - Stores TSDB   │    │ - Visualizations│
│ - System Health │    │ - Evaluates Rules│   │ - Queries       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │  Alertmanager   │
                       │                 │
                       │ - Email Alerts  │
                       │ - Webhooks      │
                       │ - Routing       │
                       └─────────────────┘
```

## Metrics Categories

### HTTP Metrics
- Request count by endpoint and status code
- Request duration histograms
- Error rates

### Authentication Metrics
- Login attempts (success/failure)
- Account lockouts
- Failed login rates

### Business Metrics
- Panic requests by service type and status
- Response times by zone and service type
- Subscription counts and purchases
- Prank detection rates
- Credit transactions

### System Health Metrics
- Database connection counts
- Redis connection counts
- Cache hit rates
- WebSocket connections

### Performance Metrics
- Zone-specific response times
- Firm-specific performance
- Service completion rates

## Quick Start

### 1. Start the Monitoring Stack

```bash
# Start Prometheus, Grafana, and Alertmanager
cd monitoring
docker-compose -f docker-compose.monitoring.yml up -d
```

### 2. Access the Interfaces

- **Grafana**: http://localhost:3000 (admin/admin123)
- **Prometheus**: http://localhost:9090
- **Alertmanager**: http://localhost:9093

### 3. Configure the Application

Add to your `.env` file:

```env
METRICS_ENABLED=true
METRICS_PORT=8001
PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus_multiproc_dir
```

### 4. Start Background Tasks

```bash
# Start Celery worker for metrics tasks
celery -A app.tasks.metrics worker --loglevel=info

# Start Celery beat for scheduled metrics updates
celery -A app.tasks.metrics beat --loglevel=info
```

## API Endpoints

### Metrics Endpoints

- `GET /api/v1/metrics/prometheus` - Prometheus metrics format
- `GET /api/v1/metrics/health` - System health check
- `GET /api/v1/metrics/business` - Business metrics summary
- `GET /api/v1/metrics/performance` - Performance metrics by zone/firm
- `GET /api/v1/metrics/alerts` - Active alerts
- `POST /api/v1/metrics/update-cache-metrics` - Update cache metrics

### Example Usage

```bash
# Get Prometheus metrics
curl http://localhost:8000/api/v1/metrics/prometheus

# Get business metrics for last 24 hours
curl http://localhost:8000/api/v1/metrics/business?hours=24

# Get performance metrics for specific firm
curl http://localhost:8000/api/v1/metrics/performance?firm_id=firm123&hours=12

# Check active alerts
curl http://localhost:8000/api/v1/metrics/alerts
```

## Dashboards

### 1. System Overview Dashboard
- HTTP request rates and response times
- Authentication metrics
- System health indicators
- Cache performance

### 2. Business Metrics Dashboard
- Panic request trends
- Response time analysis
- Zone performance heatmaps
- Subscription metrics
- Prank detection rates

## Alerting Rules

### Critical Alerts
- Service down
- Database connection lost
- Very slow panic response times (>15 minutes)

### Warning Alerts
- High error rates (>5%)
- Slow response times (>2 seconds)
- High failed login rates
- Poor zone performance
- High prank rates

### Configuration

Edit `prometheus/alerts.yml` to customize alert thresholds:

```yaml
- alert: SlowPanicResponse
  expr: histogram_quantile(0.95, rate(panic_request_response_time_seconds_bucket[10m])) > 300
  for: 5m
  labels:
    severity: critical
```

## Background Tasks

### Scheduled Tasks

1. **Update All Metrics** (every minute)
   - System health metrics
   - Subscription counts
   - Basic performance metrics

2. **Update Performance Metrics** (every 5 minutes)
   - Zone-specific calculations
   - Firm-specific calculations
   - Complex aggregations

3. **Cleanup Old Metrics** (daily)
   - Remove old metric data
   - Archive historical data

### Manual Tasks

```python
from app.tasks.metrics import (
    record_panic_request_metrics,
    record_auth_metrics,
    record_notification_metrics
)

# Record panic request metrics
record_panic_request_metrics.delay(
    service_type="security",
    status="accepted",
    firm_id="firm123",
    zone="downtown",
    response_time=180.5
)

# Record authentication metrics
record_auth_metrics.delay(
    user_type="registered_user",
    success=False,
    account_locked=True
)
```

## Custom Metrics

### Adding New Metrics

1. **Define the metric** in `app/core/metrics.py`:

```python
custom_metric = Counter(
    'custom_metric_total',
    'Description of custom metric',
    ['label1', 'label2'],
    registry=REGISTRY
)
```

2. **Add recording method** to `MetricsCollector`:

```python
def record_custom_metric(self, label1: str, label2: str):
    custom_metric.labels(label1=label1, label2=label2).inc()
```

3. **Use in your code**:

```python
from app.core.metrics import metrics_collector
metrics_collector.record_custom_metric("value1", "value2")
```

## Troubleshooting

### Common Issues

1. **Metrics not appearing in Prometheus**
   - Check that `METRICS_ENABLED=true` in configuration
   - Verify the application is running on the correct port
   - Check Prometheus configuration and targets

2. **Grafana dashboards not loading**
   - Verify Prometheus datasource is configured correctly
   - Check that dashboard JSON files are valid
   - Ensure Grafana has access to Prometheus

3. **Alerts not firing**
   - Check alert rule syntax in `alerts.yml`
   - Verify Alertmanager configuration
   - Check that metrics are being collected

### Debugging

```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Check specific metrics
curl http://localhost:8000/api/v1/metrics/prometheus | grep panic_requests

# Test alert rules
curl http://localhost:9090/api/v1/rules

# Check Alertmanager status
curl http://localhost:9093/api/v1/status
```

## Production Considerations

### Security
- Enable authentication for Grafana
- Restrict access to metrics endpoints
- Use HTTPS for all monitoring interfaces
- Secure Prometheus and Alertmanager

### Performance
- Configure appropriate retention periods
- Use recording rules for expensive queries
- Monitor metrics cardinality
- Set up proper resource limits

### High Availability
- Run multiple Prometheus instances
- Use Prometheus federation
- Set up Grafana clustering
- Configure Alertmanager clustering

### Storage
- Configure appropriate retention policies
- Set up remote storage if needed
- Monitor disk usage
- Implement backup strategies

## Configuration Files

- `prometheus/prometheus.yml` - Prometheus configuration
- `prometheus/alerts.yml` - Alert rules
- `grafana/datasources/prometheus.yml` - Grafana datasource
- `grafana/dashboards/*.json` - Dashboard definitions
- `alertmanager/alertmanager.yml` - Alert routing and notifications
- `docker-compose.monitoring.yml` - Docker services

## Integration with Application

The metrics system is automatically integrated with the FastAPI application through:

- **Middleware**: Automatic HTTP request tracking
- **Service Integration**: Business logic metrics recording
- **Background Tasks**: Periodic metrics updates
- **API Endpoints**: Manual metrics access and updates

For more details, see the application code in:
- `app/core/metrics.py` - Core metrics definitions
- `app/services/metrics.py` - Business metrics service
- `app/tasks/metrics.py` - Background tasks
- `app/api/v1/metrics.py` - API endpoints