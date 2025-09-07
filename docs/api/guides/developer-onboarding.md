# Developer Onboarding Guide

Welcome to the Panic System Platform API! This guide will help you get started with integrating our emergency response platform into your applications.

## Getting Started

### 1. Account Setup

1. **Register your organization** at [https://developer.panicsystem.com](https://developer.panicsystem.com)
2. **Verify your email** and complete organization profile
3. **Generate API credentials** in the developer dashboard
4. **Configure your application** settings and callback URLs

### 2. Environment Setup

#### Development Environment
- **Base URL**: `https://staging-api.panicsystem.com/api/v1`
- **Rate Limits**: Relaxed for testing
- **Documentation**: Interactive docs at `/docs`

#### Production Environment  
- **Base URL**: `https://api.panicsystem.com/api/v1`
- **Rate Limits**: Standard production limits
- **Monitoring**: Full observability and alerting

### 3. Authentication Flow

The API uses a two-layer authentication system:

1. **JWT Tokens** for user authentication
2. **App Attestation** for mobile app integrity (mobile endpoints only)

#### Basic Authentication (Web/Server)

```javascript
// 1. Login to get tokens
const loginResponse = await fetch('/api/v1/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'password',
    user_type: 'registered_user'
  })
});

const tokens = await loginResponse.json();

// 2. Use access token for API calls
const userResponse = await fetch('/api/v1/auth/me', {
  headers: { 'Authorization': `Bearer ${tokens.access_token}` }
});
```

#### Mobile Authentication (with Attestation)

```javascript
// 1. Generate attestation token (platform-specific)
const attestationToken = await generateAttestationToken();

// 2. Login with attestation
const loginResponse = await fetch('/api/v1/auth/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-Attestation-Token': attestationToken,
    'X-Platform': 'android' // or 'ios'
  },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'password',
    user_type: 'registered_user'
  })
});
```

## Core Integration Patterns

### 1. User Registration Flow

```javascript
class UserRegistration {
  async registerUser(userData) {
    // Step 1: Register user
    const response = await this.apiClient.post('/users/register', {
      email: userData.email,
      phone: userData.phone,
      first_name: userData.firstName,
      last_name: userData.lastName,
      password: userData.password
    });

    // Step 2: Verify phone number
    const verificationCode = await this.promptForVerificationCode();
    await this.apiClient.post('/users/verify-phone', {
      phone: userData.phone,
      verification_code: verificationCode
    });

    return response.data;
  }
}
```

### 2. Emergency Request Flow

```javascript
class EmergencyService {
  async submitEmergencyRequest(requestData) {
    try {
      // Validate location and subscription
      const validation = await this.validateRequest(requestData);
      if (!validation.valid) {
        throw new Error(validation.message);
      }

      // Submit emergency request
      const response = await this.apiClient.post('/emergency/request', {
        service_type: requestData.serviceType,
        location: requestData.location,
        address: requestData.address,
        description: requestData.description,
        group_id: requestData.groupId
      }, {
        headers: {
          'X-Attestation-Token': await this.getAttestationToken(),
          'X-Platform': this.platform
        }
      });

      // Handle call service type
      if (requestData.serviceType === 'call') {
        await this.setSilentMode(true);
      }

      // Start real-time updates
      this.startRealtimeUpdates(response.data.request_id);

      return response.data;
    } catch (error) {
      this.handleEmergencyError(error);
      throw error;
    }
  }
}
```

### 3. Real-time Updates with WebSocket

```javascript
class RealtimeUpdates {
  constructor(accessToken, attestationToken) {
    this.accessToken = accessToken;
    this.attestationToken = attestationToken;
    this.ws = null;
    this.eventHandlers = new Map();
  }

  connect() {
    const wsUrl = `wss://api.panicsystem.com/api/v1/ws?token=${this.accessToken}&attestation=${this.attestationToken}`;
    this.ws = new WebSocket(wsUrl);

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      const handler = this.eventHandlers.get(data.type);
      if (handler) {
        handler(data.payload);
      }
    };
  }

  onRequestStatusUpdate(handler) {
    this.eventHandlers.set('request_status_update', handler);
  }

  onAgentLocationUpdate(handler) {
    this.eventHandlers.set('agent_location_update', handler);
  }
}
```

## SDK and Libraries

### Official SDKs

#### JavaScript/TypeScript SDK

```bash
npm install @panicsystem/js-sdk
```

```javascript
import { PanicSystemClient } from '@panicsystem/js-sdk';

