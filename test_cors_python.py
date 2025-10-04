#!/usr/bin/env python3
"""
Test CORS configuration from Python
"""
import requests

def test_cors_preflight():
    """Test CORS preflight request"""
    print("Testing CORS preflight (OPTIONS) request...")
    
    headers = {
        'Origin': 'http://localhost:3000',
        'Access-Control-Request-Method': 'GET',
        'Access-Control-Request-Headers': 'authorization,content-type'
    }
    
    try:
        response = requests.options(
            'http://localhost:8000/api/v1/emergency/agent/requests',
            headers=headers
        )
        
        print(f"Status: {response.status_code}")
        print("CORS Headers:")
        for header, value in response.headers.items():
            if 'access-control' in header.lower():
                print(f"  {header}: {value}")
                
        if response.status_code == 200:
            print("✅ CORS preflight successful!")
        else:
            print(f"❌ CORS preflight failed with status {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def test_cors_get():
    """Test actual GET request with CORS"""
    print("\nTesting CORS GET request...")
    
    headers = {
        'Origin': 'http://localhost:3000',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(
            'http://localhost:8000/api/v1/emergency/agent/requests?limit=50&offset=0',
            headers=headers
        )
        
        print(f"Status: {response.status_code}")
        cors_origin = response.headers.get('access-control-allow-origin')
        print(f"CORS Allow Origin: {cors_origin}")
        
        if cors_origin:
            print("✅ CORS headers present!")
        else:
            print("❌ No CORS headers found")
            
        if response.status_code == 401:
            print("✅ Got 401 (expected without token) - CORS is working!")
        elif response.status_code == 403:
            print("✅ Got 403 (permission issue) - CORS is working!")
        else:
            print(f"Got status {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def test_subscription_products():
    """Test subscription products endpoint"""
    print("\nTesting subscription products endpoint...")
    
    headers = {
        'Origin': 'http://localhost:3000',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(
            'http://localhost:8000/api/v1/subscription-products/my-products',
            headers=headers
        )
        
        print(f"Status: {response.status_code}")
        cors_origin = response.headers.get('access-control-allow-origin')
        print(f"CORS Allow Origin: {cors_origin}")
        
        if cors_origin:
            print("✅ CORS headers present!")
        else:
            print("❌ No CORS headers found")
            
        if response.status_code == 401:
            print("✅ Got 401 (expected without token) - CORS is working!")
        elif response.status_code == 403:
            print("✅ Got 403 (permission issue) - CORS is working!")
        else:
            print(f"Got status {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("CORS Configuration Test")
    print("======================")
    
    test_cors_preflight()
    test_cors_get()
    test_subscription_products()