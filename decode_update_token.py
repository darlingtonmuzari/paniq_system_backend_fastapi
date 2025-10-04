#!/usr/bin/env python3

import jwt
import json

# The token from your request
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI4NjBmZmJiMS05NjkyLTRkYTEtYjBlYy1hNDNlZDdiZDQ1ZjciLCJ1c2VyX3R5cGUiOiJmaXJtX3BlcnNvbm5lbCIsImVtYWlsIjoiZGFybGluZ3RvbkBtYW5pY2Fzb2x1dGlvbnMuY29tIiwicGVybWlzc2lvbnMiOlsicmVxdWVzdDp2aWV3IiwicmVxdWVzdDphY2NlcHQiXSwiZXhwIjoxNzU4MjgwNjExLCJpYXQiOjE3NTgyNzcwMTEsImp0aSI6IjJhODkxNzY4LWRhZTYtNGNmZS04NDdmLWRiZWI2NzU5NWRiOSIsInRva2VuX3R5cGUiOiJhY2Nlc3MiLCJmaXJtX2lkIjoiZTE3OGU5ZjQtMDFjYi00YzhlLTkxMGYtOTU4NjUxNjE3MmQ2Iiwicm9sZSI6ImZpcm1fYWRtaW4ifQ.D-_-3yppRSBRaYLxdMrZmGrTji6em68A2XeY28bx6A4"

try:
    # Decode without verification (since we don't have the secret)
    decoded = jwt.decode(token, options={"verify_signature": False})
    print("🔍 JWT Token Analysis:")
    print("=" * 40)
    print(json.dumps(decoded, indent=2))
    
    print(f"\n📋 Key Information:")
    print(f"User ID: {decoded.get('sub')}")
    print(f"Firm ID: {decoded.get('firm_id')}")
    print(f"Role: {decoded.get('role')}")
    print(f"Email: {decoded.get('email')}")
    print(f"Permissions: {decoded.get('permissions')}")
    
    # Check if user has emergency provider update permissions
    permissions = decoded.get('permissions', [])
    has_emergency_perms = any('emergency' in perm for perm in permissions)
    
    print(f"\n⚠️  Emergency Provider Permissions:")
    if has_emergency_perms:
        print("✅ User has emergency-related permissions")
    else:
        print("❌ User does NOT have emergency provider permissions")
        print("   Current permissions:", permissions)
        print("   Required: emergency_provider_crud or similar")

except Exception as e:
    print(f"Error decoding token: {e}")