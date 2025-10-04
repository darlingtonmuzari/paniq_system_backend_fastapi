#!/usr/bin/env python3
"""
Debug the agent requests endpoint to find the actual issue
"""

import asyncio
import sys
import os
from uuid import UUID

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.core.database import AsyncSessionLocal
from app.models.security_firm import FirmPersonnel
from app.models.emergency import PanicRequest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

async def debug_agent_lookup():
    """Debug the agent lookup issue"""
    
    # User ID from the token
    user_id = "f8a30919-5ed5-46af-95d6-3afa4da634da"
    
    print(f"Debugging agent lookup for user_id: {user_id}")
    
    async with AsyncSessionLocal() as db:
        # Check if the user exists in firm_personnel
        result = await db.execute(
            select(FirmPersonnel).where(FirmPersonnel.id == UUID(user_id))
        )
        agent = result.scalar_one_or_none()
        
        if agent:
            print(f"✅ Found agent: {agent.first_name} {agent.last_name}")
            print(f"   Email: {agent.email}")
            print(f"   Role: {agent.role}")
            print(f"   Team ID: {agent.team_id}")
            print(f"   Firm ID: {agent.firm_id}")
            print(f"   Is Active: {agent.is_active}")
            
            if agent.team_id:
                # Check for requests assigned to this team
                result = await db.execute(
                    select(PanicRequest).options(
                        selectinload(PanicRequest.group),
                        selectinload(PanicRequest.status_updates)
                    ).where(PanicRequest.assigned_team_id == agent.team_id)
                )
                requests = result.scalars().all()
                print(f"✅ Found {len(requests)} requests assigned to team {agent.team_id}")
                
                for req in requests[:3]:  # Show first 3 requests
                    print(f"   - Request {req.id}: {req.service_type} - Status: {req.status}")
                    
            else:
                print("❌ Agent has no team assigned")
                
        else:
            print("❌ Agent not found in firm_personnel table")
            
            # Let's see if this ID exists anywhere
            print("\nChecking all personnel records...")
            result = await db.execute(select(FirmPersonnel))
            all_personnel = result.scalars().all()
            print(f"Total personnel records: {len(all_personnel)}")
            
            for p in all_personnel[:5]:  # Show first 5
                print(f"   - {p.id}: {p.email} ({p.role})")


if __name__ == "__main__":
    asyncio.run(debug_agent_lookup())