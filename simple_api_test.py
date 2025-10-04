#!/usr/bin/env python3
"""
Simple test to check if API is working and returns user data
"""
import requests
import json

# First test if server is running
try:
    response = requests.get('http://localhost:8000/', timeout=5)
    print(f"✅ Server is running - Status: {response.status_code}")
    
    # Try to login with an admin user
    auth_response = requests.post(
        'http://localhost:8000/api/v1/auth/login',
        json={
            "email": "admin@paniq.co.za",
            "password": "password123"  # Common default password
        },
        timeout=10
    )
    
    print(f"Auth attempt status: {auth_response.status_code}")
    if auth_response.status_code != 200:
        print(f"Auth response: {auth_response.text[:200]}")
    
except requests.exceptions.RequestException as e:
    print(f"❌ Server connection failed: {e}")
except Exception as e:
    print(f"❌ Error: {e}")