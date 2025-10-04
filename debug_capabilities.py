#!/usr/bin/env python3

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, '/home/melcy/Programming/kiro/paniq_system')

from app.core.database import AsyncSessionLocal
from app.services.capability import CapabilityService

async def debug_capabilities():
    """Debug capabilities service"""
    
    print("🔍 Debugging Capabilities Service")
    print("=" * 40)
    
    async with AsyncSessionLocal() as session:
        service = CapabilityService(session)
        
        try:
            print("Testing get_capabilities()...")
            capabilities = await service.get_capabilities(
                include_inactive=True,
                load_category=True
            )
            print(f"✅ Successfully retrieved {len(capabilities)} capabilities")
            
            # Show first few capabilities
            for i, cap in enumerate(capabilities[:3]):
                category_name = cap.capability_category.name if cap.capability_category else "No Category"
                print(f"  {i+1}. {cap.name} (Category: {category_name})")
                
        except Exception as e:
            print(f"❌ Error in get_capabilities(): {e}")
            print(f"Error type: {type(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_capabilities())