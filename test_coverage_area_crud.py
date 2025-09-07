#!/usr/bin/env python3
"""
Test script for Coverage Area CRUD operations
"""
import requests
import json

BASE_URL = "http://localhost:8000"

# Use the fresh token we generated earlier
ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI4NjBmZmJiMS05NjkyLTRkYTEtYjBlYy1hNDNlZDdiZDQ1ZjciLCJ1c2VyX3R5cGUiOiJmaXJtX3BlcnNvbm5lbCIsImVtYWlsIjoiZGFybGluZ3RvbkBtYW5pY2Fzb2x1dGlvbnMuY29tIiwicGVybWlzc2lvbnMiOlsicmVxdWVzdDp2aWV3IiwicmVxdWVzdDphY2NlcHQiXSwiZXhwIjoxNzU3MTM2MTE2LCJpYXQiOjE3NTcwNDk3MTYsImp0aSI6InRlc3QtdG9rZW4tODYwZmZiYjEiLCJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZmlybV9pZCI6ImUxNzhlOWY0LTAxY2ItNGM4ZS05MTBmLTk1ODY1MTYxNzJkNiIsInJvbGUiOiJmaXJtX2FkbWluIn0.iZbEu7nSsJxqeA1-bNuWVrD7THAgCHRIQ_Q9wnj9LII"

# Firm ID from the token
FIRM_ID = "e178e9f4-01cb-4c8e-910f-9586516172d6"

def make_request(method, url, data=None):
    """Make HTTP request with authentication"""
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data)
        elif method.upper() == "PUT":
            response = requests.put(url, headers=headers, json=data)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        print(f"{method.upper()} {url}")
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

def test_create_coverage_area():
    """Test creating a coverage area"""
    print("\n" + "="*60)
    print("1. CREATE COVERAGE AREA")
    print("="*60)
    
    url = f"{BASE_URL}/api/v1/security-firms/{FIRM_ID}/coverage-areas"
    
    # Create a test coverage area in Sandton
    coverage_data = {
        "name": "Sandton Business District",
        "boundary_coordinates": [
            [28.0400, -26.1100],  # Southwest corner
            [28.0500, -26.1100],  # Southeast corner
            [28.0500, -26.1000],  # Northeast corner
            [28.0400, -26.1000],  # Northwest corner
            [28.0400, -26.1100]   # Close polygon
        ]
    }
    
    result = make_request("POST", url, coverage_data)
    
    if result and isinstance(result, dict) and "id" in result:
        print(f"✅ Coverage area created successfully!")
        print(f"Area ID: {result['id']}")
        print(f"Area Name: {result['name']}")
        return result["id"]
    else:
        print("❌ Failed to create coverage area")
        return None

def test_get_coverage_areas():
    """Test getting all coverage areas"""
    print("\n" + "="*60)
    print("2. GET ALL COVERAGE AREAS")
    print("="*60)
    
    url = f"{BASE_URL}/api/v1/security-firms/{FIRM_ID}/coverage-areas"
    
    result = make_request("GET", url)
    
    if result and isinstance(result, list):
        print(f"✅ Found {len(result)} coverage area(s)")
        for i, area in enumerate(result):
            print(f"  {i+1}. {area['name']} (ID: {area['id']})")
        return result
    else:
        print("❌ Failed to get coverage areas")
        return []

def test_update_coverage_area(area_id):
    """Test updating a coverage area"""
    print("\n" + "="*60)
    print("3. UPDATE COVERAGE AREA")
    print("="*60)
    
    if not area_id:
        print("❌ No area ID provided for update")
        return False
    
    url = f"{BASE_URL}/api/v1/security-firms/{FIRM_ID}/coverage-areas/{area_id}"
    
    # Test 1: Update only the name
    print("\n3a. Update name only:")
    update_data = {
        "name": "Sandton Business District - Updated"
    }
    
    result = make_request("PUT", url, update_data)
    
    if result and isinstance(result, dict):
        print(f"✅ Name updated successfully!")
        print(f"New name: {result['name']}")
    else:
        print("❌ Failed to update name")
        return False
    
    # Test 2: Update both name and boundary
    print("\n3b. Update name and boundary:")
    update_data = {
        "name": "Sandton Extended Business District",
        "boundary_coordinates": [
            [28.0350, -26.1150],  # Expanded area
            [28.0550, -26.1150],
            [28.0550, -26.0950],
            [28.0350, -26.0950],
            [28.0350, -26.1150]
        ]
    }
    
    result = make_request("PUT", url, update_data)
    
    if result and isinstance(result, dict):
        print(f"✅ Name and boundary updated successfully!")
        print(f"New name: {result['name']}")
        print(f"New boundary has {len(result['boundary_coordinates'])} points")
        return True
    else:
        print("❌ Failed to update name and boundary")
        return False

