#!/usr/bin/env python3
"""
Test script for Coverage Area Active Status functionality
"""
import requests
import json

BASE_URL = "http://localhost:8000"

# Use the fresh token we generated earlier
ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI4NjBmZmJiMS05NjkyLTRkYTEtYjBlYy1hNDNlZDdiZDQ1ZjciLCJ1c2VyX3R5cGUiOiJmaXJtX3BlcnNvbm5lbCIsImVtYWlsIjoiZGFybGluZ3RvbkBtYW5pY2Fzb2x1dGlvbnMuY29tIiwicGVybWlzc2lvbnMiOlsicmVxdWVzdDp2aWV3IiwicmVxdWVzdDphY2NlcHQiXSwiZXhwIjoxNzU3MTM2MTE2LCJpYXQiOjE3NTcwNDk3MTYsImp0aSI6InRlc3QtdG9rZW4tODYwZmZiYjEiLCJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZmlybV9pZCI6ImUxNzhlOWY0LTAxY2ItNGM4ZS05MTBmLTk1ODY1MTYxNzJkNiIsInJvbGUiOiJmaXJtX2FkbWluIn0.iZbEu7nSsJxqeA1-bNuWVrD7THAgCHRIQ_Q9wnj9LII"

# Firm ID from the token
FIRM_ID = "e178e9f4-01cb-4c8e-910f-9586516172d6"

def make_request(method, url, data=None, params=None):
    """Make HTTP request with authentication"""
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=params)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data)
        elif method.upper() == "PUT":
            response = requests.put(url, headers=headers, json=data)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        print(f"{method.upper()} {url}")
        if params:
            print(f"Params: {params}")
        print(f"Status: {response.status_code}")
        
        if response.text:
            try:
                response_data = response.json()
                print(f"Response: {json.dumps(response_data, indent=2)}")
                return response_data
            except:
                print(f"Response: {response.text}")
                return response.text
        else:
            print("Response: (empty)")
            return None
            
    except Exception as e:
        print(f"Request failed: {e}")
        return None

def test_create_coverage_area_with_active_status():
    """Test creating a coverage area (should default to active)"""
    print("\n" + "="*60)
    print("1. CREATE COVERAGE AREA (DEFAULT ACTIVE)")
    print("="*60)
    
    url = f"{BASE_URL}/api/v1/security-firms/{FIRM_ID}/coverage-areas"
    
    coverage_data = {
        "name": "Test Active Coverage Area",
        "boundary_coordinates": [
            [28.0300, -26.1200],
            [28.0400, -26.1200],
            [28.0400, -26.1100],
            [28.0300, -26.1100],
            [28.0300, -26.1200]
        ]
    }
    
    result = make_request("POST", url, coverage_data)
    
    if result and isinstance(result, dict) and "id" in result:
        print(f"✅ Coverage area created successfully!")
        print(f"Area ID: {result['id']}")
        print(f"Area Name: {result['name']}")
        print(f"Is Active: {result.get('is_active', 'Not specified')}")
        return result["id"]
    else:
        print("❌ Failed to create coverage area")
        return None

def test_get_coverage_areas_with_filtering(area_id):
    """Test getting coverage areas with active/inactive filtering"""
    print("\n" + "="*60)
    print("2. GET COVERAGE AREAS WITH FILTERING")
    print("="*60)
    
    base_url = f"{BASE_URL}/api/v1/security-firms/{FIRM_ID}/coverage-areas"
    
    # Test 1: Get all areas (default)
    print("\n2a. Get all coverage areas (default):")
    result = make_request("GET", base_url)
    
    if result and isinstance(result, list):
        print(f"✅ Found {len(result)} total coverage area(s)")
        for i, area in enumerate(result):
            status = "🟢 Active" if area.get('is_active', True) else "🔴 Inactive"
            print(f"  {i+1}. {area['name']} - {status}")
    
    # Test 2: Get all areas explicitly
    print("\n2b. Get all coverage areas (explicit include_inactive=true):")
    result = make_request("GET", base_url, params={"include_inactive": "true"})
    
    if result and isinstance(result, list):
        print(f"✅ Found {len(result)} total coverage area(s)")
    
    # Test 3: Get only active areas
    print("\n2c. Get only active coverage areas:")
    result = make_request("GET", base_url, params={"include_inactive": "false"})
    
    if result and isinstance(result, list):
        active_count = len(result)
        print(f"✅ Found {active_count} active coverage area(s)")
        return active_count
    
    return 0

