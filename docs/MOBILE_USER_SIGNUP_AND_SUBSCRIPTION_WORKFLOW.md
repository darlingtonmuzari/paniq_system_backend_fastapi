# 📱 Mobile User Signup & Subscription Workflow

**Version:** 1.0  
**Last Updated:** 2025-09-19  
**System:** Panic Emergency Response System

---

## 📋 Overview

This document outlines the complete end-to-end workflow for mobile users from initial signup through subscription management, covering registration, account activation, group creation, subscription purchase, allocation, usage tracking, and renewal processes.

## 🎯 Key Concepts

| Concept | Definition |
|---------|------------|
| **Registered User** | Individual who has signed up for the mobile app |
| **User Group** | Location-based entity (home, business) that can receive emergency services |
| **Subscription Product** | Service package offered by security firms |
| **Stored Subscription** | Purchased subscription not yet applied to a group |
| **Active Subscription** | Subscription applied to a specific user group |
| **Coverage Area** | Geographic region where a security firm provides services |

---

## 🔄 Complete Workflow Process

### **Step 1: 📝 Mobile User Registration**

**Endpoint:** `POST /api/v1/mobile/users/register`

**Process:**
1. User downloads mobile app
2. User provides registration details
3. System creates user account (unverified)
4. Verification process initiated

**Registration Payload:**
```json
{
  "email": "john.doe@example.com",
  "phone": "+27123456789", 
  "first_name": "John",
  "last_name": "Doe"
}
```

**System Actions:**
- ✅ Creates `RegisteredUser` record
- ✅ Sets `is_verified = false`
- ✅ Generates secure password automatically
- ✅ Initiates phone/email verification
- ✅ Returns user profile

