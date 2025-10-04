# Test Credentials & User Accounts

## Overview
This file contains all test credentials and user accounts for the Panic System Platform. These accounts are created by sample data scripts and are intended for development and testing purposes only.

⚠️ **SECURITY WARNING**: These are test credentials only. Never use these in production environments.

---

## System Admin Accounts

### Platform Super Admin
- **Email**: `admin@paniq.co.za`
- **Password**: `Password@2025` (updated for development)
- **Role**: admin
- **Permissions**: Full system access, all administrative functions
- **Firm**: Platform Headquarters
- **Status**: Active
- **Created by**: `scripts/create_super_admin.py`

### System Seeder Account
- **Email**: `system@paniq.co.za`
- **Password**: N/A (cannot login - system account)
- **Role**: System seeder
- **Purpose**: Used for seeding document types and system data
- **Created by**: `scripts/seed_document_types.py`

---

## Security Firm Admin Accounts

### Demo Security Firm Admin
- **Email**: `admin@securityfirm.com`
- **Password**: `Password@2025`
- **Role**: firm_admin
- **Firm**: Demo Security Services
- **Permissions**: Firm management, personnel management, coverage areas
- **Status**: Active
- **Reference**: DEMO_CREDENTIALS.md

### Sample Security Firm Admin
- **Email**: `admin@sample.com`
- **Password**: `Password@2025`
- **Role**: Security Firm Administrator
- **Firm**: Sample Security Firm
- **Created by**: `insert_emergency_sample_data.py`

### Cape Town Security Admin
- **Email**: `admin@ctss.co.za`
- **Password**: `Password@2025`
- **Role**: Security Firm Administrator
- **Firm**: Cape Town Security Services
- **Created by**: `create_emergency_sample_data.py`

---

## Personnel & Staff Accounts

### Demo Field Agent
- **Email**: `agent@securityfirm.com`
- **Password**: `Password@2025`
- **Role**: firm_field_security
- **Firm**: Demo Security Services
- **Permissions**: Emergency response, request management
- **Status**: Active
- **Reference**: DEMO_CREDENTIALS.md

### Manica Solutions Personnel
- **Email**: `darlington@manicasolutions.com`
- **Password**: `Password@2025`
- **Role**: Firm Personnel
- **Firm**: Manica Solutions
- **Usage**: Used in token generation and testing scripts
- **Files**: `generate_test_token.py`, `generate_fresh_token.py`, `generate_debug_token.py`

### Test Personnel Account
- **Email**: `test.personnel@example.com`
- **Password**: `Password@2025`
- **Role**: Personnel
- **Purpose**: RBAC testing
- **Created by**: `scripts/test_personnel_rbac.py`

---

## Mobile User Accounts

### Demo Mobile User
- **Phone**: `+27123456789`
- **PIN**: `1234`
- **Status**: Active subscriber
- **Location**: Johannesburg area
- **Reference**: DEMO_CREDENTIALS.md

### Test Mobile User
- **Email**: `panic.test@example.com`
- **Phone**: Generated during sample data creation
- **Purpose**: Panic request testing
- **Created by**: `create_sample_panic_requests_simple.py`

---

## Emergency Service Provider Contacts

### Rapid Response Emergency
- **Contact Email**: `dispatch@rapidresponse.co.za`
- **Type**: Ambulance Service
- **Status**: Active

### City Tow Services
- **Contact Email**: `dispatch@citytow.co.za`
- **Type**: Tow Truck Service
- **Status**: Active

### Elite Security
- **Contact Email**: `ops@elitesecurity.co.za`
- **Type**: Security Service
- **Status**: Active

### Cape Town Emergency Medical
- **Contact Email**: `dispatch@ctem.co.za`
- **Type**: Medical Service
- **Status**: Active

### Atlantic Towing
- **Contact Email**: `operations@atlantictowing.co.za`
- **Type**: Tow Truck Service
- **Status**: Active

### Metro Security
- **Contact Email**: `control@metrosecurity.co.za`
- **Type**: Security Service
- **Status**: Active

### SS Ambulance
- **Contact Email**: `emergency@ssambulance.co.za`
- **Type**: Ambulance Service
- **Status**: Active

---

## Test User Roles & Permissions

### Role Hierarchy
1. **Platform Administrator** (`admin`)
   - Full system access
   - Manage all security firms
   - System configuration

2. **Security Firm Administrator** (`firm_admin`)
   - Manage own firm
   - Personnel management
   - Coverage area management
   - Financial operations

3. **Firm Supervisor** (`firm_supervisor`)
   - Oversee operations
   - Manage field personnel
   - Monitor emergency requests

4. **Team Leader** (`firm_team_leader`)
   - Lead response teams
   - Coordinate field operations
   - Field personnel management

5. **Field Security** (`firm_field_security`)
   - Respond to emergencies
   - Update request status
   - Location reporting

6. **Office Staff** (`firm_staff`)
   - Administrative tasks
   - Customer support
   - Data entry

