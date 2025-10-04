#!/usr/bin/env python3
"""
Debug CORS middleware behavior
"""
import requests

def test_cors_with_debug():
    """Test CORS with debug information"""
    
    endpoints = [
        "/api/v1/emergency/agent/requests",
        "/api/v1/subscription-products/my-products",
        "/api/v1/auth/login"
    ]
    
    origin = "http://localhost:4050"
    
    print(f"Testing CORS with origin: {origin}")
    print("=" * 60)
    
    for endpoint in endpoints:
        print(f"\nTesting: {endpoint}")
        
        # Test OPTIONS (preflight)
        print("  OPTIONS request:")
        try:
            response = requests.options(
                f"http://localhost:8000{endpoint}",
                headers={
                    'Origin': origin,
                    'Access-Control-Request-Method': 'GET',
                    'Access-Control-Request-Headers': 'authorization,content-type'
                }
            )
            
            print(f"    Status: {response.status_code}")
            cors_headers = {}
            for header, value in response.headers.items():
                if 'access-control' in header.lower():
                    cors_headers[header] = value
            
            if cors_headers:
                print("    CORS Headers:")
                for header, value in cors_headers.items():
                    print(f"      {header}: {value}")
            else:
                print("    No CORS headers found")
                
        except Exception as e:
            print(f"    Error: {e}")
        
        # Test GET request
        print("  GET request:")
        try:
            response = requests.get(
                f"http://localhost:8000{endpoint}",
                headers={
                    'Origin': origin,
                    'Content-Type': 'application/json'
                }
            )
            
            print(f"    Status: {response.status_code}")
            cors_origin = response.headers.get('access-control-allow-origin')
            
            if cors_origin:
                print(f"    CORS Allow Origin: {cors_origin}")
            else:
                print("    No CORS Allow Origin header")
                
        except Exception as e:
            print(f"    Error: {e}")

if __name__ == "__main__":
    test_cors_with_debug()