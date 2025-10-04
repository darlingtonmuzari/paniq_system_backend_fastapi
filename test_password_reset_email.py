#!/usr/bin/env python3
"""
Test script for mobile password reset endpoint with proper headers.
This script tests the email OTP delivery functionality.
"""

import asyncio
import httpx
import json

async def test_password_reset_email():
    """Test the mobile password reset endpoint with proper headers"""
    
    # API endpoint
    url = "http://localhost:8000/api/v1/auth/mobile/password-reset/request"
    
    # Required headers for mobile endpoints
    headers = {
        "Content-Type": "application/json",
        "X-Platform": "web",  # This allows web testing
        "X-App-Version": "1.0.0",
        "X-Device-ID": "test-device-123",
        "User-Agent": "PaniqTest/1.0.0"
    }
    
    # Test data
    payload = {
        "email": "test@example.com",
        "device_fingerprint": {
            "screen_resolution": "1920x1080",
            "timezone": "Africa/Johannesburg",
            "user_agent": "PaniqTest/1.0.0"
        }
    }
    
    async with httpx.AsyncClient() as client:
        try:
            print("Testing password reset endpoint...")
            print(f"URL: {url}")
            print(f"Headers: {json.dumps(headers, indent=2)}")
            print(f"Payload: {json.dumps(payload, indent=2)}")
            print("-" * 50)
            
            response = await client.post(
                url, 
                json=payload, 
                headers=headers,
                timeout=30.0
            )
            
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            print(f"Response Body: {response.text}")
            
            if response.status_code == 200:
                print("\n✅ SUCCESS: Request was accepted")
                print("📧 Check the server logs for email sending status")
                print("📧 Also check your email inbox for the OTP")
            elif response.status_code == 400:
                print("\n⚠️  WARNING: Bad Request - probably validation error")
                print("💡 Check the response body for details")
            elif response.status_code == 404:
                print("\n⚠️  WARNING: Email not found in database")
                print("💡 Try with an email that exists in the users table")
            elif response.status_code == 401:
                print("\n❌ ERROR: Authentication/Authorization issue")
            else:
                print(f"\n❌ ERROR: Unexpected status code {response.status_code}")
                
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_password_reset_email())