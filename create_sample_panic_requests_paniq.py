#!/usr/bin/env python3
"""
Create sample panic requests for Paniq Security Solutions
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
from app.models.user import UserGroup
from app.models.emergency import PanicRequest
from sqlalchemy import text

async def create_sample_data():
    """Create sample panic requests for Paniq Security Solutions"""
    
    firm_id = "e178e9f4-01cb-4c8e-910f-9586516172d6"  # Paniq Security Solutions
    team_id = "1fe8bbb8-472f-42c0-8200-e9ee28a552aa"  # Rapid Response Team Alpha
    
    print("Creating sample panic requests for Paniq Security Solutions...")
    
    async with AsyncSessionLocal() as db:
        try:
            # Sample data for different types of requests
            sample_requests = [
                {
                    "service_type": "medical_emergency",
                    "priority": "high",
                    "status": "pending_assignment",
                    "description": "Elderly person collapsed at home",
                    "location_description": "123 Oak Street, Newlands",
                    "latitude": -26.1434,
                    "longitude": 28.0144,
                    "requester_phone": "+27823456789"
                },
                {
                    "service_type": "security_breach",
                    "priority": "critical",
                    "status": "assigned",
                    "description": "Break-in in progress, family hiding in safe room",
                    "location_description": "456 Pine Avenue, Westbury Ext",
                    "latitude": -26.1521,
                    "longitude": 28.0198,
                    "requester_phone": "+27834567890"
                },
                {
                    "service_type": "fire_emergency",
                    "priority": "critical",
                    "status": "in_progress",
                    "description": "Kitchen fire spreading to living area",
                    "location_description": "789 Maple Drive, Newlands",
                    "latitude": -26.1389,
                    "longitude": 28.0156,
                    "requester_phone": "+27845678901"
                },
                {
                    "service_type": "medical_emergency",
                    "priority": "medium",
                    "status": "completed",
                    "description": "Diabetic emergency, patient stabilized",
                    "location_description": "321 Birch Road, Westbury Ext",
                    "latitude": -26.1567,
                    "longitude": 28.0212,
                    "requester_phone": "+27856789012"
                },
                {
                    "service_type": "personal_safety",
                    "priority": "high",
                    "status": "assigned",
                    "description": "Suspicious individuals around property",
                    "location_description": "654 Cedar Street, Newlands",
                    "latitude": -26.1401,
                    "longitude": 28.0131,
                    "requester_phone": "+27867890123"
                }
            ]
            
            created_requests = []
            
            for i, request_data in enumerate(sample_requests):
                # Create a user group for each request
                group_id = str(uuid4())
                user_id = str(uuid4())
                
                # Create user group
                await db.execute(text("""
                    INSERT INTO registered_users (id, email, phone, first_name, last_name, created_at, updated_at)
                    VALUES (:user_id, :email, :phone, :first_name, :last_name, NOW(), NOW())
                """), {
                    "user_id": user_id,
                    "email": f"testuser{i+1}@example.com",
                    "phone": request_data["requester_phone"],
                    "first_name": f"TestUser{i+1}",
                    "last_name": "Sample"
                })
                
                await db.execute(text("""
                    INSERT INTO user_groups (id, user_id, name, address, location, created_at, updated_at)
                    VALUES (:group_id, :user_id, :name, :address, ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326), NOW(), NOW())
                """), {
                    "group_id": group_id,
                    "user_id": user_id,
                    "name": f"Family Group {i+1}",
                    "address": request_data["location_description"],
                    "latitude": request_data["latitude"],
                    "longitude": request_data["longitude"]
                })
                
                # Create panic request
                request_id = str(uuid4())
                created_at = datetime.utcnow() - timedelta(hours=random.randint(1, 48))
                
                await db.execute(text("""
                    INSERT INTO panic_requests (
                        id, group_id, requester_phone, service_type, priority, status,
                        description, location_description, latitude, longitude,
                        assigned_team_id, created_at, updated_at
                    ) VALUES (
                        :id, :group_id, :requester_phone, :service_type, :priority, :status,
                        :description, :location_description, :latitude, :longitude,
                        :assigned_team_id, :created_at, :updated_at
                    )
                """), {
                    "id": request_id,
                    "group_id": group_id,
                    "requester_phone": request_data["requester_phone"],
                    "service_type": request_data["service_type"],
                    "priority": request_data["priority"],
                    "status": request_data["status"],
                    "description": request_data["description"],
                    "location_description": request_data["location_description"],
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
            raise

if __name__ == "__main__":
    asyncio.run(create_sample_data())