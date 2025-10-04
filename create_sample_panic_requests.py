#!/usr/bin/env python3

import asyncio
import sys
from datetime import datetime, timedelta
from uuid import uuid4, UUID

# Add the project root to Python path
sys.path.insert(0, '/home/melcy/Programming/kiro/paniq_system')

from app.core.database import AsyncSessionLocal
from app.models.emergency import PanicRequest
from app.models.user import UserGroup, GroupMobileNumber
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert

async def create_sample_panic_requests():
    """Create sample panic requests for testing"""
    
    print("🚨 Creating Sample Panic Requests")
    print("=" * 40)
    
    # Your firm ID from the token
    firm_id = UUID("e178e9f4-01cb-4c8e-910f-9586516172d6")
    
    async with AsyncSessionLocal() as session:
        try:
            print(f"✅ Creating panic requests for firm: {firm_id}")
            
            # Create or find sample user groups
            sample_groups = [
                {
                    "name": "Residential Complex A",
                    "address": "123 Oak Street, Sandton, Johannesburg",
                    "phone": "+27123456789",
                    "latitude": -26.1076,
                    "longitude": 28.0567
                },
                {
                    "name": "Shopping Mall Security",
                    "address": "456 Pine Avenue, Rosebank, Johannesburg", 
                    "phone": "+27987654321",
                    "latitude": -26.1448,
                    "longitude": 28.0436
                },
                {
                    "name": "Office Park B",
                    "address": "789 Cedar Road, Fourways, Johannesburg",
                    "phone": "+27555123456",
                    "latitude": -26.0123,
                    "longitude": 28.0089
                }
            ]
            
            created_groups = []
            
            for group_data in sample_groups:
                # Create a dummy user ID for the group (you may need to adjust this)
                dummy_user_id = uuid4()
                
                # Insert user group using PostGIS point
                group = UserGroup(
                    id=uuid4(),
                    user_id=dummy_user_id,
                    name=group_data["name"],
                    address=group_data["address"],
                    location=func.ST_SetSRID(func.ST_MakePoint(group_data["longitude"], group_data["latitude"]), 4326),
                    subscription_id=uuid4(),  # Dummy subscription
                    subscription_expires_at=datetime.utcnow() + timedelta(days=365)
                )
                
                session.add(group)
                await session.flush()  # Get the ID
                
                # Add mobile number for the group
                mobile = GroupMobileNumber(
                    group_id=group.id,
                    phone_number=group_data["phone"],
                    user_type="individual",
                    is_verified=True
                )
                session.add(mobile)
                
                created_groups.append({
                    "id": group.id,
                    "name": group.name,
                    "phone": group_data["phone"],
                    "lat": group_data["latitude"],
                    "lon": group_data["longitude"]
                })
                
                print(f"✅ Created group: {group.name}")
            
            await session.commit()
            
            # Now create sample panic requests
            service_types = ["security", "ambulance", "fire", "towing"]
            descriptions = [
                "Suspicious activity reported near main entrance",
                "Medical emergency - elderly resident fell",
                "Smoke detected in basement parking",
                "Vehicle breakdown blocking main road",
                "Break-in attempt reported",
                "Heart attack emergency",
                "Small fire in kitchen area",
                "Accident in parking lot"
            ]
            
            panic_requests = []
            
            for i in range(8):  # Create 8 sample requests
                group = created_groups[i % len(created_groups)]
                service_type = service_types[i % len(service_types)]
                description = descriptions[i]
                
                # Create slight location variations around the group location
                lat_offset = (i - 4) * 0.001  # Small random offset
                lon_offset = (i - 4) * 0.001
                
                request_lat = group["lat"] + lat_offset
                request_lon = group["lon"] + lon_offset
                
                panic_request = PanicRequest(
                    id=uuid4(),
                    group_id=group["id"],
                    requester_phone=group["phone"],
                    service_type=service_type,
                    location=func.ST_SetSRID(func.ST_MakePoint(request_lon, request_lat), 4326),
                    address=f"Emergency at {group['name']}, {service_type} needed",
                    description=description,
                    status="pending",
                    created_at=datetime.utcnow() - timedelta(minutes=i*15)  # Spread out creation times
                )
                
                session.add(panic_request)
                panic_requests.append({
                    "service_type": service_type,
                    "group": group["name"],
                    "description": description
                })
                
            await session.commit()
            
            print(f"\n✅ Successfully created {len(panic_requests)} sample panic requests!")
            print("\n📋 Sample Requests Created:")
            for i, req in enumerate(panic_requests, 1):
                print(f"   {i}. {req['service_type'].upper()} - {req['group']}")
                print(f"      {req['description']}")
            
            print(f"\n🔍 Test the endpoint:")
            print(f"GET http://localhost:8000/api/v1/emergency/firm/{firm_id}/pending")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error creating sample data: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(create_sample_panic_requests())