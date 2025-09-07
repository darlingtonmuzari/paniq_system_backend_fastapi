#!/usr/bin/env python3
"""
Test the route without authentication to isolate the issue
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_routes():
    """Test various routes to see which ones work"""
    
    routes_to_test = [
        "/api/v1/subscription-products/",
        "/api/v1/subscription-products/my-products",
        "/api/v1/subscription-products/firm/e178e9f4-01cb-4c8e-910f-9586516172d6",
    ]
    
    for route in routes_to_test:
        url = f"{BASE_URL}{route}"
        print(f"\nTesting: {url}")
        
        try:
            response = requests.get(url)
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            
        except Exception as e:
            print(f"Request failed: {e}")

def test_openapi_spec():
    """Check the OpenAPI spec to see if the route is registered"""
    url = f"{BASE_URL}/openapi.json"
    print(f"\nChecking OpenAPI spec: {url}")
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            spec = response.json()
            paths = spec.get("paths", {})
            
            print("Available subscription-products paths:")
            for path in paths:
                if "subscription-products" in path:
                    print(f"  {path}")
                    methods = list(paths[path].keys())
                    print(f"    Methods: {methods}")
        else:
            print(f"Failed to get OpenAPI spec: {response.status_code}")
            
    except Exception as e:
        print(f"OpenAPI request failed: {e}")

if __name__ == "__main__":
    test_openapi_spec()
    test_routes()