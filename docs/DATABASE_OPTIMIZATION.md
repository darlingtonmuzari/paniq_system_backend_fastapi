# Database Query Optimization System

This document describes the database query optimization system implemented for the Panic System Platform.

## Overview

The database optimization system provides comprehensive query performance monitoring, optimization recommendations, and automated performance analysis. It includes optimized queries for geospatial operations, connection pool management, and real-time performance monitoring.

## Components

### 1. Query Optimizer (`app/core/query_optimizer.py`)

The core query optimization engine that provides:

- **Query Performance Monitoring**: Tracks execution time, row counts, and query patterns
- **Slow Query Detection**: Automatically identifies and logs queries exceeding performance thresholds
- **Performance Analysis**: Generates detailed performance reports and trends
- **EXPLAIN Plan Analysis**: Provides query execution plan analysis for optimization

#### Key Features:

```python
from app.core.query_optimizer import query_optimizer

# Monitor query performance
async with query_optimizer.monitor_query("user_lookup", query, params):
    result = await execute_query(query, params)

# Analyze performance over time
analysis = await query_optimizer.analyze_query_performance(hours_back=24)
```

### 2. Optimized Query Classes

#### OptimizedGeospatialQueries
Provides optimized implementations for spatial operations:

- **Coverage Area Lookup**: Efficient point-in-polygon queries using spatial indexes
- **Nearest Service Providers**: Distance-based queries with ST_DWithin optimization
- **Zone Performance Metrics**: Aggregated performance data by geographical zones

#### OptimizedUserQueries
Optimized user and subscription related queries:

- **Active Subscriptions**: Complex joins with proper indexing
- **Personnel Management**: Team and role-based queries with filtering

#### OptimizedEmergencyQueries
Emergency request optimization:

- **Recent Requests with Metrics**: Comprehensive request data with performance calculations
- **Response Time Analysis**: Automated response time tracking and reporting

### 3. Connection Pool Optimization

Enhanced connection pooling with:

- **Dynamic Pool Sizing**: Automatic adjustment based on load
- **Connection Lifecycle Management**: Optimized connection reuse and recycling
- **Performance Monitoring**: Real-time pool utilization tracking

```python
# Optimized pool settings
min_size = max(5, settings.DATABASE_POOL_SIZE // 4)
max_size = settings.DATABASE_POOL_SIZE
max_queries = 50000  # Queries per connection before recycling
max_inactive_connection_lifetime = 300  # 5 minutes
```

### 4. Database Optimization Service

High-level service providing:

- **Performance Dashboard**: Comprehensive system health overview
- **Optimization Testing**: Automated performance testing for different query types
- **Recommendation Engine**: Intelligent optimization suggestions
- **Comprehensive Reports**: Detailed analysis with actionable insights

## Database Indexes

### Spatial Indexes (PostGIS)
```sql
-- Efficient geospatial queries
CREATE INDEX idx_coverage_areas_boundary ON coverage_areas USING GIST (boundary);
CREATE INDEX idx_user_groups_location ON user_groups USING GIST (location);
CREATE INDEX idx_panic_requests_location ON panic_requests USING GIST (location);
```

### Composite Indexes
```sql
-- Multi-column indexes for complex queries
CREATE INDEX idx_panic_requests_status_created ON panic_requests (status, created_at);
CREATE INDEX idx_firm_personnel_firm_role_active ON firm_personnel (firm_id, role, is_active);
CREATE INDEX idx_stored_subscriptions_user_applied ON stored_subscriptions (user_id, is_applied);
```

### Partial Indexes
```sql
-- Indexes only on active records for better performance
CREATE INDEX idx_active_firm_personnel_role 
ON firm_personnel (firm_id, role) 
WHERE is_active = true;
```

### Expression Indexes
```sql
-- Indexes on calculated values
CREATE INDEX idx_panic_requests_response_time 
ON panic_requests (
    EXTRACT(EPOCH FROM (completed_at - accepted_at)) / 60.0
) 
WHERE completed_at IS NOT NULL AND accepted_at IS NOT NULL;
```

## API Endpoints

The optimization system exposes several admin-only endpoints:

### Performance Monitoring
- `GET /admin/database-optimization/dashboard` - Complete performance dashboard
- `GET /admin/database-optimization/pool-statistics` - Connection pool stats
- `GET /admin/database-optimization/slow-queries` - Slow query analysis
- `GET /admin/database-optimization/health` - Database health status

### Optimization Testing
- `POST /admin/database-optimization/optimize/geospatial` - Test geospatial queries
- `POST /admin/database-optimization/optimize/user-queries` - Test user queries
- `POST /admin/database-optimization/optimize/emergency-queries` - Test emergency queries
- `POST /admin/database-optimization/optimize/comprehensive` - Full optimization analysis

