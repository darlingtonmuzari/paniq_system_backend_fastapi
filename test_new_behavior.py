#!/usr/bin/env python3
"""
Test the new filtering behavior for credit tiers
"""
import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, '.')

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings


async def test_new_behavior():
    """Test the new filtering behavior"""
    
    engine = create_async_engine(settings.DATABASE_URL)
    
    async with engine.begin() as conn:
        # First check database state
        result = await conn.execute(text("""
            SELECT name, is_active 
            FROM credit_tiers 
            ORDER BY sort_order, created_at
        """))
        all_db_tiers = result.fetchall()
        
        active_count = sum(1 for _, is_active in all_db_tiers if is_active)
        inactive_count = len(all_db_tiers) - active_count
        
        print("🗄️  Database State:")
        print(f"   Total tiers: {len(all_db_tiers)}")
        print(f"   Active tiers: {active_count}")
        print(f"   Inactive tiers: {inactive_count}")
        
        print(f"\n📋 All tiers in database:")
        for name, is_active in all_db_tiers:
            status = "✅ Active" if is_active else "❌ Inactive"
            print(f"   - {name:<18} {status}")
        
        print(f"\n🧪 Expected API Behavior (for admin users):")
        print(f"   GET /credit-tiers/")
        print(f"   → Should return ALL {len(all_db_tiers)} tiers (active + inactive)")
        print(f"   ")
        print(f"   GET /credit-tiers/?active_only=true")
        print(f"   → Should return {active_count} ACTIVE tiers only")
        print(f"   ")
        print(f"   GET /credit-tiers/?active_only=false")
        print(f"   → Should return {inactive_count} INACTIVE tiers only")
        
        if inactive_count == 0:
            print(f"\n⚠️  Warning: No inactive tiers found!")
            print(f"   The active_only=false test won't show any results.")
            print(f"   Consider setting one tier to inactive for testing.")
    
    await engine.dispose()


if __name__ == "__main__":
    print("🔧 Testing New Credit Tier Filtering Behavior")
    print("=" * 55)
    
    try:
        asyncio.run(test_new_behavior())
        print(f"\n✅ Database analysis complete!")
        print(f"Now test the API endpoints with an admin token:")
        print(f"")
        print(f"curl -H 'Authorization: Bearer ADMIN_TOKEN' \\")
        print(f"     'http://localhost:8000/api/v1/credit-tiers/'")
        print(f"")
        print(f"curl -H 'Authorization: Bearer ADMIN_TOKEN' \\")
        print(f"     'http://localhost:8000/api/v1/credit-tiers/?active_only=true'")
        print(f"")
        print(f"curl -H 'Authorization: Bearer ADMIN_TOKEN' \\")
        print(f"     'http://localhost:8000/api/v1/credit-tiers/?active_only=false'")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()