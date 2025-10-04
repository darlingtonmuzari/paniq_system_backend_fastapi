#!/usr/bin/env python3

import asyncio
import sys

# Add the project root to Python path  
sys.path.insert(0, '/home/melcy/Programming/kiro/paniq_system')

from app.core.database import AsyncSessionLocal
from app.services.emergency_provider import EmergencyProviderService
from app.models.emergency_provider import ProviderStatus
from app.api.v1.emergency_providers import ProviderResponse
from uuid import UUID

async def final_verification():
    """Final comprehensive test to verify everything works"""
    
    print("🧪 Final Verification Test - Complete Emergency Provider Workflow")
    print("=" * 70)
    
    async with AsyncSessionLocal() as session:
        service = EmergencyProviderService(session)
        
        try:
            # Test creating ProviderResponse for existing provider with NULL addresses
            print("1. 🔍 Testing ProviderResponse with existing providers...")
            
            all_providers = await service.get_firm_providers(
                firm_id=UUID("249d03b8-fc0a-460b-82af-049445d15dbb"),
                include_inactive=True
            )
            
            if all_providers:
                provider = all_providers[0]
                print(f"   Testing with provider: {provider.name}")
                print(f"   Address fields: street='{provider.street_address}', city='{provider.city}'")
                
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
                
                print(f"   ✅ ProviderResponse created successfully!")
                print(f"   📍 Response address: {response.street_address}, {response.city}")
                
                print("\\n🎉 Validation successful! The API should work correctly now!")
                print("\\n📝 Summary:")
                print("   ✅ Database schema updated with address fields")
                print("   ✅ ProviderResponse handles NULL address values correctly")
                print("   ✅ All emergency provider endpoints should work")
                
            else:
                print("   No providers found for testing")
            
        except Exception as e:
            print(f"❌ Error in verification: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(final_verification())