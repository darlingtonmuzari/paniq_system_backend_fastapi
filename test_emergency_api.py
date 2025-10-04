#!/usr/bin/env python3
"""
Test the emergency providers API endpoint directly
"""
import asyncio
import sys
import os
import traceback

# Add the app directory to Python path
sys.path.append('/home/melcy/Programming/kiro/paniq_system')

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.emergency_provider import EmergencyProviderService
from uuid import UUID

async def test_emergency_providers_service():
    """Test the emergency provider service directly"""
    
    print("🔧 Testing Emergency Provider Service")
    print("=" * 60)
    
    try:
        # Get database session
        async for db in get_db():
            # Create service
            service = EmergencyProviderService(db)
            
            # Test firm_id from sample data
            firm_id = UUID("804972bd-f3c0-497f-aeee-254711fd107c")
            
            print(f"Testing with firm_id: {firm_id}")
            
            # Test get_firm_providers
            print("Calling get_firm_providers...")
            providers = await service.get_firm_providers(firm_id)
            
            print(f"✅ Found {len(providers)} providers:")
            for provider in providers:
                print(f"  - {provider.name} ({provider.provider_type.value})")
            
            break  # Only need first iteration from the generator
            
    except Exception as e:
        print(f"❌ Error testing service: {e}")
        print("Full traceback:")
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    result = asyncio.run(test_emergency_providers_service())
    print(f"\nService test {'✅ PASSED' if result else '❌ FAILED'}")