def test_update_active_status(area_id):
    """Test updating the is_active status"""
    print("\n" + "="*60)
    print("3. UPDATE ACTIVE STATUS")
    print("="*60)
    
    if not area_id:
        print("❌ No area ID provided for update")
        return False
    
    url = f"{BASE_URL}/api/v1/security-firms/{FIRM_ID}/coverage-areas/{area_id}"
    
    # Test 1: Deactivate the area
    print("\n3a. Deactivate coverage area:")
    update_data = {"is_active": False}
    
    result = make_request("PUT", url, update_data)
    
    if result and isinstance(result, dict):
        print(f"✅ Area deactivated successfully!")
        print(f"Name: {result['name']}")
        print(f"Is Active: {result.get('is_active', 'Not specified')}")
    else:
        print("❌ Failed to deactivate area")
        return False
    
    # Test 2: Reactivate the area
    print("\n3b. Reactivate coverage area:")
    update_data = {"is_active": True}
    
    result = make_request("PUT", url, update_data)
    
    if result and isinstance(result, dict):
        print(f"✅ Area reactivated successfully!")
        print(f"Name: {result['name']}")
        print(f"Is Active: {result.get('is_active', 'Not specified')}")
        return True
    else:
        print("❌ Failed to reactivate area")
        return False

def test_convenience_endpoints(area_id):
    """Test the activate/deactivate convenience endpoints"""
    print("\n" + "="*60)
    print("4. CONVENIENCE ENDPOINTS")
    print("="*60)
    
    if not area_id:
        print("❌ No area ID provided for convenience endpoint testing")
        return False
    
    # Test 1: Deactivate using convenience endpoint
    print("\n4a. Deactivate using convenience endpoint:")
    deactivate_url = f"{BASE_URL}/api/v1/security-firms/{FIRM_ID}/coverage-areas/{area_id}/deactivate"
    
    result = make_request("PUT", deactivate_url)
    
    if result and isinstance(result, dict):
        print(f"✅ Area deactivated using convenience endpoint!")
        print(f"Name: {result['name']}")
        print(f"Is Active: {result.get('is_active', 'Not specified')}")
    else:
        print("❌ Failed to deactivate using convenience endpoint")
        return False
    
    # Test 2: Activate using convenience endpoint
    print("\n4b. Activate using convenience endpoint:")
    activate_url = f"{BASE_URL}/api/v1/security-firms/{FIRM_ID}/coverage-areas/{area_id}/activate"
    
    result = make_request("PUT", activate_url)
    
    if result and isinstance(result, dict):
        print(f"✅ Area activated using convenience endpoint!")
        print(f"Name: {result['name']}")
        print(f"Is Active: {result.get('is_active', 'Not specified')}")
        return True
    else:
        print("❌ Failed to activate using convenience endpoint")
        return False

