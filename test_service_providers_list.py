#!/usr/bin/env python3

import asyncio
import sys

# Add the project root to Python path
sys.path.insert(0, '/home/melcy/Programming/kiro/paniq_system')

from app.core.database import AsyncSessionLocal
from app.services.emergency_provider import EmergencyProviderService
from uuid import UUID

async def test_service_providers_list():
    """Test the service layer to see if providers have address fields"""
    
    print("🧪 Testing Service Layer - Get Firm Providers with Address Fields")
    print("=" * 65)
    
    async with AsyncSessionLocal() as session:
        try:
            service = EmergencyProviderService(session)
            
            # Get providers for a firm
            providers = await service.get_firm_providers(
                firm_id=UUID("249d03b8-fc0a-460b-82af-049445d15dbb"),
                include_inactive=True
            )
            
            print(f"✅ Service called successfully!")
            print(f"Total providers: {len(providers)}")
            
            if providers:
                provider = providers[0]
                print(f"\n📋 First Provider Details:")
                print(f"ID: {provider.id}")
                print(f"Name: {provider.name}")
                print(f"Type: {provider.provider_type}")
                print(f"Status: {provider.status}")
                
                print(f"\n📍 Address Fields from Database:")
                print(f"Street: '{provider.street_address}'")
                print(f"City: '{provider.city}'")
                print(f"Province: '{provider.province}'")
                print(f"Country: '{provider.country}'")
                print(f"Postal Code: '{provider.postal_code}'")
                
                # Check if attributes exist
                address_fields = ['street_address', 'city', 'province', 'country', 'postal_code']
                for field in address_fields:
                    if hasattr(provider, field):
                        value = getattr(provider, field)
                        if value is None:
                            print(f"✅ {field}: attribute exists but is NULL")
                        elif value == "":
                            print(f"✅ {field}: attribute exists but is empty string")
                        else:
                            print(f"✅ {field}: has value '{value}'")
                    else:
                        print(f"❌ {field}: attribute does not exist")
                        
                # Test creating a ProviderResponse object manually
                print(f"\n🔧 Testing ProviderResponse Creation:")
                from app.api.v1.emergency_providers import ProviderResponse
                
                try:
                    response = ProviderResponse(
                        id=str(provider.id),
                        firm_id=str(provider.firm_id),
                        name=provider.name,
                        provider_type=provider.provider_type.value,
                        license_number=provider.license_number,
                        contact_phone=provider.contact_phone,
                        contact_email=provider.contact_email,
                        street_address=provider.street_address,
                        city=provider.city,
                        province=provider.province,
                        country=provider.country,
                        postal_code=provider.postal_code,
                        current_latitude=provider.current_latitude,
                        current_longitude=provider.current_longitude,
                        base_latitude=provider.base_latitude,
                        base_longitude=provider.base_longitude,
                        coverage_radius_km=provider.coverage_radius_km,
                        status=provider.status.value,
                        is_active=provider.is_active,
                        description=provider.description,
                        equipment_details=provider.equipment_details,
                        capacity=provider.capacity,
                        capabilities=provider.capabilities,
                        created_at=provider.created_at.isoformat(),
                        updated_at=provider.updated_at.isoformat(),
                        last_location_update=provider.last_location_update.isoformat()
                    )
                    print(f"✅ ProviderResponse created successfully!")
                    print(f"Response street: '{response.street_address}'")
                    print(f"Response city: '{response.city}'")
                    
                except Exception as response_error:
                    print(f"❌ ProviderResponse creation failed: {response_error}")
                    import traceback
                    traceback.print_exc()
            else:
                print("No providers found")
                
        except Exception as e:
            print(f"❌ Error in service: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_service_providers_list())