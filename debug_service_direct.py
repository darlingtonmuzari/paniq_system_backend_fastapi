#!/usr/bin/env python3

import asyncio
import sys
import traceback
from uuid import UUID

# Add the project root to Python path
sys.path.insert(0, '/home/melcy/Programming/kiro/paniq_system')

from app.core.database import AsyncSessionLocal
from app.services.emergency_provider import EmergencyProviderService

async def debug_service_creation():
    """Debug emergency provider service directly"""
    
    print("🔍 Testing Emergency Provider Service Directly")
    print("=" * 50)
    
    async with AsyncSessionLocal() as session:
        service = EmergencyProviderService(session)
        
        try:
            # Test the service method directly
            provider = await service.create_provider(
                firm_id=UUID("249d03b8-fc0a-460b-82af-049445d15dbb"),  # Sample firm ID
                name="Emras",
                provider_type=None,  # Let it be derived
                provider_type_id=UUID("3518e746-40d3-4a47-ac05-9b29d1a0a74f"),
                contact_phone="+27746537702",
                street_address="100 Johannesburg Road",
                city="Lyndhurst",
                province="Gauteng",
                postal_code="2191",
                current_latitude=-26.1273,
                current_longitude=28.1128,
                base_latitude=-26.1273,
                base_longitude=28.1128,
                contact_email="help@emras.com",
                country="South Africa",
                description="",
                equipment_details="5x AMC Ambulawanes",
                capacity="5",
                capabilities=["advanced_life_support", "emergency_medical_transport"]
            )
            
            print(f"✅ Provider created successfully!")
            print(f"ID: {provider.id}")
            print(f"Name: {provider.name}")
            print(f"Type: {provider.provider_type}")
            print(f"Status: {provider.status}")
            
        except Exception as e:
            print(f"❌ Error in service: {e}")
            print(f"Error type: {type(e)}")
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_service_creation())