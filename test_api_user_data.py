#!/usr/bin/env python3
"""
Simple API test to verify user data is properly retrieved in panic_requests
"""
import requests
import json

def test_api_user_data():
    """Test panic requests API to ensure user data is included"""
    
    try:
        # Get an admin token first
        auth_response = requests.post(
            'http://localhost:8000/api/v1/auth/login',
            json={
                "email": "admin@example.com",
                "password": "securepassword123"
            }
        )
        
        if auth_response.status_code != 200:
            print("❌ Failed to get admin token")
            return
            
        token = auth_response.json().get('access_token')
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        # Get requests using the dashboard endpoint (doesn't require mobile attestation)
        response = requests.get(
            'http://localhost:8000/api/v1/emergency/dashboard/agent/requests?limit=5',
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            panic_requests = data.get('requests', [])
            
            print(f"Found {len(panic_requests)} requests")
            
            for request in panic_requests[:3]:  # Check first 3 requests
                print(f"\n--- Request {request.get('id')} ---")
                print(f"Requester phone: {request.get('requester_phone')}")
                print(f"Service type: {request.get('service_type')}")
                print(f"Status: {request.get('status')}")
                
                # Check if requester_name is present
                requester_name = request.get('requester_name')
                if requester_name:
                    print(f"✅ Requester name: {requester_name}")
                else:
                    print("❌ Requester name NOT included")
                
                print(f"Group ID: {request.get('group_id')}")
                print(f"Address: {request.get('address')}")
        else:
            print(f"❌ API request failed with status {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error testing API: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_api_user_data()