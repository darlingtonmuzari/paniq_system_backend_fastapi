#!/usr/bin/env python3
"""
Test authentication and endpoint access
"""
import asyncio
import httpx
import json

BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

async def test_endpoint_access():
    """Test endpoint access with different authentication scenarios"""
    print("🔍 Testing Endpoint Access...")
    
    async with httpx.AsyncClient() as client:
        
        # Test 1: No authentication
        print("\n1. Testing without authentication...")
        try:
            response = await client.get(f"{API_BASE}/subscription-products/my-products")
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
        except Exception as e:
            print(f"Error: {e}")
        
        # Test 2: Invalid token
        print("\n2. Testing with invalid token...")
        try:
            headers = {"Authorization": "Bearer invalid_token"}
            response = await client.get(
                f"{API_BASE}/subscription-products/my-products",
                headers=headers
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.json()}")
        except Exception as e:
            print(f"Error: {e}")
        
        # Test 3: Check if we can access the public endpoint
        print("\n3. Testing public endpoint without auth...")
        try:
            response = await client.get(f"{API_BASE}/subscription-products/")
            print(f"Status: {response.status_code}")
            if response.status_code == 401:
                print(f"Response: {response.json()}")
            elif response.status_code == 200:
                data = response.json()
                print(f"Success! Found {data.get('total_count', 0)} products")
            else:
                print(f"Unexpected status: {response.text}")
        except Exception as e:
            print(f"Error: {e}")
        
        # Test 4: Check available auth endpoints
        print("\n4. Checking available auth endpoints...")
        try:
            response = await client.get(f"{BASE_URL}/docs")
            if response.status_code == 200:
                print("✅ API documentation is accessible at /docs")
            else:
                print(f"❌ Cannot access API docs: {response.status_code}")
        except Exception as e:
            print(f"Error accessing docs: {e}")

if __name__ == "__main__":
    print("🚀 Testing Authentication and Endpoint Access")
    print("=" * 60)
    
    asyncio.run(test_endpoint_access())
    
    print("\n" + "=" * 60)
    print("🎉 Test Complete!")
    print("\nTo properly test the firm admin endpoints, you need to:")
    print("1. Create a firm admin user account")
    print("2. Login to get a valid JWT token")
    print("3. Use that token in the Authorization header")