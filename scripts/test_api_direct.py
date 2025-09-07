#!/usr/bin/env python3
"""
Test the API directly to see the actual error response
"""
import requests
import json

def test_api_direct():
    """Test the API directly"""
    
    base_url = "http://localhost:8000"
    
    print("🧪 Testing API Direct Response")
    print("=" * 40)
    
    # Test without authentication first
    print("\n1. Testing without authentication...")
    try:
        response = requests.post(
            f"{base_url}/api/v1/payments/purchase-credits",
            json={
                "firm_id": "01356a70-72a6-4c69-b9c3-719c69c69c69",
                "amount": 150.00
            },
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Text: {response.text}")
        
        if response.headers.get('content-type', '').startswith('application/json'):
            try:
                response_json = response.json()
                print(f"Response JSON: {json.dumps(response_json, indent=2)}")
            except:
                print("Could not parse JSON response")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    # Test credit tiers endpoint (no auth required)
    print("\n2. Testing credit tiers endpoint...")
    try:
        response = requests.get(f"{base_url}/api/v1/payments/credit-tiers")
        print(f"Credit Tiers Status: {response.status_code}")
        if response.status_code == 200:
            tiers = response.json()
            print(f"Found {len(tiers)} credit tiers")
        else:
            print(f"Credit Tiers Error: {response.text}")
    except Exception as e:
        print(f"❌ Credit Tiers Error: {str(e)}")
    
    print("\n✅ API Direct Test Completed!")


if __name__ == "__main__":
    test_api_direct()