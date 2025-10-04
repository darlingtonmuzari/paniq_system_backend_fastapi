#!/usr/bin/env python3
"""
Test the exact SQL query being generated
"""
import asyncio
import sys
import os

sys.path.insert(0, '.')
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text, select
from app.core.config import settings
from app.models.payment import CreditTier


async def test_sql_query():
    """Test the exact SQL queries"""
    
    engine = create_async_engine(settings.DATABASE_URL)
    
    async with engine.begin() as conn:
        print("🔍 Testing exact SQL queries:")
        print("=" * 50)
        
        # Test 1: Query with no WHERE clause (should return all)
        print("1️⃣ Query with NO WHERE clause (active_only=false for admin):")
        query_all = select(CreditTier).order_by(CreditTier.sort_order, CreditTier.created_at)
        
        result = await conn.execute(query_all)
        all_tiers = result.scalars().all()
        
        print(f"   SQL: {query_all}")
        print(f"   Results: {len(all_tiers)} tiers found")
        for tier in all_tiers:
            status = "✅ Active" if tier.is_active else "❌ Inactive" 
            print(f"   - {tier.name:<18} {status}")
        
        # Test 2: Query with WHERE is_active = true
        print(f"\n2️⃣ Query WITH WHERE is_active = true (active_only=true):")
        query_active = select(CreditTier).where(CreditTier.is_active == True).order_by(CreditTier.sort_order, CreditTier.created_at)
        
        result = await conn.execute(query_active)
        active_tiers = result.scalars().all()
        
        print(f"   SQL: {query_active}")
        print(f"   Results: {len(active_tiers)} tiers found")
        for tier in active_tiers:
            status = "✅ Active" if tier.is_active else "❌ Inactive"
            print(f"   - {tier.name:<18} {status}")
        
        print(f"\n📊 Summary:")
        print(f"   - No filter query returned: {len(all_tiers)} tiers")
        print(f"   - Active-only query returned: {len(active_tiers)} tiers")
        print(f"   - Difference: {len(all_tiers) - len(active_tiers)} inactive tiers")
        
        if len(all_tiers) > len(active_tiers):
            print(f"   ✅ SQL queries work correctly - inactive tiers exist and can be queried")
        else:
            print(f"   ❌ Problem: Both queries return same number of results")
    
    await engine.dispose()


if __name__ == "__main__":
    print("🧪 Testing SQL Query Generation")
    print("=" * 40)
    
    try:
        asyncio.run(test_sql_query())
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()