def test_filtering_after_status_changes(area_id):
    """Test filtering after changing active status"""
    print("\n" + "="*60)
    print("5. FILTERING AFTER STATUS CHANGES")
    print("="*60)
    
    if not area_id:
        print("❌ No area ID provided for filtering test")
        return
    
    base_url = f"{BASE_URL}/api/v1/security-firms/{FIRM_ID}/coverage-areas"
    
    # First, deactivate the test area
    print("\n5a. Deactivating test area...")
    update_url = f"{BASE_URL}/api/v1/security-firms/{FIRM_ID}/coverage-areas/{area_id}"
    make_request("PUT", update_url, {"is_active": False})
    
    # Test active-only filtering
    print("\n5b. Get only active areas (should exclude our test area):")
    result = make_request("GET", base_url, params={"include_inactive": "false"})
    
    if result and isinstance(result, list):
        active_areas = [area for area in result if area.get('is_active', True)]
        inactive_areas = [area for area in result if not area.get('is_active', True)]
        
        print(f"✅ Active areas returned: {len(active_areas)}")
        print(f"✅ Inactive areas returned: {len(inactive_areas)} (should be 0)")
        
        # Check if our test area is excluded
        test_area_found = any(area['id'] == area_id for area in result)
        if not test_area_found:
            print("✅ Test area correctly excluded from active-only results")
        else:
            print("❌ Test area incorrectly included in active-only results")
    
    # Test include all
    print("\n5c. Get all areas (should include our inactive test area):")
    result = make_request("GET", base_url, params={"include_inactive": "true"})
    
    if result and isinstance(result, list):
        test_area_found = any(area['id'] == area_id for area in result)
        if test_area_found:
            print("✅ Test area correctly included in all results")
        else:
            print("❌ Test area missing from all results")
    
    # Reactivate for cleanup
    print("\n5d. Reactivating test area for cleanup...")
    make_request("PUT", update_url, {"is_active": True})

def test_combined_updates(area_id):
    """Test updating multiple fields including is_active"""
    print("\n" + "="*60)
    print("6. COMBINED UPDATES")
    print("="*60)
    
    if not area_id:
        print("❌ No area ID provided for combined update test")
        return
    
    url = f"{BASE_URL}/api/v1/security-firms/{FIRM_ID}/coverage-areas/{area_id}"
    
    # Update name, boundary, and active status together
    print("\n6a. Update name, boundary, and active status together:")
    update_data = {
        "name": "Updated Test Coverage Area - Inactive",
        "boundary_coordinates": [
            [28.0250, -26.1250],  # Slightly different boundary
            [28.0450, -26.1250],
            [28.0450, -26.1050],
            [28.0250, -26.1050],
            [28.0250, -26.1250]
        ],
        "is_active": False
    }
    
    result = make_request("PUT", url, update_data)
    
    if result and isinstance(result, dict):
        print(f"✅ Combined update successful!")
        print(f"Name: {result['name']}")
        print(f"Is Active: {result.get('is_active', 'Not specified')}")
        print(f"Boundary points: {len(result.get('boundary_coordinates', []))}")
        return True
    else:
        print("❌ Combined update failed")
        return False

def cleanup_test_area(area_id):
    """Clean up the test area"""
    print("\n" + "="*60)
    print("7. CLEANUP")
    print("="*60)
    
    if not area_id:
        print("❌ No area ID provided for cleanup")
        return
    
    url = f"{BASE_URL}/api/v1/security-firms/{FIRM_ID}/coverage-areas/{area_id}"
    
    result = make_request("DELETE", url)
    
    if result and isinstance(result, dict) and "message" in result:
        print(f"✅ Test area cleaned up successfully!")
        print(f"Message: {result['message']}")
    else:
        print("❌ Failed to clean up test area")

def main():
    """Run all active status tests"""
    print("🧪 Coverage Area Active Status Testing")
    print("Testing is_active field functionality for coverage areas")
    
    # Step 1: Create a test coverage area
    area_id = test_create_coverage_area_with_active_status()
    
    if area_id:
        # Step 2: Test filtering
        test_get_coverage_areas_with_filtering(area_id)
        
        # Step 3: Test updating active status
        test_update_active_status(area_id)
        
        # Step 4: Test convenience endpoints
        test_convenience_endpoints(area_id)
        
        # Step 5: Test filtering after status changes
        test_filtering_after_status_changes(area_id)
        
        # Step 6: Test combined updates
        test_combined_updates(area_id)
        
        # Step 7: Cleanup
        cleanup_test_area(area_id)
    
    print("\n🎉 Coverage Area Active Status testing completed!")

if __name__ == "__main__":
    main()