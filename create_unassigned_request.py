#!/usr/bin/env python3
"""
Create an unassigned panic request for testing distance assignment
"""
import asyncio
import sys
import os
from datetime import datetime
from uuid import uuid4

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.core.database import AsyncSessionLocal
from sqlalchemy import text

async def create_unassigned_request():
    """Create an unassigned panic request"""
    
    print("Creating unassigned panic request for distance assignment testing...")
    
    async with AsyncSessionLocal() as db:
        try:
            # Get existing user group
            result = await db.execute(text("""
                SELECT id FROM user_groups 
                ORDER BY created_at DESC LIMIT 1
            """))
            group = result.fetchone()
            
            if not group:
                print("❌ No user groups found!")
                return
            
            group_id = group[0]
            
            # Create unassigned panic request
            request_id = str(uuid4())
            created_at = datetime.utcnow()
            
            await db.execute(text("""
                INSERT INTO panic_requests (
                    id, group_id, requester_phone, service_type, status,
                    description, address, location, assigned_team_id, created_at, updated_at
                ) VALUES (
                    :id, :group_id, :requester_phone, :service_type, :status,
                    :description, :address, ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326), 
                    NULL, :created_at, :updated_at
                )
            """), {
                "id": request_id,
                "group_id": group_id,
                "requester_phone": "+27898765432",
                "service_type": "security_breach",
                "status": "pending",
                "description": "UNASSIGNED: Urgent security assistance needed",
                "address": "999 Test Avenue, Johannesburg",
                "latitude": -26.1450,
                "longitude": 28.0160,
                "created_at": created_at,
                "updated_at": created_at
            })
            
            await db.commit()
            
            print(f"✅ Created unassigned panic request!")
            print(f"📍 Request ID: {request_id}")
            print(f"📍 Status: pending (unassigned)")
            print(f"📍 Location: -26.1450, 28.0160")
            
            return request_id
            
        except Exception as e:
            print(f"❌ Error creating request: {e}")
            await db.rollback()
            raise

if __name__ == "__main__":
    asyncio.run(create_unassigned_request())