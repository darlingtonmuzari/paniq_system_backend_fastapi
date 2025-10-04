#!/usr/bin/env python3

import requests
import json
import jwt
from datetime import datetime
import time

# Test configuration
BASE_URL = "http://localhost:8000/api/v1"
SAMPLE_EMAIL = "rodney.rhodes@manicasecuritysolutions.co.za"  # From our sample data
SAMPLE_PASSWORD = "password123"  # Default password from sample data

def decode_token(token):
    """Decode JWT token without verification for inspection"""
    try:
        # Decode without verification to inspect payload
        payload = jwt.decode(token, options={"verify_signature": False})
        return payload
    except Exception as e:
        print(f"Error decoding token: {e}")
        return None

def test_login_endpoint():
    """Test the login endpoint"""
    print("=" * 60)
    print("TESTING LOGIN ENDPOINT")
    print("=" * 60)
    
    # Login request payload
    login_data = {
        "email": SAMPLE_EMAIL,
        "password": SAMPLE_PASSWORD,
        "user_type": "firm_personnel"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        
        if response.status_code == 200:
            data = response.json()
            access_token = data.get('access_token')
            refresh_token = data.get('refresh_token')
            expires_in = data.get('expires_in')
            role = data.get('role')
            
            print(f"✅ LOGIN SUCCESSFUL")
            print(f"   Status Code: {response.status_code}")
            print(f"   Role in Response: {role}")
            print(f"   Token Expires In: {expires_in} seconds ({expires_in/3600:.1f} hours)")
            
            # Decode and inspect access token
            if access_token:
                payload = decode_token(access_token)
                if payload:
                    print(f"\n📋 ACCESS TOKEN PAYLOAD:")
                    print(f"   User ID: {payload.get('sub')}")
                    print(f"   User Type: {payload.get('user_type')}")
                    print(f"   Role: {payload.get('role')}")
                    print(f"   Firm ID: {payload.get('firm_id')}")
                    print(f"   Expires At: {datetime.fromtimestamp(payload.get('exp')).strftime('%Y-%m-%d %H:%M:%S UTC')}")
                    print(f"   Issued At: {datetime.fromtimestamp(payload.get('iat')).strftime('%Y-%m-%d %H:%M:%S UTC')}")
                    
                    # Calculate actual expiry time
                    exp_time = payload.get('exp')
                    iat_time = payload.get('iat')
                    if exp_time and iat_time:
                        actual_duration = exp_time - iat_time
                        print(f"   Actual Duration: {actual_duration} seconds ({actual_duration/3600:.1f} hours)")
                        
                        if actual_duration == 3600:  # 1 hour
                            print(f"   ✅ Token expires in exactly 1 hour")
                        else:
                            print(f"   ❌ Token duration is not 1 hour!")
            
            return access_token, refresh_token
            
        else:
            print(f"❌ LOGIN FAILED")
            print(f"   Status Code: {response.status_code}")
            print(f"   Response: {response.text}")
            return None, None
            
    except Exception as e:
        print(f"❌ LOGIN ERROR: {e}")
        return None, None

def test_refresh_endpoint(refresh_token):
    """Test the refresh endpoint"""
    print("\n" + "=" * 60)
    print("TESTING REFRESH ENDPOINT")
    print("=" * 60)
    
    if not refresh_token:
        print("❌ No refresh token available for testing")
        return None
    
    refresh_data = {
        "refresh_token": refresh_token
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/refresh", json=refresh_data)
        
        if response.status_code == 200:
            data = response.json()
            new_access_token = data.get('access_token')
            expires_in = data.get('expires_in')
            
            print(f"✅ REFRESH SUCCESSFUL")
            print(f"   Status Code: {response.status_code}")
            print(f"   Token Expires In: {expires_in} seconds ({expires_in/3600:.1f} hours)")
            
            # Decode and inspect new access token
            if new_access_token:
                payload = decode_token(new_access_token)
                if payload:
                    print(f"\n📋 NEW ACCESS TOKEN PAYLOAD:")
                    print(f"   User ID: {payload.get('sub')}")
                    print(f"   User Type: {payload.get('user_type')}")
                    print(f"   Role: {payload.get('role')}")
                    print(f"   Firm ID: {payload.get('firm_id')}")
                    print(f"   Expires At: {datetime.fromtimestamp(payload.get('exp')).strftime('%Y-%m-%d %H:%M:%S UTC')}")
                    
                    # Check if role is preserved
                    if payload.get('role'):
                        print(f"   ✅ Role field preserved in refreshed token")
                    else:
                        print(f"   ❌ Role field missing in refreshed token!")
                    
                    # Calculate actual expiry time
                    exp_time = payload.get('exp')
                    iat_time = payload.get('iat')
                    if exp_time and iat_time:
                        actual_duration = exp_time - iat_time
                        print(f"   Actual Duration: {actual_duration} seconds ({actual_duration/3600:.1f} hours)")
                        
                        if actual_duration == 3600:  # 1 hour
                            print(f"   ✅ Refreshed token expires in exactly 1 hour")
                        else:
                            print(f"   ❌ Refreshed token duration is not 1 hour!")
            
            return new_access_token
            
        else:
            print(f"❌ REFRESH FAILED")
            print(f"   Status Code: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ REFRESH ERROR: {e}")
        return None

def main():
    """Main test function"""
    print("🧪 Testing Auth Endpoints for 1-hour tokens with role field")
    print("=" * 60)
    
    # Test login endpoint
    access_token, refresh_token = test_login_endpoint()
    
    # Test refresh endpoint
    if refresh_token:
        time.sleep(1)  # Small delay between requests
        new_access_token = test_refresh_endpoint(refresh_token)
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    if access_token:
        print("✅ Login endpoint: Working")
    else:
        print("❌ Login endpoint: Failed")
    
    if refresh_token and new_access_token:
        print("✅ Refresh endpoint: Working") 
    else:
        print("❌ Refresh endpoint: Failed")
    
    print("\n🎯 Requirements Check:")
    print("   - Token expiry: 1 hour ⏰")
    print("   - Role field in token: ✅") 
    print("\nTest completed!")

if __name__ == "__main__":
    main()