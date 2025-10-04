#!/usr/bin/env python3
"""
Create sample emergency providers using the API endpoints
"""
import requests
import json
from uuid import uuid4
import sys
import os

# Add the app directory to Python path
sys.path.append('/home/melcy/Programming/kiro/paniq_system')

from app.services.auth import JWTTokenService

def create_sample_providers():
    """Create sample emergency providers via API"""
    
    # Generate a token with firm_admin role and a firm_id
    jwt_service = JWTTokenService()
    
    # Use a known firm ID - let's generate one for our sample firm
    sample_firm_id = uuid4()
    
    admin_token = jwt_service.create_access_token(
        user_id=uuid4(),
        user_type="firm_personnel",
        email="admin@ctss.co.za",
        permissions=[],
        firm_id=sample_firm_id,
        role="firm_admin"
    )
    
    print("🔑 Generated Admin Token:")
    print("=" * 80)
    print(admin_token)
    print()
    
    base_url = "http://localhost:8000/api/v1"
    headers = {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }
    
    # First, let's try to create some emergency provider types
    print("📋 Creating Emergency Provider Types...")
    
    provider_types_data = [
        {
            "name": "Ambulance Service",
            "code": "ambulance",
            "description": "Emergency medical transport services",
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
        }
    ]
    
    created_type_ids = []
    
    for type_data in provider_types_data:
        try:
            response = requests.post(
                f"{base_url}/emergency-provider-types/",
                headers=headers,
                json=type_data
            )
            if response.status_code == 201:
                result = response.json()
                created_type_ids.append(result["id"])
                print(f"✅ Created provider type: {type_data['name']} (ID: {result['id']})")
            else:
                print(f"❌ Failed to create provider type {type_data['name']}: {response.status_code}")
                print(f"   Response: {response.text}")
        except Exception as e:
            print(f"❌ Error creating provider type {type_data['name']}: {e}")
    
    # If no types were created via API, let's use some default UUIDs that might exist
    if not created_type_ids:
        print("⚠️  No provider types created via API, using default UUIDs...")
        created_type_ids = [str(uuid4()), str(uuid4())]  # Fallback IDs
    
    print(f"\n🏗️  Creating Emergency Providers...")
    
    # Sample emergency providers data
    providers_data = [
        {
            "name": "Cape Town Emergency Medical",
            "provider_type": "ambulance",
            "provider_type_id": created_type_ids[0] if len(created_type_ids) > 0 else str(uuid4()),
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
            "provider_type_id": created_type_ids[1] if len(created_type_ids) > 1 else str(uuid4()),
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
            "provider_type_id": created_type_ids[0] if len(created_type_ids) > 0 else str(uuid4()),  # Reuse first ID
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
                print(f"✅ Created provider: {provider_data['name']} (ID: {result['id']})")
            else:
                print(f"❌ Failed to create provider {provider_data['name']}: {response.status_code}")
                print(f"   Response: {response.text}")
        except Exception as e:
            print(f"❌ Error creating provider {provider_data['name']}: {e}")
    
    print(f"\n🎉 Summary:")
    print(f"   - Created {len(created_providers)} emergency providers")
    print(f"   - Firm ID: {sample_firm_id}")
    
    # Test the GET endpoint
    print(f"\n📋 Testing GET endpoint...")
    try:
        response = requests.get(f"{base_url}/emergency-providers/", headers=headers)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ GET endpoint works! Found {result['total_count']} providers")
            
            for provider in result['providers']:
                print(f"   - {provider['name']} ({provider['provider_type']}) - {provider['status']}")
        else:
            print(f"❌ GET endpoint failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Error testing GET endpoint: {e}")
    
    print(f"\n🔧 Test Commands:")
    print("=" * 80)
    print(f'# List all emergency providers:')
    print(f'curl -H "Authorization: Bearer {admin_token}" \\')
    print(f'     "http://localhost:8000/api/v1/emergency-providers/"')
    print()
    print(f'# List only ambulances:')
    print(f'curl -H "Authorization: Bearer {admin_token}" \\')
    print(f'     "http://localhost:8000/api/v1/emergency-providers/?provider_type=ambulance"')

if __name__ == "__main__":
    create_sample_providers()