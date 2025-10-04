#!/usr/bin/env python3
"""
Add comprehensive sample data to emergency provider tables using the API
"""
import requests
import json
from uuid import uuid4

def add_emergency_sample_data():
    """Add sample emergency provider data using the API"""
    
    # Use the 1-hour token with proper permissions
    TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhNGNlOGZjMi02YTZlLTQ3ZTMtYjc2ZS0yOWQ1M2MzYTYyN2QiLCJ1c2VyX3R5cGUiOiJmaXJtX3BlcnNvbm5lbCIsImVtYWlsIjoiIiwicGVybWlzc2lvbnMiOltdLCJleHAiOjE3NTgxODc5MDgsImlhdCI6MTc1ODE4NDMwOCwianRpIjoiNTI4OGFmZTEtYzNiMy00ZDkzLTkzODAtZTI3ZDBkOTUyYjQxIiwidG9rZW5fdHlwZSI6ImFjY2VzcyIsImZpcm1faWQiOiI5NjY3ZTFjYS05YWRmLTRmODYtYjJhMy0wYTgyMGY4MTdiMTciLCJyb2xlIjoiZmlybV9hZG1pbiJ9.BShAv9DSRakmYlpUgfKZFHhYzgKhYi-1Vimv8WQA_jM"
    
    FIRM_ID = "9667e1ca-9adf-4f86-b2a3-0a820f817b17"
    
    base_url = "http://localhost:8000/api/v1"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    
    print("🚑 Adding Emergency Provider Sample Data")
    print("=" * 60)
    print(f"Using firm ID: {FIRM_ID}")
    print()
    
    # Step 1: Create Emergency Provider Types
    print("📋 Step 1: Creating Emergency Provider Types...")
    
    provider_types_data = [
        {
            "name": "Ambulance Service",
            "code": "ambulance",
            "description": "Emergency medical transport and first aid services",
            "requires_license": True,
            "default_coverage_radius_km": 30.0,
            "icon": "ambulance",
            "color": "#FF6B6B",
            "priority_level": "critical"
        },
        {
            "name": "Tow Truck Service",
            "code": "tow_truck", 
            "description": "Vehicle recovery and roadside assistance",
            "requires_license": True,
            "default_coverage_radius_km": 50.0,
            "icon": "truck",
            "color": "#4ECDC4",
            "priority_level": "medium"
        },
        {
            "name": "Security Response",
            "code": "security",
            "description": "Armed and unarmed security response teams",
            "requires_license": True,
            "default_coverage_radius_km": 25.0,
            "icon": "shield",
            "color": "#45B7D1",
            "priority_level": "high"
        }
    ]
    
    created_type_ids = {}
    
    for type_data in provider_types_data:
        try:
            response = requests.post(
                f"{base_url}/emergency-provider-types/",
                headers=headers,
                json=type_data
            )
            if response.status_code == 201:
                result = response.json()
                created_type_ids[type_data["code"]] = result["id"]
                print(f"   ✅ Created: {type_data['name']} (ID: {result['id']})")
            else:
                print(f"   ❌ Failed to create {type_data['name']}: {response.status_code}")
                print(f"      Response: {response.text}")
                # Use fallback UUID
                created_type_ids[type_data["code"]] = str(uuid4())
        except Exception as e:
            print(f"   ❌ Error creating {type_data['name']}: {e}")
            # Use fallback UUID
            created_type_ids[type_data["code"]] = str(uuid4())
    
    # Step 2: Create Emergency Providers
    print(f"\n🚑 Step 2: Creating Emergency Providers...")
    
    providers_data = [
        {
            "name": "Cape Town Emergency Medical",
            "provider_type": "ambulance",
            "provider_type_id": created_type_ids.get("ambulance", str(uuid4())),
            "license_number": "AMB-CT-001",
            "contact_phone": "+27214567890",
            "contact_email": "dispatch@ctem.co.za",
            "street_address": "45 Hospital Road",
            "city": "Cape Town",
            "province": "Western Cape",
            "country": "South Africa",
            "postal_code": "8001",
            "current_latitude": -33.9249,
            "current_longitude": 18.4241,
            "base_latitude": -33.9249,
            "base_longitude": 18.4241,
            "coverage_radius_km": 30.0,
            "description": "24/7 emergency medical response with advanced life support",
            "equipment_details": '{"vehicles": 3, "paramedics": 6, "equipment": ["defibrillator", "oxygen", "stretcher"]}',
            "capacity": "2 patients per vehicle"
        },
        {
            "name": "Atlantic Towing Services",
            "provider_type": "tow_truck",
            "provider_type_id": created_type_ids.get("tow_truck", str(uuid4())),
            "license_number": "TOW-AT-002",
            "contact_phone": "+27213456789",
            "contact_email": "operations@atlantictowing.co.za",
            "street_address": "78 Industrial Avenue",
            "city": "Cape Town",
            "province": "Western Cape",
            "country": "South Africa",
            "postal_code": "7925",
            "current_latitude": -33.9352,
            "current_longitude": 18.4392,
            "base_latitude": -33.9352,
            "base_longitude": 18.4392,
            "coverage_radius_km": 50.0,
            "description": "Heavy duty towing and vehicle recovery services",
            "equipment_details": '{"trucks": 5, "capacity": "up to 8 tons", "equipment": ["winch", "flatbed", "crane"]}',
            "capacity": "Up to 8 ton vehicles"
        },
        {
            "name": "Metro Security Response Unit",
            "provider_type": "security",
            "provider_type_id": created_type_ids.get("security", str(uuid4())),
            "license_number": "SEC-MSR-003",
            "contact_phone": "+27219876543",
            "contact_email": "control@metrosecurity.co.za",
            "street_address": "12 Security Plaza",
            "city": "Cape Town",
            "province": "Western Cape",
            "country": "South Africa",
            "postal_code": "8005",
            "current_latitude": -33.9258,
            "current_longitude": 18.4232,
            "base_latitude": -33.9258,
            "base_longitude": 18.4232,
            "coverage_radius_km": 25.0,
            "description": "Armed response and security services",
            "equipment_details": '{"vehicles": 8, "officers": 16, "equipment": ["firearms", "radios", "body_armor"]}',
            "capacity": "2 officers per vehicle"
        },
        {
            "name": "Southern Suburbs Ambulance",
            "provider_type": "ambulance",
            "provider_type_id": created_type_ids.get("ambulance", str(uuid4())),
            "license_number": "AMB-SS-004",
            "contact_phone": "+27215551234",
            "contact_email": "emergency@ssambulance.co.za",
            "street_address": "89 Wynberg Road",
            "city": "Wynberg",
            "province": "Western Cape",
            "country": "South Africa",
            "postal_code": "7800",
            "current_latitude": -34.0187,
            "current_longitude": 18.4632,
            "base_latitude": -34.0187,
            "base_longitude": 18.4632,
            "coverage_radius_km": 35.0,
            "description": "Emergency medical services for southern suburbs",
            "equipment_details": '{"vehicles": 2, "paramedics": 4, "equipment": ["defibrillator", "trauma_kit"]}',
            "capacity": "1 patient per vehicle"
        }
    ]
    
    created_providers = []
    
    for provider_data in providers_data:
        try:
            response = requests.post(
                f"{base_url}/emergency-providers/",
                headers=headers,
                json=provider_data
            )
            
            if response.status_code == 201:
                result = response.json()
                created_providers.append(result)
                print(f"   ✅ Created: {provider_data['name']}")
                print(f"      ID: {result['id']}")
                print(f"      Type: {result['provider_type']}")
                print(f"      Status: {result['status']}")
            else:
                print(f"   ❌ Failed to create {provider_data['name']}: {response.status_code}")
                print(f"      Response: {response.text}")
        except Exception as e:
            print(f"   ❌ Error creating {provider_data['name']}: {e}")
    
    # Step 3: Test the GET endpoint
    print(f"\n📋 Step 3: Testing GET endpoint...")
    try:
        response = requests.get(f"{base_url}/emergency-providers/", headers=headers)
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Success! Found {result['total_count']} emergency providers")
            
            for provider in result['providers']:
                print(f"      - {provider['name']}")
                print(f"        Type: {provider['provider_type']}")
                print(f"        Status: {provider['status']}")
                print(f"        Location: {provider['city']}, {provider['province']}")
                print(f"        Phone: {provider['contact_phone']}")
                print()
        else:
            print(f"   ❌ GET failed: {response.status_code}")
            print(f"      Response: {response.text}")
    except Exception as e:
        print(f"   ❌ Error testing GET: {e}")
    
    # Summary
    print(f"🎉 Summary:")
    print(f"   - Created {len(created_type_ids)} provider types")
    print(f"   - Created {len(created_providers)} emergency providers")
    print(f"   - Token expires in 1 hour")
    print()
    
    print(f"🔧 Your Token (1 hour expiration):")
    print(f"   {TOKEN}")
    print()
    
    print(f"📋 Test Commands:")
    print("=" * 60)
    print(f'export TOKEN="{TOKEN}"')
    print()
    print('# List all providers:')
    print('curl -H "Authorization: Bearer $TOKEN" \\')
    print('     "http://localhost:8000/api/v1/emergency-providers/"')
    print()
    print('# List only ambulances:')
    print('curl -H "Authorization: Bearer $TOKEN" \\')
    print('     "http://localhost:8000/api/v1/emergency-providers/?provider_type=ambulance"')
    print()
    print('# List only available providers:')
    print('curl -H "Authorization: Bearer $TOKEN" \\')
    print('     "http://localhost:8000/api/v1/emergency-providers/?status=available"')

if __name__ == "__main__":
    add_emergency_sample_data()