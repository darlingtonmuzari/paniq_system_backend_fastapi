# Email Verification System Guide

## Overview
The Paniq platform has two separate verification systems:

### 1. Phone Verification (SMS-based)
- **Endpoint:** `POST /api/v1/users/verify-phone`
- **Purpose:** Verify phone numbers for SMS notifications
- **Delivery:** SMS (currently simulated - logs OTP to console)
- **Use case:** For users who want SMS alerts

### 2. Email Verification (Email-based)
- **Endpoint:** `POST /api/v1/auth/resend-verification`
- **Purpose:** Verify email addresses for account activation
- **Delivery:** Email (fully functional)
- **Use case:** For account registration and email notifications

## Working Email Verification

### Step 1: Register a User
```bash
curl -X POST http://localhost:8000/api/v1/users/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your-email@example.com",
    "phone": "+1234567890",
    "first_name": "Your",
    "last_name": "Name"
  }'
```

### Step 2: Request Email Verification
```bash
curl -X POST http://localhost:8000/api/v1/auth/resend-verification \
  -H "Content-Type: application/json" \
  -d '{"email": "your-email@example.com"}'
```

**Response:**
```json
{
  "message": "Verification code sent to your email",
  "expires_in_minutes": 10
}
```

### Step 3: Check Your Email
You should receive an email with:
- Subject: "Account Verification Code - Paniq"
- 6-digit OTP code
- 10-minute expiration

### Step 4: Verify Account
```bash
curl -X POST http://localhost:8000/api/v1/auth/verify-account \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your-email@example.com",
    "otp": "123456"
  }'
```

## Email Configuration Status

✅ **SMTP Server:** mail.paniq.co.za:587  
✅ **Authentication:** Working  
✅ **TLS/SSL:** Configured  
✅ **Email Delivery:** Functional  

## Test Results

### Email Test (2025-08-26)
- **Status:** ✅ SUCCESS
- **SMTP Response:** `250 OK id=1uqtrJ-0000000DldB-48kT`
- **Delivery Time:** ~3.4 seconds
- **Email Format:** HTML + Plain text

### API Test Results
- **Registration:** ✅ Working
- **Email Verification:** ✅ Working
- **OTP Generation:** ✅ Working
- **Database Storage:** ✅ Working

## Troubleshooting

### If You Don't Receive Email:

1. **Check Spam/Junk Folder**
   - Emails from `no-reply@paniq.co.za` might be filtered

2. **Verify Email Address**
   - Ensure the email address is correct in the request

3. **Check API Response**
   - Should return: `"message": "Verification code sent to your email"`

4. **Check Logs**
   ```bash
   docker logs panic-system-api --tail 50 | grep verification
   ```

5. **Test Email Delivery**
   ```bash
   python3 scripts/send_working_email.py your-email@example.com
   ```

## Current Status

✅ **Email verification system is fully functional**  
✅ **SMTP configuration is working correctly**  
✅ **OTP delivery via email is operational**  

The system is ready for production use with email-based account verification.