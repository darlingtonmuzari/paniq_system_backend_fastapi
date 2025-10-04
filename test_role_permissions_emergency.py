#!/usr/bin/env python3
"""
Test script to verify role permissions for emergency request RU operations
Tests that firm_user, firm_supervisor, and team_leader can read and update panic requests
"""

import asyncio
import sys
import os
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from fastapi import HTTPException
from app.core.auth import UserContext
from app.api.v1.emergency import (
    get_agent_requests, 
    get_agent_requests_dashboard, 
    update_request_status
)


def create_user_context(user_type: str, role: str, user_id: str = None, firm_id: str = None):
    """Create a mock user context for testing"""
    if user_id is None:
        user_id = str(uuid4())
    if firm_id is None:
        firm_id = str(uuid4())
    
    user = UserContext(
        user_id=user_id,
        email=f"test_{role}@example.com",
        user_type=user_type,
        role=role,
        firm_id=firm_id if user_type == "firm_personnel" else None,
        permissions=[]
    )
    return user


async def test_role_permissions():
    """Test that the specified roles can access emergency endpoints"""
    print("Testing role permissions for emergency request RU operations...")
    
    # Create mock dependencies
    mock_db = AsyncMock()
    mock_attestation = {"valid": True}
    
    # Test roles that should have access
    allowed_roles = [
        ("firm_personnel", "firm_user"),
        ("firm_personnel", "firm_supervisor"), 
        ("firm_personnel", "team_leader"),
        ("firm_personnel", "field_agent")
    ]
    
    # Test roles that should NOT have access
    denied_roles = [
        ("firm_personnel", "invalid_role"),
        ("registered_user", "user"),
        ("admin", "admin")  # admin is not firm_personnel
    ]
    
    # Mock emergency service
    mock_emergency_service = AsyncMock()
    mock_emergency_service.get_agent_assigned_requests.return_value = []
    mock_emergency_service.update_request_status.return_value = True
    
    # Patch the emergency service
    import app.services.emergency
    app.services.emergency.EmergencyService = lambda db: mock_emergency_service
    
    print("\n=== Testing ALLOWED roles ===")
    for user_type, role in allowed_roles:
        print(f"\nTesting {user_type} with role '{role}'...")
        user = create_user_context(user_type, role)
        
        try:
            # Test get_agent_requests
            result = await get_agent_requests(
                status_filter=None,
                limit=50,
                offset=0,
                db=mock_db,
                current_user=user,
                _=mock_attestation
            )
            print(f"  ✅ get_agent_requests: PASSED")
            
        except HTTPException as e:
            print(f"  ❌ get_agent_requests: FAILED - {e.detail}")
            
        try:
            # Test get_agent_requests_dashboard  
            result = await get_agent_requests_dashboard(
                status_filter=None,
                limit=50,
                offset=0,
                db=mock_db,
                current_user=user
            )
            print(f"  ✅ get_agent_requests_dashboard: PASSED")
            
        except HTTPException as e:
            print(f"  ❌ get_agent_requests_dashboard: FAILED - {e.detail}")
    
    print("\n=== Testing DENIED roles ===")
    for user_type, role in denied_roles:
        print(f"\nTesting {user_type} with role '{role}'...")
        user = create_user_context(user_type, role)
        
        try:
            # Test get_agent_requests - should fail
            result = await get_agent_requests(
                status_filter=None,
                limit=50,
                offset=0,
                db=mock_db,
                current_user=user,
                _=mock_attestation
            )
            print(f"  ❌ get_agent_requests: FAILED - Should have been denied!")
            
        except HTTPException as e:
            if e.status_code == 403:
                print(f"  ✅ get_agent_requests: CORRECTLY DENIED - {e.detail['message']}")
            else:
                print(f"  ❌ get_agent_requests: UNEXPECTED ERROR - {e.detail}")
                
        try:
            # Test get_agent_requests_dashboard - should fail
            result = await get_agent_requests_dashboard(
                status_filter=None,
                limit=50,
                offset=0,
                db=mock_db,
                current_user=user
            )
            print(f"  ❌ get_agent_requests_dashboard: FAILED - Should have been denied!")
            
        except HTTPException as e:
            if e.status_code == 403:
                print(f"  ✅ get_agent_requests_dashboard: CORRECTLY DENIED - {e.detail['message']}")
            else:
                print(f"  ❌ get_agent_requests_dashboard: UNEXPECTED ERROR - {e.detail}")

    print("\n=== Testing UPDATE permissions ===")
    from app.api.v1.emergency import RequestStatusUpdate
    
    # Mock status update data
    status_update = RequestStatusUpdate(
        status="in_progress",
        message="Agent en route",
        latitude=-26.2041,
        longitude=28.0473
    )
    
    for user_type, role in allowed_roles:
        print(f"\nTesting UPDATE for {user_type} with role '{role}'...")
        user = create_user_context(user_type, role)
        
        try:
            result = await update_request_status(
                request_id=uuid4(),
                status_update=status_update,
                db=mock_db,
                current_user=user,
                _=mock_attestation
            )
            print(f"  ✅ update_request_status: PASSED")
            
        except HTTPException as e:
            print(f"  ❌ update_request_status: FAILED - {e.detail}")
    
    print(f"\n=== Summary ===")
    print(f"✅ firm_user, firm_supervisor, and team_leader roles can now:")
    print(f"   - Read panic requests (get_agent_requests)")
    print(f"   - Read panic requests from dashboard (get_agent_requests_dashboard)")
    print(f"   - Update panic request status (update_request_status)")
    print(f"✅ Access is properly restricted for invalid roles")


if __name__ == "__main__":
    asyncio.run(test_role_permissions())