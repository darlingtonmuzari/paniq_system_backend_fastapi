#!/usr/bin/env python3
"""
Send a password reset email to darlingtonmuzari@gmail.com
"""

import asyncio
import httpx
import json

async def send_password_reset():
    """Send password reset email to the specified address"""
    
    url = "http://localhost:8000/api/v1/auth/mobile/password-reset/request"
    
    headers = {
        "Content-Type": "application/json",
        "X-Platform": "web",
    }
    
    payload = {
        "email": "darlingtonmuzari@gmail.com",
        "device_info": {
            "device_id": "test-web-device-123",
            "device_type": "web",
            "device_model": "Chrome Browser",
            "os_version": "Ubuntu 22.04",
            "app_version": "1.0.0",
            "platform_version": "web-1.0"
        }
    }
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            print("Sending password reset email...")
            print(f"URL: {url}")
            print(f"Email: {payload['email']}")
            print("-" * 50)
            
            response = await client.post(url, json=payload, headers=headers)
            
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            print(f"Response Body: {response.text}")
            
            if response.status_code == 200:
                print("\n✅ SUCCESS: Password reset email sent!")
                print("📧 Check darlingtonmuzari@gmail.com for the OTP email")
                print("📧 Also check server logs for SMTP sending details")
            elif response.status_code == 400:
                print("\n⚠️  Bad Request - checking error details...")
                try:
                    error_data = response.json()
                    print(f"Error details: {json.dumps(error_data, indent=2)}")
                except:
                    print("Could not parse error response")
            elif response.status_code == 404:
                print("\n⚠️  Email not found in database")
                print("💡 The email darlingtonmuzari@gmail.com may not be registered")
            else:
                print(f"\n❌ Unexpected status: {response.status_code}")
                
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")

if __name__ == "__main__":
    asyncio.run(send_password_reset())