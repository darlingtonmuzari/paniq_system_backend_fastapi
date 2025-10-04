#!/usr/bin/env python3
"""
Test the new web dashboard endpoint for agent requests
"""
import requests
import json

def test_dashboard_endpoint():
    """Test the new dashboard endpoint that doesn't require mobile attestation"""
    
    # Test from localhost:4000 (admin port range)
    headers = {
        'Origin': 'http://localhost:4000',
        'Content-Type': 'application/json'
    }
    
    print("Testing new dashboard endpoint...")
    print(f"Origin: {headers['Origin']}")
    print()
    
    try:
        # Test the new dashboard endpoint
        response = requests.get(
            'http://localhost:8000/api/v1/emergency/dashboard/agent/requests?limit=50&offset=0',
            headers=headers,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        print("Response Headers:")
        for header, value in response.headers.items():
            if 'access-control' in header.lower():
                print(f"  {header}: {value}")
        
        print()
        print("Response Body:")
        try:
            print(json.dumps(response.json(), indent=2))
        except:
            print(response.text)
            
        # Check if CORS headers are present
        cors_headers = [h for h in response.headers.keys() if 'access-control' in h.lower()]
        if cors_headers:
            print(f"\n✅ CORS headers found: {cors_headers}")
        else:
            print("\n❌ No CORS headers found in response")
            
        # Check if we get a different error (should be authentication, not mobile attestation)
        if response.status_code == 401:
            response_data = response.json()
            if "attestation" not in response_data.get("message", "").lower():
                print("✅ No mobile attestation error - endpoint is web accessible")
            else:
                print("❌ Still getting mobile attestation error")
                
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    test_dashboard_endpoint()