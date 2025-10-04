#!/usr/bin/env python3
"""
Test CORS headers on authentication errors
"""
import requests
import json

def test_cors_on_auth_error():
    """Test that CORS headers are present on 401 authentication errors"""
    
    # Test from localhost:4000 (admin port range)
    headers = {
        'Origin': 'http://localhost:4000',
        'Content-Type': 'application/json'
    }
    
    print("Testing CORS headers on authentication error...")
    print(f"Origin: {headers['Origin']}")
    print()
    
    try:
        # Make request without authentication token (should get 401)
        response = requests.get(
            'http://localhost:8000/api/v1/emergency/agent/requests?limit=50&offset=0',
            headers=headers,
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        print("Response Headers:")
        for header, value in response.headers.items():
            if 'access-control' in header.lower() or 'cors' in header.lower():
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
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    test_cors_on_auth_error()