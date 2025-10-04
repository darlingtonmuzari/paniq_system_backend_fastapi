# Mobile Authentication API Documentation

## Overview

The Mobile Authentication API provides secure authentication endpoints specifically designed for mobile applications with enhanced security features including device attestation, rate limiting, and comprehensive audit logging.

## Base URL

```
POST /api/v1/auth/mobile/*
```

## Security Features

### 1. Device Attestation
- **Android**: Google Play Integrity API verification
- **iOS**: Apple App Attest validation
- **Configurable**: Can be enabled/disabled via `REQUIRE_MOBILE_ATTESTATION` setting

### 2. Rate Limiting
- Registration: 3 attempts per 5 minutes
- Login: 10 attempts per 5 minutes  
- Email verification: 5 attempts per 5 minutes
- Password reset: 3 requests per 10 minutes
- Global: 60 requests per minute, 100 auth requests per hour

### 3. Enhanced Password Validation
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- At least one special character

### 4. Session Management
- Unique session IDs for tracking
- Device fingerprinting
- Automatic session cleanup

## Endpoints

### 1. User Registration

**Endpoint:** `POST /mobile/register`

**Description:** Register a new mobile user with enhanced security validation.

**Request Body:**
```json
{
  "email": "user@example.com",
  "phone": "+27123456789",
  "first_name": "John",
  "last_name": "Doe",
  "password": "SecurePass123!",
  "device_info": {
    "device_id": "unique_device_identifier",
    "device_type": "android",
    "device_model": "Samsung Galaxy S21",
    "os_version": "Android 13",
    "app_version": "1.0.0",
    "platform_version": "33"
  },
  "security_attestation": {
    "attestation_token": "play_integrity_token",
    "integrity_verdict": "MEETS_DEVICE_INTEGRITY,MEETS_BASIC_INTEGRITY",
    "timestamp": "2025-01-20T10:30:00.000Z",
    "nonce": "cryptographic_nonce"
  }
}
```

**Response (201 Created):**
```json
{
  "message": "Registration successful. Please verify your email to complete the process.",
  "user_id": "uuid",
  "email_verification_sent": true,
  "session_id": "session_identifier",
  "requires_verification": true
}
```

**Error Responses:**
- `400 Bad Request`: Validation errors, weak password, existing email
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

### 2. Email Verification

**Endpoint:** `POST /mobile/verify-email`

**Description:** Verify user's email address with OTP code.

**Request Body:**
```json
{
  "email": "user@example.com",
  "verification_code": "123456",
  "session_id": "session_identifier"
}
```

**Response (200 OK):**
```json
{
  "verified": true,
  "message": "Email verified successfully. You can now log in.",
  "can_login": true
}
```

### 3. Resend Verification

**Endpoint:** `POST /mobile/resend-verification`

**Description:** Resend email verification code.

**Request Body:**
```json
{
  "email": "user@example.com",
  "session_id": "session_identifier"
}
```

**Response (200 OK):**
```json
{
  "sent": true,
  "message": "Verification code sent to your email",
  "expires_in_minutes": 10
}
```

### 4. Mobile Login

**Endpoint:** `POST /mobile/login`

**Description:** Authenticate mobile user with enhanced security checks.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "device_info": {
    "device_id": "unique_device_identifier",
    "device_type": "android",
    "device_model": "Samsung Galaxy S21",
    "os_version": "Android 13",
    "app_version": "1.0.0",
    "platform_version": "33"
  },
  "security_attestation": {
    "attestation_token": "play_integrity_token",
    "integrity_verdict": "MEETS_DEVICE_INTEGRITY",
    "timestamp": "2025-01-20T10:30:00.000Z",
    "nonce": "cryptographic_nonce"
  },
  "biometric_hash": "optional_biometric_hash"
}
```

**Response (200 OK):**
```json
{
  "access_token": "jwt_access_token",
  "refresh_token": "jwt_refresh_token",
  "token_type": "Bearer",
  "expires_in": 3600,
  "user_id": "uuid",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "is_verified": true,
  "device_registered": true,
  "requires_additional_verification": false,
  "session_id": "session_identifier"
}
```

**Error Responses:**
- `401 Unauthorized`: Invalid credentials, unverified account
- `403 Forbidden`: Device attestation failed (if required)
- `429 Too Many Requests`: Rate limit exceeded

### 5. Password Reset Request

**Endpoint:** `POST /mobile/password-reset/request`

**Description:** Request password reset code via email.

**Request Body:**
```json
{
  "email": "user@example.com",
  "device_info": {
    "device_id": "unique_device_identifier",
    "device_type": "android",
    "device_model": "Samsung Galaxy S21",
    "os_version": "Android 13",
    "app_version": "1.0.0",
    "platform_version": "33"
  }
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Password reset code sent to your email",
  "expires_in_minutes": 10,
  "session_id": "reset_session_identifier"
}
```

### 6. Password Reset Verification

**Endpoint:** `POST /mobile/password-reset/verify`

**Description:** Verify reset code and set new password.

**Request Body:**
```json
{
  "email": "user@example.com",
  "reset_code": "123456",
  "new_password": "NewSecurePass123!",
  "device_info": {
    "device_id": "unique_device_identifier",
    "device_type": "android",
    "device_model": "Samsung Galaxy S21",
    "os_version": "Android 13",
    "app_version": "1.0.0",
    "platform_version": "33"
  }
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Password reset successfully. You can now log in with your new password.",
  "can_login": true,
  "session_id": "completion_session_identifier"
}
```

### 7. Device Registration

**Endpoint:** `POST /mobile/register-device`

**Description:** Register device for push notifications (requires authentication).

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "device_token": "push_notification_token",
  "device_info": {
    "device_id": "unique_device_identifier",
    "device_type": "android",
    "device_model": "Samsung Galaxy S21",
    "os_version": "Android 13",
    "app_version": "1.0.0",
    "platform_version": "33"
  }
}
```

