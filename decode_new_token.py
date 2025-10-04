#!/usr/bin/env python3
"""
Decode the new JWT token 
"""
import jwt
import json
from datetime import datetime

def decode_new_token():
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhNGNlOGZjMi02YTZlLTQ3ZTMtYjc2ZS0yOWQ1M2MzYTYyN2QiLCJ1c2VyX3R5cGUiOiJmaXJtX3BlcnNvbm5lbCIsImVtYWlsIjoiYWRtaW5AcGFuaXEuY28uemEiLCJwZXJtaXNzaW9ucyI6WyJyZXF1ZXN0OnZpZXciLCJyZXF1ZXN0OmFjY2VwdCIsImFkbWluOmFsbCIsImZpcm06bWFuYWdlIiwidXNlcjptYW5hZ2UiLCJzeXN0ZW06bWFuYWdlIiwidGVhbTptYW5hZ2UiLCJwZXJzb25uZWw6bWFuYWdlIl0sImV4cCI6MTc1ODEzNTU1NywiaWF0IjoxNzU4MTMzNzU3LCJqdGkiOiIzZDI1NjE1ZC04OTRjLTQ4NjItOGVjNi0wZmZjM2VlMTExYmIiLCJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZmlybV9pZCI6IjI0OWQwM2I4LWZjMGEtNDYwYi04MmFmLTA0OTQ0NWQxNWRiYiIsInJvbGUiOiJhZG1pbiJ9.zkwka_PDTr_QwPnFvq40Izwjop9UgRMGBA0PAv7SPBE"
    
    try:
        # Decode without verification
        decoded = jwt.decode(token, options={"verify_signature": False})
        
        print("🎉 NEW JWT Token Analysis:")
        print("=" * 50)
        print(f"User ID: {decoded.get('sub')}")
        print(f"User Type: {decoded.get('user_type')}")
        print(f"Email: {decoded.get('email')}")
        print(f"Role: {decoded.get('role')}")
        print(f"Firm ID: {decoded.get('firm_id')}")
        print(f"Permissions: {len(decoded.get('permissions', []))} permissions")
        
        # Show permissions
        permissions = decoded.get('permissions', [])
        print(f"\nPermissions:")
        for perm in permissions:
            print(f"  - {perm}")
        
        # Check expiration
        exp = decoded.get('exp')
        if exp:
            exp_date = datetime.fromtimestamp(exp)
            print(f"\nExpires: {exp_date}")
            if datetime.now() > exp_date:
                print("❌ Token is EXPIRED")
            else:
                print("✅ Token is still valid")
        
        # Authorization check
        print(f"\n🔒 Authorization Status:")
        user_type = decoded.get('user_type')
        role = decoded.get('role')
        
        print(f"✅ User type: {user_type}")
        print(f"✅ Role: {role}")
        
        # Check if this meets credit tiers requirements
        has_admin_access = (
            user_type == "admin" or 
            (user_type == "firm_personnel" and role in ["admin", "super_admin"])
        )
        
        if has_admin_access:
            print(f"🎯 AUTHORIZATION STATUS: ✅ FULL ACCESS")
            print(f"   You can now:")
            print(f"   ✅ GET /api/v1/credit-tiers/ (list tiers)")
            print(f"   ✅ GET /api/v1/credit-tiers/{{id}} (get specific tier)")
            print(f"   ✅ POST /api/v1/credit-tiers/ (create tier)")
            print(f"   ✅ PUT /api/v1/credit-tiers/{{id}} (update tier)")
            print(f"   ✅ DELETE /api/v1/credit-tiers/{{id}} (delete tier)")
        else:
            print(f"❌ Still no admin access")
            
    except Exception as e:
        print(f"Error decoding token: {e}")

if __name__ == "__main__":
    decode_new_token()