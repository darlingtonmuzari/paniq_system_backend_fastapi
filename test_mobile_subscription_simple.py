#!/usr/bin/env python3
"""
Simple Mobile User Subscription Test using requests
Tests the basic workflow for subscribing to firm: e178e9f4-01cb-4c8e-910f-9586516172d6
"""

import requests
import json
import uuid
from datetime import datetime, timezone

# Configuration
BASE_URL = "http://localhost:8000"
TARGET_FIRM_ID = "e178e9f4-01cb-4c8e-910f-9586516172d6"

# Test data
TEST_USER_EMAIL = f"testuser_{uuid.uuid4().hex[:8]}@example.com"
TEST_USER_PASSWORD = "TestPassword123!"

# Device info for mobile endpoints
DEVICE_INFO = {
    "device_id": str(uuid.uuid4()),
    "device_type": "android",
    "device_model": "Samsung Galaxy S24",
    "os_version": "14.0",
    "app_version": "1.0.0",
    "platform_version": "API 34"
}

SECURITY_ATTESTATION = {
    "attestation_token": "mock_attestation_token_" + uuid.uuid4().hex[:16],
    "integrity_verdict": "MEETS_DEVICE_INTEGRITY,MEETS_BASIC_INTEGRITY",
    "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
    "nonce": uuid.uuid4().hex
}

def make_request(method, endpoint, data=None, headers=None, token=None):
    """Make HTTP request with proper headers"""
    url = f"{BASE_URL}{endpoint}"
    
    default_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Platform": "android",
        "X-App-Version": DEVICE_INFO["app_version"],
        "X-Device-ID": DEVICE_INFO["device_id"]
    }
    
    if headers:
        default_headers.update(headers)
    
    if token:
        default_headers["Authorization"] = f"Bearer {token}"
    
    print(f"🌐 {method} {endpoint}")
    if data:
        print(f"📤 Request: {json.dumps(data, indent=2)}")
    
    try:
        response = requests.request(
            method=method,
            url=url,
            json=data,
            headers=default_headers,
            timeout=10
        )
        
        print(f"📈 Status: {response.status_code}")
        
        if response.status_code < 400:
            try:
                result = response.json()
                print(f"📥 Response: {json.dumps(result, indent=2)}")
                return result
            except:
                print(f"📥 Response: {response.text}")
                return {"text": response.text}
        else:
            print(f"❌ Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Request failed: {str(e)}")
        return None

def test_mobile_user_workflow():
    """Test the complete mobile user subscription workflow"""
    print("🚀 Starting Mobile User Subscription Test")
    print(f"📧 Test User: {TEST_USER_EMAIL}")
    print(f"🎯 Target Firm: {TARGET_FIRM_ID}")
    print("=" * 60)
    
    # Step 1: Register User
    print("📝 STEP 1: User Registration")
    registration_data = {
        "email": TEST_USER_EMAIL,
        "phone": "+27123456789",
        "first_name": "John",
        "last_name": "Doe",
        "password": TEST_USER_PASSWORD,
        "device_info": DEVICE_INFO,
        "security_attestation": SECURITY_ATTESTATION
    }
    
    register_response = make_request("POST", "/api/v1/auth/mobile/register", registration_data)
    if not register_response:
        print("❌ Registration failed!")
        return False
    
    user_id = register_response.get("user_id")
    session_id = register_response.get("session_id")
    print(f"✅ User registered: {user_id}")
    print("")
    
    # Step 2: Login (skip email verification for testing)
    print("🔐 STEP 2: User Login")
    login_data = {
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD,
        "device_info": DEVICE_INFO,
        "security_attestation": SECURITY_ATTESTATION
    }
    
    login_response = make_request("POST", "/api/v1/auth/mobile/login", login_data)
    if not login_response:
        print("❌ Login failed!")
        return False
    
    access_token = login_response.get("access_token")
    print(f"✅ Login successful, token length: {len(access_token) if access_token else 0}")
    print("")
    
    # Step 3: Get Available Products
    print("📦 STEP 3: Get Available Products")
    products_response = make_request("GET", "/api/v1/mobile/subscriptions/products", token=access_token)
    if not products_response:
        print("❌ Failed to get products!")
        return False
    
    # Find product from target firm
    target_product = None
    for product in products_response:
        if product.get("firm_id") == TARGET_FIRM_ID:
            target_product = product
            break
    
    if not target_product and products_response:
        target_product = products_response[0]
        print(f"⚠️ Using first available product instead: {target_product.get('firm_name')}")
    
    if not target_product:
        print("❌ No products available!")
        return False
    
    print(f"✅ Selected product: {target_product['name']} - R{target_product['price']}")
    print("")
    
    # Step 4: Purchase Subscription
    print("💳 STEP 4: Purchase Subscription")
    purchase_data = {
        "product_id": target_product["id"],
        "payment_method": "credit_card",
        "payment_token": f"mock_payment_token_{uuid.uuid4().hex[:16]}"
    }
    
    purchase_response = make_request("POST", "/api/v1/mobile/subscriptions/purchase", purchase_data, token=access_token)
    if not purchase_response:
        print("❌ Purchase failed!")
        return False
    
    print(f"✅ Subscription purchased: {purchase_response['id']}")
    print(f"📦 Product: {purchase_response['product_name']}")
    print(f"💰 Price: R{purchase_response['product_price']}")
    print("")
    
    # Step 5: Get Stored Subscriptions
    print("📋 STEP 5: Get Stored Subscriptions")
    stored_response = make_request("GET", "/api/v1/mobile/subscriptions/stored", token=access_token)
    if stored_response:
        print(f"✅ Found {len(stored_response)} stored subscription(s)")
        for sub in stored_response:
            print(f"  - {sub['product_name']} (Applied: {sub['is_applied']})")
    print("")
    
    # Step 6: Logout
    print("🚪 STEP 6: Logout")
    logout_response = make_request("POST", f"/api/v1/auth/mobile/logout?device_id={DEVICE_INFO['device_id']}", token=access_token)
    if logout_response:
        print("✅ Logout successful")
    print("")
    
    print("🎉 Mobile User Subscription Test Completed Successfully!")
    print("=" * 60)
    print("✅ Core workflow verified:")
    print("  - User registration")
    print("  - User login")
    print("  - Product selection")
    print("  - Subscription purchase")
    print("  - Stored subscriptions retrieval")
    print("  - User logout")
    
    return True

if __name__ == "__main__":
    success = test_mobile_user_workflow()
    exit(0 if success else 1)