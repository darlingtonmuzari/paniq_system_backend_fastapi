# API Error Codes Reference

This document provides a comprehensive reference for all error codes returned by the Panic System Platform API.

## Error Response Format

All API errors follow this consistent format:

```json
{
  "error_code": "AUTH_001",
  "message": "Invalid attestation token",
  "details": {
    "platform": "android",
    "token_status": "expired"
  },
  "timestamp": "2024-08-24T10:30:00Z",
  "request_id": "req_123456789"
}
```

## Authentication Errors (AUTH_xxx)

| Code | HTTP Status | Message | Description |
|------|-------------|---------|-------------|
| AUTH_001 | 401 | Invalid attestation token | Mobile app attestation failed or expired |
| AUTH_002 | 401 | Expired token | JWT access token has expired |
| AUTH_003 | 403 | Insufficient permissions | User lacks required permissions for action |
| AUTH_004 | 423 | Account locked | Account temporarily locked due to failed attempts |
| AUTH_005 | 429 | Too many failed attempts | Rate limit exceeded for login attempts |
| AUTH_006 | 400 | Account not locked | Attempted to unlock account that isn't locked |
| AUTH_007 | 400 | Invalid OTP | OTP code is incorrect or malformed |
| AUTH_008 | 400 | OTP expired | OTP code has expired (10 minute limit) |
| AUTH_009 | 400 | Invalid delivery method | OTP delivery method must be 'sms' or 'email' |
| AUTH_010 | 401 | Invalid credentials | Email/password combination is incorrect |
| AUTH_011 | 400 | User type required | user_type field is required for login |
| AUTH_012 | 404 | User not found | No user found with provided identifier |

## Subscription Errors (SUB_xxx)

| Code | HTTP Status | Message | Description |
|------|-------------|---------|-------------|
| SUB_001 | 400 | Insufficient credits | Security firm lacks credits for operation |
| SUB_002 | 403 | Subscription expired | User's subscription has expired |
| SUB_003 | 409 | Subscription already applied | Subscription has already been applied to a group |
| SUB_004 | 400 | Invalid product | Subscription product not found or inactive |
| SUB_005 | 400 | User limit exceeded | Group exceeds subscription's maximum user limit |
| SUB_006 | 404 | Subscription not found | Stored subscription not found in user's profile |
| SUB_007 | 403 | Subscription not owned | User doesn't own the specified subscription |
| SUB_008 | 400 | Invalid group | Target group not found or not owned by user |

## Geographic Errors (GEO_xxx)

| Code | HTTP Status | Message | Description |
|------|-------------|---------|-------------|
| GEO_001 | 400 | Location not covered | Location is outside service coverage area |
| GEO_002 | 400 | Invalid coordinates | GPS coordinates are malformed or invalid |
| GEO_003 | 404 | Coverage area not found | Specified coverage area doesn't exist |
| GEO_004 | 400 | Invalid address | Address format is invalid or incomplete |
| GEO_005 | 503 | Geocoding service unavailable | External geocoding service is down |

## Request Errors (REQ_xxx)

| Code | HTTP Status | Message | Description |
|------|-------------|---------|-------------|
| REQ_001 | 409 | Duplicate request | Similar request already exists (rate limiting) |
| REQ_002 | 404 | Request not found | Emergency request not found |
| REQ_003 | 400 | Invalid service type | Service type must be call, security, ambulance, fire, or towing |
| REQ_004 | 400 | Invalid status transition | Cannot change request status to specified value |
| REQ_005 | 403 | Request not assigned | Cannot update request that isn't assigned to user |
| REQ_006 | 400 | Missing location | Location is required for emergency requests |
| REQ_007 | 400 | Invalid priority | Priority must be low, medium, or high |
| REQ_008 | 429 | Request rate limit exceeded | Too many emergency requests in time window |

## User Management Errors (USER_xxx)

| Code | HTTP Status | Message | Description |
|------|-------------|---------|-------------|
| USER_001 | 409 | Email already exists | Email address is already registered |
| USER_002 | 409 | Phone already exists | Phone number is already registered |
| USER_003 | 400 | Invalid phone format | Phone number format is invalid |
| USER_004 | 400 | Phone not verified | Phone number must be verified before use |
| USER_005 | 404 | Group not found | User group not found |
| USER_006 | 403 | Group not owned | User doesn't own the specified group |
| USER_007 | 400 | Invalid user type | User type must be individual, alarm, or camera |
| USER_008 | 409 | Phone already in group | Phone number already exists in group |

## Firm Management Errors (FIRM_xxx)