def test_update_boundary_only(area_id):
    """Test updating only the boundary coordinates"""
    print("\n" + "="*60)
    print("4. UPDATE BOUNDARY ONLY")
    print("="*60)
    
    if not area_id:
        print("❌ No area ID provided for boundary update")
        return False
    
    url = f"{BASE_URL}/api/v1/security-firms/{FIRM_ID}/coverage-areas/{area_id}"
    
    # Update only boundary coordinates
    update_data = {
        "boundary_coordinates": [
            [28.0380, -26.1120],  # Slightly different area
            [28.0520, -26.1120],
            [28.0520, -26.0980],
            [28.0380, -26.0980],
            [28.0380, -26.1120]
        ]
    }
    
    result = make_request("PUT", url, update_data)
    
    if result and isinstance(result, dict):
        print(f"✅ Boundary updated successfully!")
        print(f"Name unchanged: {result['name']}")
        print(f"New boundary has {len(result['boundary_coordinates'])} points")
        return True
    else:
        print("❌ Failed to update boundary")
        return False

def test_delete_coverage_area(area_id):
    """Test deleting a coverage area"""
    print("\n" + "="*60)
    print("5. DELETE COVERAGE AREA")
    print("="*60)
    
    if not area_id:
        print("❌ No area ID provided for deletion")
        return False
    
    url = f"{BASE_URL}/api/v1/security-firms/{FIRM_ID}/coverage-areas/{area_id}"
    
    result = make_request("DELETE", url)
    
    if result and isinstance(result, dict) and "message" in result:
        print(f"✅ Coverage area deleted successfully!")
        print(f"Message: {result['message']}")
        return True
    else:
        print("❌ Failed to delete coverage area")
        return False

def test_error_cases():
    """Test various error cases"""
    print("\n" + "="*60)
    print("6. ERROR CASE TESTING")
    print("="*60)
    
    # Test 1: Update non-existent area
    print("\n6a. Update non-existent area:")
    fake_area_id = "00000000-0000-0000-0000-000000000000"
    url = f"{BASE_URL}/api/v1/security-firms/{FIRM_ID}/coverage-areas/{fake_area_id}"
    
    update_data = {"name": "This should fail"}
    result = make_request("PUT", url, update_data)
    
    # Test 2: Invalid boundary coordinates
    print("\n6b. Invalid boundary coordinates:")
    # First create an area to update
    create_url = f"{BASE_URL}/api/v1/security-firms/{FIRM_ID}/coverage-areas"
    test_area = {
        "name": "Test Area for Error Testing",
        "boundary_coordinates": [
            [28.0400, -26.1100],
            [28.0500, -26.1100],
            [28.0500, -26.1000],
            [28.0400, -26.1000],
            [28.0400, -26.1100]
        ]
    }
    
    created_area = make_request("POST", create_url, test_area)
    
    if created_area and "id" in created_area:
        # Try to update with invalid coordinates (too few points)
        invalid_update = {
            "boundary_coordinates": [
                [28.0400, -26.1100],
                [28.0500, -26.1100]  # Only 2 points - invalid
            ]
        }
        
        update_url = f"{BASE_URL}/api/v1/security-firms/{FIRM_ID}/coverage-areas/{created_area['id']}"
        result = make_request("PUT", update_url, invalid_update)
        
        # Clean up - delete the test area
        make_request("DELETE", update_url)

def main():
    """Run all coverage area CRUD tests"""
    print("🧪 Coverage Area CRUD Testing")
    print("Testing endpoints for creating, reading, updating, and deleting coverage areas")
    
    # Step 1: Create a coverage area
    area_id = test_create_coverage_area()
    
    # Step 2: Get all coverage areas
    areas = test_get_coverage_areas()
    
    if area_id:
        # Step 3: Update the coverage area
        test_update_coverage_area(area_id)
        
        # Step 4: Update boundary only
        test_update_boundary_only(area_id)
        
        # Step 5: Get areas again to see changes
        print("\n" + "="*60)
        print("VERIFY CHANGES")
        print("="*60)
        test_get_coverage_areas()
        
        # Step 6: Delete the coverage area
        test_delete_coverage_area(area_id)
        
        # Step 7: Verify deletion
        print("\n" + "="*60)
        print("VERIFY DELETION")
        print("="*60)
        test_get_coverage_areas()
    
    # Step 8: Test error cases
    test_error_cases()
    
    print("\n🎉 Coverage Area CRUD testing completed!")

if __name__ == "__main__":
    main()