**Database Schema:**
```sql
CREATE TABLE registered_users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20) UNIQUE NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255),
    role VARCHAR(20) DEFAULT 'user',
    is_verified BOOLEAN DEFAULT FALSE,
    prank_flags INTEGER DEFAULT 0,
    total_fines DECIMAL(10,2) DEFAULT 0,
    is_suspended BOOLEAN DEFAULT FALSE,
    is_locked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

### **Step 2: ✅ Account Activation & Verification**

**Verification Methods:**

**A. Phone Verification (Primary)**
```json
POST /api/v1/auth/request-otp
{
  "phone": "+27123456789",
  "user_type": "registered_user"
}
```

**B. Email Verification (Alternative)**
```json
POST /api/v1/auth/verify-email
{
  "email": "john.doe@example.com",
  "verification_code": "ABC123"
}
```

**Verification Process:**
1. **OTP Generation**: System sends 6-digit code via SMS
2. **Code Submission**: User enters code in mobile app
3. **Verification**: System validates and activates account
4. **Account Status**: `is_verified = true`

**Post-Verification:**
- ✅ User can log into mobile app
- ✅ Access to subscription marketplace
- ✅ Ability to create user groups
- ✅ Password can be set/updated

---

### **Step 3: 🔐 Mobile App Login**

**Endpoint:** `POST /api/v1/auth/login`

**Login Process:**
```json
{
  "email": "john.doe@example.com",
  "password": "securePassword123",
  "user_type": "registered_user"
}
```

**Authentication Response:**
```json
{
  "access_token": "eyJhbGci...",
  "refresh_token": "eyJhbGci...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "id": "user-uuid",
  "first_name": "John",
  "last_name": "Doe",
  "email": "john.doe@example.com",
  "phone": "+27123456789",
  "role": "user",
  "is_active": true
}
```

**Mobile App Features Unlocked:**
- 📱 User profile management
- 🏠 Group creation and management
- 🛒 Subscription marketplace
- 🚨 Emergency panic button (if subscribed)
- 📊 Usage statistics

---

### **Step 4: 🏠 User Group Creation**

**Endpoint:** `POST /api/v1/mobile/users/groups`

**Purpose:** Groups represent locations that need emergency services (home, office, etc.)

**Group Creation Process:**
```json
{
  "name": "Smith Family Home",
  "address": "123 Oak Street, Sandton, Johannesburg", 
  "latitude": -26.1076,
  "longitude": 28.0567,
  "mobile_numbers": [
    {
      "phone_number": "+27123456789",
      "user_type": "individual"
    },
    {
      "phone_number": "+27987654321", 
      "user_type": "individual"
    }
  ]
}
```

**System Validations:**
- ✅ Address geocoding verification
- ✅ Coverage area analysis
- ✅ Phone number uniqueness
- ✅ Location accuracy validation

**Database Schema:**
```sql
CREATE TABLE user_groups (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES registered_users(id),
    name VARCHAR(255) NOT NULL,
    address TEXT NOT NULL,
    location GEOMETRY(POINT, 4326), -- PostGIS location
    subscription_id UUID,
    subscription_expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE group_mobile_numbers (
    id UUID PRIMARY KEY,
    group_id UUID REFERENCES user_groups(id),
    phone_number VARCHAR(20) NOT NULL,
    user_type VARCHAR(20) NOT NULL, -- individual, alarm, camera
    is_verified BOOLEAN DEFAULT FALSE
);
```

**Group Features:**
- 📍 GPS location tracking
- 📞 Multiple phone numbers support
- 🏷️ Named locations for easy identification
- 📱 Mobile number verification

---

### **Step 5: 🛒 Subscription Marketplace Browsing**

**Endpoint:** `GET /api/v1/mobile/subscriptions/products`

**Process:**
1. User views available subscription products
2. Products filtered by location coverage
3. Comparison of features and pricing
4. Security firm information displayed

**Marketplace Response:**
```json
{
  "products": [
    {
      "id": "prod-uuid-1",
      "firm_id": "firm-uuid-1", 
      "firm_name": "SecureGuard Solutions",
      "name": "Premium Home Security",
      "description": "24/7 monitoring with rapid response",
      "max_users": 5,
      "price": 299.99,
      "credit_cost": 150,
      "is_active": true,
      "coverage_areas": ["Sandton", "Rosebank", "Fourways"],
      "response_time": "< 8 minutes",
      "services": ["security", "medical", "fire", "roadside"]
    },
    {
      "id": "prod-uuid-2",
      "firm_id": "firm-uuid-2",
      "firm_name": "Elite Protection Services", 
      "name": "Business Security Plus",
      "description": "Comprehensive business protection",
      "max_users": 10,
      "price": 599.99,
      "credit_cost": 300,
      "is_active": true,
      "coverage_areas": ["Johannesburg CBD", "Sandton"],
      "response_time": "< 5 minutes",
      "services": ["security", "medical", "fire"]
    }
  ]
}
```

**Selection Criteria:**
- 📍 **Location Coverage**: Products available in user's area
- 💰 **Pricing**: Monthly subscription cost
- 👥 **User Capacity**: Maximum users per group
- ⏱️ **Response Time**: Emergency response SLA
- 🚨 **Services**: Types of emergency coverage

---

### **Step 6: 💳 Subscription Purchase**

**Endpoint:** `POST /api/v1/mobile/subscriptions/purchase`

**Purchase Process:**
```json
{
  "product_id": "prod-uuid-1",
  "payment_method": "card",
  "payment_data": {
    "card_number": "4111111111111111",
    "expiry_month": "12",
    "expiry_year": "2025", 
    "cvv": "123",
    "cardholder_name": "John Doe"
  }
}
```

**Payment Integration:**
- 💳 **Credit/Debit Cards**: Visa, Mastercard
- 📱 **Mobile Money**: Available in some regions
- 🏦 **Bank Transfer**: EFT options
- 🔒 **Security**: PCI DSS compliant processing

**Post-Purchase State:**
- ✅ Creates `StoredSubscription` record
- ✅ `is_applied = false` (not yet assigned to group)
- ✅ Payment confirmation sent
- ✅ Available for group allocation

**Stored Subscription Schema:**
```sql
CREATE TABLE stored_subscriptions (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES registered_users(id),
    product_id UUID REFERENCES subscription_products(id),
    is_applied BOOLEAN DEFAULT FALSE,
    applied_to_group_id UUID REFERENCES user_groups(id),
    purchased_at TIMESTAMP DEFAULT NOW(),
    applied_at TIMESTAMP
);
```

---

### **Step 7: 🎯 Subscription Allocation to Group**

**Endpoint:** `POST /api/v1/mobile/subscriptions/apply`

**Allocation Process:**
```json
{
  "subscription_id": "stored-sub-uuid",
  "group_id": "group-uuid"
}
```

**System Validations:**
- ✅ **Ownership**: User owns both subscription and group
- ✅ **Coverage**: Group location within firm's service area
- ✅ **Capacity**: Group mobile numbers ≤ subscription max_users
- ✅ **Availability**: Subscription not already applied
- ✅ **Active Status**: Security firm is operational

**Coverage Validation Process:**
```sql
-- Check if group location is within firm's coverage area
SELECT 
    sf.id,
    sf.name,
    ST_DWithin(
        ug.location,
        sf.coverage_area,
        0  -- 0 meters - exact coverage
    ) as is_covered
FROM security_firms sf
JOIN subscription_products sp ON sf.id = sp.firm_id  
JOIN user_groups ug ON ug.id = $group_id
WHERE sp.id = $product_id
```

**Successful Allocation:**
- ✅ `is_applied = true`
- ✅ `applied_to_group_id` set
- ✅ `applied_at` timestamp recorded
- ✅ Group gains emergency service access
- ✅ Subscription expiry calculated

**Group Status Update:**
```sql
UPDATE user_groups 
SET 
    subscription_id = $subscription_id,
    subscription_expires_at = NOW() + INTERVAL '1 month'
WHERE id = $group_id
```

---

### **Step 8: 🚨 Subscription Usage & Emergency Services**

**Active Subscription Benefits:**

**Emergency Panic Access:**
```json
POST /api/v1/emergency/request
{
  "requester_phone": "+27123456789",
  "group_id": "group-uuid",
  "service_type": "security", 
  "latitude": -26.1076,
  "longitude": 28.0567,
  "address": "123 Oak Street, Sandton",
  "description": "Break-in attempt"
}
```

**Usage Tracking:**
- 📊 **Panic Requests**: Number of emergency calls
- ⏱️ **Response Times**: Firm performance metrics
- 📍 **Location History**: Request locations
- 💰 **Cost Tracking**: Credit deductions per service
- 📈 **Monthly Reports**: Usage analytics

**Credit System:**
```sql
CREATE TABLE credit_transactions (
    id UUID PRIMARY KEY,
    firm_id UUID REFERENCES security_firms(id),
    user_group_id UUID REFERENCES user_groups(id),
    amount INTEGER NOT NULL, -- Credits deducted
    transaction_type VARCHAR(50), -- 'panic_request', 'monthly_fee'
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Service Level Validation:**
- ✅ **Subscription Active**: Not expired
- ✅ **Firm Credits**: Adequate balance
- ✅ **Location Coverage**: Within service area
- ✅ **User Limits**: Within max_users capacity

---

### **Step 9: 📊 Usage Monitoring & Analytics**

**User Analytics Endpoint:** `GET /api/v1/mobile/users/statistics`

**Usage Metrics:**
```json
{
  "total_groups": 2,
  "active_subscriptions": 1,
  "total_panic_requests": 12,
  "this_month_requests": 3,
  "average_response_time": "6.5 minutes",
  "subscription_expires_at": "2025-10-19T14:30:00Z",
  "current_usage": {
    "security_calls": 8,
    "medical_calls": 3, 
    "fire_calls": 1,
    "roadside_calls": 0
  },
  "monthly_breakdown": [
    {"month": "2025-08", "requests": 4, "avg_response": "7.2 min"},
    {"month": "2025-09", "requests": 3, "avg_response": "5.8 min"}
  ]
}
```

**Firm Performance Tracking:**
- ⏱️ **Response Times**: Average and per-incident
- 📍 **Coverage Quality**: Success rate by location
- 💯 **Service Rating**: User satisfaction scores
- 🚨 **Incident Resolution**: Completion rates

---

### **Step 10: 🔄 Subscription Renewal Process**

**Auto-Renewal (Default):**
- 📅 **7 Days Before Expiry**: Renewal notification sent
- 💳 **Payment Processing**: Automatic charge attempt
- ✅ **Successful Renewal**: Subscription extended 30 days
- ❌ **Payment Failed**: Grace period + retry logic

**Manual Renewal:**
```json
POST /api/v1/mobile/subscriptions/renew
{
  "group_id": "group-uuid",
  "payment_method": "saved_card_1"
}
```

**Renewal Notifications:**
```json
{
  "notification_type": "subscription_renewal_reminder",
  "group_name": "Smith Family Home",
  "expires_at": "2025-10-19T14:30:00Z",
  "days_remaining": 7,
  "renewal_amount": 299.99,
  "auto_renewal_enabled": true
}
```

**Grace Period Handling:**
- 📅 **Expiry Day**: Service continues with warnings
- 📅 **3 Days After**: Limited emergency access
- 📅 **7 Days After**: Service suspended
- 📅 **30 Days After**: Subscription deleted

---

### **Step 11: 💔 Subscription Expiry & Reactivation**

**Expiry Process:**
1. **Pre-Expiry Warnings**: 7, 3, 1 days before
2. **Grace Period**: 7 days limited access
3. **Service Suspension**: Emergency access disabled
4. **Account Recovery**: Reactivation options

**Reactivation Options:**

**A. Renew Existing:**
```json
POST /api/v1/mobile/subscriptions/reactivate
{
  "group_id": "group-uuid",
  "payment_data": {...}
}
```

**B. Purchase New Subscription:**
```json
POST /api/v1/mobile/subscriptions/purchase
{
  "product_id": "new-product-uuid",
  "payment_data": {...}
}
```

**Emergency Access During Expiry:**
- 🚨 **Emergency Only**: Limited panic button access
- ⚠️ **Additional Charges**: Premium rates apply
- 📞 **Direct Contact**: Fallback to standard emergency numbers

---

## 📱 Mobile App Integration Points

### **Registration & Authentication:**
- 📝 User registration with verification
- 🔐 Secure login with JWT tokens
- 🔄 Token refresh and session management
- 📱 Mobile attestation for security

### **Group Management:**
- 🏠 Create and manage multiple groups
- 📍 GPS location selection and verification
- 📞 Mobile number management per group
- 🏷️ Group naming and identification

### **Subscription Management:**
- 🛒 Browse and compare subscription products
- 💳 Secure payment processing
- 🎯 Subscription allocation to groups
- 📊 Usage tracking and analytics

### **Emergency Services:**
- 🚨 One-tap panic button
- 📍 Automatic location detection
- 🚨 Service type selection
- 📱 Real-time status updates

---

## 🔐 Security & Privacy

### **Data Protection:**
- 🔒 **Encryption**: End-to-end encrypted communications
- 🛡️ **Authentication**: Multi-factor authentication support  
- 🔐 **Authorization**: Role-based access control
- 📱 **Mobile Security**: Device attestation required

### **Privacy Controls:**
- 📍 **Location Data**: Only collected during emergencies
- 📞 **Contact Information**: Encrypted storage
- 💳 **Payment Data**: PCI DSS compliant processing
- 📊 **Usage Analytics**: Anonymized where possible

### **Compliance:**
- 🛡️ **POPIA Compliance**: South African data protection
- 🔐 **GDPR Ready**: European privacy standards
- 🏥 **HIPAA Considerations**: Medical emergency data
- 🔒 **Industry Standards**: ISO 27001 security

---

## 📊 Database Schema Summary

### **Core User Tables:**
```sql
-- User registration and profile
registered_users (id, email, phone, first_name, last_name, is_verified...)

-- Location-based groups  
user_groups (id, user_id, name, address, location, subscription_id...)

-- Phone numbers per group
group_mobile_numbers (id, group_id, phone_number, user_type, is_verified)

-- Available subscription products
subscription_products (id, firm_id, name, description, max_users, price...)

-- Purchased subscriptions
stored_subscriptions (id, user_id, product_id, is_applied, applied_to_group_id...)

-- Usage tracking
credit_transactions (id, firm_id, user_group_id, amount, transaction_type...)
```

---

## 🚀 API Endpoint Summary

### **User Management:**
```bash
POST /api/v1/mobile/users/register          # User registration
POST /api/v1/auth/login                      # User login
GET  /api/v1/mobile/users/profile           # Get profile
PUT  /api/v1/mobile/users/profile           # Update profile
GET  /api/v1/mobile/users/statistics        # Usage stats
```

### **Group Management:**
```bash
POST /api/v1/mobile/users/groups            # Create group
GET  /api/v1/mobile/users/groups            # List groups
PUT  /api/v1/mobile/users/groups/{id}       # Update group
DELETE /api/v1/mobile/users/groups/{id}     # Delete group
POST /api/v1/mobile/users/groups/{id}/mobile # Add phone number
```

### **Subscription Management:**
```bash
GET  /api/v1/mobile/subscriptions/products  # Browse marketplace
POST /api/v1/mobile/subscriptions/purchase  # Purchase subscription
GET  /api/v1/mobile/subscriptions/stored    # List purchased
POST /api/v1/mobile/subscriptions/apply     # Apply to group
GET  /api/v1/mobile/subscriptions/active    # Active subscriptions
POST /api/v1/mobile/subscriptions/renew     # Renew subscription
```

### **Emergency Services:**
```bash
POST /api/v1/emergency/request              # Create panic request
GET  /api/v1/emergency/history             # Request history
```

---

## 🎯 User Journey Examples

### **Example 1: New User Registration**
```
1. Download app → 2. Register → 3. Verify phone → 4. Login → 
5. Create home group → 6. Browse subscriptions → 7. Purchase → 
8. Apply to group → 9. Emergency access enabled
```

### **Example 2: Multi-Location User**
```
1. Existing user → 2. Create office group → 3. Purchase business subscription → 
4. Apply to office → 5. Manage 2 active subscriptions → 6. Different service levels
```

### **Example 3: Subscription Renewal**
```
1. Expiry notification → 2. Review usage → 3. Auto-renewal → 
4. Payment processed → 5. Service continued → 6. New expiry date
```

---

## 🔧 Error Handling & Edge Cases

### **Common Error Scenarios:**

| Error | Cause | Resolution |
|-------|-------|------------|
| `COVERAGE_UNAVAILABLE` | Group location outside service area | Show alternative firms |
| `SUBSCRIPTION_EXPIRED` | Service expired | Prompt renewal |
| `PAYMENT_FAILED` | Card declined | Update payment method |
| `MAX_USERS_EXCEEDED` | Too many phones in group | Upgrade subscription |
| `DUPLICATE_PHONE` | Phone already registered | Verify ownership |

### **Graceful Degradation:**
- 🚨 **Emergency Access**: Always available during grace period
- 📞 **Alternative Contact**: Fallback to direct emergency numbers
- 💾 **Offline Mode**: Basic functionality without network
- 🔄 **Sync Recovery**: Automatic data sync when reconnected

---

*This comprehensive workflow ensures seamless mobile user experience from initial signup through ongoing subscription management with full emergency service access.*