#!/usr/bin/env python3
"""
Simple test for password reset endpoint bypassing rate limiting issues.
"""

import asyncio
import httpx
import json

async def test_simple_password_reset():
    """Test the mobile password reset endpoint directly"""
    
    # Use curl-like approach with simpler headers
    url = "http://localhost:8000/api/v1/auth/mobile/password-reset/request"
    
    # Minimal headers to test the core functionality
    headers = {
        "Content-Type": "application/json",
        "X-Platform": "web",
    }
    
    # Simple payload
    payload = {
        "email": "admin@example.com"  # Use a simpler email that might exist
    }
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            print("Testing password reset endpoint (simple version)...")
            print(f"URL: {url}")
            print(f"Payload: {json.dumps(payload, indent=2)}")
            print("-" * 50)
            
            response = await client.post(url, json=payload, headers=headers)
            
            print(f"Status Code: {response.status_code}")
            print(f"Response Body: {response.text}")
            
            if response.status_code == 200:
                print("\n✅ SUCCESS: Password reset request accepted!")
                print("📧 Check server logs for email sending details")
            elif response.status_code == 400:
                print("\n⚠️  Bad Request - likely validation error")
                try:
                    error_data = response.json()
                    print(f"Error details: {json.dumps(error_data, indent=2)}")
                except:
                    print("Could not parse error response")
            elif response.status_code == 404:
                print("\n⚠️  Email not found in database")
            else:
                print(f"\n❌ Unexpected status: {response.status_code}")
                
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_simple_password_reset())