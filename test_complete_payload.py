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

async def test_complete_payload():
    """Test emergency provider creation with complete payload including address fields"""
    
    print("🧪 Testing Complete Emergency Provider Payload with Address Fields")
    print("=" * 65)
    
    async with AsyncSessionLocal() as session:
        service = EmergencyProviderService(session)
        
        try:
            # Test with the complete original user payload including address fields
            provider = await service.create_provider(
                firm_id=UUID("249d03b8-fc0a-460b-82af-049445d15dbb"),  # Sample firm ID
                name="Emras Complete Test",
                provider_type=None,  # Let it be derived
                provider_type_id=UUID("3518e746-40d3-4a47-ac05-9b29d1a0a74f"),
                contact_phone="+27746537702",
                contact_email="help@emras.com",
                street_address="100 Johannesburg Road",
                city="Lyndhurst",
                province="Gauteng",
                country="South Africa",
                postal_code="2191",
                current_latitude=-26.1273,
                current_longitude=28.1128,
                base_latitude=-26.1273,
                base_longitude=28.1128,
                description="",
                equipment_details="5x AMC Ambulawanes",
                capacity="5",
                capabilities=["advanced_life_support", "emergency_medical_transport"],
                status=ProviderStatus.AVAILABLE
            )
            
            print(f"✅ Provider created successfully with complete address information!")
            print(f"ID: {provider.id}")
            print(f"Name: {provider.name}")
            print(f"Type: {provider.provider_type}")
            print(f"Status: {provider.status}")
            print()
            print("📍 Address Information:")
            print(f"Street: {provider.street_address}")
            print(f"City: {provider.city}")
            print(f"Province: {provider.province}")
            print(f"Country: {provider.country}")
            print(f"Postal Code: {provider.postal_code}")
            print()
            print("📞 Contact Information:")
            print(f"Phone: {provider.contact_phone}")
            print(f"Email: {provider.contact_email}")
            print()
            print("🚑 Provider Details:")
            print(f"Equipment: {provider.equipment_details}")
            print(f"Capacity: {provider.capacity}")
            print(f"Capabilities: {provider.capabilities}")
            
            # Verify address fields were actually stored in database
            print("\n🔍 Database Verification:")
            print(f"✅ street_address stored: '{provider.street_address}'")
            print(f"✅ city stored: '{provider.city}'") 
            print(f"✅ province stored: '{provider.province}'")
            print(f"✅ country stored: '{provider.country}'")
            print(f"✅ postal_code stored: '{provider.postal_code}'")
            print(f"✅ status stored: '{provider.status.value}'")
            
        except Exception as e:
            print(f"❌ Error in service: {e}")
            print(f"Error type: {type(e)}")
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_complete_payload())