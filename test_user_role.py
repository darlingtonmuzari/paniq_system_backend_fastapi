#!/usr/bin/env python3
"""
Test what user role is being detected and debug the active_only logic
"""
import jwt
import sys
import os

def decode_token():
    """Decode the JWT token to see what role is being detected"""
    
    # The token provided by the user previously
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhNGNlOGZjMi02YTZlLTQ3ZTMtYjc2ZS0yOWQ1M2MzYTYyN2QiLCJ1c2VyX3R5cGUiOiJhZG1pbiIsImVtYWlsIjoiIiwicGVybWlzc2lvbnMiOltdLCJleHAiOjE3NTgxMzM2NDcsImlhdCI6MTc1ODEzMTg0NywianRpIjoiZjZiN2U0NmEtZmM1OS00YjZmLWIxNmEtODE5ZmM0ZTUzNjBhIiwidG9rZW5fdHlwZSI6ImFjY2VzcyIsInJvbGUiOiJhZG1pbiJ9.Gg_e8KQFjfXJJ3qpyaOJm-zq31lC0F2LGRxe6GZgC5c"
    
    try:
        # Decode without verification for debugging (don't do this in production!)
        payload = jwt.decode(token, options={"verify_signature": False})
        
        print("🔍 JWT Token Payload:")
        print(f"   user_type: {payload.get('user_type')}")
        print(f"   role: {payload.get('role')}")
        print(f"   permissions: {payload.get('permissions')}")
        print(f"   Full payload: {payload}")
        
        # Check which condition would be met in the API
        user_type = payload.get('user_type')
        role = payload.get('role')
        
        print(f"\n🧪 API Logic Test:")
        
        # Test the condition from the API
        is_admin = (user_type == "admin" or 
                   (user_type == "firm_personnel" and role in ["admin", "super_admin"]))
        
        print(f"   user_type == 'admin': {user_type == 'admin'}")
        print(f"   user_type == 'firm_personnel': {user_type == 'firm_personnel'}")
        print(f"   role in ['admin', 'super_admin']: {role in ['admin', 'super_admin'] if role else False}")
        print(f"   Final is_admin result: {is_admin}")
        
        # Test the query logic
        print(f"\n🔄 Query Logic Simulation:")
        
        # Test active_only=True
        print(f"   With active_only=True:")
        if not is_admin:
            print(f"     → Non-admin: WHERE is_active = true")
        elif True:  # active_only=True
            print(f"     → Admin with active_only=true: WHERE is_active = true")
        
        # Test active_only=False
        print(f"   With active_only=False:")
        if not is_admin:
            print(f"     → Non-admin: WHERE is_active = true (forced)")
        elif False:  # active_only=False
            print(f"     → This elif won't trigger because active_only=False")
        else:
            print(f"     → Admin with active_only=false: NO WHERE clause (should show all)")
        
        return is_admin
        
    except Exception as e:
        print(f"❌ Error decoding token: {str(e)}")
        return False


if __name__ == "__main__":
    print("🔑 JWT Token Role Analysis")
    print("=" * 40)
    
    is_admin = decode_token()
    
    if is_admin:
        print(f"\n✅ User is detected as admin")
        print(f"   → active_only=false should show ALL tiers (active + inactive)")
        print(f"   → active_only=true should show only active tiers")
    else:
        print(f"\n⚠️  User is NOT detected as admin")
        print(f"   → Will always show only active tiers regardless of active_only parameter")