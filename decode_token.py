#!/usr/bin/env python3
"""
Decode JWT token to check user details and role
"""
import jwt
import json
from datetime import datetime

def decode_token():
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhNGNlOGZjMi02YTZlLTQ3ZTMtYjc2ZS0yOWQ1M2MzYTYyN2QiLCJ1c2VyX3R5cGUiOiJmaXJtX3BlcnNvbm5lbCIsImVtYWlsIjoiIiwicGVybWlzc2lvbnMiOltdLCJleHAiOjE3NTgxMzM2NDcsImlhdCI6MTc1ODEzMTg0NywianRpIjoiZjZiN2U0NmEtZmM1OS00YjZmLWIxNmEtODE5ZmM0ZTUzNjBhIiwidG9rZW5fdHlwZSI6ImFjY2VzcyJ9.9dIwO_yW6b2VL5KpUlso3xtkwvGFU3US73_MyzHKnt4"
    
    try:
        # Decode without verification first to see the payload
        decoded = jwt.decode(token, options={"verify_signature": False})
        
        print("🔍 JWT Token Analysis:")
        print("=" * 50)
        print(f"User ID: {decoded.get('sub')}")
        print(f"User Type: {decoded.get('user_type')}")
        print(f"Email: {decoded.get('email', 'Not provided')}")
        print(f"Permissions: {decoded.get('permissions', [])}")
        print(f"Role: {decoded.get('role', 'Not specified in token')}")
        print(f"Firm ID: {decoded.get('firm_id', 'Not specified in token')}")
        
        # Check expiration
        exp = decoded.get('exp')
        if exp:
            exp_date = datetime.fromtimestamp(exp)
            print(f"Expires: {exp_date}")
            if datetime.now() > exp_date:
                print("❌ Token is EXPIRED")
            else:
                print("✅ Token is still valid")
        
        print(f"\nFull token payload:")
        print(json.dumps(decoded, indent=2))
        
        # Analyze authorization issue
        print(f"\n🔒 Authorization Analysis:")
        user_type = decoded.get('user_type')
        role = decoded.get('role')
        
        print(f"Current user type: {user_type}")
        print(f"Current role: {role}")
        
        print(f"\n📋 Required for credit tiers CRUD:")
        print(f"- Admin user type: user_type == 'admin' OR")
        print(f"- Firm personnel with admin role: user_type == 'firm_personnel' AND role in ['admin', 'super_admin']")
        
        print(f"\n🎯 Your access level:")
        if user_type == "admin":
            print("✅ You have admin user type - should have access")
        elif user_type == "firm_personnel":
            if role in ["admin", "super_admin"]:
                print("✅ You have firm personnel with admin role - should have access")
            else:
                print(f"❌ You have firm personnel but role '{role}' is not admin - ACCESS DENIED")
                print("❗ You need 'admin' or 'super_admin' role for CRUD operations")
        else:
            print(f"❌ User type '{user_type}' doesn't have admin access")
            
    except Exception as e:
        print(f"Error decoding token: {e}")

if __name__ == "__main__":
    decode_token()