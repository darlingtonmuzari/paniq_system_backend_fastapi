# Panic System Platform API Documentation

## Overview

The Panic System Platform API is a comprehensive emergency response system that connects security firms, emergency service providers, and end users through mobile applications. This documentation provides detailed information about API endpoints, authentication, and integration patterns.

## Quick Start

### 1. Authentication

All API requests require authentication using JWT tokens. Mobile endpoints additionally require app attestation.

```bash
# Login to get tokens
curl -X POST "https://api.panicsystem.com/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword",
    "user_type": "registered_user"
  }'
```

### 2. Making Authenticated Requests

Include the access token in the Authorization header:

```bash
curl -X GET "https://api.panicsystem.com/api/v1/auth/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 3. Mobile App Attestation

Mobile endpoints require app attestation tokens:

```bash
curl -X POST "https://api.panicsystem.com/api/v1/mobile/users/groups" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "X-Attestation-Token: YOUR_ATTESTATION_TOKEN" \
  -H "X-Platform: android" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Family Group",
    "address": "123 Main St, City, State",
    "location": {"latitude": 40.7128, "longitude": -74.0060}
  }'
```

## API Endpoints

### Authentication & Security
- [Authentication](./endpoints/authentication.md) - Login, token management, account protection
- [App Attestation](./endpoints/attestation.md) - Mobile app integrity verification

### User Management
- [Security Firms](./endpoints/security-firms.md) - Firm registration and management
- [Registered Users](./endpoints/users.md) - User profiles and management
- [Mobile Users](./endpoints/mobile-users.md) - Mobile-specific user operations
- [Personnel](./endpoints/personnel.md) - Firm personnel and team management

### Subscription System
- [Credits](./endpoints/credits.md) - Credit purchase and management
- [Subscriptions](./endpoints/subscriptions.md) - Subscription products and purchases

### Emergency Services
- [Emergency Requests](./endpoints/emergency.md) - Panic request processing
- [Feedback](./endpoints/feedback.md) - Service feedback and ratings
- [WebSocket](./endpoints/websocket.md) - Real-time communication

### Administrative
- [Metrics](./endpoints/metrics.md) - Performance analytics
- [Prank Detection](./endpoints/prank-detection.md) - User fining system
- [System Management](./endpoints/admin.md) - Cache, database, and log management

## Integration Guides

- [Mobile App Integration](./guides/mobile-integration.md) - Complete mobile app setup
- [Security Firm Onboarding](./guides/security-firm-setup.md) - Firm registration process
- [Emergency Response Flow](./guides/emergency-flow.md) - End-to-end emergency handling
- [WebSocket Integration](./guides/websocket-guide.md) - Real-time updates setup

## Error Handling

All API errors follow a consistent format:

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

See [Error Codes](./error-codes.md) for complete error reference.

## Rate Limits

| Endpoint Category | Rate Limit | Window |
|------------------|------------|---------|
| Authentication | 10 requests | 1 minute |
| Emergency Requests | 5 requests | 1 minute |
| General API | 100 requests | 1 minute |
| WebSocket Connections | 5 connections | 1 minute |

## Versioning

The API uses URL versioning with the format `/api/v{version}/`. Current version is `v1`.

Breaking changes will result in a new version. Non-breaking changes are deployed to existing versions.

## Support

- **Documentation**: [https://docs.panicsystem.com](https://docs.panicsystem.com)
- **Support Email**: support@panicsystem.com
- **Status Page**: [https://status.panicsystem.com](https://status.panicsystem.com)

## SDKs and Libraries

- [JavaScript/TypeScript SDK](https://github.com/panicsystem/js-sdk)
- [Python SDK](https://github.com/panicsystem/python-sdk)
- [React Native SDK](https://github.com/panicsystem/react-native-sdk)
- [Flutter SDK](https://github.com/panicsystem/flutter-sdk)