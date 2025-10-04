#!/usr/bin/env python3
"""
Test the API endpoint directly to see debug output
"""
import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.config import settings
from app.api.v1.credit_tiers import list_credit_tiers
from app.services.auth import UserContext


async def test_api_direct():
    """Test the API endpoint directly with mock user context"""
    
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = async_sessionmaker(engine)
    
    async with async_session() as db:
        # Create a mock admin user context
        mock_admin = UserContext(
            user_id="test-admin-id",
            user_type="admin", 
            email="test@example.com",
            permissions=[],
            role="admin"  # Make sure role is set
        )
        
        print("🧪 Testing with active_only=False (should show all tiers)")
        print("=" * 60)
        
        try:
            # Test active_only=False
            tiers = await list_credit_tiers(
                active_only=False,
                current_user=mock_admin,
                db=db
            )
            
            print(f"\n📊 Results with active_only=False:")
            print(f"   Total tiers returned: {len(tiers)}")
            
            for tier in tiers:
                status = "✅ Active" if tier.is_active else "❌ Inactive"
                print(f"   - {tier.name:<18} {status}")
            
            print(f"\n🧪 Testing with active_only=True (should show only active)")
            print("=" * 60)
            
            # Test active_only=True
            active_tiers = await list_credit_tiers(
                active_only=True,
                current_user=mock_admin,
                db=db
            )
            
            print(f"\n📊 Results with active_only=True:")
            print(f"   Total tiers returned: {len(active_tiers)}")
            
            for tier in active_tiers:
                status = "✅ Active" if tier.is_active else "❌ Inactive"
                print(f"   - {tier.name:<18} {status}")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()
    
    await engine.dispose()


if __name__ == "__main__":
    print("🔧 Testing API Endpoint Directly")
    print("=" * 40)
    
    try:
        asyncio.run(test_api_direct())
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)