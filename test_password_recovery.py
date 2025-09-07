#!/usr/bin/env python3
"""
Test script for password recovery functionality
"""
import asyncio
import httpx
import json

BASE_URL = "http://localhost:8000"

async def test_password_recovery():
    """Test the password recovery flow"""
    
    async with httpx.AsyncClient() as client:
        print("🔐 Testing Password Recovery Flow")
        print("=" * 50)
        
        # Test 1: Request password reset OTP
        print("\n1. Requesting password reset OTP...")
        
        reset_request = {
            "email": "admin@paniq.co.za",
            "user_type": "firm_personnel"
        }
        
        response = await client.post(
            f"{BASE_URL}/api/v1/auth/password-reset/request",
            json=reset_request
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✅ Password reset OTP request successful")
        else:
            print("❌ Password reset OTP request failed")
            return
        
        # Test 2: Verify OTP and reset password (with test OTP)
        print("\n2. Verifying OTP and resetting password...")
        
        # For testing, we'll use a test OTP (you would get this from email in real scenario)
        test_otp = "123456"  # This matches the test implementation
        
        verify_request = {
            "email": "admin@paniq.co.za",
            "otp": test_otp,
            "new_password": "NewSecurePassword123!",
            "user_type": "firm_personnel"
        }
        
        response = await client.post(
            f"{BASE_URL}/api/v1/auth/password-reset/verify",
            json=verify_request
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✅ Password reset verification successful")
        else:
            print("❌ Password reset verification failed")
        
        # Test 3: Test with invalid OTP
        print("\n3. Testing with invalid OTP...")
        
        invalid_verify_request = {
            "email": "admin@paniq.co.za",
            "otp": "999999",
            "new_password": "AnotherPassword123!",
            "user_type": "firm_personnel"
        }
        
        response = await client.post(
            f"{BASE_URL}/api/v1/auth/password-reset/verify",
            json=invalid_verify_request
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 400:
            print("✅ Invalid OTP correctly rejected")
        else:
            print("❌ Invalid OTP should have been rejected")
        
        # Test 4: Test with non-existent email
        print("\n4. Testing with non-existent email...")
        
        nonexistent_request = {
            "email": "nonexistent@example.com",
            "user_type": "firm_personnel"
        }
        
        response = await client.post(
            f"{BASE_URL}/api/v1/auth/password-reset/request",
            json=nonexistent_request
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("✅ Non-existent email handled securely (no information disclosure)")
        else:
            print("❌ Non-existent email handling failed")

async def test_api_documentation():
    """Test that the API documentation includes the new endpoints"""
    
    async with httpx.AsyncClient() as client:
        print("\n📚 Testing API Documentation")
        print("=" * 50)
        
        response = await client.get(f"{BASE_URL}/openapi.json")
        
        if response.status_code == 200:
            openapi_spec = response.json()
            paths = openapi_spec.get("paths", {})
            
            # Check if password reset endpoints are documented
            reset_request_path = "/api/v1/auth/password-reset/request"
            reset_verify_path = "/api/v1/auth/password-reset/verify"
            
            if reset_request_path in paths:
                print("✅ Password reset request endpoint documented")
            else:
                print("❌ Password reset request endpoint not found in documentation")
            
            if reset_verify_path in paths:
                print("✅ Password reset verify endpoint documented")
            else:
                print("❌ Password reset verify endpoint not found in documentation")
        else:
            print("❌ Failed to fetch API documentation")

async def main():
    """Main test function"""
    try:
        await test_password_recovery()
        await test_api_documentation()
        
        print("\n🎉 Password Recovery Testing Complete!")
        print("\nTo test with real emails:")
        print("1. Configure SMTP settings in your .env file")
        print("2. Set SMTP_USERNAME, SMTP_PASSWORD, and FROM_EMAIL")
        print("3. The OTP will be sent to the actual email address")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")

if __name__ == "__main__":
    asyncio.run(main())