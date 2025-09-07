#!/usr/bin/env python3
"""
Test the purchase-credits endpoint
"""
import requests
import json

# Test data
test_data = {
    "firm_id": "01234567-89ab-cdef-0123-456789abcdef",
    "amount": 150.00
}

# API endpoint
url = "http://localhost:8000/api/v1/payments/purchase-credits-raw"

# Headers (you'll need a valid JWT token)
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer YOUR_JWT_TOKEN_HERE"
}

try:
    response = requests.post(url, json=test_data, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print(f"Response Body:")
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"Error: {str(e)}")
    print(f"Response text: {response.text if 'response' in locals() else 'No response'}")