7. **Registered User** (`registered_user`)
   - Mobile app access
   - Emergency requests
   - Subscription management

---

## API Testing Credentials

### Login Endpoints

#### Security Firm Personnel Login
```bash
curl -X POST "http://localhost:8010/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@securityfirm.com",
    "password": "Password@2025",
    "user_type": "firm_personnel"
  }'
```

#### Platform Admin Login
```bash
curl -X POST "http://localhost:8010/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@paniq.co.za",
    "password": "Password@2025",
    "user_type": "firm_personnel"
  }'
```

#### Mobile User Login
```bash
curl -X POST "http://localhost:8010/api/v1/mobile/auth/login" \
  -H "Content-Type: application/json" \
  -H "X-Platform: android" \
  -H "X-Attestation-Token: demo-token" \
  -d '{
    "phone": "+27123456789",
    "pin": "1234"
  }'
```

---

## System Email Configuration

### SMTP Settings
- **Server**: `mail.paniq.co.za`
- **Port**: `587`
- **Username**: `no-reply@paniq.co.za`
- **Password**: `14Dmin@2025`
- **From Email**: `no-reply@paniq.co.za`

### Test Email Recipients
- `darlingtonmuzari@gmail.com` - Used for password reset testing
- `test.manicasolutions@gmail.com` - Personnel email testing

---

## Database Sample Data

### Security Firms
1. **Demo Security Services**
   - Coverage: Johannesburg area
   - Personnel: Multiple roles
   - Status: Active

2. **Sample Security Firm**
   - Coverage: Various areas
   - Emergency providers: Multiple types
   - Status: Active

3. **Cape Town Security Services**
   - Coverage: Cape Town area
   - Providers: Medical, Towing, Security
   - Status: Active

### Credit Tiers
- **Basic**: 100 credits for R50
- **Standard**: 250 credits for R120
- **Premium**: 500 credits for R200
- **Enterprise**: 1000 credits for R350

### Subscription Products
- 8 active subscription products with various pricing tiers
- Different user limits and feature sets

---

## Token Generation Scripts

### Available Scripts
- `generate_admin_token.py` - Generate admin tokens
- `generate_test_token.py` - Generate test user tokens
- `generate_fresh_token.py` - Generate fresh tokens for existing users
- `generate_debug_token.py` - Generate debugging tokens
- `generate_agent_token_quick.py` - Quick agent token generation
- `generate_manica_token.py` - Manica Solutions specific tokens

### Usage Example
```bash
python3 generate_admin_token.py
python3 generate_test_token.py
```

---

## Coverage Areas & Testing Locations

### Johannesburg Test Locations
- **Latitude**: `-26.2041`
- **Longitude**: `28.0473`
- **Coverage**: Demo Security Services

### Cape Town Test Locations
- **Latitude**: `-33.9249`
- **Longitude**: `18.4241`
- **Coverage**: Cape Town Security Services

### Additional Test Areas
Multiple areas across Cape Town including:
- Sea Point, Camps Bay, Hout Bay
- Constantia, Observatory, Woodstock
- Bellville, Parow, Durbanville
- Milnerton, Table View

---

## Emergency Request Testing

### Sample Emergency Types
- Panic button
- Medical emergency
- Security incident
- Vehicle breakdown
- Fire emergency

### Test Request Data
```json
{
  "latitude": -26.2041,
  "longitude": 28.0473,
  "emergency_type": "panic",
  "description": "Emergency assistance needed"
}
```

---

## Payment Testing

### Ozow Integration
- Use Ozow sandbox credentials for payment testing
- Test credit purchases and subscriptions
- Verify payment status callbacks

### Test Payment Amounts
- R50, R120, R200, R350 (matching credit tiers)
- Various subscription amounts based on products

---

## Important Notes

🔒 **Security**
- These credentials are for development/testing only
- Never use in production environments
- Regularly rotate passwords in production

📱 **Mobile Testing**
- Include required attestation headers
- Use appropriate platform identifiers
- Test on supported coverage areas

🌍 **Geographic Testing**
- Test locations are within demo firm coverage areas
- Use provided coordinates for consistent results
- Test both Johannesburg and Cape Town areas

⚙️ **API Testing**
- All endpoints require proper authentication
- Include platform headers for mobile endpoints
- Use appropriate user types for different operations

---

## Support & Maintenance

### Adding New Test Users
1. Use existing sample data scripts as templates
2. Follow the established naming conventions
3. Update this document with new credentials
4. Test all login flows after creation

### Updating Passwords
1. Use `update_admin_password.py` for admin accounts
2. Update personnel passwords through API endpoints
3. Mobile users: Use PIN reset functionality
4. Document changes in this file

### Cleaning Test Data
1. Review and remove obsolete test accounts
2. Update sample data scripts as needed
3. Maintain security firm associations
4. Preserve essential system accounts

---

**Last Updated**: October 2025
**Version**: 1.0
**Maintainer**: Platform Development Team