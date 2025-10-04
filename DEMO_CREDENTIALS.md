# Demo Credentials & Test Data

## Overview
This file contains demo credentials and test data for the Panic System Platform API.

## Admin/Test Users

### Security Firm Admin
- **Email**: admin@securityfirm.com
- **Password**: Password@2025
- **Role**: Security Firm Administrator
- **Firm**: Demo Security Services

### Agent/Personnel
- **Email**: agent@securityfirm.com  
- **Password**: Password@2025
- **Role**: Field Agent
- **Firm**: Demo Security Services

### Mobile User
- **Phone**: +27123456789
- **PIN**: 1234
- **Status**: Active subscriber

## API Testing

### Authentication Endpoints
```bash
# Login as security firm admin
curl -X POST "http://localhost:8010/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@securityfirm.com",
    "password": "Password@2025"
  }'

# Mobile user login
curl -X POST "http://localhost:8010/api/v1/mobile/auth/login" \
  -H "Content-Type: application/json" \
  -H "X-Platform: android" \
  -H "X-Attestation-Token: demo-token" \
  -d '{
    "phone": "+27123456789",
    "pin": "1234"
  }'
```

### Sample API Calls

#### Health Check
```bash
curl http://localhost:8010/health
```

#### Get Security Firms (requires auth token)
```bash
curl -X GET "http://localhost:8010/api/v1/security-firms/" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### Create Emergency Request (mobile)
```bash
curl -X POST "http://localhost:8010/api/v1/mobile/emergency/request" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_MOBILE_JWT_TOKEN" \
  -H "X-Platform: android" \
  -H "X-Attestation-Token: demo-token" \
  -d '{
    "latitude": -26.2041,
    "longitude": 28.0473,
    "emergency_type": "panic",
    "description": "Emergency assistance needed"
  }'
```

## Database Demo Data

The app starts with some pre-loaded demo data:
- 2 Security firms with coverage areas
- 8 Active subscription products
- Sample emergency provider types
- Credit tier configurations

## Testing Locations

### Johannesburg Coverage Area
- **Latitude**: -26.2041
- **Longitude**: 28.0473
- **Coverage**: Demo Security Services

### Cape Town Test Location  
- **Latitude**: -33.9249
- **Longitude**: 18.4241
- **Coverage**: Available

## Mobile App Testing

For mobile endpoints, include these headers:
```
X-Platform: android|ios
X-Attestation-Token: demo-token
```

## Admin Operations

### Generate Admin Token (for testing)
```bash
python3 generate_admin_token.py
```

### Test Emergency Assignment
```bash
python3 test_emergency_api.py
```

## Important Notes

⚠️ **Demo Only**: These are test credentials for development/demo purposes
🔒 **Security**: Never use these credentials in production
📱 **Mobile**: Mobile endpoints require attestation headers
🌍 **Coverage**: Test locations are within demo firm coverage areas

## Subscription Testing

### Credit Tiers Available
- Basic: 100 credits for R50
- Standard: 250 credits for R120  
- Premium: 500 credits for R200
- Enterprise: 1000 credits for R350

### Payment Testing
Use Ozow sandbox credentials for payment testing.

## Support

For additional test data or credentials, check the sample data scripts:
- `add_emergency_sample_data.py`
- `create_sample_panic_requests.py`
- `generate_test_token.py`