#!/usr/bin/env python3
"""
Debug script to decode and analyze JWT token
"""
import jwt
import json
from datetime import datetime

def decode_token(token):
    """Decode JWT token without verification to see contents"""
    try:
        # Decode without verification to see the payload
        decoded = jwt.decode(token, options={"verify_signature": False})
        
        print("=== JWT Token Contents ===")
        print(json.dumps(decoded, indent=2, default=str))
        
        print("\n=== Key Fields ===")
        print(f"User ID: {decoded.get('sub')}")
        print(f"User Type: {decoded.get('user_type')}")
        print(f"Email: {decoded.get('email')}")
        print(f"Role: {decoded.get('role')}")
        print(f"Firm ID: {decoded.get('firm_id')}")
        print(f"Permissions: {decoded.get('permissions')}")
        
        # Check expiration
        exp = decoded.get('exp')
        if exp:
            exp_date = datetime.fromtimestamp(exp)
            now = datetime.now()
            print(f"Expires: {exp_date}")
            print(f"Is Expired: {now > exp_date}")
        
        # Check if it should work for firm_admin
        user_type = decoded.get('user_type')
        role = decoded.get('role')
        
        print(f"\n=== Authorization Check ===")
        print(f"User Type: {user_type}")
        print(f"Role: {role}")
        
        is_firm_admin = (user_type == "firm_personnel" and role == "firm_admin")
        print(f"Should pass require_firm_admin: {is_firm_admin}")
        
        if not is_firm_admin:
            print("\n❌ ISSUE FOUND:")
            if user_type != "firm_personnel":
                print(f"   - User type is '{user_type}', should be 'firm_personnel'")
            if role != "firm_admin":
                print(f"   - Role is '{role}', should be 'firm_admin'")
        else:
            print("\n✅ Token should work for firm admin endpoints")
            
    except Exception as e:
        print(f"Error decoding token: {e}")

if __name__ == "__main__":
    print("JWT Token Debugger")
    print("==================")
    
    # You can paste your token here or pass it as argument
    token = input("Enter your JWT token: ").strip()
    
    if token:
        decode_token(token)
    else:
        print("No token provided")