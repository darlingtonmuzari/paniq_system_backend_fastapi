#!/usr/bin/env python3

import requests
import json

# Configuration
API_BASE = "http://localhost:8000"
# You'll need to provide a valid token
TOKEN = "YOUR_TOKEN_HERE"

def test_create_emergency_provider():
    """Test creating an emergency provider with debug info"""
    
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Your updated payload
    payload = {
        "name": "Emras",
        "provider_type_id": "3518e746-40d3-4a47-ac05-9b29d1a0a74f",
        "contact_phone": "+27746537702",
        "contact_email": "help@emras.com",
        "street_address": "100 Johannesburg Road",
        "city": "Lyndhurst",
        "province": "Gauteng",
        "country": "South Africa",
        "postal_code": "2191",
        "description": "",
        "current_latitude": -26.1273,
        "current_longitude": 28.1128,
        "base_latitude": -26.1273,
        "base_longitude": 28.1128,
        "capabilities": ["advanced_life_support", "emergency_medical_transport"],
        "status": "available",
        "equipment_details": "5x AMC Ambulawanes",
        "capacity": "5"
    }
    
    print("🔍 Debugging Emergency Provider Creation")
    print("=" * 50)
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print()
    
    # Test the endpoint
    response = requests.post(f"{API_BASE}/api/v1/emergency-providers/", 
                           headers=headers, 
                           json=payload)
    
    print(f"Status Code: {response.status_code}")
    
    try:
        response_data = response.json()
        print(f"Response: {json.dumps(response_data, indent=2)}")
    except:
        print(f"Response text: {response.text}")
    
    if response.status_code == 200:
        print("\n✅ Emergency provider created successfully!")
        return response.json()
    else:
        print(f"\n❌ Failed to create emergency provider")
        return None

if __name__ == "__main__":
    result = test_create_emergency_provider()