# Password Recovery Implementation

This document describes the password recovery functionality that has been added to the Panic System Platform authentication system.

## Overview

The password recovery system allows users to reset their passwords using a secure OTP (One-Time Password) sent via email. The implementation follows security best practices and includes proper error handling and logging.

## Features

- **Secure OTP Generation**: 6-digit random OTP codes with 10-minute expiration
- **Email Delivery**: HTML and plain text email templates for OTP delivery
- **Security**: No information disclosure about account existence
- **Rate Limiting**: Built-in protection against abuse
- **Audit Logging**: Comprehensive logging of all password recovery events
- **Multi-User Support**: Works with both firm personnel and registered users

## API Endpoints

### 1. Request Password Reset OTP

**Endpoint**: `POST /api/v1/auth/password-reset/request`

**Request Body**:
```json
{
  "email": "user@example.com",
  "user_type": "firm_personnel"
}
```

**Response**:
```json
{
  "message": "If the email exists in our system, a password reset code has been sent",
  "expires_in_minutes": 10
}
```

**Features**:
- Always returns success message (no information disclosure)
- Generates and stores OTP in Redis with expiration
- Sends formatted email with OTP code
- Logs all requests for security monitoring

### 2. Verify OTP and Reset Password

**Endpoint**: `POST /api/v1/auth/password-reset/verify`

**Request Body**:
```json
{
  "email": "user@example.com",
  "otp": "123456",
  "new_password": "NewSecurePassword123!",
  "user_type": "firm_personnel"
}
```

**Response**:
```json
{
  "message": "Password reset successfully"
}
```

**Features**:
- Verifies OTP against stored value
- Updates password with bcrypt hashing
- Clears failed login attempts
- Optionally invalidates existing tokens
- One-time use OTP (deleted after verification)

## Implementation Details

### Files Modified/Added

1. **`app/api/v1/auth.py`**
   - Added password reset request and verify endpoints
   - Added request/response models
   - Integrated with auth service

2. **`app/services/auth.py`**
   - Added `request_password_reset_otp()` method
   - Added `verify_password_reset_otp()` method
   - Added helper methods for user lookup and password updates

3. **`app/services/account_security.py`**
   - Enhanced OTP generation and verification
   - Added separate password reset OTP handling
   - Improved Redis-based storage with expiration

4. **`app/services/otp_delivery.py`**
   - Added `send_password_reset_email()` method
   - Professional HTML email templates
   - SMTP configuration handling

### Security Features

1. **No Information Disclosure**
   - Always returns success message regardless of email existence
   - Prevents account enumeration attacks

2. **OTP Security**
   - 6-digit random codes
   - 10-minute expiration
   - One-time use (deleted after verification)
   - Stored securely in Redis

3. **Password Security**
   - bcrypt hashing for new passwords
   - Password strength validation (8+ characters)
   - Existing tokens can be invalidated

4. **Rate Limiting**
   - Built into Redis storage mechanism
   - Prevents brute force attacks

5. **Audit Logging**
   - All requests logged with structured logging
   - Security events tracked
   - Failed attempts monitored

### Email Templates

The system includes professional email templates with:
- Clear OTP display
- Security warnings
- Expiration information
- Branded styling
- Both HTML and plain text versions

## Configuration

### Required Environment Variables

```bash
# SMTP Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
FROM_EMAIL=noreply@yourdomain.com

# Redis Configuration (already configured)
REDIS_URL=redis://localhost:6379/0

# Security Settings (optional)
OTP_EXPIRY_MINUTES=10
OTP_MAX_ATTEMPTS=3
```

### Docker Environment

The implementation works with the existing Docker setup. SMTP configuration can be added to the `docker-compose.yml` environment section:

```yaml
environment:
  - SMTP_SERVER=smtp.gmail.com
  - SMTP_PORT=587
  - SMTP_USERNAME=your_email@gmail.com
  - SMTP_PASSWORD=your_app_password
  - FROM_EMAIL=noreply@yourdomain.com
```

## Testing

### Automated Tests

Run the test suite to verify functionality:

```bash
python3 test_password_recovery_simple.py
```

### Manual Testing

1. **Request OTP**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/password-reset/request \
     -H "Content-Type: application/json" \
     -d '{"email": "admin@paniq.co.za", "user_type": "firm_personnel"}'
   ```

2. **Verify OTP** (use OTP from email):
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/password-reset/verify \
     -H "Content-Type: application/json" \
     -d '{"email": "admin@paniq.co.za", "otp": "123456", "new_password": "NewPassword123!", "user_type": "firm_personnel"}'
   ```

### Test Scenarios

- ✅ Valid email with correct OTP
- ✅ Invalid email (no information disclosure)
- ✅ Expired OTP
- ✅ Invalid OTP
- ✅ Reused OTP (should fail)
- ✅ API documentation generation
- ✅ Existing endpoints still functional

## Monitoring and Logging

### Log Events

The system logs the following events:
- `password_reset_otp_requested` - OTP generation
- `password_reset_otp_generated` - OTP stored in cache
- `password_reset_otp_verified` - Successful OTP verification
- `invalid_password_reset_otp` - Failed OTP verification
- `password_reset_completed` - Password successfully updated

### Metrics

Monitor these metrics for security:
- Password reset request rate
- Failed OTP verification rate
- Successful password resets
- Email delivery failures

## Security Considerations

1. **Rate Limiting**: Consider implementing additional rate limiting at the API gateway level
2. **Account Lockout**: Failed OTP attempts could trigger temporary account lockout
3. **Notification**: Consider sending notification emails when passwords are changed
4. **Audit Trail**: All password changes are logged for compliance
5. **Token Invalidation**: Existing sessions can be invalidated after password reset

## Future Enhancements

1. **SMS Support**: Add SMS delivery option for OTP
2. **Multi-Factor**: Integrate with existing MFA systems
3. **Admin Override**: Allow admins to reset passwords without OTP
4. **Bulk Operations**: Support for bulk password resets
5. **Custom Templates**: Configurable email templates
6. **Webhook Integration**: Notify external systems of password changes

## API Documentation

The endpoints are automatically documented in the OpenAPI specification available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Troubleshooting

### Common Issues

1. **Email Not Sending**
   - Check SMTP configuration
   - Verify credentials and server settings
   - Check firewall/network connectivity

2. **OTP Not Working**
   - Verify Redis is running
   - Check OTP expiration (10 minutes)
   - Ensure OTP hasn't been used already

3. **Password Not Updating**
   - Check database connectivity
   - Verify user exists in database
   - Check password validation rules

### Debug Mode

For development, the system will log OTP codes when SMTP is not configured:
```
SMTP not configured, simulating password reset email to user@example.com with OTP: 123456
```

## Conclusion

The password recovery system provides a secure, user-friendly way for users to reset their passwords. It follows security best practices and integrates seamlessly with the existing authentication system.

The implementation is production-ready and includes comprehensive logging, error handling, and security features to protect against common attacks.