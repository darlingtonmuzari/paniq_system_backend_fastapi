#!/usr/bin/env python3
"""
Direct test of EmergencyService.get_agent_assigned_requests method
"""
import asyncio
import uuid
from app.core.database import AsyncSessionLocal
from app.services.emergency import EmergencyService

async def test_emergency_service_directly():
    """Test the get_agent_assigned_requests method directly"""
    
    async with AsyncSessionLocal() as db:
        emergency_service = EmergencyService(db)
        
        try:
            # Test with a fake agent ID to see if the method works without crashes
            fake_agent_id = uuid.uuid4()
            
            print(f"Testing get_agent_assigned_requests with agent_id: {fake_agent_id}")
            
            requests = await emergency_service.get_agent_assigned_requests(
                agent_id=fake_agent_id,
                limit=10
            )
            
            print(f"✅ Method executed successfully!")
            print(f"Returned {len(requests)} requests")
            
            if requests:
                for req in requests[:2]:  # Show first 2
                    print(f"  - Request {req.id}: {req.service_type} at {req.address}")
            else:
                print("  (No requests returned - expected for fake agent ID)")
                
        except Exception as e:
            print(f"❌ Method failed with error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_emergency_service_directly())