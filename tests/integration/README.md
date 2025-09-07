# Integration Tests

This directory contains comprehensive integration tests for the Panic System Platform. These tests verify that all components work together correctly and meet the performance requirements.

## Test Structure

### 1. API Integration Tests (`test_api_integration.py`)
Tests all API endpoints with real database interactions:
- Authentication flow with account lockout/unlock
- User registration and group management
- Subscription purchase and application
- Emergency request submission and status updates
- Security firm registration and personnel management
- Credit purchase and balance management
- Feedback submission and prank detection
- Metrics collection and reporting

### 2. Database Integration Tests (`test_database_integration.py`)
Tests database operations, transactions, and data integrity:
- Schema constraints and foreign key relationships
- PostGIS geospatial operations (point-in-polygon, distance calculations)
- Transaction integrity and rollback scenarios
- Data integrity and business rule enforcement
- Query performance with spatial indexes
- Subscription expiry and prank detection logic

### 3. External Services Integration Tests (`test_external_services_integration.py`)
Tests integration with external services using mocks:
- Mobile app attestation (Android Play Integrity, iOS App Attest)
- OTP delivery (SMS and email services)
- Push notifications with retry logic
- Payment processing and refund handling
- Geolocation services (geocoding, distance calculation)
- Error handling and circuit breaker patterns

### 4. End-to-End Workflow Tests (`test_end_to_end_workflows.py`)
Tests complete business workflows from start to finish:
- User registration → verification → login workflow
- Security firm onboarding → approval → service activation
- Emergency response → allocation → completion → feedback
- Subscription purchase → application → renewal lifecycle
- Prank detection → fining → payment → account management
- Metrics collection → analysis → reporting workflow

### 5. Performance and Load Tests (`test_performance_load.py`)
Tests system performance under various load conditions:
- API endpoint performance under concurrent load
- Database query performance with large datasets
- Memory usage and resource consumption
- Cache performance and hit ratios
- Scalability limits and concurrent user handling
- Resource cleanup and garbage collection

## Running Integration Tests

### Prerequisites
1. PostgreSQL with PostGIS extension
2. Redis server
3. Python dependencies installed (`pip install -r requirements.txt`)

### Environment Setup
```bash
# Set up test database
createdb panic_system_test
psql -d panic_system_test -c "CREATE EXTENSION postgis;"

# Set environment variables
export DATABASE_URL="postgresql://user:password@localhost:5432/panic_system_test"
export REDIS_URL="redis://localhost:6379/1"
export TESTING=true
```

### Running Tests

#### Run All Integration Tests
```bash
python tests/run_integration_tests.py --all
```

#### Run Specific Test Categories
```bash
# API tests only
python -m pytest tests/integration/test_api_integration.py -v

# Database tests only
python -m pytest tests/integration/test_database_integration.py -v

# External services tests only
python -m pytest tests/integration/test_external_services_integration.py -v

# End-to-end workflow tests only
python -m pytest tests/integration/test_end_to_end_workflows.py -v

# Performance tests only (fast subset)
python -m pytest tests/integration/test_performance_load.py -v -m "not slow"

# All performance tests (including slow ones)
python -m pytest tests/integration/test_performance_load.py -v
```

#### Run with Coverage
```bash
python -m pytest tests/integration/ --cov=app --cov-report=html
```

## Test Configuration

### Fixtures
The `conftest.py` file provides shared fixtures:
- `test_engine`: Test database engine with PostGIS
- `db_session`: Database session for each test
- `client`: FastAPI test client with database override
- Sample data fixtures for all major entities
- `mock_external_services`: Mocked external service responses
- `auth_headers`: Helper for generating authentication headers

### Mocking Strategy
External services are mocked to ensure:
- Tests run reliably without external dependencies
- Consistent test results regardless of external service status
- Fast test execution
- Ability to test error scenarios

### Performance Benchmarks
Performance tests include benchmarks for:
- API response times (< 500ms for most endpoints)
- Database query performance (< 10ms for geospatial queries)
- Concurrent request handling (95%+ success rate)
- Memory usage limits (< 200MB increase under load)
- Cache performance (< 1ms average operation time)

## Test Data Management

### Sample Data
Tests use factory fixtures to create consistent sample data:
- Security firms with coverage areas
- Registered users with groups and mobile numbers
- Subscription products and stored subscriptions
- Personnel, teams, and service providers
- Panic requests with various statuses
- Feedback and metrics data

### Data Cleanup
Each test runs in isolation with:
- Database transactions rolled back after each test
- Redis cache cleared between tests
- Temporary files cleaned up
- Mock state reset

## Continuous Integration

### GitHub Actions Integration
```yaml
name: Integration Tests
on: [push, pull_request]
jobs:
  integration-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgis/postgis:13-3.1
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:6
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run integration tests
        run: python tests/run_integration_tests.py --all
```

### Local Development
For local development, use Docker Compose:
```yaml
version: '3.8'
services:
  postgres-test:
    image: postgis/postgis:13-3.1
    environment:
      POSTGRES_DB: panic_system_test
      POSTGRES_PASSWORD: postgres
    ports:
      - "5433:5432"
  
  redis-test:
    image: redis:6
    ports:
      - "6380:6379"
```

## Troubleshooting

### Common Issues

#### Database Connection Errors
```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Check PostGIS extension
psql -d panic_system_test -c "SELECT PostGIS_Version();"
```

#### Redis Connection Errors
```bash
# Check Redis is running
redis-cli ping

# Check Redis configuration
redis-cli config get "*"
```

#### Test Failures
```bash
# Run with verbose output
python -m pytest tests/integration/ -v -s

# Run specific failing test
python -m pytest tests/integration/test_api_integration.py::TestAuthAPIIntegration::test_complete_auth_flow -v -s

# Check test logs
tail -f logs/test.log
```

### Performance Issues
If performance tests fail:
1. Check system resources (CPU, memory, disk I/O)
2. Verify database indexes are created
3. Check Redis cache configuration
4. Monitor network latency to external services
5. Review application logs for bottlenecks

### Memory Leaks
If memory usage tests fail:
1. Run tests with memory profiling
2. Check for unclosed database connections
3. Verify cache cleanup is working
4. Look for circular references in code
5. Monitor garbage collection behavior

## Test Metrics and Reporting

### Coverage Requirements
- Minimum 90% code coverage for integration tests
- All critical paths must be tested
- Error scenarios must be covered
- Performance benchmarks must pass

### Test Reports
Integration tests generate:
- JUnit XML reports for CI/CD integration
- HTML coverage reports
- Performance benchmark results
- Resource usage statistics
- Error logs and stack traces

### Monitoring
Integration tests can be run continuously to monitor:
- System performance degradation
- External service reliability
- Database performance trends
- Memory usage patterns
- Error rate changes