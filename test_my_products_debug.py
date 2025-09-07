#!/usr/bin/env python3
"""
Debug script to test the my-products endpoint with the provided token
"""
import requests
import json

# Your access token
ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI4NjBmZmJiMS05NjkyLTRkYTEtYjBlYy1hNDNlZDdiZDQ1ZjciLCJ1c2VyX3R5cGUiOiJmaXJtX3BlcnNvbm5lbCIsImVtYWlsIjoiZGFybGluZ3RvbkBtYW5pY2Fzb2x1dGlvbnMuY29tIiwicGVybWlzc2lvbnMiOlsicmVxdWVzdDp2aWV3IiwicmVxdWVzdDphY2NlcHQiXSwiZXhwIjoxNzU3MDU2NTg4LCJpYXQiOjE3NTcwNTI5ODgsImp0aSI6IjUzMTc2OTAwLTBmOWYtNDU0My1iMzA0LTEzZDhkY2VkNmFhYiIsInRva2VuX3R5cGUiOiJhY2Nlc3MiLCJmaXJtX2lkIjoiZTE3OGU5ZjQtMDFjYi00YzhlLTkxMGYtOTU4NjUxNjE3MmQ2Iiwicm9sZSI6ImZpcm1fYWRtaW4ifQ.nsgpEjkVmOjAujpFj6-jj551qOm-GHgpNRAuXzHjQi0"

BASE_URL = "http://localhost:8000"

def test_my_products():
    """Test the my-products endpoint"""
    url = f"{BASE_URL}/api/v1/subscription-products/my-products"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    print(f"Testing: {url}")
    print(f"Headers: {headers}")
    
    try:
        response = requests.get(url, headers=headers, params={"include_inactive": "false"})
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success! Products: {len(data.get('products', []))}")
        else:
            print(f"Error: {response.status_code}")
            
    except Exception as e:
        print(f"Request failed: {e}")

def test_auth_endpoint():
    """Test if auth is working"""
    url = f"{BASE_URL}/api/v1/auth/me"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    print(f"\nTesting auth: {url}")
    
    try:
        response = requests.get(url, headers=headers)
        print(f"Auth Status Code: {response.status_code}")
        print(f"Auth Response: {response.text}")
        
    except Exception as e:
        print(f"Auth request failed: {e}")

def test_available_endpoints():
    """Test what endpoints are available"""
    url = f"{BASE_URL}/docs"
    print(f"\nAPI docs available at: {url}")
    
    # Test the root subscription products endpoint
    url = f"{BASE_URL}/api/v1/subscription-products/"
    print(f"\nTesting root endpoint: {url}")
    
    try:
        response = requests.get(url)
        print(f"Root endpoint status: {response.status_code}")
        print(f"Root endpoint response: {response.text}")
        
    except Exception as e:
        print(f"Root endpoint failed: {e}")

if __name__ == "__main__":
    test_auth_endpoint()
    test_available_endpoints()
    test_my_products()