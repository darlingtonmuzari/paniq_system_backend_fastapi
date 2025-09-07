# OTP Troubleshooting Guide

## Issue: Not Receiving OTP Messages

### Root Cause Analysis

1. **SMS Service Not Configured**: The SMS provider credentials are set to placeholder values in the environment configuration
2. **SMTP Server Issues**: The email server `mail.paniq.co.za` is not accessible from the development environment
3. **Fallback Mechanism**: The system falls back to logging OTP codes in the application logs when external services fail

### Current Status

- ✅ **Email OTP Generation**: Working correctly
- ✅ **OTP Verification**: Working correctly  
- ✅ **Resend Verification**: Working correctly
- ❌ **SMS Delivery**: Not configured (placeholder credentials)
- ⚠️ **Email Delivery**: Falls back to console logging in development

### Solutions

#### 1. Send OTP via Email (Current Working Solution)

Use the resend verification endpoint to generate and send OTP codes:

```bash
# Send verification OTP
curl -X POST "http://localhost:8000/api/v1/auth/resend-verification" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com"}'

# Check application logs for the OTP code
docker logs panic-system-api --tail 20
```

#### 2. Using the Helper Script

A helper script has been created at `scripts/send_otp_email.py`:

```bash
# Register a new user and send OTP
python3 scripts/send_otp_email.py register user@example.com +1234567890 John Doe

# Send OTP to existing user
python3 scripts/send_otp_email.py send user@example.com

# Verify OTP
python3 scripts/send_otp_email.py verify user@example.com 123456
```

#### 3. Check Application Logs for OTP

When SMTP is not accessible, the system logs the OTP code:

```bash
# View recent logs
docker logs panic-system-api --tail 50 | grep -i otp

# Look for lines like:
# "SMTP server not accessible, simulating verification email to user@example.com with OTP: 123456"
```

### API Endpoints

#### Resend Verification OTP
- **Endpoint**: `POST /api/v1/auth/resend-verification`
- **Body**: `{"email": "user@example.com"}`
- **Response**: Success message with expiry time

#### Verify Account
- **Endpoint**: `POST /api/v1/auth/verify-account`  
- **Body**: `{"email": "user@example.com", "otp": "123456"}`
- **Response**: Verification status

#### Phone Verification (Alternative)
- **Request OTP**: `POST /api/v1/users/verify-phone`
- **Verify OTP**: `POST /api/v1/users/verify-otp`

### Configuration for Production

To enable actual email/SMS delivery in production:

#### Email Configuration
Update `.env` with working SMTP credentials:
```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=noreply@yourcompany.com
```

#### SMS Configuration
Update `.env` with real SMS provider credentials:
```env
SMS_API_KEY=your-real-sms-api-key
SMS_API_URL=https://api.twilio.com/2010-04-01/Accounts/YOUR_ACCOUNT_SID/Messages.json
```

### Testing Workflow

1. **Register a new user**:
   ```bash
   python3 scripts/send_otp_email.py register test@example.com +1234567890 Test User
   ```

2. **Check logs for OTP**:
   ```bash
   docker logs panic-system-api --tail 10 | grep "OTP:"
   ```

3. **Verify the OTP**:
   ```bash
   python3 scripts/send_otp_email.py verify test@example.com 123456
   ```

### Recent Test Results

- ✅ User registration: `verification.test@paniq.co.za` created successfully
- ✅ OTP generation: `338084` generated and logged
- ✅ OTP verification: Successfully verified and account activated
- ✅ Resend functionality: Working correctly

### Next Steps

1. **For Development**: Continue using the log-based OTP system
2. **For Production**: Configure proper SMTP and SMS credentials
3. **For Testing**: Use the provided helper script for easy OTP management

The OTP system is fully functional - the only issue is delivery method configuration for the development environment.