**Response (200 OK):**
```json
{
  "registered": true,
  "message": "Device registered successfully for push notifications",
  "device_id": "unique_device_identifier"
}
```

### 8. Security Status

**Endpoint:** `GET /mobile/security-status?device_id=<device_id>`

**Description:** Get security status and recommendations (requires authentication).

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
  "user_id": "uuid",
  "email_verified": true,
  "device_registered": true,
  "attestation_valid": true,
  "biometric_enabled": false,
  "last_login": "2025-01-20T10:30:00.000Z",
  "security_level": "high",
  "recommendations": [
    "Enable biometric authentication for faster and more secure login"
  ]
}
```

### 9. Mobile Logout

**Endpoint:** `POST /mobile/logout?device_id=<device_id>&session_id=<session_id>`

**Description:** Logout and cleanup device sessions (requires authentication).

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
  "logged_out": true,
  "message": "Logged out successfully",
  "session_cleared": true,
  "device_cleared": true
}
```

## Error Handling

All endpoints return consistent error formats:

```json
{
  "error": "error_type",
  "message": "Human readable error message",
  "details": "Additional error details",
  "timestamp": "2025-01-20T10:30:00.000Z",
  "request_id": "uuid"
}
```

## Rate Limiting Headers

Rate-limited responses include these headers:

```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 300
Retry-After: 120
```

## Security Headers

All responses include security headers:

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Content-Security-Policy: default-src 'self'; ...
```

## Device Attestation Implementation

### Android (Play Integrity API)

1. Generate nonce in your app
2. Call Play Integrity API with your app's package name
3. Include the integrity token in `security_attestation.integrity_verdict`
4. Server validates the token with Google's servers

### iOS (App Attest)

1. Generate key pair using App Attest
2. Create attestation with your app's Team ID and Bundle ID  
3. Include the attestation token in `security_attestation.app_attest_token`
4. Server validates with Apple's servers

## Testing

Use the provided test script:

```bash
python test_mobile_auth_endpoints.py
```

This script tests:
- User registration flow
- Email verification
- Login attempts
- Password reset flow
- Rate limiting
- Security headers
- Device attestation validation

## Configuration

Key settings in `app/core/config.py`:

```python
# Mobile attestation (set to True in production)
REQUIRE_MOBILE_ATTESTATION: bool = False

# Play Integrity API settings
GOOGLE_PLAY_INTEGRITY_PACKAGE_NAME: str = "za.co.paniq"
GOOGLE_PLAY_INTEGRITY_API_KEY: Optional[str] = None

# App Attest settings  
APPLE_APP_ATTEST_TEAM_ID: str = "YOUR_TEAM_ID"
APPLE_APP_ATTEST_BUNDLE_ID: str = "za.co.paniq.client"
```

## Security Best Practices

1. **Always use HTTPS** in production
2. **Enable device attestation** for production apps
3. **Validate all input** on both client and server
4. **Monitor rate limiting** and adjust limits as needed
5. **Rotate JWT secrets** regularly
6. **Log security events** for audit trails
7. **Use biometric authentication** when available
8. **Implement certificate pinning** in mobile apps
9. **Validate app signatures** during attestation
10. **Monitor for suspicious patterns** in login attempts

## Audit Logging

All sensitive operations are logged with:
- Timestamp
- User ID and email
- Device ID
- Client IP address
- Operation result
- Additional context

Logs are stored in Redis with 30-day retention for compliance and security monitoring.