| Code | HTTP Status | Message | Description |
|------|-------------|---------|-------------|
| FIRM_001 | 409 | Firm already exists | Security firm with registration number exists |
| FIRM_002 | 400 | Invalid registration | Firm registration data is invalid |
| FIRM_003 | 403 | Firm not verified | Firm must be verified before operation |
| FIRM_004 | 404 | Firm not found | Security firm not found |
| FIRM_005 | 400 | Invalid coverage area | Coverage area polygon is invalid |
| FIRM_006 | 403 | Personnel limit exceeded | Firm has reached maximum personnel limit |
| FIRM_007 | 400 | Invalid personnel role | Role must be field_agent, team_leader, or office_staff |

## Payment Errors (PAY_xxx)

| Code | HTTP Status | Message | Description |
|------|-------------|---------|-------------|
| PAY_001 | 400 | Invalid payment method | Payment method is not supported |
| PAY_002 | 402 | Payment failed | Payment processing failed |
| PAY_003 | 400 | Invalid amount | Payment amount is invalid or below minimum |
| PAY_004 | 409 | Payment already processed | Payment has already been processed |
| PAY_005 | 503 | Payment service unavailable | External payment service is down |

## System Errors (SYS_xxx)

| Code | HTTP Status | Message | Description |
|------|-------------|---------|-------------|
| SYS_001 | 500 | Database error | Internal database error occurred |
| SYS_002 | 503 | Service unavailable | Service is temporarily unavailable |
| SYS_003 | 500 | Cache error | Redis cache error occurred |
| SYS_004 | 503 | External service error | External service dependency failed |
| SYS_005 | 429 | Rate limit exceeded | API rate limit exceeded |
| SYS_006 | 413 | Request too large | Request payload exceeds size limit |
| SYS_007 | 400 | Invalid request format | Request format is malformed |

## Validation Errors (VAL_xxx)

| Code | HTTP Status | Message | Description |
|------|-------------|---------|-------------|
| VAL_001 | 422 | Required field missing | Required field is missing from request |
| VAL_002 | 422 | Invalid field format | Field format doesn't match requirements |
| VAL_003 | 422 | Field too long | Field exceeds maximum length |
| VAL_004 | 422 | Field too short | Field is below minimum length |
| VAL_005 | 422 | Invalid enum value | Field value is not in allowed enum values |
| VAL_006 | 422 | Invalid date format | Date format is invalid (use ISO 8601) |
| VAL_007 | 422 | Invalid UUID format | UUID format is invalid |

## WebSocket Errors (WS_xxx)

| Code | Status | Message | Description |
|------|--------|---------|-------------|
| WS_001 | 4001 | Authentication required | WebSocket connection requires authentication |
| WS_002 | 4002 | Invalid token | WebSocket authentication token is invalid |
| WS_003 | 4003 | Connection limit exceeded | Too many concurrent WebSocket connections |
| WS_004 | 4004 | Attestation required | Mobile WebSocket requires app attestation |
| WS_005 | 4005 | Invalid message format | WebSocket message format is invalid |

## Error Handling Best Practices

### Client-Side Error Handling

```javascript
function handleAPIError(error) {
  const { error_code, message, details } = error.response.data;
  
  switch (error_code) {
    case 'AUTH_001':
      // Regenerate attestation token
      return regenerateAttestation();
    
    case 'AUTH_002':
      // Refresh access token
      return refreshToken();
    
    case 'AUTH_004':
      // Show account unlock dialog
      return showAccountUnlockDialog(details);
    
    case 'SUB_002':
      // Show subscription renewal dialog
      return showSubscriptionRenewalDialog();
    
    case 'GEO_001':
      // Show coverage area error with alternatives
      return showCoverageError(details.suggested_firms);
    
    case 'REQ_008':
      // Show rate limit error with retry time
      return showRateLimitError(details.retry_after);
    
    default:
      // Show generic error message
      return showGenericError(message);
  }
}
```

### Retry Logic

```javascript
async function apiCallWithRetry(apiCall, maxRetries = 3) {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await apiCall();
    } catch (error) {
      const { error_code } = error.response?.data || {};
      
      // Don't retry certain errors
      const nonRetryableErrors = [
        'AUTH_003', 'AUTH_004', 'SUB_002', 'SUB_003',
        'GEO_001', 'USER_001', 'USER_002', 'FIRM_001'
      ];
      
      if (nonRetryableErrors.includes(error_code) || attempt === maxRetries) {
        throw error;
      }
      
      // Exponential backoff
      const delay = Math.pow(2, attempt) * 1000;
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
}
```

### Logging Errors

```javascript
function logError(error, context = {}) {
  const errorData = {
    error_code: error.response?.data?.error_code,
    message: error.response?.data?.message,
    status: error.response?.status,
    url: error.config?.url,
    method: error.config?.method,
    timestamp: new Date().toISOString(),
    user_id: context.user_id,
    request_id: error.response?.data?.request_id
  };
  
  // Send to logging service
  console.error('API Error:', errorData);
  
  // Report to crash analytics if critical
  if (error.response?.status >= 500) {
    crashAnalytics.recordError(error, errorData);
  }
}
```

This error code reference should be used alongside the API documentation to implement proper error handling in client applications.