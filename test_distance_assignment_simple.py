#!/usr/bin/env python3
"""
Simple test for distance-based team assignment functionality
"""
import requests
import json

BASE_URL = "http://localhost:8000"

# Token from the previous output
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmOGEzMDkxOS01ZWQ1LTQ2YWYtOTVkNi0zYWZhNGRhNjM0ZGEiLCJ1c2VyX3R5cGUiOiJmaXJtX3BlcnNvbm5lbCIsImVtYWlsIjoidGVzdC5tYW5pY2Fzb2x1dGlvbnNAZ21haWwuY29tIiwicGVybWlzc2lvbnMiOlsicmVxdWVzdDp2aWV3IiwicmVxdWVzdDphY2NlcHQiXSwiZXhwIjoxNzU4ODAyMzUwLCJpYXQiOjE3NTg3MTU5NTAsImp0aSI6InRlc3QtdG9rZW4tZjhhMzA5MTkiLCJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZmlybV9pZCI6ImUxNzhlOWY0LTAxY2ItNGM4ZS05MTBmLTk1ODY1MTYxNzJkNiIsInJvbGUiOiJmaXJtX3N1cGVydmlzb3IifQ.7c1lzettWTqa7KDerjFAyg3WjKFd9WvEJjFU85ZcpT4"

def test_distance_assignment():
    """Test the distance-based team assignment endpoints"""
    print("🚀 Testing distance-based team assignment functionality...\n")
    
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Test 1: Get nearest teams for a specific location
    print("1. Testing 'Find Nearest Teams' endpoint...")
    nearest_teams_url = f"{BASE_URL}/api/v1/emergency/teams/nearest"
    params = {
        "latitude": -26.1434,  # Johannesburg coordinates
        "longitude": 28.0144,
        "max_distance_km": 50
    }
    
    try:
        response = requests.get(nearest_teams_url, headers=headers, params=params)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            teams_data = response.json()
            print(f"✅ Found {len(teams_data.get('teams', []))} nearby teams")
            for team in teams_data.get('teams', []):
                print(f"  - {team['name']}: {team['distance_km']:.2f}km away")
        else:
            print(f"❌ Error: {response.text}")
    except Exception as e:
        print(f"❌ Request failed: {e}")
    
    # Test 2: First create a panic request to test assignment
    print("\n2. Creating a test panic request...")
    create_request_url = f"{BASE_URL}/api/v1/emergency/requests"
    request_data = {
        "requester_phone": "+27821234567",
        "service_type": "security_breach",
        "latitude": -26.1434,
        "longitude": 28.0144,
        "address": "123 Test Street, Johannesburg",
        "description": "Test request for distance assignment"
    }
    
    try:
        response = requests.post(create_request_url, headers=headers, json=request_data)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 201:
            request_response = response.json()
            request_id = request_response.get('request_id')
            print(f"✅ Created panic request: {request_id}")
            
            # Test 3: Assign the request to the nearest team
            print("\n3. Testing 'Assign to Nearest Team' endpoint...")
            assign_url = f"{BASE_URL}/api/v1/emergency/requests/{request_id}/assign-nearest-team"
            assign_params = {
                "max_distance_km": 50
            }
            
            response = requests.post(assign_url, headers=headers, params=assign_params)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                assign_data = response.json()
                print(f"✅ Request assigned successfully!")
                print(f"  - Team: {assign_data.get('assigned_team', {}).get('name', 'Unknown')}")
                print(f"  - Distance: {assign_data.get('distance_km', 0):.2f}km")
                print(f"  - Status: {assign_data.get('status', 'Unknown')}")
            else:
                print(f"❌ Assignment failed: {response.text}")
        else:
            print(f"❌ Failed to create panic request: {response.text}")
    except Exception as e:
        print(f"❌ Request failed: {e}")
    
    print("\n🎉 Distance assignment functionality test completed!")

if __name__ == "__main__":
    test_distance_assignment()