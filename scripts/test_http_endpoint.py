#!/usr/bin/env python3
"""
Test the HTTP endpoint directly to see what's happening
"""
import asyncio
import sys
import os

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

async def test_http_endpoint():
    """Test the HTTP endpoint directly"""
    
    print("🔍 Testing HTTP endpoint behavior...")
    
    try:
        import httpx
        
        base_url = "http://localhost:8000"
        
        # Test 1: Try without authentication (should get 401)
        print("\n1️⃣ Testing without authentication...")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{base_url}/api/v1/firm-applications/?page=1&per_page=10")
                print(f"   Status: {response.status_code}")
                print(f"   Response: {response.text}")
        except Exception as e:
            print(f"   ❌ Request failed: {e}")
        
        # Test 2: Check if server is running
        print("\n2️⃣ Testing server health...")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{base_url}/api/v1/")
                print(f"   Status: {response.status_code}")
                print(f"   Response: {response.text}")
        except Exception as e:
            print(f"   ❌ Server not reachable: {e}")
            print("   💡 Make sure the FastAPI server is running on localhost:8000")
        
        # Test 3: Try to get a token (if auth endpoint exists)
        print("\n3️⃣ Checking authentication endpoint...")
        try:
            async with httpx.AsyncClient() as client:
                # Try to login with test credentials
                login_data = {
                    "email": "darlington@manicasolutions.com",
                    "password": "test_password"  # This might not work, just testing
                }
                response = await client.post(f"{base_url}/api/v1/auth/login", json=login_data)
                print(f"   Login Status: {response.status_code}")
                if response.status_code == 200:
                    token_data = response.json()
                    access_token = token_data.get("access_token")
                    
                    if access_token:
                        print("   ✅ Got access token, testing authenticated request...")
                        
                        # Test authenticated request
                        headers = {"Authorization": f"Bearer {access_token}"}
                        auth_response = await client.get(
                            f"{base_url}/api/v1/firm-applications/?page=1&per_page=10",
                            headers=headers
                        )
                        print(f"   Authenticated Status: {auth_response.status_code}")
                        print(f"   Authenticated Response: {auth_response.text}")
                else:
                    print(f"   Login failed: {response.text}")
        except Exception as e:
            print(f"   ❌ Auth test failed: {e}")
        
        return True
        
    except ImportError:
        print("❌ httpx not installed. Install with: pip install httpx")
        return False
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_http_endpoint())
    
    if success:
        print("\n💡 HTTP ENDPOINT TEST COMPLETED!")
        print("\n🔑 AUTHENTICATION REQUIRED:")
        print("   The firm-applications endpoint requires a valid JWT token.")
        print("   You need to:")
        print("   1. Login via POST /api/v1/auth/login")
        print("   2. Get the access_token from the response")
        print("   3. Include it in the Authorization header: 'Bearer <token>'")
        print("\n📝 Example:")
        print("   curl -H 'Authorization: Bearer <your-token>' \\")
        print("        'http://localhost:8000/api/v1/firm-applications/?page=1&per_page=10'")
    else:
        print("\n❌ HTTP ENDPOINT TEST FAILED!")
    
    sys.exit(0 if success else 1)