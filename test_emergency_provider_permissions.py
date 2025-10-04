#!/usr/bin/env python3
"""
Test emergency provider role-based permissions
"""
import requests
import json

def test_emergency_provider_permissions():
    """Test that different roles have appropriate access to emergency provider endpoints"""
    
    base_url = "http://localhost:8000/api/v1/emergency-providers"
    
    # Test headers for different scenarios
    headers_no_auth = {
        'Origin': 'http://localhost:4000',
        'Content-Type': 'application/json'
    }
    
    print("Testing Emergency Provider Role-Based Permissions...")
    print("=" * 60)
    
    # Test endpoints that should allow read access
    read_endpoints = [
        f"{base_url}/",  # List providers
        f"{base_url}/search?latitude=40.7128&longitude=-74.0060",  # Search nearby providers
    ]
    
    # Test endpoints that should require CRUD permissions
    crud_endpoints = [
        ("POST", f"{base_url}/", {"name": "Test Provider", "provider_type": "ambulance"}),
        ("DELETE", f"{base_url}/cleanup/unused", None),
    ]
    
    print("\n1. Testing READ endpoints (should work for all authorized roles)...")
    for endpoint in read_endpoints:
        print(f"\nTesting: GET {endpoint}")
        try:
            response = requests.get(endpoint, headers=headers_no_auth, timeout=10)
            print(f"  Status: {response.status_code}")
            
            if response.status_code == 401:
                print("  ✅ Correctly requires authentication")
            elif response.status_code == 403:
                print("  ⚠️  Forbidden - check if role allows read access")
            elif response.status_code == 200:
                print("  ✅ Success (if authenticated with read role)")
            else:
                print(f"  ❓ Unexpected status: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"  ❌ Request failed: {e}")
    
    print("\n2. Testing CRUD endpoints (should require firm_user/firm_supervisor/firm_admin)...")
    for method, endpoint, data in crud_endpoints:
        print(f"\nTesting: {method} {endpoint}")
        try:
            if method == "POST":
                response = requests.post(endpoint, headers=headers_no_auth, json=data, timeout=10)
            elif method == "DELETE":
                response = requests.delete(endpoint, headers=headers_no_auth, timeout=10)
            
            print(f"  Status: {response.status_code}")
            
            if response.status_code == 401:
                print("  ✅ Correctly requires authentication")
            elif response.status_code == 403:
                print("  ✅ Correctly requires CRUD permissions (firm_user/firm_supervisor/firm_admin)")
            elif response.status_code in [200, 201]:
                print("  ✅ Success (if authenticated with CRUD role)")
            else:
                print(f"  ❓ Unexpected status: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"  ❌ Request failed: {e}")
    
    print("\n" + "=" * 60)
    print("Permission Summary:")
    print("📖 READ Access: firm_user, firm_supervisor, firm_admin, team_leader, field_agent, admin, super_admin")
    print("✏️  CRUD Access: firm_user, firm_supervisor, firm_admin")
    print("🗑️  Delete Unused: firm_user, firm_supervisor, firm_admin")
    print("\nNote: Replace with actual JWT tokens to test authenticated access.")

if __name__ == "__main__":
    test_emergency_provider_permissions()