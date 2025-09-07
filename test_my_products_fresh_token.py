#!/usr/bin/env python3
"""
Test script to get a fresh token and test the my-products endpoint
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def get_fresh_token():
    """Get a fresh access token"""
    login_url = f"{BASE_URL}/api/v1/auth/login"
    
    # Use the credentials from the JWT payload
    login_data = {
        "email": "darlington@manicasolutions.com",
        "password": "password123"  # You'll need to provide the actual password
    }
    
    print(f"Attempting login at: {login_url}")
    print(f"Email: {login_data['email']}")
    
    try:
        response = requests.post(login_url, json=login_data)
        print(f"Login Status Code: {response.status_code}")
        print(f"Login Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token")
        else:
            print("Login failed")
            return None
            
    except Exception as e:
        print(f"Login request failed: {e}")
        return None

def test_my_products_with_fresh_token():
    """Test the my-products endpoint with a fresh token"""
    # First try to get a fresh token
    token = get_fresh_token()
    
    if not token:
        print("Could not get fresh token, using the provided token")
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI4NjBmZmJiMS05NjkyLTRkYTEtYjBlYy1hNDNlZDdiZDQ1ZjciLCJ1c2VyX3R5cGUiOiJmaXJtX3BlcnNvbm5lbCIsImVtYWlsIjoiZGFybGluZ3RvbkBtYW5pY2Fzb2x1dGlvbnMuY29tIiwicGVybWlzc2lvbnMiOlsicmVxdWVzdDp2aWV3IiwicmVxdWVzdDphY2NlcHQiXSwiZXhwIjoxNzU3MDU2NTg4LCJpYXQiOjE3NTcwNTI5ODgsImp0aSI6IjUzMTc2OTAwLTBmOWYtNDU0My1iMzA0LTEzZDhkY2VkNmFhYiIsInRva2VuX3R5cGUiOiJhY2Nlc3MiLCJmaXJtX2lkIjoiZTE3OGU5ZjQtMDFjYi00YzhlLTkxMGYtOTU4NjUxNjE3MmQ2Iiwicm9sZSI6ImZpcm1fYWRtaW4ifQ.nsgpEjkVmOjAujpFj6-jj551qOm-GHgpNRAuXzHjQi0"
    
    url = f"{BASE_URL}/api/v1/subscription-products/my-products"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print(f"\nTesting: {url}")
    
    try:
        response = requests.get(url, headers=headers, params={"include_inactive": "false"})
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success! Products: {len(data.get('products', []))}")
        else:
            print(f"Error: {response.status_code}")
            
    except Exception as e:
        print(f"Request failed: {e}")

def test_direct_firm_endpoint():
    """Test the direct firm endpoint as an alternative"""
    # Use the firm ID from the JWT
    firm_id = "e178e9f4-01cb-4c8e-910f-9586516172d6"
    
    # Try to get a fresh token
    token = get_fresh_token()
    if not token:
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI4NjBmZmJiMS05NjkyLTRkYTEtYjBlYy1hNDNlZDdiZDQ1ZjciLCJ1c2VyX3R5cGUiOiJmaXJtX3BlcnNvbm5lbCIsImVtYWlsIjoiZGFybGluZ3RvbkBtYW5pY2Fzb2x1dGlvbnMuY29tIiwicGVybWlzc2lvbnMiOlsicmVxdWVzdDp2aWV3IiwicmVxdWVzdDphY2NlcHQiXSwiZXhwIjoxNzU3MDU2NTg4LCJpYXQiOjE3NTcwNTI5ODgsImp0aSI6IjUzMTc2OTAwLTBmOWYtNDU0My1iMzA0LTEzZDhkY2VkNmFhYiIsInRva2VuX3R5cGUiOiJhY2Nlc3MiLCJmaXJtX2lkIjoiZTE3OGU5ZjQtMDFjYi00YzhlLTkxMGYtOTU4NjUxNjE3MmQ2Iiwicm9sZSI6ImZpcm1fYWRtaW4ifQ.nsgpEjkVmOjAujpFj6-jj551qOm-GHgpNRAuXzHjQi0"
    
    url = f"{BASE_URL}/api/v1/subscription-products/firm/{firm_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print(f"\nTesting direct firm endpoint: {url}")
    
    try:
        response = requests.get(url, headers=headers, params={"include_inactive": "false"})
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_my_products_with_fresh_token()
    test_direct_firm_endpoint()