#!/usr/bin/env python3
"""
Test with real agent ID
"""
import asyncio
import uuid
from app.core.database import AsyncSessionLocal
from app.services.emergency import EmergencyService

async def test_with_real_agent():
    """Test with a real agent ID"""
    
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
                for req in requests[:2]:  # Show first 2
                    print(f"  - Request {req.id}: {req.service_type} at {req.address}")
                    if hasattr(req, 'user') and req.user:
                        print(f"    Requester: {req.user.first_name} {req.user.last_name}")
                    else:
                        print(f"    Requester phone: {req.requester_phone}")
            else:
                print("  (No requests returned)")
                
        except Exception as e:
            print(f"❌ Method failed with error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_with_real_agent())