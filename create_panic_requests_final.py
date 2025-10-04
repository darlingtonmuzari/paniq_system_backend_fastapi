#!/usr/bin/env python3
"""
Create sample panic requests for Paniq Security Solutions - Final version with correct schema
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from uuid import uuid4
import random

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.core.database import AsyncSessionLocal
from sqlalchemy import text

async def create_sample_panic_requests():
    """Create sample panic requests directly using existing users/groups"""
    
    firm_id = "e178e9f4-01cb-4c8e-910f-9586516172d6"  # Paniq Security Solutions
    team_id = "1fe8bbb8-472f-42c0-8200-e9ee28a552aa"  # Rapid Response Team Alpha
    
    print("Creating sample panic requests for Paniq Security Solutions...")
    
    async with AsyncSessionLocal() as db:
        try:
            # Get existing user groups we can use
            result = await db.execute(text("""
                SELECT id, name, address FROM user_groups 
                ORDER BY created_at DESC LIMIT 1
            """))
            existing_groups = result.fetchall()
            
            if existing_groups:
                group_to_use = existing_groups[0]
                print(f"Using existing group: {group_to_use[1]}")
            else:
                print("No existing user groups found, creating a minimal test setup...")
                # Create one test user and group quickly
                user_id = str(uuid4())
                group_id = str(uuid4())
                
                await db.execute(text("""
                    INSERT INTO registered_users (id, email, phone, first_name, last_name)
                    VALUES (:user_id, :email, :phone, :first_name, :last_name)
                    ON CONFLICT (email) DO NOTHING
                """), {
                    "user_id": user_id,
                    "email": "panic.test@example.com",
                    "phone": "+27821234567",
                    "first_name": "Test",
                    "last_name": "User"
                })
                
                await db.execute(text("""
                    INSERT INTO user_groups (id, user_id, name, address, location)
                    VALUES (:group_id, :user_id, :name, :address, ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326))
                """), {
                    "group_id": group_id,
                    "user_id": user_id,
                    "name": "Emergency Test Group",
                    "address": "123 Test Street, Johannesburg",
                    "latitude": -26.1434,
                    "longitude": 28.0144
                })
                
                group_to_use = (group_id, "Emergency Test Group", "123 Test Street, Johannesburg")
            
            # Sample panic requests data with correct columns only
            sample_requests = [
                {
                    "service_type": "medical_emergency",
                    "status": "pending",
                    "description": "Elderly person collapsed at home",
                    "address": "123 Oak Street, Newlands",
                    "latitude": -26.1434,
                    "longitude": 28.0144,
                    "requester_phone": "+27823456789"
                },
                {
                    "service_type": "security_breach",
                    "status": "assigned",
                    "description": "Break-in in progress, family hiding in safe room",
                    "address": "456 Pine Avenue, Westbury Ext",
                    "latitude": -26.1521,
                    "longitude": 28.0198,
                    "requester_phone": "+27834567890"
                },
                {
                    "service_type": "fire_emergency",
                    "status": "in_progress",
                    "description": "Kitchen fire spreading to living area",
                    "address": "789 Maple Drive, Newlands",
                    "latitude": -26.1389,
                    "longitude": 28.0156,
                    "requester_phone": "+27845678901"
                },
                {
                    "service_type": "medical_emergency",
                    "status": "completed",
                    "description": "Diabetic emergency, patient stabilized",
                    "address": "321 Birch Road, Westbury Ext",
                    "latitude": -26.1567,
                    "longitude": 28.0212,
                    "requester_phone": "+27856789012"
                },
                {
                    "service_type": "personal_safety",
                    "status": "assigned",
                    "description": "Suspicious individuals around property",
                    "address": "654 Cedar Street, Newlands",
                    "latitude": -26.1401,
                    "longitude": 28.0131,
                    "requester_phone": "+27867890123"
                }
            ]
            
            created_requests = []
            
            for i, request_data in enumerate(sample_requests):
                request_id = str(uuid4())
                created_at = datetime.utcnow() - timedelta(hours=random.randint(1, 48))
                
                # Insert with only the columns that exist
                await db.execute(text("""
                    INSERT INTO panic_requests (
                        id, group_id, requester_phone, service_type, status,
                        description, address, location, assigned_team_id, created_at, updated_at
                    ) VALUES (
                        :id, :group_id, :requester_phone, :service_type, :status,
                        :description, :address, ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326), 
                        :assigned_team_id, :created_at, :updated_at
                    )
                """), {
                    "id": request_id,
                    "group_id": group_to_use[0],
                    "requester_phone": request_data["requester_phone"],
                    "service_type": request_data["service_type"],
                    "status": request_data["status"],
                    "description": request_data["description"],
                    "address": request_data["address"],
                    "latitude": request_data["latitude"],
                    "longitude": request_data["longitude"],
                    "assigned_team_id": team_id,
                    "created_at": created_at,
                    "updated_at": created_at
                })
                
                created_requests.append({
                    "id": request_id,
                    "service_type": request_data["service_type"],
                    "status": request_data["status"],
                    "description": request_data["description"]
                })
                
                print(f"✅ Created {request_data['service_type']} request: {request_data['description'][:50]}...")
            
            await db.commit()
            
            print(f"\n🎉 Successfully created {len(created_requests)} sample panic requests!")
            print(f"📋 Team: Rapid Response Team Alpha (ID: {team_id})")
            print(f"🏢 Firm: Paniq Security Solutions (ID: {firm_id})")
            
            print("\n📊 Summary:")
            for req in created_requests:
                print(f"  - {req['service_type']}: {req['status']} - {req['description'][:40]}...")
                
        except Exception as e:
            print(f"❌ Error creating sample data: {e}")
            await db.rollback()
            import traceback
            traceback.print_exc()
            raise

if __name__ == "__main__":
    asyncio.run(create_sample_panic_requests())
