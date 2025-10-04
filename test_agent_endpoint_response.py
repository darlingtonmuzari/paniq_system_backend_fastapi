#!/usr/bin/env python3
"""
Test agent endpoint response to see current data structure
"""
import asyncio
import uuid
from app.core.database import AsyncSessionLocal
from app.services.emergency import EmergencyService

async def test_agent_response():
    """Test agent response structure"""
    
    async with AsyncSessionLocal() as db:
        emergency_service = EmergencyService(db)
        
        try:
            # Use real agent ID from database
            real_agent_id = uuid.UUID("a4ce8fc2-6a6e-47e3-b76e-29d53c3a627d")
            
            print(f"Testing get_agent_assigned_requests with real agent_id: {real_agent_id}")
            
            requests = await emergency_service.get_agent_assigned_requests(
                agent_id=real_agent_id,
                limit=10
            )
            
            print(f"✅ Method executed successfully!")
            print(f"Returned {len(requests)} requests")
            
            if requests:
                for req in requests:
                    print(f"\n--- Request {req.id} ---")
                    print(f"Service Type: {req.service_type}")
                    print(f"Address: {req.address}")
                    print(f"Requester Phone: {req.requester_phone}")
                    
                    # Check if user relationship exists
                    if hasattr(req, 'user') and req.user:
                        print(f"User ID: {req.user.id}")
                        print(f"User Name: {req.user.first_name} {req.user.last_name}")
                        print(f"User Email: {req.user.email}")
                    else:
                        print("❌ User relationship not loaded")
                    
                    # Check if group relationship exists    
                    if hasattr(req, 'group') and req.group:
                        print(f"Group ID: {req.group.id}")
                        print(f"Group Name: {req.group.name}")
                    else:
                        print("❌ Group relationship not loaded")
                        
                    # Print all available attributes
                    print(f"Available attributes: {[attr for attr in dir(req) if not attr.startswith('_')]}")
                    break
            else:
                print("  (No requests returned)")
                
        except Exception as e:
            print(f"❌ Method failed with error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_agent_response())