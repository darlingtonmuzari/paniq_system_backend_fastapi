# API Versioning Strategy

This document outlines the versioning strategy for the Panic System Platform API, including version management, backward compatibility, and migration guidelines.

## Versioning Approach

### URL-Based Versioning

The API uses URL-based versioning with the format `/api/v{version}/`:

```
https://api.panicsystem.com/api/v1/auth/login
https://api.panicsystem.com/api/v2/auth/login
```

### Version Format

- **Major Version**: Incremented for breaking changes
- **Minor Version**: Not exposed in URL, used internally for non-breaking changes
- **Patch Version**: Not exposed in URL, used for bug fixes

Current version: **v1.0.0** (exposed as `v1`)

## Breaking vs Non-Breaking Changes

### Breaking Changes (Require New Major Version)

- Removing endpoints or fields
- Changing field types or formats
- Changing authentication mechanisms
- Modifying error response structures
- Changing required fields
- Altering endpoint behavior significantly

**Example Breaking Change:**
```json
// v1 - Original
{
  "user_id": "123",
  "email": "user@example.com"
}

// v2 - Breaking change (field type change)
{
  "user_id": 123,  // Changed from string to number
  "email": "user@example.com"
}
```

### Non-Breaking Changes (Same Major Version)

- Adding new endpoints
- Adding optional fields to requests
- Adding fields to responses
- Adding new enum values
- Improving error messages
- Performance optimizations

**Example Non-Breaking Change:**
```json
// v1.0 - Original
{
  "user_id": "123",
  "email": "user@example.com"
}

// v1.1 - Non-breaking addition
{
  "user_id": "123",
  "email": "user@example.com",
  "created_at": "2024-08-24T10:30:00Z"  // New optional field
}
```

## Version Lifecycle

### Support Timeline

| Version | Status | Support End | Notes |
|---------|--------|-------------|-------|
| v1 | Current | TBD | Active development |
| v2 | Planned | N/A | In design phase |

### Lifecycle Stages

1. **Development**: Version in active development
2. **Current**: Latest stable version with full support
3. **Maintenance**: Security fixes and critical bugs only
4. **Deprecated**: 12-month notice before end of support
5. **End of Life**: No longer supported

### Deprecation Process

1. **Announcement**: 12 months advance notice
2. **Warning Headers**: Add deprecation headers to responses
3. **Documentation**: Update docs with migration guides
4. **Support**: Provide migration assistance
5. **Sunset**: Remove version after support period

## Version Detection and Headers

### Request Headers

Clients can specify version preferences:

```http
GET /api/v1/auth/me HTTP/1.1
Host: api.panicsystem.com
Authorization: Bearer token
Accept: application/json
API-Version: 1.0
```

### Response Headers

API responses include version information:

```http
HTTP/1.1 200 OK
Content-Type: application/json
API-Version: 1.0
API-Supported-Versions: 1.0
API-Deprecated: false
```

### Deprecation Headers

For deprecated versions:

```http
HTTP/1.1 200 OK
Content-Type: application/json
API-Version: 1.0
API-Deprecated: true
API-Sunset: 2025-08-24T00:00:00Z
API-Migration-Guide: https://docs.panicsystem.com/migration/v1-to-v2
```

## Migration Guidelines

### Client Migration Strategy

#### 1. Gradual Migration

```javascript
class APIClient {
  constructor(version = 'v1') {
    this.version = version;
    this.baseURL = `https://api.panicsystem.com/api/${version}`;
  }

  // Support multiple versions during migration
  async makeRequest(endpoint, options = {}) {
    try {
      return await this.request(endpoint, options);
    } catch (error) {
      if (error.status === 410 && this.version === 'v1') {
        // Version no longer supported, try v2
        console.warn('API v1 no longer supported, migrating to v2');
        this.version = 'v2';
        this.baseURL = `https://api.panicsystem.com/api/v2`;
        return await this.request(endpoint, options);
      }
      throw error;
    }
  }
}
```

#### 2. Feature Flags for Version Testing

```javascript
class FeatureFlags {
  static shouldUseV2() {
    return localStorage.getItem('api_v2_enabled') === 'true' ||
           Math.random() < 0.1; // 10% rollout
  }
}

const apiVersion = FeatureFlags.shouldUseV2() ? 'v2' : 'v1';
const client = new APIClient(apiVersion);
```

### Server-Side Version Management

#### Version Routing

```python
from fastapi import APIRouter, Request
from app.api.v1 import router as v1_router
from app.api.v2 import router as v2_router

app = FastAPI()

# Version-specific routers
app.include_router(v1_router, prefix="/api/v1")
app.include_router(v2_router, prefix="/api/v2")

# Default version redirect
@app.get("/api/")
async def api_root():
    return RedirectResponse(url="/api/v1/")
```

#### Shared Business Logic

```python
# Shared service layer
class UserService:
    async def get_user(self, user_id: str) -> User:
        # Business logic remains the same
        return await self.user_repository.get_by_id(user_id)

