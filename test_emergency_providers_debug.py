#!/usr/bin/env python3

import asyncio
import requests
import json

# The JWT token from the user (updated with 24-hour validity)
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI4NjBmZmJiMS05NjkyLTRkYTEtYjBlYy1hNDNlZDdiZDQ1ZjciLCJ1c2VyX3R5cGUiOiJmaXJtX3BlcnNvbm5lbCIsImVtYWlsIjoiZGFybGluZ3RvbkBtYW5pY2Fzb2x1dGlvbnMuY29tIiwicGVybWlzc2lvbnMiOlsicmVxdWVzdDp2aWV3IiwicmVxdWVzdDphY2NlcHQiXSwiZmlybV9pZCI6ImUxNzhlOWY0LTAxY2ItNGM4ZS05MTBmLTk1ODY1MTYxNzJkNiIsInJvbGUiOiJmaXJtX2FkbWluIiwidG9rZW5fdHlwZSI6ImFjY2VzcyIsImp0aSI6Im5ldy10ZXN0LXRva2VuLWlkLTEyMyIsImlhdCI6MTc1ODIxODA3MCwiZXhwIjoxNzU4MzA0NDcwfQ.w-wtRhbYn089xN0_lv-0Hdpuy-kKPQ5c1W_c5nzdkL4"

# Test the emergency providers endpoint
def test_emergency_providers():
    url = "http://localhost:8001/api/v1/emergency-providers/"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print("=== TESTING EMERGENCY PROVIDERS ENDPOINT ===")
    print(f"URL: {url}")
    print(f"Headers: {headers}")
    print()
    
    try:
        response = requests.get(url, headers=headers)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print()
        
        if response.status_code == 200:
            data = response.json()
            print("SUCCESS! Response:")
            print(json.dumps(data, indent=2))
        else:
            print("FAILED! Response:")
            try:
                error_data = response.json()
                print(json.dumps(error_data, indent=2))
            except:
                print(response.text)
                
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to the server. Is it running on localhost:8000?")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test_emergency_providers()