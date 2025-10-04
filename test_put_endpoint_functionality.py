#!/usr/bin/env python3

import asyncio
import sys
import json

# Add the project root to Python path
sys.path.insert(0, '/home/melcy/Programming/kiro/paniq_system')

from app.core.database import AsyncSessionLocal
from app.services.emergency_provider import EmergencyProviderService
from app.models.emergency_provider import ProviderStatus
from uuid import UUID

async def test_put_endpoint_functionality():
    """Test the PUT endpoint functionality with the user's payload"""
    
    print("🧪 Testing PUT Endpoint Functionality")
    print("=" * 45)
    
    # The user's payload from the PUT request
    payload = {
        "name": "Emras",
        "provider_type_id": "3518e746-40d3-4a47-ac05-9b29d1a0a74f",
        "contact_phone": "+27746537702",
        "contact_email": "help@emras.com",
        "street_address": "100 Johannesburg Road",
        "city": "Lyndhurst",
        "province": "Gauteng",
        "country": "South Africa",
        "postal_code": "2191",
        "description": "",
        "current_latitude": -26.1273,
        "current_longitude": 28.1128,
        "base_latitude": -26.1273,
        "base_longitude": 28.1128,
        "capabilities": ["advanced_life_support", "emergency_medical_transport"],
        "status": "available",
        "coverage_radius_km": 50,
        "license_number": "",
        "equipment_details": "5x AMC Ambulawanes",
        "capacity": "5",
        "is_active": True
    }
    
    # Provider ID from the user's request
    provider_id = "afada8ce-97bf-42da-8716-b5c66d7cfa60"
    
    print(f"📋 Testing with payload:")
    print(json.dumps(payload, indent=2))
    print(f"\\nProvider ID: {provider_id}")
    
    async with AsyncSessionLocal() as session:
        service = EmergencyProviderService(session)
        
        try:
            # First, check if the provider exists
            print(f"\\n1. 🔍 Checking if provider exists...")
            existing_provider = await service.get_provider_by_id(UUID(provider_id))
            
            if not existing_provider:
                print(f"   ❌ Provider {provider_id} not found in database")
                print(f"   💡 This would return 404 in the API")
                return
            
            print(f"   ✅ Provider found: {existing_provider.name}")
            print(f"   🏢 Firm ID: {existing_provider.firm_id}")
            print(f"   📍 Current address: {existing_provider.street_address or 'None'}")
            
            # Test the update functionality
            print(f"\\n2. 🔄 Testing update with payload fields...")
            
            updated_provider = await service.update_provider(
                provider_id=UUID(provider_id),
                name=payload.get("name"),
                provider_type_id=UUID(payload["provider_type_id"]) if payload.get("provider_type_id") else None,
                contact_phone=payload.get("contact_phone"),
                contact_email=payload.get("contact_email"),
                street_address=payload.get("street_address"),
                city=payload.get("city"),
                province=payload.get("province"),
                country=payload.get("country"),
                postal_code=payload.get("postal_code"),
                current_latitude=payload.get("current_latitude"),
                current_longitude=payload.get("current_longitude"),
                base_latitude=payload.get("base_latitude"),
                base_longitude=payload.get("base_longitude"),
                coverage_radius_km=payload.get("coverage_radius_km"),
                status=ProviderStatus(payload["status"]) if payload.get("status") else None,
                description=payload.get("description"),
                equipment_details=payload.get("equipment_details"),
                capacity=payload.get("capacity"),
                capabilities=payload.get("capabilities"),
                is_active=payload.get("is_active")
            )
            
            if updated_provider:
                print(f"   ✅ Update successful!")
                print(f"   📝 Updated fields:")
                print(f"      Name: {updated_provider.name}")
                print(f"      Street: {updated_provider.street_address}")
                print(f"      City: {updated_provider.city}")
                print(f"      Province: {updated_provider.province}")
                print(f"      Country: {updated_provider.country}")
                print(f"      Status: {updated_provider.status.value}")
                print(f"      Equipment: {updated_provider.equipment_details}")
                print(f"      Capacity: {updated_provider.capacity}")
                
                print(f"\\n3. ✅ All payload fields should now be stored in database!")
                print(f"\\n🎯 Expected API Response:")
                print(f"   - Status: 200 OK")
                print(f"   - Updated provider object with all new field values")
                
            else:
                print(f"   ❌ Update failed - service returned None")
                
        except ValueError as e:
            print(f"❌ Validation error: {e}")
            print(f"💡 This would return 400 Bad Request in the API")
        except Exception as e:
            print(f"❌ Error in update: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_put_endpoint_functionality())