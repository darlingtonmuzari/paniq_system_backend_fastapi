#!/usr/bin/env python3

import asyncio
import sys

# Add the project root to Python path
sys.path.insert(0, '/home/melcy/Programming/kiro/paniq_system')

from app.core.database import AsyncSessionLocal
from app.services.emergency_provider import EmergencyProviderService
from app.api.v1.emergency_providers import get_firm_providers
from app.services.auth import UserContext
from uuid import UUID

async def test_get_providers_endpoint():
    """Test the get_firm_providers endpoint to ensure address fields work"""
    
    print("🧪 Testing Get Firm Providers Endpoint with Address Fields")
    print("=" * 60)
    
    async with AsyncSessionLocal() as session:
        try:
            # Create a mock user context
            mock_user = UserContext(
                user_id=UUID("249d03b8-fc0a-460b-82af-049445d15dbb"),
                firm_id=UUID("249d03b8-fc0a-460b-82af-049445d15dbb"),
                role="admin",
                permissions=["read_emergency_providers"]
            )
            
            # Test the endpoint directly
            result = await get_firm_providers(
                current_user=mock_user,
                db=session
            )
            
            print(f"✅ Endpoint called successfully!")
            print(f"Total providers: {result.total_count}")
            
            if result.providers:
                provider = result.providers[0]
                print(f"\n📋 First Provider Details:")
                print(f"ID: {provider.id}")
                print(f"Name: {provider.name}")
                print(f"Type: {provider.provider_type}")
                print(f"Status: {provider.status}")
                print(f"\n📍 Address Fields:")
                print(f"Street: {provider.street_address}")
                print(f"City: {provider.city}")
                print(f"Province: {provider.province}")
                print(f"Country: {provider.country}")
                print(f"Postal Code: {provider.postal_code}")
                
                # Check if all address fields are present (even if None/empty)
                address_fields = ['street_address', 'city', 'province', 'country', 'postal_code']
                for field in address_fields:
                    value = getattr(provider, field, "MISSING")
                    if value != "MISSING":
                        print(f"✅ {field}: present (value: '{value}')")
                    else:
                        print(f"❌ {field}: MISSING from response")
            else:
                print("No providers found")
                
        except Exception as e:
            print(f"❌ Error in endpoint: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_get_providers_endpoint())