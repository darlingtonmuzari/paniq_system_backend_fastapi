#!/usr/bin/env python3
"""
Test authentication for the my-products endpoint
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_my_products_endpoint(token):
    """Test the my-products endpoint with the given token"""
    
    url = f"{BASE_URL}/api/v1/subscription-products/my-products"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print(f"Testing endpoint: {url}")
    print(f"Headers: {headers}")
    
    try:
        response = requests.get(url, headers=headers)
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        try:
            response_data = response.json()
            print(f"Response Body: {json.dumps(response_data, indent=2)}")
        except:
            print(f"Response Body (raw): {response.text}")
            
        if response.status_code == 403:
            print("\n❌ 403 Forbidden - This means your token is valid but doesn't have the right role")
            print("Expected: user_type='firm_personnel' AND role='firm_admin'")
            
        elif response.status_code == 401:
            print("\n❌ 401 Unauthorized - This means your token is invalid or expired")
            
        elif response.status_code == 200:
            print("\n✅ Success! Your token works correctly")
            
        else:
            print(f"\n❓ Unexpected status code: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - make sure the API server is running on localhost:8000")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("Authentication Debug Tool")
    print("========================")
    
    token = input("Enter your JWT token: ").strip()
    
    if token:
        test_my_products_endpoint(token)
    else:
        print("No token provided")