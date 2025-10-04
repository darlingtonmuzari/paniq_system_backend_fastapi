#!/usr/bin/env python3

import requests
import json

# Configuration
API_BASE = "http://localhost:8000"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhNGNlOGZjMi02YTZlLTQ3ZTMtYjc2ZS0yOWQ1M2MzYTYyN2QiLCJ1c2VyX3R5cGUiOiJmaXJtX3BlcnNvbm5lbCIsImVtYWlsIjoiYWRtaW5AcGFuaXEuY28uemEiLCJwZXJtaXNzaW9ucyI6WyJyZXF1ZXN0OnZpZXciLCJyZXF1ZXN0OmFjY2VwdCIsImFkbWluOmFsbCIsImZpcm06bWFuYWdlIiwidXNlcjptYW5hZ2UiLCJzeXN0ZW06bWFuYWdlIiwidGVhbTptYW5hZ2UiLCJwZXJzb25uZWw6bWFuYWdlIl0sImV4cCI6MTc1ODI1NTQxMywiaWF0IjoxNzU4MjUxODEzLCJqdGkiOiIwMzQ1YjU2Ny1lOGE4LTQ4ZGQtOWE0Ny05YzJjYTgxZTFkZTciLCJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZmlybV9pZCI6IjI0OWQwM2I4LWZjMGEtNDYwYi04MmFmLTA0OTQ0NWQxNWRiYiIsInJvbGUiOiJhZG1pbiJ9.i5TyYonHSiGZcZbQUeBjalxUwdyp4G2Aqf5lLyjvEu8"

def test_create_emergency_provider():
    """Test creating an emergency provider with the provided payload"""
    
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Your original payload
    payload = {
        "name": "Emras",
        "provider_type_id": "3518e746-40d3-4a47-ac05-9b29d1a0a74f",
        "contact_phone": "+27746537701",
        "contact_email": "help@emars.com",
        "street_address": "100 Johannesburg Road",
        "city": "Lyndhurst",
        "province": "Gauteng",
        "country": "South Africa",
        "postal_code": "211",
        "description": "",
        "current_latitude": -26.1273,
        "current_longitude": 28.1128,
        "base_latitude": -26.1273,
        "base_longitude": 28.1128,
        "capabilities": ["basic_life_support", "emergency_medical_transport", "emergency_medical_services"],
        "status": "available",
        "equipment_details": "5 x AMC Ambulawances",
        "capacity": "5"
    }
    
    print("🧪 Testing Emergency Provider Creation")
    print("=" * 50)
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print()
    
    # Test the endpoint
    response = requests.post(f"{API_BASE}/api/v1/emergency-providers/", 
                           headers=headers, 
                           json=payload)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        print("\n✅ Emergency provider created successfully!")
        return response.json()
    else:
        print(f"\n❌ Failed to create emergency provider")
        return None

if __name__ == "__main__":
    result = test_create_emergency_provider()