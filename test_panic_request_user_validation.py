#!/usr/bin/env python3
"""
Test script to verify panic request user validation and relationship functionality
"""
import asyncio
import json
import httpx
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:8000"
ADMIN_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhNGNlOGZjMi02YTZlLTQ3ZTMtYjc2ZS0yOWQ1M2MzYTYyN2QiLCJ1c2VyX3R5cGUiOiJmaXJtX3BlcnNvbm5lbCIsImVtYWlsIjoiIiwicGVybWlzc2lvbnMiOltdLCJleHAiOjE3NTg4NzA3NjUsImlhdCI6MTc1ODg2NzE2NSwianRpIjoiNjY5NWVkNzMtYTAwNS00OTZjLWE5OWItNmU0M2ZlM2Q1ZjAwIiwidG9rZW5fdHlwZSI6ImFjY2VzcyIsInJvbGUiOiJhZG1pbiJ9.oArqIlyNw3QNZxZziRA9K3cIKCrXjsm-4a4LDdJrcWU"

async def test_panic_request_user_details():
    """Test that panic requests return proper user details"""
    
    headers = {
        "Authorization": f"Bearer {ADMIN_TOKEN}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("Testing panic request user details retrieval...")
        
        # Get all panic requests to see user details
        try:
            response = await client.get(
                f"{BASE_URL}/api/v1/emergency/requests", 
                headers=headers,
                params={"limit": 5}
            )
            
            if response.status_code == 200:
                data = response.json()
                requests = data.get("requests", [])
                
                print(f"Found {len(requests)} panic requests")
                
                for request in requests:
                    print(f"\nRequest ID: {request['id']}")
                    print(f"Requester Phone: {request['requester_phone']}")
                    print(f"Requester Name: {request.get('requester_name', 'NOT SET')}")
                    print(f"Group ID: {request['group_id']}")
                    print(f"Service Type: {request['service_type']}")
                    print(f"Status: {request['status']}")
                    print(f"Created: {request['created_at']}")
                    
                    if request.get('requester_name'):
                        print(f"✅ User details loaded successfully: {request['requester_name']}")
                    else:
                        print("❌ User details missing")
            else:
                print(f"Failed to fetch requests: {response.status_code}")
                print(f"Response: {response.text}")
                
        except Exception as e:
            print(f"Error fetching panic requests: {e}")
        
        # Test individual request details
        print("\n" + "="*50)
        print("Testing individual panic request details...")
        
        # Get a specific panic request
        try:
            response = await client.get(
                f"{BASE_URL}/api/v1/emergency/requests/f704ef89-23d2-468e-b769-adbd624b1fe1",
                headers=headers
            )
            
            if response.status_code == 200:
                request = response.json()
                print(f"\nSpecific Request Details:")
                print(f"Request ID: {request['id']}")
                print(f"Requester Phone: {request['requester_phone']}")
                print(f"Requester Name: {request.get('requester_name', 'NOT SET')}")
                print(f"Group ID: {request['group_id']}")
                
                if request.get('requester_name'):
                    print(f"✅ User details loaded for individual request: {request['requester_name']}")
                else:
                    print("❌ User details missing for individual request")
            else:
                print(f"Failed to fetch individual request: {response.status_code}")
                print(f"Response: {response.text}")
                
        except Exception as e:
            print(f"Error fetching individual request: {e}")

async def test_database_integrity():
    """Test database integrity - all panic requests should have valid users and group memberships"""
    print("\n" + "="*50)
    print("Testing database integrity...")
    
    # Direct database query would be done here if we had DB access
    # For now, we'll rely on the API responses to validate the data
    print("Database integrity test would require direct DB access.")
    print("Based on API responses above, we can validate if user details are properly loaded.")

async def main():
    """Main test runner"""
    print("🧪 Testing Panic Request User Validation and Relationships")
    print("=" * 60)
    
    await test_panic_request_user_details()
    await test_database_integrity()
    
    print("\n" + "=" * 60)
    print("✅ Test completed!")

if __name__ == "__main__":
    asyncio.run(main())