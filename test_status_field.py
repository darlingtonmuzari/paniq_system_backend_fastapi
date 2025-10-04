#!/usr/bin/env python3

import asyncio
import sys
import traceback
from uuid import UUID

# Add the project root to Python path
sys.path.insert(0, '/home/melcy/Programming/kiro/paniq_system')

from app.core.database import AsyncSessionLocal
from app.services.emergency_provider import EmergencyProviderService
from app.models.emergency_provider import ProviderStatus

async def test_status_field():
    """Test emergency provider creation with status field"""
    
    print("🧪 Testing Emergency Provider Creation with Status Field")
    print("=" * 60)
    
    async with AsyncSessionLocal() as session:
        service = EmergencyProviderService(session)
        
        try:
            # Test the service method directly with status field
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
                capabilities=["advanced_life_support", "emergency_medical_transport"],
                status=ProviderStatus.AVAILABLE  # Test with status field
            )
            
            print(f"✅ Provider created successfully with status!")
            print(f"ID: {provider.id}")
            print(f"Name: {provider.name}")
            print(f"Type: {provider.provider_type}")
            print(f"Status: {provider.status}")
            print(f"Status value: {provider.status.value}")
            
            # Test with different status
            provider2 = await service.create_provider(
                firm_id=UUID("249d03b8-fc0a-460b-82af-049445d15dbb"),
                name="Metro Tow Service",
                provider_type=None,
                provider_type_id=UUID("3518e746-40d3-4a47-ac05-9b29d1a0a74f"),
                contact_phone="+27123456789",
                street_address="456 Main Street",
                city="Cape Town",
                province="Western Cape",
                postal_code="8001",
                current_latitude=-33.9249,
                current_longitude=18.4241,
                base_latitude=-33.9249,
                base_longitude=18.4241,
                contact_email="dispatch@metrotow.co.za",
                description="24/7 towing service",
                equipment_details="Heavy duty tow truck",
                capacity="1 vehicle",
                capabilities=["vehicle_towing", "roadside_assistance"],
                status=ProviderStatus.BUSY  # Test with different status
            )
            
            print(f"\n✅ Second provider created with different status!")
            print(f"ID: {provider2.id}")
            print(f"Name: {provider2.name}")
            print(f"Status: {provider2.status}")
            print(f"Status value: {provider2.status.value}")
            
            # Test with no status (should default to AVAILABLE)
            provider3 = await service.create_provider(
                firm_id=UUID("249d03b8-fc0a-460b-82af-049445d15dbb"),
                name="Emergency Response Unit",
                provider_type=None,
                provider_type_id=UUID("3518e746-40d3-4a47-ac05-9b29d1a0a74f"),
                contact_phone="+27987654321",
                street_address="789 Emergency Lane",
                city="Johannesburg",
                province="Gauteng",
                postal_code="2000",
                current_latitude=-26.2041,
                current_longitude=28.0473,
                base_latitude=-26.2041,
                base_longitude=28.0473,
                contact_email="dispatch@eru.co.za",
                description="Emergency response",
                equipment_details="Emergency response vehicle",
                capacity="4 personnel",
                capabilities=["emergency_response"]
                # No status provided - should default to AVAILABLE
            )
            
            print(f"\n✅ Third provider created with default status!")
            print(f"ID: {provider3.id}")
            print(f"Name: {provider3.name}")
            print(f"Status: {provider3.status}")
            print(f"Status value: {provider3.status.value}")
            
        except Exception as e:
            print(f"❌ Error in service: {e}")
            print(f"Error type: {type(e)}")
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_status_field())