const client = new PanicSystemClient({
  baseURL: 'https://api.panicsystem.com/api/v1',
  apiKey: 'your-api-key'
});

// Authenticate
await client.auth.login('user@example.com', 'password');

// Submit emergency request
const request = await client.emergency.submit({
  serviceType: 'security',
  location: { latitude: 40.7128, longitude: -74.0060 },
  address: '123 Main St, New York, NY',
  groupId: 'group-uuid'
});
```

#### React Native SDK

```bash
npm install @panicsystem/react-native-sdk
```

```javascript
import { PanicSystemClient } from '@panicsystem/react-native-sdk';

const client = new PanicSystemClient({
  baseURL: 'https://api.panicsystem.com/api/v1',
  platform: Platform.OS
});

// Login with attestation
await client.auth.loginWithAttestation('user@example.com', 'password');

// Submit emergency request (automatically handles attestation)
const request = await client.emergency.submit({
  serviceType: 'security',
  location: await client.location.getCurrentLocation(),
  address: '123 Main St, New York, NY',
  groupId: 'group-uuid'
});
```

#### Python SDK

```bash
pip install panicsystem-python-sdk
```

```python
from panicsystem import PanicSystemClient

client = PanicSystemClient(
    base_url='https://api.panicsystem.com/api/v1',
    api_key='your-api-key'
)

# Authenticate
client.auth.login('user@example.com', 'password')

# Submit emergency request
request = client.emergency.submit(
    service_type='security',
    location={'latitude': 40.7128, 'longitude': -74.0060},
    address='123 Main St, New York, NY',
    group_id='group-uuid'
)
```

## Testing Your Integration

### 1. Unit Testing

```javascript
// Jest example
describe('EmergencyService', () => {
  let emergencyService;
  let mockApiClient;

  beforeEach(() => {
    mockApiClient = {
      post: jest.fn(),
      get: jest.fn()
    };
    emergencyService = new EmergencyService(mockApiClient);
  });

  test('should submit emergency request successfully', async () => {
    mockApiClient.post.mockResolvedValue({
      data: { request_id: 'req_123', status: 'pending' }
    });

    const result = await emergencyService.submitEmergencyRequest({
      serviceType: 'security',
      location: { latitude: 40.7128, longitude: -74.0060 },
      address: '123 Main St',
      groupId: 'group_123'
    });

    expect(result.request_id).toBe('req_123');
    expect(mockApiClient.post).toHaveBeenCalledWith('/emergency/request', 
      expect.objectContaining({ service_type: 'security' }),
      expect.any(Object)
    );
  });
});
```

### 2. Integration Testing

```javascript
// Integration test with test environment
describe('API Integration', () => {
  let client;

  beforeAll(async () => {
    client = new PanicSystemClient({
      baseURL: 'https://staging-api.panicsystem.com/api/v1'
    });
    
    // Login with test credentials
    await client.auth.login('test@example.com', 'testpassword');
  });

  test('should handle complete emergency flow', async () => {
    // Create test group
    const group = await client.users.createGroup({
      name: 'Test Group',
      address: '123 Test St',
      location: { latitude: 40.7128, longitude: -74.0060 }
    });

    // Submit emergency request
    const request = await client.emergency.submit({
      serviceType: 'security',
      location: { latitude: 40.7128, longitude: -74.0060 },
      address: '123 Test St',
      groupId: group.id
    });

    expect(request.request_id).toBeDefined();
    expect(request.status).toBe('pending');
  });
});
```

### 3. Load Testing

```javascript
// Artillery.js load test configuration
module.exports = {
  config: {
    target: 'https://staging-api.panicsystem.com',
    phases: [
      { duration: 60, arrivalRate: 10 },
      { duration: 120, arrivalRate: 20 },
      { duration: 60, arrivalRate: 10 }
    ]
  },
  scenarios: [
    {
      name: 'Emergency Request Flow',
      weight: 100,
      flow: [
        {
          post: {
            url: '/api/v1/auth/login',
            json: {
              email: 'test@example.com',
              password: 'testpassword',
              user_type: 'registered_user'
            },
            capture: {
              json: '$.access_token',
              as: 'accessToken'
            }
          }
        },
        {
          post: {
            url: '/api/v1/emergency/request',
            headers: {
              'Authorization': 'Bearer {{ accessToken }}'
            },
            json: {
              service_type: 'security',
              location: { latitude: 40.7128, longitude: -74.0060 },
              address: '123 Test St',
              group_id: 'test-group-id'
            }
          }
        }
      ]
    }
  ]
};
```

## Best Practices

### 1. Error Handling

```javascript
class APIErrorHandler {
  static async handleWithRetry(apiCall, maxRetries = 3) {
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        return await apiCall();
      } catch (error) {
        if (this.shouldRetry(error) && attempt < maxRetries) {
          await this.delay(Math.pow(2, attempt) * 1000);
          continue;
        }
        throw this.transformError(error);
      }
    }
  }

  static shouldRetry(error) {
    const retryableStatuses = [429, 500, 502, 503, 504];
    return retryableStatuses.includes(error.response?.status);
  }

  static transformError(error) {
    const { error_code, message, details } = error.response?.data || {};
    
    return new APIError({
      code: error_code,
      message: message,
      details: details,
      originalError: error
    });
  }
}
```

### 2. Security

```javascript
// Secure token storage
class SecureStorage {
  static async storeTokens(tokens) {
    if (typeof window !== 'undefined') {
      // Web - use secure storage
      await this.storeInSecureStorage(tokens);
    } else {
      // Mobile - use keychain/keystore
      await this.storeInKeychain(tokens);
    }
  }

