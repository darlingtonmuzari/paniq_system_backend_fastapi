#!/usr/bin/env python3
"""
Test script for Emergency Providers API
"""
import requests
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8000/api/v1"

# You'll need to replace this with a valid firm admin JWT token
ACCESS_TOKEN = "your-jwt-token-here"

def make_request(method: str, endpoint: str, data: Dict[Any, Any] = None) -> Dict[Any, Any]:
    """Make authenticated API request"""
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data)
        elif method.upper() == "PUT":
            response = requests.put(url, headers=headers, json=data)
        elif method.upper() == "PATCH":
            response = requests.patch(url, headers=headers, json=data)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        print(f"{method.upper()} {endpoint}")
        print(f"Status: {response.status_code}")
        
        try:
            result = response.json()
            print(f"Response: {json.dumps(result, indent=2)}")
            return result
        except:
            print(f"Response: {response.text}")
            return {"status_code": response.status_code, "text": response.text}
            
    except Exception as e:
        print(f"Error: {e}")
        return {"error": str(e)}

def test_emergency_providers():
    """Test emergency providers functionality"""
    
    print("=" * 60)
    print("EMERGENCY PROVIDERS API TEST")
    print("=" * 60)
    
    # 1. Create an ambulance provider
    print("\n1. Creating an ambulance provider...")
    ambulance_data = {
        "name": "City Emergency Ambulance #1",
        "provider_type": "ambulance",
        "license_number": "AMB-001-2024",
        "contact_phone": "+27123456789",
        "contact_email": "ambulance1@cityemergency.co.za",
        "current_latitude": -26.2041,
        "current_longitude": 28.0473,
        "base_latitude": -26.2041,
        "base_longitude": 28.0473,
        "coverage_radius_km": 25.0,
        "description": "Advanced Life Support ambulance with cardiac equipment",
        "equipment_details": '{"defibrillator": true, "oxygen": true, "stretcher": 2, "paramedics": 2}',
        "capacity": "2 patients, 2 paramedics"
    }
    
    ambulance = make_request("POST", "/emergency-providers", ambulance_data)
    ambulance_id = ambulance.get("id") if "id" in ambulance else None
    
    # 2. Create a tow truck provider
    print("\n2. Creating a tow truck provider...")
    tow_truck_data = {
        "name": "Highway Towing Service #1",
        "provider_type": "tow_truck",
        "license_number": "TOW-001-2024",
        "contact_phone": "+27123456790",
        "contact_email": "tow1@highwaytowing.co.za",
        "current_latitude": -26.1500,
        "current_longitude": 28.1000,
        "base_latitude": -26.1500,
        "base_longitude": 28.1000,
        "coverage_radius_km": 50.0,
        "description": "Heavy duty tow truck for all vehicle types",
        "equipment_details": '{"max_weight": "5000kg", "winch": true, "flatbed": true}',
        "capacity": "Up to 5 ton vehicles"
    }
    
    tow_truck = make_request("POST", "/emergency-providers", tow_truck_data)
    tow_truck_id = tow_truck.get("id") if "id" in tow_truck else None
    
    # 3. Get all providers for the firm
    print("\n3. Getting all providers for the firm...")
    make_request("GET", "/emergency-providers")
    
    # 4. Get providers filtered by type
    print("\n4. Getting ambulance providers only...")
    make_request("GET", "/emergency-providers?provider_type=ambulance")
    
    # 5. Update provider location
    if ambulance_id:
        print(f"\n5. Updating ambulance location...")
        location_update = {
            "latitude": -26.2100,
            "longitude": 28.0500
        }
        make_request("PATCH", f"/emergency-providers/{ambulance_id}/location", location_update)
    
    # 6. Search for nearest providers
    print("\n6. Searching for nearest ambulances...")
    search_params = "latitude=-26.2000&longitude=28.0400&provider_type=ambulance&max_distance_km=30&limit=5"
    make_request("GET", f"/emergency-providers/search/nearest?{search_params}")
    
    # 7. Update provider status
    if tow_truck_id:
        print(f"\n7. Updating tow truck details...")
        update_data = {
            "status": "busy",
            "description": "Heavy duty tow truck - currently on assignment"
        }
        make_request("PUT", f"/emergency-providers/{tow_truck_id}", update_data)
    
    # 8. Get specific provider
    if ambulance_id:
        print(f"\n8. Getting ambulance details...")
        make_request("GET", f"/emergency-providers/{ambulance_id}")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETED")
    print("=" * 60)
    print("\nNOTE: Make sure to:")
    print("1. Replace ACCESS_TOKEN with a valid firm admin JWT token")
    print("2. Ensure the API server is running on localhost:8000")
    print("3. Run database migrations to create the emergency_providers tables")

def test_distance_calculation():
    """Test distance calculation functionality"""
    print("\n" + "=" * 60)
    print("DISTANCE CALCULATION TEST")
    print("=" * 60)
    
    # Test coordinates (Johannesburg area)
    locations = [
        {"name": "Sandton", "lat": -26.1076, "lon": 28.0567},
        {"name": "Rosebank", "lat": -26.1463, "lon": 28.0436},
        {"name": "Midrand", "lat": -25.9953, "lon": 28.1294},
        {"name": "Pretoria", "lat": -25.7479, "lon": 28.2293}
    ]
    
    print("\nDistance calculations between locations:")
    for i, loc1 in enumerate(locations):
        for j, loc2 in enumerate(locations[i+1:], i+1):
            # This would use the Haversine formula in the service
            print(f"{loc1['name']} to {loc2['name']}: ~{calculate_distance(loc1['lat'], loc1['lon'], loc2['lat'], loc2['lon']):.2f} km")

def calculate_distance(lat1, lon1, lat2, lon2):
    """Simple distance calculation for demo"""
    import math
    
    # Convert to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Earth radius in km
    r = 6371
    
    return c * r

if __name__ == "__main__":
    print("Emergency Providers API Test")
    print("============================")
    
    if ACCESS_TOKEN == "your-jwt-token-here":
        print("⚠️  WARNING: Please set a valid ACCESS_TOKEN before running tests")
        print("   You can get a token by logging in as a firm admin")
        print()
    
    test_distance_calculation()
    
    if ACCESS_TOKEN != "your-jwt-token-here":
        test_emergency_providers()
    else:
        print("\nSkipping API tests - no valid token provided")
        print("Set ACCESS_TOKEN and run again to test the API endpoints")