### Query Analysis
- `GET /admin/database-optimization/explain-plan` - Get query execution plans
- `GET /admin/database-optimization/query-performance` - Query performance analysis

## Configuration

### Environment Variables
```bash
# Database connection pool settings
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30

# Query optimization settings
SLOW_QUERY_THRESHOLD_MS=1000
QUERY_CACHE_TTL=300
```

### Application Settings
```python
# Query optimizer configuration
query_optimizer.slow_query_threshold_ms = 1000  # 1 second
query_optimizer.cache_ttl = 300  # 5 minutes
query_optimizer.performance_monitoring_enabled = True
```

## Performance Monitoring

### Metrics Collected
- Query execution time (milliseconds)
- Rows returned/affected
- Query frequency and patterns
- Connection pool utilization
- Cache hit rates
- Slow query identification

### Alerting
The system automatically generates alerts for:
- High connection pool utilization (>80%)
- Excessive slow queries (>10 per hour)
- High average execution time (>200ms)
- Database connection failures

### Recommendations
Automated recommendations include:
- Index suggestions for slow queries
- Connection pool size adjustments
- Query optimization opportunities
- Database configuration improvements

## Usage Examples

### Basic Performance Monitoring
```python
from app.services.database_optimization import database_optimization_service

# Get performance dashboard
dashboard = await database_optimization_service.get_performance_dashboard()

# Run geospatial optimization tests
geo_results = await database_optimization_service.optimize_geospatial_queries()

# Generate comprehensive report
report = await database_optimization_service.run_comprehensive_optimization()
```

### Custom Query Optimization
```python
from app.core.query_optimizer import OptimizedGeospatialQueries

# Find coverage areas for a location
coverage = await OptimizedGeospatialQueries.find_coverage_for_location(
    latitude=40.7128,
    longitude=-74.0060
)

# Find nearest service providers
providers = await OptimizedGeospatialQueries.find_nearest_service_providers(
    latitude=40.7128,
    longitude=-74.0060,
    service_type="ambulance",
    firm_id=firm_id,
    max_distance_km=10.0
)
```

### Query Performance Analysis
```python
from app.core.query_optimizer import query_optimizer

# Analyze recent query performance
analysis = await query_optimizer.analyze_query_performance(
    query_type="emergency_requests",
    hours_back=24
)

# Get explain plan for optimization
explain_plan = await query_optimizer.get_query_explain_plan(
    "SELECT * FROM panic_requests WHERE status = 'pending'"
)
```

## Best Practices

### Query Optimization
1. **Use Appropriate Indexes**: Ensure queries use spatial and composite indexes
2. **Limit Result Sets**: Always use LIMIT clauses for large datasets
3. **Optimize Joins**: Use proper join order and conditions
4. **Avoid N+1 Queries**: Use batch loading and eager loading strategies

### Connection Management
1. **Pool Sizing**: Set appropriate min/max pool sizes based on load
2. **Connection Lifecycle**: Configure connection recycling and timeouts
3. **Query Timeout**: Set reasonable query timeout values
4. **Connection Monitoring**: Monitor pool utilization and adjust as needed

### Performance Monitoring
1. **Regular Analysis**: Run performance analysis regularly
2. **Threshold Tuning**: Adjust slow query thresholds based on requirements
3. **Index Maintenance**: Regularly analyze and maintain database indexes
4. **Query Review**: Review and optimize frequently executed queries

## Troubleshooting

### Common Issues

#### High Connection Pool Utilization
- **Symptoms**: Pool utilization >80%, connection timeouts
- **Solutions**: Increase pool size, optimize long-running queries, implement connection pooling

#### Slow Geospatial Queries
- **Symptoms**: Spatial queries >1 second execution time
- **Solutions**: Ensure spatial indexes exist, use ST_DWithin for distance queries, optimize polygon complexity

#### Memory Usage
- **Symptoms**: High memory consumption, out of memory errors
- **Solutions**: Limit query result sets, optimize work_mem settings, implement query result caching

### Monitoring Commands
```bash
# Check database performance
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/admin/database-optimization/health

# Get slow queries
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/admin/database-optimization/slow-queries

# Run comprehensive optimization
curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/admin/database-optimization/optimize/comprehensive
```

## Migration

The optimization system includes database migrations for indexes:

```bash
# Apply optimization indexes
alembic upgrade head

# The migration includes:
# - Spatial indexes for geospatial queries
# - Composite indexes for complex queries  
# - Partial indexes for active records
# - Expression indexes for calculated values
```

## Security

- All optimization endpoints require admin authentication
- Query explain plans are limited to SELECT statements only
- Dangerous SQL operations are blocked in analysis tools
- All optimization activities are logged for audit purposes