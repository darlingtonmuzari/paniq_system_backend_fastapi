#!/usr/bin/env python3

"""
Investigate why a provider is marked as busy instead of available
"""

import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, and_
from uuid import UUID
from datetime import datetime, timedelta

# Add the project path
sys.path.append('/home/melcy/Programming/kiro/paniq_system')

from app.models.emergency_provider import EmergencyProvider, ProviderStatus
from app.models.emergency import PanicRequest

# Set up database connection
DATABASE_URL = "postgresql+asyncpg://postgres:password@localhost:5433/panic_system"

async def investigate_provider_status():
    """Investigate why the provider is busy"""
    
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    provider_id = UUID("c4e7b181-6d65-480c-af9b-166ed7ec98bd")
    
    async with async_session() as session:
        try:
            # Get the provider details
            provider_stmt = select(EmergencyProvider).where(EmergencyProvider.id == provider_id)
            provider_result = await session.execute(provider_stmt)
            provider = provider_result.scalar_one_or_none()
            
            if not provider:
                print(f"❌ Provider not found: {provider_id}")
                return
                
            print(f"🔍 Investigating Provider: {provider.name}")
            print(f"   ID: {provider.id}")
            print(f"   Status: {provider.status}")
            print(f"   Active: {provider.is_active}")
            print(f"   Created: {provider.created_at}")
            print(f"   Updated: {provider.updated_at}")
            print("=" * 60)
            
            # Check if provider is assigned to any active requests
            print("\n📋 Checking Active Request Assignments...")
            
            # Look for requests where this provider is assigned
            active_requests_stmt = select(PanicRequest).where(
                and_(
                    PanicRequest.assigned_service_provider_id == provider_id,
                    PanicRequest.status.in_(["pending", "accepted", "dispatched", "en_route", "arrived"])
                )
            )
            active_result = await session.execute(active_requests_stmt)
            active_requests = active_result.scalars().all()
            
            if active_requests:
                print(f"🚨 Found {len(active_requests)} active request(s) assigned to this provider:")
                for req in active_requests:
                    print(f"   • Request ID: {req.id}")
                    print(f"     Status: {req.status}")
                    print(f"     Created: {req.created_at}")
                    print(f"     Service Type: {req.service_type}")
                    print(f"     Accepted At: {req.accepted_at}")
                    print(f"     Completed At: {req.completed_at}")
                    print(f"     Address: {req.address}")
                    print("-" * 40)
            else:
                print("✅ No active requests found assigned to this provider")
                
            # Check for any recent completed requests
            print("\n📊 Recent Request History (last 24 hours)...")
            yesterday = datetime.utcnow() - timedelta(days=1)
            
            recent_requests_stmt = select(PanicRequest).where(
                and_(
                    PanicRequest.assigned_service_provider_id == provider_id,
                    PanicRequest.created_at >= yesterday
                )
            ).order_by(PanicRequest.created_at.desc())
            
            recent_result = await session.execute(recent_requests_stmt)
            recent_requests = recent_result.scalars().all()
            
            if recent_requests:
                print(f"📈 Found {len(recent_requests)} request(s) in the last 24 hours:")
                for req in recent_requests:
                    print(f"   • {req.created_at.strftime('%Y-%m-%d %H:%M:%S')} - {req.status} ({req.service_type})")
            else:
                print("📭 No requests in the last 24 hours")
                
            # Check if status was manually set
            print("\n💡 Possible Reasons for 'busy' Status:")
            print("   1. Provider is assigned to an active emergency request")
            print("   2. Status was manually set to 'busy' in the system")
            print("   3. Provider status wasn't updated after completing a request")
            print("   4. System automatically set status based on assignment")
            
            if not active_requests:
                print("\n🔧 Recommendation:")
                print("   Since no active requests are found, the provider status")
                print("   might need to be manually updated to 'available'")
                
        except Exception as e:
            print(f"❌ Error investigating provider: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(investigate_provider_status())