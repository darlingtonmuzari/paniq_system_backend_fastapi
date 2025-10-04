#!/usr/bin/env python3
"""
Test endpoint directly to see the error
"""
import requests

# Try to hit the endpoint directly without auth to see what error we get
try:
    print("Testing endpoint without authentication...")
    response = requests.get(
        'http://localhost:8001/api/v1/emergency/agent/requests?limit=50&offset=0',
        timeout=30
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
except Exception as e:
    print(f"Error: {e}")

# Also test with fake token to see the actual endpoint error
try:
    print("\nTesting endpoint with fake token...")
    headers = {
        'Authorization': 'Bearer fake_token_for_test',
        'X-Mobile-Attestation': 'debug-mobile-app-v1.0.0'
    }
    
    response = requests.get(
        'http://localhost:8001/api/v1/emergency/agent/requests?limit=50&offset=0',
        headers=headers,
        timeout=30
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
except Exception as e:
    print(f"Error: {e}")