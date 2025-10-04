#!/usr/bin/env python3
"""
Generate a new admin token with proper role permissions
"""
import sys
import os
from uuid import UUID

# Add the app directory to Python path
sys.path.append('/home/melcy/Programming/kiro/paniq_system')

from app.services.auth import JWTTokenService

def generate_admin_token():
    """Generate a token with admin role for testing"""
    
    # Initialize JWT service
    jwt_service = JWTTokenService()
    
    # Create admin token with same user ID but add admin role
    user_id = UUID("a4ce8fc2-6a6e-47e3-b76e-29d53c3a627d")
    
    admin_token = jwt_service.create_access_token(
        user_id=user_id,
        user_type="firm_personnel",
        email="",
        permissions=[],
        firm_id=None,
        role="admin"  # This is the key addition!
    )
    
    print("New Admin Token Generated:")
    print("=" * 60)
    print(admin_token)
    print()
    
    # Verify the token contains the role
    import jwt as pyjwt
    decoded = pyjwt.decode(admin_token, options={'verify_signature': False})
    
    print("Token Payload:")
    print(f"  user_id: {decoded['sub']}")
    print(f"  user_type: {decoded['user_type']}")
    print(f"  role: {decoded.get('role', 'NOT SET')}")
    print(f"  permissions: {decoded['permissions']}")
    print()
    
    print("Test Commands:")
    print("=" * 60)
    print("# View all credit tiers (including inactive):")
    print(f'curl -H "Authorization: Bearer {admin_token}" http://localhost:8000/api/v1/credit-tiers/')
    print()
    print("# View only inactive tiers:")
    print(f'curl -H "Authorization: Bearer {admin_token}" "http://localhost:8000/api/v1/credit-tiers/?active_only=false"')
    print()
    print("# Update a tier:")
    print(f'curl -X PUT -H "Authorization: Bearer {admin_token}" -H "Content-Type: application/json" \\')
    print('  -d \'{"is_active": true}\' \\')
    print('  http://localhost:8000/api/v1/credit-tiers/dc1a0597-1706-488d-a091-d176678c30b5')

if __name__ == "__main__":
    generate_admin_token()