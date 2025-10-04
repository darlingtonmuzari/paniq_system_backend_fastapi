#!/usr/bin/env python3

import requests
import json
import asyncio

async def test_api_endpoints():
    """Test the emergency providers API endpoints"""
    
    print("🧪 Testing Emergency Providers API Endpoints")
    print("=" * 50)
    
    base_url = "http://localhost:8000/api/v1/emergency-providers"
    
    # Test the GET endpoint that was failing
    print("1. Testing GET /api/v1/emergency-providers/")
    try:
        response = requests.get(f"{base_url}/", timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success! Got {len(data.get('providers', []))} providers")
            
            if data.get('providers'):
                provider = data['providers'][0]
                print(f"\nFirst provider:")
                print(f"Name: {provider.get('name')}")
                print(f"Street: {provider.get('street_address')}")
                print(f"City: {provider.get('city')}")
                print(f"Province: {provider.get('province')}")
                print(f"Country: {provider.get('country')}")
                print(f"Postal Code: {provider.get('postal_code')}")
                print(f"Status: {provider.get('status')}")
        else:
            print(f"❌ Failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error: {error_data}")
            except:
                print(f"Error: {response.text}")
                
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - make sure the API server is running")
        print("Start the server with: uvicorn app.main:app --reload --port 8000")
    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_api_endpoints())