# Version-specific serializers
class V1UserSerializer:
    def serialize(self, user: User) -> dict:
        return {
            "user_id": str(user.id),
            "email": user.email
        }

class V2UserSerializer:
    def serialize(self, user: User) -> dict:
        return {
            "id": user.id,  # Changed field name
            "email": user.email,
            "created_at": user.created_at.isoformat()
        }
```

## Version-Specific Documentation

### OpenAPI Specifications

Each version maintains its own OpenAPI specification:

```
docs/api/
├── v1/
│   ├── openapi.yaml
│   ├── endpoints/
│   └── examples/
├── v2/
│   ├── openapi.yaml
│   ├── endpoints/
│   └── examples/
└── migration/
    └── v1-to-v2.md
```

### Documentation Generation

```python
# Generate version-specific docs
from fastapi.openapi.utils import get_openapi

def generate_openapi_spec(app, version):
    return get_openapi(
        title=f"Panic System Platform API v{version}",
        version=version,
        description=f"API documentation for version {version}",
        routes=app.routes,
    )

# Save specs for each version
v1_spec = generate_openapi_spec(v1_app, "1.0")
v2_spec = generate_openapi_spec(v2_app, "2.0")
```

## Migration Examples

### Example: v1 to v2 Migration

#### Authentication Endpoint Changes

**v1 Response:**
```json
{
  "access_token": "jwt_token",
  "refresh_token": "refresh_token",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

**v2 Response:**
```json
{
  "tokens": {
    "access": "jwt_token",
    "refresh": "refresh_token"
  },
  "token_type": "Bearer",
  "expires_at": "2024-08-24T11:30:00Z",
  "user": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "email": "user@example.com"
  }
}
```

#### Client Migration Code

```javascript
class AuthClient {
  constructor(version = 'v1') {
    this.version = version;
  }

  async login(email, password) {
    const response = await fetch(`/api/${this.version}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });

    const data = await response.json();

    // Handle version differences
    if (this.version === 'v1') {
      return {
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
        expiresIn: data.expires_in
      };
    } else {
      return {
        accessToken: data.tokens.access,
        refreshToken: data.tokens.refresh,
        expiresAt: new Date(data.expires_at),
        user: data.user
      };
    }
  }
}
```

## Testing Strategy

### Version Compatibility Testing

```javascript
describe('API Version Compatibility', () => {
  const versions = ['v1', 'v2'];

  versions.forEach(version => {
    describe(`API ${version}`, () => {
      let client;

      beforeEach(() => {
        client = new APIClient(version);
      });

      test('should authenticate successfully', async () => {
        const result = await client.auth.login('test@example.com', 'password');
        expect(result.accessToken).toBeDefined();
      });

      test('should handle emergency requests', async () => {
        await client.auth.login('test@example.com', 'password');
        const request = await client.emergency.submit({
          serviceType: 'security',
          location: { latitude: 40.7128, longitude: -74.0060 }
        });
        expect(request.requestId).toBeDefined();
      });
    });
  });
});
```

### Contract Testing

```javascript
// Pact contract testing
const { Pact } = require('@pact-foundation/pact');

describe('API Contract Tests', () => {
  const provider = new Pact({
    consumer: 'mobile-app',
    provider: 'panic-system-api-v1'
  });

  test('should get user info', async () => {
    await provider
      .given('user exists')
      .uponReceiving('a request for user info')
      .withRequest({
        method: 'GET',
        path: '/api/v1/auth/me',
        headers: { Authorization: 'Bearer token' }
      })
      .willRespondWith({
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: {
          user_id: '123',
          email: 'user@example.com'
        }
      });

    // Test implementation
  });
});
```

## Monitoring and Analytics

### Version Usage Tracking

```python
from prometheus_client import Counter

api_version_requests = Counter(
    'api_version_requests_total',
    'Total API requests by version',
    ['version', 'endpoint', 'status']
)

@app.middleware("http")
async def track_version_usage(request: Request, call_next):
    version = extract_version_from_path(request.url.path)
    
    response = await call_next(request)
    
    api_version_requests.labels(
        version=version,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    return response
```

### Migration Progress Dashboard

Track migration progress with metrics:

- Version usage distribution
- Deprecated endpoint usage
- Client migration status
- Error rates by version

## Best Practices

### For API Developers

1. **Plan Breaking Changes**: Group breaking changes into major versions
2. **Maintain Backward Compatibility**: Support previous versions during transition
3. **Clear Communication**: Provide advance notice of deprecations
4. **Migration Tools**: Offer automated migration utilities when possible
5. **Documentation**: Maintain comprehensive migration guides

### For API Consumers

1. **Version Pinning**: Always specify API version in requests
2. **Monitor Deprecations**: Watch for deprecation headers and announcements
3. **Gradual Migration**: Test new versions thoroughly before full migration
4. **Error Handling**: Handle version-related errors gracefully
5. **Stay Updated**: Subscribe to API change notifications

This versioning strategy ensures smooth evolution of the Panic System Platform API while maintaining stability for existing integrations.