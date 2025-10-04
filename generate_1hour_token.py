#!/usr/bin/env python3
"""
Generate a new token with 1 hour expiration and proper emergency provider permissions
"""
import sys
import os
from uuid import UUID
from datetime import timedelta

# Add the app directory to Python path
sys.path.append('/home/melcy/Programming/kiro/paniq_system')

from app.services.auth import JWTTokenService

def generate_1hour_token():
    """Generate a token with 1 hour expiration for emergency providers"""
    
    # Initialize JWT service
    jwt_service = JWTTokenService()
    
    # Use the same user ID from the provided token
    user_id = UUID("a4ce8fc2-6a6e-47e3-b76e-29d53c3a627d")
    
    # Use the firm ID from the sample data
    firm_id = UUID("804972bd-f3c0-497f-aeee-254711fd107c")
    
    # Create token with 1 hour expiration
    token_1_hour = jwt_service.create_access_token(
        user_id=user_id,
        user_type="firm_personnel",
        email="",
        permissions=[],
        firm_id=firm_id,
        role="firm_admin",  # Add role needed for emergency provider access
        expires_delta=timedelta(hours=1)  # 1 hour expiration
    )
    
    print("New 1-Hour Token Generated:")
    print("=" * 80)
    print(token_1_hour)
    print()
    
    # Verify the token contains the correct fields
    import jwt as pyjwt
    decoded = pyjwt.decode(token_1_hour, options={'verify_signature': False})
    
    print("Token Payload:")
    print(f"  user_id: {decoded['sub']}")
    print(f"  user_type: {decoded['user_type']}")
    print(f"  role: {decoded.get('role', 'NOT SET')}")
    print(f"  firm_id: {decoded.get('firm_id', 'NOT SET')}")
    print(f"  permissions: {decoded['permissions']}")
    
    # Calculate duration
    from datetime import datetime
    exp_time = datetime.fromtimestamp(decoded['exp'])
    iat_time = datetime.fromtimestamp(decoded['iat'])
    duration_hours = (exp_time - iat_time).total_seconds() / 3600
    
    print(f"  expires_in: {duration_hours:.1f} hours")
    print()
    
    return token_1_hour, firm_id

if __name__ == "__main__":
    token, firm_id = generate_1hour_token()
    
    print("Emergency Provider Test Commands:")
    print("=" * 80)
    print(f"export TOKEN='{token}'")
    print()
    print("# Test emergency providers endpoint:")
    print('curl -H "Authorization: Bearer $TOKEN" \\')
    print('     "http://localhost:8000/api/v1/emergency-providers/"')
    print()
    print(f"# Firm ID for sample data: {firm_id}")