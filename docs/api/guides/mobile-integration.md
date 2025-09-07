# Mobile App Integration Guide

This guide covers the complete integration process for mobile applications with the Panic System Platform API, including app attestation, authentication, and emergency request handling.

## Prerequisites

- Mobile app registered with Google Play Console (Android) or Apple Developer Program (iOS)
- App attestation configured (Google Play Integrity API or Apple App Attest)
- HTTPS-enabled API endpoint
- Valid API credentials

## 1. App Attestation Setup

### Android - Google Play Integrity API

1. **Enable Play Integrity API** in Google Cloud Console
2. **Configure your app** in Play Console
3. **Implement attestation** in your Android app:

```kotlin
// Android Kotlin example
import com.google.android.play.core.integrity.IntegrityManager
import com.google.android.play.core.integrity.IntegrityManagerFactory

class AttestationService {
    private val integrityManager: IntegrityManager by lazy {
        IntegrityManagerFactory.create(applicationContext)
    }

    suspend fun getAttestationToken(nonce: String): String {
        return suspendCoroutine { continuation ->
            val integrityTokenRequest = IntegrityTokenRequest.builder()
                .setNonce(nonce)
                .build()

            integrityManager.requestIntegrityToken(integrityTokenRequest)
                .addOnSuccessListener { response ->
                    continuation.resume(response.token())
                }
                .addOnFailureListener { exception ->
                    continuation.resumeWithException(exception)
                }
        }
    }
}
```

### iOS - Apple App Attest

1. **Enable App Attest** in your app's capabilities
2. **Implement attestation** in your iOS app:

```swift
// iOS Swift example
import DeviceCheck

class AttestationService {
    func generateAttestation(challenge: Data) async throws -> String {
        guard DCAppAttestService.shared.isSupported else {
            throw AttestationError.notSupported
        }
        
        let keyId = try await DCAppAttestService.shared.generateKey()
        let attestation = try await DCAppAttestService.shared.attestKey(
            keyId, 
            clientDataHash: challenge
        )
        
        return attestation.base64EncodedString()
    }
}
```

## 2. Authentication Flow

### Step 1: Generate Attestation Token

```javascript
// React Native example
import { generateAttestationToken } from './attestation';

async function authenticateWithAttestation(email, password) {
  try {
    // Generate attestation token
    const attestationToken = await generateAttestationToken();
    
    // Login with attestation
    const response = await fetch('/api/v1/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Attestation-Token': attestationToken,
        'X-Platform': Platform.OS // 'android' or 'ios'
      },
      body: JSON.stringify({
        email: email,
        password: password,
        user_type: 'registered_user'
      })
    });

    if (!response.ok) {
      throw new Error(`Authentication failed: ${response.status}`);
    }

    const tokens = await response.json();
    
    // Store tokens securely
    await storeTokensSecurely(tokens);
    
    return tokens;
  } catch (error) {
    console.error('Authentication error:', error);
    throw error;
  }
}
```

### Step 2: Handle Account Lockout

```javascript
async function handleAccountLockout(email) {
  try {
    // Request unlock OTP
    await fetch('/api/v1/auth/request-unlock-otp', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        identifier: email,
        delivery_method: 'sms' // or 'email'
      })
    });

    // Show OTP input dialog
    const otp = await showOTPDialog();

    // Verify OTP and unlock account
    const response = await fetch('/api/v1/auth/verify-unlock-otp', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        identifier: email,
        otp: otp
      })
    });

    if (response.ok) {
      // Account unlocked, can retry login
      return true;
    }
  } catch (error) {
    console.error('Account unlock error:', error);
    return false;
  }
}
```

## 3. Emergency Request Implementation

### Basic Emergency Request

```javascript
class EmergencyService {
  constructor(apiClient) {
    this.apiClient = apiClient;
  }

  async submitEmergencyRequest(serviceType, location, address, description, groupId) {
    try {
      // Get current attestation token
      const attestationToken = await this.generateFreshAttestationToken();
      
      const response = await this.apiClient.post('/emergency/request', {
        service_type: serviceType,
        location: location,
        address: address,
        description: description,
        group_id: groupId
      }, {
        headers: {
          'X-Attestation-Token': attestationToken,
          'X-Platform': Platform.OS
        }
      });

      // Handle call service type - set phone to silent
      if (serviceType === 'call') {
        await this.setSilentMode(true);
      }

      return response.data;
    } catch (error) {
      console.error('Emergency request failed:', error);
      throw error;
    }
  }

  async setSilentMode(enabled) {
    // Platform-specific implementation
    if (Platform.OS === 'android') {
      // Android implementation
      await AndroidSilentMode.setSilentMode(enabled);
    } else if (Platform.OS === 'ios') {
      // iOS implementation
      await IOSSilentMode.setSilentMode(enabled);
    }
  }
}
```

### Real-time Updates with WebSocket

```javascript
class EmergencyWebSocket {
  constructor(accessToken, attestationToken) {
    this.accessToken = accessToken;
    this.attestationToken = attestationToken;
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
  }

  connect() {
    const wsUrl = `wss://api.panicsystem.com/api/v1/ws?token=${this.accessToken}&attestation=${this.attestationToken}`;
    
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleMessage(data);
    };

    this.ws.onclose = () => {
      console.log('WebSocket disconnected');
      this.handleReconnect();
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  handleMessage(data) {
    switch (data.type) {
      case 'request_status_update':
        this.onRequestStatusUpdate(data.payload);
        break;
      case 'agent_location_update':
        this.onAgentLocationUpdate(data.payload);
        break;
      case 'eta_update':
        this.onETAUpdate(data.payload);
        break;
      default:
        console.log('Unknown message type:', data.type);
    }
  }

  handleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = Math.pow(2, this.reconnectAttempts) * 1000; // Exponential backoff
      
      setTimeout(() => {
        console.log(`Reconnecting... Attempt ${this.reconnectAttempts}`);
        this.connect();
      }, delay);
    }
  }
}
```

## 4. Location Services

### GPS Location Handling

```javascript
import Geolocation from '@react-native-community/geolocation';

