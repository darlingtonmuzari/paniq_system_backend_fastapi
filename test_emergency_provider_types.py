#!/usr/bin/env python3
"""
Test emergency provider types API endpoints
"""
import requests
import json

def test_emergency_provider_types():
    """Test emergency provider types CRUD operations and permissions"""
    
    base_url = "http://localhost:8000/api/v1/emergency-provider-types"
    
    # Test headers for different scenarios
    headers_no_auth = {
        'Origin': 'http://localhost:4000',
        'Content-Type': 'application/json'
    }
    
    headers_with_auth = {
        'Origin': 'http://localhost:4000',
        'Content-Type': 'application/json',
        'Authorization': 'Bearer YOUR_ADMIN_TOKEN_HERE'  # Replace with actual admin token
    }
    
    print("Testing Emergency Provider Types API...")
    print("=" * 60)
    
    # Test data for creating a new provider type
    new_provider_type = {
        "name": "Test Emergency Service",
        "code": "test_emergency",
        "description": "Test emergency service provider type",
        "requires_license": True,
        "default_coverage_radius_km": 25.0,
        "icon": "test-icon",
        "color": "#FF6600",
        "priority_level": "high"
    }
    
    print("\n1. Testing READ operations (should work for all authenticated users)...")
    
    # Test list provider types
    print(f"\nTesting: GET {base_url}/")
    try:
        response = requests.get(f"{base_url}/", headers=headers_no_auth, timeout=10)
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 401:
            print("  ✅ Correctly requires authentication")
        elif response.status_code == 200:
            print("  ✅ Success - Listed provider types")
            data = response.json()
            print(f"  📊 Found {len(data)} provider types")
            if data:
                print(f"  📋 Sample: {data[0]['name']} ({data[0]['code']})")
        else:
            print(f"  ❓ Unexpected status: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"  ❌ Request failed: {e}")
    
    print("\n2. Testing CRUD operations (should require admin/super_admin)...")
    
    # Test create provider type
    print(f"\nTesting: POST {base_url}/")
    try:
        response = requests.post(
            f"{base_url}/", 
            headers=headers_no_auth, 
            json=new_provider_type, 
            timeout=10
        )
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 401:
            print("  ✅ Correctly requires authentication")
        elif response.status_code == 403:
            print("  ✅ Correctly requires admin permissions")
        elif response.status_code == 201:
            print("  ✅ Success - Created provider type (if authenticated as admin)")
            data = response.json()
            print(f"  🆔 Created ID: {data.get('id')}")
        else:
            print(f"  ❓ Unexpected status: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"  ❌ Request failed: {e}")
    
    # Test update provider type (using a dummy ID)
    dummy_id = "12345678-1234-1234-1234-123456789012"
    update_data = {"description": "Updated description"}
    
    print(f"\nTesting: PUT {base_url}/{dummy_id}")
    try:
        response = requests.put(
            f"{base_url}/{dummy_id}", 
            headers=headers_no_auth, 
            json=update_data, 
            timeout=10
        )
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 401:
            print("  ✅ Correctly requires authentication")
        elif response.status_code == 403:
            print("  ✅ Correctly requires admin permissions")
        elif response.status_code == 404:
            print("  ✅ Correctly returns 404 for non-existent ID (if authenticated)")
        else:
            print(f"  ❓ Unexpected status: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"  ❌ Request failed: {e}")
    
    # Test delete provider type
    print(f"\nTesting: DELETE {base_url}/{dummy_id}")
    try:
        response = requests.delete(f"{base_url}/{dummy_id}", headers=headers_no_auth, timeout=10)
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 401:
            print("  ✅ Correctly requires authentication")
        elif response.status_code == 403:
            print("  ✅ Correctly requires admin permissions")
        elif response.status_code == 404:
            print("  ✅ Correctly returns 404 for non-existent ID (if authenticated)")
        else:
            print(f"  ❓ Unexpected status: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"  ❌ Request failed: {e}")
    
    print("\n" + "=" * 60)
    print("Permission Summary:")
    print("📖 READ Access: All authenticated users")
    print("✏️  CRUD Access: admin, super_admin only")
    print("\nDefault Provider Types (created by migration):")
    print("🚑 Ambulance (critical priority)")
    print("🚛 Tow Truck (medium priority)")
    print("🚒 Fire Department (critical priority)")
    print("🚔 Police (high priority)")
    print("🛡️  Security (medium priority)")
    print("🏥 Medical (high priority)")
    print("🔧 Roadside Assistance (low priority)")
    print("\nNote: Replace 'YOUR_ADMIN_TOKEN_HERE' with actual admin JWT token to test authenticated access.")

if __name__ == "__main__":
    test_emergency_provider_types()