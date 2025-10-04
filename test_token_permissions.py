#!/usr/bin/env python3

import asyncio
import sys

# Add the project root to Python path
sys.path.insert(0, '/home/melcy/Programming/kiro/paniq_system')

from app.services.auth import auth_service
from app.core.auth import require_emergency_provider_crud, require_any_role

async def test_token_permissions():
    """Test if the user's token would pass emergency provider permissions"""
    
    print("🧪 Testing Token Permissions for Emergency Provider Updates")
    print("=" * 60)
    
    # The actual token from the user's request
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI4NjBmZmJiMS05NjkyLTRkYTEtYjBlYy1hNDNlZDdiZDQ1ZjciLCJ1c2VyX3R5cGUiOiJmaXJtX3BlcnNvbm5lbCIsImVtYWlsIjoiZGFybGluZ3RvbkBtYW5pY2Fzb2x1dGlvbnMuY29tIiwicGVybWlzc2lvbnMiOlsicmVxdWVzdDp2aWV3IiwicmVxdWVzdDphY2NlcHQiXSwiZXhwIjoxNzU4MjgwNjExLCJpYXQiOjE3NTgyNzcwMTEsImp0aSI6IjJhODkxNzY4LWRhZTYtNGNmZS04NDdmLWRiZWI2NzU5NWRiOSIsInRva2VuX3R5cGUiOiJhY2Nlc3MiLCJmaXJtX2lkIjoiZTE3OGU5ZjQtMDFjYi00YzhlLTkxMGYtOTU4NjUxNjE3MmQ2Iiwicm9sZSI6ImZpcm1fYWRtaW4ifQ.D-_-3yppRSBRaYLxdMrZmGrTji6em68A2XeY28bx6A4"
    
    try:
        # Test token validation
        print("1. 🔐 Testing token validation...")
        user_context = await auth_service.validate_token(token)
        
        print(f"   ✅ Token is valid!")
        print(f"   👤 User: {user_context.email}")
        print(f"   🏢 Firm ID: {user_context.firm_id}")
        print(f"   🎭 Role: {user_context.role}")
        print(f"   🔑 Permissions: {user_context.permissions}")
        
        # Check if role allows emergency provider access
        print(f"\\n2. 📋 Testing role-based access...")
        
        allowed_roles = ["firm_user", "firm_supervisor", "firm_admin"]
        user_role = user_context.role
        
        if user_role in allowed_roles:
            print(f"   ✅ Role '{user_role}' is in allowed roles: {allowed_roles}")
            print(f"   🎯 User should have emergency provider CRUD access")
        else:
            print(f"   ❌ Role '{user_role}' is NOT in allowed roles: {allowed_roles}")
            print(f"   🚫 User should be denied emergency provider access")
            
        # Check permissions
        print(f"\\n3. 🔍 Analyzing token permissions...")
        perms = user_context.permissions
        has_emergency_perms = any('emergency' in p for p in perms)
        
        if has_emergency_perms:
            print(f"   ✅ User has emergency-related permissions")
        else:
            print(f"   ⚠️  User does NOT have explicit emergency permissions")
            print(f"   💡 But role-based access should still work")
            
        print(f"\\n📝 Summary:")
        print(f"   Token Status: Valid ✅")
        print(f"   Role Access: {'Allowed' if user_role in allowed_roles else 'Denied'}")
        print(f"   Expected Result: {'Should work' if user_role in allowed_roles else 'Should fail'}")
            
    except Exception as e:
        print(f"❌ Token validation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_token_permissions())