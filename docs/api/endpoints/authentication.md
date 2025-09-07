# Authentication API

The Authentication API handles user login, token management, and account security features including account lockout protection and OTP-based unlock functionality.

## Endpoints

### POST /api/v1/auth/login

Authenticate user and return JWT tokens with account protection.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword",
  "user_type": "registered_user"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

**Account Protection:**
- After 5 failed attempts, account is locked for 30 minutes
- Locked accounts can be unlocked using OTP verification
- Failed attempt counter resets on successful login

**Error Responses:**
- `401 Unauthorized` - Invalid credentials
- `423 Locked` - Account temporarily locked
- `429 Too Many Requests` - Rate limit exceeded

### POST /api/v1/auth/refresh

Refresh access token using refresh token.

**Request Body:**
```json
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

### POST /api/v1/auth/revoke

Revoke (blacklist) a token for security purposes.

**Headers:**
```
Authorization: Bearer YOUR_ACCESS_TOKEN
```

**Request Body:**
```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Response:**
```json
{
  "message": "Token revoked successfully"
}
```

### POST /api/v1/auth/logout

Logout current user by revoking their token.

**Headers:**
```
Authorization: Bearer YOUR_ACCESS_TOKEN
```

**Response:**
```json
{
  "message": "Logged out successfully"
}
```

### GET /api/v1/auth/me

Get current authenticated user information.

**Headers:**
```
Authorization: Bearer YOUR_ACCESS_TOKEN
```

**Response:**
```json
{
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "user@example.com",
  "user_type": "registered_user",
  "permissions": ["read:profile", "write:groups"],
  "firm_id": null,
  "role": null
}
```

### POST /api/v1/auth/verify-token

Verify if the provided token is valid.

**Headers:**
```
Authorization: Bearer YOUR_ACCESS_TOKEN
```

**Response:**
```json
{
  "valid": true,
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "user_type": "registered_user",
  "expires_soon": false
}
```

## Account Protection Features

### POST /api/v1/auth/request-unlock-otp

Request OTP for account unlock when account is locked due to failed login attempts.

**Request Body:**
```json
{
  "identifier": "user@example.com",
  "delivery_method": "email"
}
```

**Response:**
```json
{
  "message": "OTP sent successfully",
  "expires_in_minutes": 10
}
```

**Delivery Methods:**
- `email` - Send OTP to registered email address
- `sms` - Send OTP to registered mobile number

### POST /api/v1/auth/verify-unlock-otp

Verify OTP and unlock account.

**Request Body:**
```json
{
  "identifier": "user@example.com",
  "otp": "123456"
}
```

**Response:**
```json
{
  "message": "Account unlocked successfully"
}
```

**OTP Security:**
- OTP expires after 10 minutes
- Maximum 3 OTP verification attempts
- New OTP required after failed attempts

### GET /api/v1/auth/account-status/{identifier}

Get account lock status and failed attempts information.

**Response:**
```json
{
  "is_locked": false,
  "failed_attempts": 2,
  "max_attempts": 5,
  "remaining_attempts": 3
}
```

## Code Examples

### JavaScript/TypeScript

```typescript
import axios from 'axios';

class AuthClient {
  private baseURL = 'https://api.panicsystem.com/api/v1';
  private accessToken: string | null = null;

  async login(email: string, password: string, userType: string = 'registered_user') {
    try {
      const response = await axios.post(`${this.baseURL}/auth/login`, {
        email,
        password,
        user_type: userType
      });
      
      this.accessToken = response.data.access_token;
      localStorage.setItem('access_token', this.accessToken);
      localStorage.setItem('refresh_token', response.data.refresh_token);
      
      return response.data;
    } catch (error) {
      if (error.response?.status === 423) {
        throw new Error('Account is locked. Please use OTP to unlock.');
      }
      throw error;
    }
  }

  async requestUnlockOTP(identifier: string, deliveryMethod: string = 'email') {
    const response = await axios.post(`${this.baseURL}/auth/request-unlock-otp`, {
      identifier,
      delivery_method: deliveryMethod
    });
    return response.data;
  }

  async verifyUnlockOTP(identifier: string, otp: string) {
    const response = await axios.post(`${this.baseURL}/auth/verify-unlock-otp`, {
      identifier,
      otp
    });
    return response.data;
  }

  async getCurrentUser() {
    if (!this.accessToken) {
      throw new Error('No access token available');
    }

    const response = await axios.get(`${this.baseURL}/auth/me`, {
      headers: {
        Authorization: `Bearer ${this.accessToken}`
      }
    });
    return response.data;
  }
}
```

### Python

```python
import requests
from typing import Optional, Dict, Any

class AuthClient:
    def __init__(self, base_url: str = "https://api.panicsystem.com/api/v1"):
        self.base_url = base_url
        self.access_token: Optional[str] = None

    def login(self, email: str, password: str, user_type: str = "registered_user") -> Dict[str, Any]:
        """Login and store access token"""
        response = requests.post(f"{self.base_url}/auth/login", json={
            "email": email,
            "password": password,
            "user_type": user_type
        })
        
        if response.status_code == 423:
            raise Exception("Account is locked. Please use OTP to unlock.")
        
        response.raise_for_status()
        data = response.json()
        self.access_token = data["access_token"]
        return data

    def request_unlock_otp(self, identifier: str, delivery_method: str = "email") -> Dict[str, Any]:
        """Request OTP for account unlock"""
        response = requests.post(f"{self.base_url}/auth/request-unlock-otp", json={
            "identifier": identifier,
            "delivery_method": delivery_method
        })
        response.raise_for_status()
        return response.json()

    def verify_unlock_otp(self, identifier: str, otp: str) -> Dict[str, Any]:
        """Verify OTP and unlock account"""
        response = requests.post(f"{self.base_url}/auth/verify-unlock-otp", json={
            "identifier": identifier,
            "otp": otp
        })
        response.raise_for_status()
        return response.json()

    def get_current_user(self) -> Dict[str, Any]:
        """Get current user information"""
        if not self.access_token:
            raise Exception("No access token available")
        
        response = requests.get(f"{self.base_url}/auth/me", headers={
            "Authorization": f"Bearer {self.access_token}"
        })
        response.raise_for_status()
        return response.json()
```

## Security Considerations

1. **Token Storage**: Store tokens securely (keychain on mobile, secure storage on web)
2. **Token Rotation**: Implement automatic token refresh before expiration
3. **Account Lockout**: Handle locked account scenarios gracefully
4. **OTP Security**: Implement proper OTP input validation and retry limits
5. **HTTPS Only**: Always use HTTPS for authentication requests
6. **Rate Limiting**: Implement client-side rate limiting to avoid hitting API limits