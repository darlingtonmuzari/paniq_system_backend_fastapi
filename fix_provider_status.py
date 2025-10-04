#!/usr/bin/env python3

"""
Fix the provider status by updating it to available
"""

import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, update
from uuid import UUID
from datetime import datetime

# Add the project path
sys.path.append('/home/melcy/Programming/kiro/paniq_system')

from app.models.emergency_provider import EmergencyProvider, ProviderStatus

# Set up database connection
DATABASE_URL = "postgresql+asyncpg://postgres:password@localhost:5433/panic_system"

async def fix_provider_status():
    """Update the provider status to available"""
    
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    provider_id = UUID("c4e7b181-6d65-480c-af9b-166ed7ec98bd")
    
    async with async_session() as session:
        try:
            # First, verify current status
            provider_stmt = select(EmergencyProvider).where(EmergencyProvider.id == provider_id)
            provider_result = await session.execute(provider_stmt)
            provider = provider_result.scalar_one_or_none()
            
            if not provider:
                print(f"❌ Provider not found: {provider_id}")
                return
                
            print(f"🔍 Current Provider Status:")
            print(f"   Name: {provider.name}")
            print(f"   Status: {provider.status}")
            print(f"   Updated: {provider.updated_at}")
            
            if provider.status == ProviderStatus.AVAILABLE:
                print("✅ Provider is already available!")
                return
                
            # Update the provider status
            print(f"\n🔄 Updating provider status to 'available'...")
            
            update_stmt = update(EmergencyProvider).where(
                EmergencyProvider.id == provider_id
            ).values(
                status=ProviderStatus.AVAILABLE,
                updated_at=datetime.utcnow()
            )
            
            await session.execute(update_stmt)
            await session.commit()
            
            # Verify the update
            verification_result = await session.execute(provider_stmt)
            updated_provider = verification_result.scalar_one_or_none()
            
            print(f"✅ Provider status updated successfully!")
            print(f"   New Status: {updated_provider.status}")
            print(f"   Updated At: {updated_provider.updated_at}")
            
            print(f"\n🎉 Provider '{provider.name}' is now available for assignment!")
                
        except Exception as e:
            print(f"❌ Error updating provider status: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await engine.dispose()

if __name__ == "__main__":
    print("🚑 Provider Status Fix Utility")
    print("=" * 50)
    asyncio.run(fix_provider_status())