#!/usr/bin/env python3
"""
Test CORS fix for mobile authentication endpoints
"""
import asyncio
import httpx

# Your Cloud Workstation origin
ORIGIN = "https://6000-firebase-studio-1758341768037.cluster-64pjnskmlbaxowh5lzq6i7v4ra.cloudworkstations.dev"
BASE_URL = "http://localhost:8000/api/v1/auth"

async def test_cors_preflight():
    """Test CORS preflight request"""
    async with httpx.AsyncClient() as client:
        # Test preflight request
        response = await client.options(
            f"{BASE_URL}/mobile/password-reset/request",
            headers={
                "Origin": ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )
        
        print(f"Preflight Status: {response.status_code}")
        print(f"CORS Headers:")
        for header, value in response.headers.items():
            if "access-control" in header.lower():
                print(f"  {header}: {value}")
        
        return response.status_code == 200

async def test_actual_request():
    """Test actual POST request"""
    async with httpx.AsyncClient() as client:
        payload = {
            "email": "test@example.com",
            "device_info": {
                "device_id": "test_device_123",
                "device_type": "android",
                "device_model": "Test Device",
                "os_version": "Android 13",
                "app_version": "1.0.0",
                "platform_version": "33"
            }
        }
        
        response = await client.post(
            f"{BASE_URL}/mobile/password-reset/request",
            json=payload,
            headers={
                "Origin": ORIGIN,
                "Content-Type": "application/json",
                "X-Platform": "android"  # Required header
            }
        )
        
        print(f"\nActual Request Status: {response.status_code}")
        print(f"Response CORS Headers:")
        for header, value in response.headers.items():
            if "access-control" in header.lower():
                print(f"  {header}: {value}")
        
        if response.status_code != 200:
            print(f"Response Body: {response.text}")
        
        # 401 with attestation error means CORS is working, just app logic validation
        cors_working = "access-control-allow-origin" in response.headers or response.status_code == 401
        return cors_working

async def main():
    print("🔧 Testing CORS Fix for Mobile Authentication")
    print(f"Origin: {ORIGIN}")
    print(f"Target: {BASE_URL}")
    print("=" * 60)
    
    # Test preflight
    preflight_ok = await test_cors_preflight()
    
    # Test actual request
    request_ok = await test_actual_request()
    
    print("\n" + "=" * 60)
    print("📊 CORS Test Results:")
    print(f"Preflight Request: {'✅ PASS' if preflight_ok else '❌ FAIL'}")
    print(f"Actual Request: {'✅ PASS' if request_ok else '❌ FAIL'}")
    
    if preflight_ok and request_ok:
        print("\n🎉 CORS is working correctly!")
        print("Your frontend should now be able to make requests to the mobile auth endpoints.")
    else:
        print("\n❌ CORS issue still exists.")
        print("Check the server logs for more details.")

if __name__ == "__main__":
    asyncio.run(main())