class LocationService {
  async getCurrentLocation() {
    return new Promise((resolve, reject) => {
      Geolocation.getCurrentPosition(
        (position) => {
          resolve({
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy: position.coords.accuracy
          });
        },
        (error) => {
          reject(error);
        },
        {
          enableHighAccuracy: true,
          timeout: 15000,
          maximumAge: 10000
        }
      );
    });
  }

  async watchLocation(callback) {
    return Geolocation.watchPosition(
      (position) => {
        callback({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy,
          timestamp: position.timestamp
        });
      },
      (error) => {
        console.error('Location watch error:', error);
      },
      {
        enableHighAccuracy: true,
        distanceFilter: 10, // Update every 10 meters
        interval: 5000 // Update every 5 seconds
      }
    );
  }
}
```

## 5. Error Handling

### Comprehensive Error Handler

```javascript
class APIErrorHandler {
  static handle(error) {
    if (error.response) {
      const { status, data } = error.response;
      
      switch (status) {
        case 401:
          return this.handleUnauthorized(data);
        case 403:
          return this.handleForbidden(data);
        case 423:
          return this.handleAccountLocked(data);
        case 429:
          return this.handleRateLimit(data);
        default:
          return this.handleGenericError(data);
      }
    } else if (error.request) {
      return this.handleNetworkError();
    } else {
      return this.handleUnknownError(error);
    }
  }

  static handleUnauthorized(data) {
    if (data.error_code === 'AUTH_001') {
      // Invalid attestation - regenerate
      return { action: 'regenerate_attestation', message: 'App verification failed' };
    } else if (data.error_code === 'AUTH_002') {
      // Expired token - refresh
      return { action: 'refresh_token', message: 'Session expired' };
    }
    return { action: 'login', message: 'Authentication required' };
  }

  static handleAccountLocked(data) {
    return { 
      action: 'unlock_account', 
      message: 'Account is locked. Use OTP to unlock.',
      details: data.details 
    };
  }

  static handleRateLimit(data) {
    const retryAfter = data.details?.retry_after || 60;
    return { 
      action: 'retry_after', 
      message: `Rate limit exceeded. Try again in ${retryAfter} seconds.`,
      retry_after: retryAfter 
    };
  }
}
```

## 6. Security Best Practices

### Token Management

```javascript
import * as Keychain from 'react-native-keychain';

class SecureTokenStorage {
  static async storeTokens(tokens) {
    try {
      await Keychain.setInternetCredentials(
        'panic_system_tokens',
        'access_token',
        JSON.stringify(tokens)
      );
    } catch (error) {
      console.error('Failed to store tokens:', error);
    }
  }

  static async getTokens() {
    try {
      const credentials = await Keychain.getInternetCredentials('panic_system_tokens');
      if (credentials) {
        return JSON.parse(credentials.password);
      }
    } catch (error) {
      console.error('Failed to retrieve tokens:', error);
    }
    return null;
  }

  static async clearTokens() {
    try {
      await Keychain.resetInternetCredentials('panic_system_tokens');
    } catch (error) {
      console.error('Failed to clear tokens:', error);
    }
  }
}
```

### Certificate Pinning

```javascript
// React Native certificate pinning
import { NetworkingModule } from 'react-native';

const certificatePin = 'sha256/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=';

NetworkingModule.addCertificatePinner({
  hostname: 'api.panicsystem.com',
  pin: certificatePin
});
```

## 7. Testing

### Unit Tests

```javascript
// Jest test example
import { EmergencyService } from '../services/EmergencyService';

describe('EmergencyService', () => {
  let emergencyService;
  let mockApiClient;

  beforeEach(() => {
    mockApiClient = {
      post: jest.fn()
    };
    emergencyService = new EmergencyService(mockApiClient);
  });

  test('should submit emergency request successfully', async () => {
    const mockResponse = {
      data: {
        request_id: 'req_123',
        status: 'pending'
      }
    };
    
    mockApiClient.post.mockResolvedValue(mockResponse);

    const result = await emergencyService.submitEmergencyRequest(
      'security',
      { latitude: 40.7128, longitude: -74.0060 },
      '123 Main St',
      'Emergency',
      'group_123'
    );

    expect(result.request_id).toBe('req_123');
    expect(mockApiClient.post).toHaveBeenCalledWith(
      '/emergency/request',
      expect.objectContaining({
        service_type: 'security'
      }),
      expect.any(Object)
    );
  });
});
```

## 8. Performance Optimization

### Request Caching

```javascript
class CachedAPIClient {
  constructor() {
    this.cache = new Map();
    this.cacheTimeout = 5 * 60 * 1000; // 5 minutes
  }

  async get(url, options = {}) {
    const cacheKey = `${url}_${JSON.stringify(options)}`;
    const cached = this.cache.get(cacheKey);

    if (cached && Date.now() - cached.timestamp < this.cacheTimeout) {
      return cached.data;
    }

    const response = await fetch(url, options);
    const data = await response.json();

    this.cache.set(cacheKey, {
      data: data,
      timestamp: Date.now()
    });

    return data;
  }
}
```

This guide provides a comprehensive foundation for integrating mobile applications with the Panic System Platform API. Remember to test thoroughly on both Android and iOS devices, and implement proper error handling and security measures.