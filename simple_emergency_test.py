#!/usr/bin/env python3
"""
Simple test to create minimal emergency provider data and test the endpoint
"""
import requests
import json
from uuid import uuid4, UUID
import sys
import os

# Add the app directory to Python path
sys.path.append('/home/melcy/Programming/kiro/paniq_system')

from app.services.auth import JWTTokenService

def test_emergency_providers():
    """Test emergency providers with minimal data"""
    
    print("🧪 Testing Emergency Providers API")
    print("=" * 60)
    
    # Generate tokens with different roles to test permissions
    jwt_service = JWTTokenService()
    sample_firm_id = uuid4()
    
    # Try with admin role (system admin) 
    admin_token = jwt_service.create_access_token(
        user_id=uuid4(),
        user_type="firm_personnel", 
        email="admin@test.co.za",
        permissions=[],
        firm_id=sample_firm_id,
        role="admin"  # System admin
    )
    
    # Try with firm_admin role
    firm_admin_token = jwt_service.create_access_token(
        user_id=uuid4(),
        user_type="firm_personnel",
        email="firmadmin@test.co.za", 
        permissions=[],
        firm_id=sample_firm_id,
        role="firm_admin"
    )
    
    base_url = "http://localhost:8000/api/v1"
    
    print(f"🔑 Testing with admin token...")
    admin_headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }
    
    print(f"🔑 Testing with firm_admin token...")
    firm_headers = {
        "Authorization": f"Bearer {firm_admin_token}",
        "Content-Type": "application/json" 
    }
    
    # Test 1: Try to list emergency providers with both tokens
    print(f"\n📋 Test 1: GET /emergency-providers/")
    
    for token_name, headers in [("admin", admin_headers), ("firm_admin", firm_headers)]:
        try:
            response = requests.get(f"{base_url}/emergency-providers/", headers=headers)
            print(f"   {token_name} token: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"      ✅ Success! Found {result['total_count']} providers")
                if result['providers']:
                    for provider in result['providers']:
                        print(f"         - {provider['name']} ({provider['provider_type']})")
                else:
                    print(f"      📝 No providers found (empty list)")
            else:
                print(f"      ❌ Error: {response.text}")
                
        except Exception as e:
            print(f"      ❌ Exception: {e}")
    
    # Test 2: Try to create a simple emergency provider type first
    print(f"\n📋 Test 2: Create Emergency Provider Type")
    
    simple_type_data = {
        "name": "Test Ambulance Service",
        "code": "test_ambulance",
        "description": "Test ambulance for API testing"
    }
    
    for token_name, headers in [("admin", admin_headers), ("firm_admin", firm_headers)]:
        try:
            response = requests.post(
                f"{base_url}/emergency-provider-types/",
                headers=headers,
                json=simple_type_data
            )
            print(f"   {token_name} token: {response.status_code}")
            
            if response.status_code == 201:
                result = response.json()
                print(f"      ✅ Created provider type: {result.get('name', 'unknown')}")
                type_id = result.get('id')
                
                # Test 3: Try to create a simple emergency provider
                print(f"\n📋 Test 3: Create Emergency Provider")
                
                simple_provider_data = {
                    "name": "Test Emergency Response",
                    "provider_type": "ambulance",
                    "provider_type_id": type_id,
                    "contact_phone": "+27123456789",
                    "street_address": "123 Test Street",
                    "city": "Cape Town",
                    "province": "Western Cape",
                    "country": "South Africa",
                    "postal_code": "8001",
                    "current_latitude": -33.9249,
                    "current_longitude": 18.4241,
                    "base_latitude": -33.9249,
                    "base_longitude": 18.4241
                }
                
                try:
                    response = requests.post(
                        f"{base_url}/emergency-providers/",
                        headers=headers,
                        json=simple_provider_data
                    )
                    print(f"   Create provider with {token_name}: {response.status_code}")
                    
                    if response.status_code == 201:
                        result = response.json()
                        print(f"      ✅ Created provider: {result.get('name', 'unknown')}")
                        
                        # Test 4: List providers again
                        print(f"\n📋 Test 4: List providers after creation")
                        response = requests.get(f"{base_url}/emergency-providers/", headers=headers)
                        if response.status_code == 200:
                            result = response.json()
                            print(f"      ✅ Now found {result['total_count']} providers")
                            for provider in result['providers']:
                                print(f"         - {provider['name']} ({provider['provider_type']}) - {provider['status']}")
                        
                        return True  # Success!
                        
                    else:
                        print(f"      ❌ Failed to create provider: {response.text}")
                        
                except Exception as e:
                    print(f"      ❌ Exception creating provider: {e}")
                    
                break  # Don't try the second token if first succeeded
                
            else:
                print(f"      ❌ Failed to create type: {response.text}")
                
        except Exception as e:
            print(f"      ❌ Exception: {e}")
    
    print(f"\n❌ All tests failed")
    return False

if __name__ == "__main__":
    success = test_emergency_providers()
    if success:
        print(f"\n🎉 Emergency Providers API is working!")
    else:
        print(f"\n💔 Emergency Providers API needs debugging")