  static async getTokens() {
    // Retrieve from secure storage
    const tokens = await this.getFromSecureStorage();
    
    // Validate token expiry
    if (this.isTokenExpired(tokens.access_token)) {
      return await this.refreshTokens(tokens.refresh_token);
    }
    
    return tokens;
  }
}
```

### 3. Performance Optimization

```javascript
// Request caching
class CachedAPIClient {
  constructor() {
    this.cache = new Map();
    this.cacheTimeout = 5 * 60 * 1000; // 5 minutes
  }

  async get(url, options = {}) {
    const cacheKey = this.getCacheKey(url, options);
    const cached = this.cache.get(cacheKey);

    if (cached && !this.isCacheExpired(cached)) {
      return cached.data;
    }

    const response = await this.makeRequest(url, options);
    this.cache.set(cacheKey, {
      data: response,
      timestamp: Date.now()
    });

    return response;
  }
}
```

## Support and Resources

### Documentation
- **API Reference**: [https://docs.panicsystem.com/api](https://docs.panicsystem.com/api)
- **OpenAPI Spec**: [https://api.panicsystem.com/openapi.yaml](https://api.panicsystem.com/openapi.yaml)
- **Postman Collection**: [Download](https://docs.panicsystem.com/postman)

### Community
- **Developer Forum**: [https://community.panicsystem.com](https://community.panicsystem.com)
- **GitHub Discussions**: [https://github.com/panicsystem/api-discussions](https://github.com/panicsystem/api-discussions)
- **Stack Overflow**: Tag questions with `panic-system-api`

### Support Channels
- **Email Support**: developers@panicsystem.com
- **Live Chat**: Available in developer dashboard
- **Emergency Issues**: Call +1-800-PANIC-API

### Status and Monitoring
- **Status Page**: [https://status.panicsystem.com](https://status.panicsystem.com)
- **API Health**: [https://api.panicsystem.com/health](https://api.panicsystem.com/health)
- **Incident Reports**: Subscribe to status page for notifications

## Next Steps

1. **Complete the tutorial**: Follow our [Quick Start Tutorial](./quick-start-tutorial.md)
2. **Explore the SDKs**: Try our official SDKs for your platform
3. **Join the community**: Connect with other developers in our forum
4. **Build your first integration**: Start with user authentication and basic API calls
5. **Test thoroughly**: Use our staging environment for comprehensive testing
6. **Go live**: Deploy to production with confidence

Welcome to the Panic System Platform developer community! We're excited to see what you'll build.