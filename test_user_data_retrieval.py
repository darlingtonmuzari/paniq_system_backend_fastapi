#!/usr/bin/env python3
"""
Test script to verify user data is properly retrieved in panic_requests API responses
"""
import asyncio
import json
from app.core.database import AsyncSessionLocal
from app.services.emergency import EmergencyService

async def test_user_data_retrieval():
    """Test that panic requests include user details"""
    
    async with AsyncSessionLocal() as db:
        emergency_service = EmergencyService(db)
        
        # Get the first few requests to test
        try:
            # Get a request by ID to test detailed retrieval
            from sqlalchemy import select, text
            
            # First get a request ID
            result = await db.execute(text("SELECT id FROM panic_requests LIMIT 1"))
            request_id = result.scalar()
            
            if request_id:
                print(f"Testing request ID: {request_id}")
                
                # Get the request with full details
                panic_request = await emergency_service.get_request_by_id(request_id)
                
                if panic_request:
                    print(f"Request found: {panic_request.id}")
                    print(f"Requester phone: {panic_request.requester_phone}")
                    print(f"Service type: {panic_request.service_type}")
                    print(f"Status: {panic_request.status}")
                    
                    # Check if user relationship is loaded
                    if hasattr(panic_request, 'user') and panic_request.user:
                        user = panic_request.user
                        print(f"User ID: {user.id}")
                        print(f"User name: {user.first_name} {user.last_name}")
                        print(f"User email: {user.email}")
                        print(f"User phone: {user.phone}")
                        print("✅ User data successfully loaded!")
                    else:
                        print("❌ User data NOT loaded")
                    
                    # Check if group relationship is loaded
                    if hasattr(panic_request, 'group') and panic_request.group:
                        group = panic_request.group
                        print(f"Group ID: {group.id}")
                        print(f"Group name: {group.name}")
                        print("✅ Group data successfully loaded!")
                    else:
                        print("❌ Group data NOT loaded")
                        
                else:
                    print("❌ Request not found")
            else:
                print("❌ No requests found in database")
                
        except Exception as e:
            print(f"❌ Error testing user data retrieval: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_user_data_retrieval())