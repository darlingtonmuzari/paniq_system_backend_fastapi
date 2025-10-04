#!/usr/bin/env python3
"""
Generate a fresh token for testing
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta
import jwt

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.core.database import get_db
from app.core.config import settings
from sqlalchemy import select, text

async def generate_token():
    """Generate a fresh token for the existing user"""
    print("Generating fresh token...")
    
    async for db in get_db():
        try:
            # Get the user details
            result = await db.execute(text("""
                SELECT fp.id, fp.first_name, fp.last_name, fp.email, fp.role, fp.firm_id,
                       sf.name as firm_name
                FROM firm_personnel fp
                JOIN security_firms sf ON fp.firm_id = sf.id
                WHERE fp.email = 'test.manicasolutions@gmail.com'
                AND fp.role = 'firm_supervisor'
            """))
            
            user = result.fetchone()
            
            if not user:
                print("User not found!")
                return
            
            print(f"Found user: {user.first_name} {user.last_name}")
            print(f"Email: {user.email}")
            print(f"Firm: {user.firm_name} (ID: {user.firm_id})")
            
            # Create JWT payload
            now = datetime.utcnow()
            payload = {
                "sub": str(user.id),
                "user_type": "firm_personnel",
                "email": user.email,
                "permissions": ["request:view", "request:accept"],
                "exp": int((now + timedelta(hours=24)).timestamp()),  # 24 hours from now
                "iat": int(now.timestamp()),
                "jti": "test-token-" + str(user.id)[:8],
                "token_type": "access",
                "firm_id": str(user.firm_id),
                "role": user.role
            }
            
            # Generate token using the JWT secret key
            try:
                # Use the JWT secret key from settings
                secret_key = settings.JWT_SECRET_KEY
                token = jwt.encode(payload, secret_key, algorithm="HS256")
                
                print(f"\n🎉 Fresh token generated!")
                print(f"Token: {token}")
                print(f"Expires: {datetime.fromtimestamp(payload['exp'])}")
                
                # Test the token immediately
                print(f"\n🧪 Testing the token...")
                import requests
                
                url = "http://localhost:8000/api/v1/subscription-products/my-products"
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
                
                response = requests.get(url, headers=headers, params={"include_inactive": "false"})
                print(f"Test Status Code: {response.status_code}")
                print(f"Test Response: {response.text}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Success! Found {len(data.get('products', []))} products")
                else:
                    print(f"❌ Test failed with status {response.status_code}")
                
            except Exception as e:
                print(f"Error generating token: {e}")
                print("You may need to check your SECRET_KEY in settings")
                
        except Exception as e:
            print(f"Database error: {e}")
            import traceback
            traceback.print_exc()
        
        break

if __name__ == "__main__":
    asyncio.run(generate_token())