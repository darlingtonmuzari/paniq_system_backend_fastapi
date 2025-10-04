#!/usr/bin/env python3

import requests
import json

# Create a simple panic request
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhNGNlOGZjMi02YTZlLTQ3ZTMtYjc2ZS0yOWQ1M2MzYTYyN2QiLCJ1c2VyX3R5cGUiOiJmaXJtX3BlcnNvbm5lbCIsImVtYWlsIjoiIiwicGVybWlzc2lvbnMiOltdLCJleHAiOjE3NTg4MzA3NTAsImlhdCI6MTc1ODgyNzE1MCwianRpIjoiYzhiNjMwYzEtYmUyMC00ZTc3LWI0Y2ItMjE4M2QwNDE3MDFhIiwidG9rZW5fdHlwZSI6ImFjY2VzcyIsImZpcm1faWQiOiI4MDQ5NzJiZC1mM2MwLTQ5N2YtYWVlZS0yNTQ3MTFmZDEwN2MiLCJyb2xlIjoiZmlybV9hZG1pbiJ9.NPTKJN5GH3XPC1DTI8szR6sPYqjbMGyO_wTcIUcO3tY"

headers = {
    "Authorization": f"Bearer {token}",
    "X-Mobile-App-Attestation": "mobile-app-test",
    "Content-Type": "application/json"
}

# First, let's check if we can get any existing data
try:
    response = requests.get("http://localhost:8000/api/v1/emergency/agent/requests?limit=10&offset=0", headers=headers)
    print(f"Agent requests response: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Response data: {json.dumps(data, indent=2)}")
        
        # Check if we have requests with requester_name field
        if data.get('requests'):
            for req in data['requests']:
                print(f"Request {req.get('id')} has requester_name: {req.get('requester_name', 'NOT FOUND')}")
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Error making request: {e}")