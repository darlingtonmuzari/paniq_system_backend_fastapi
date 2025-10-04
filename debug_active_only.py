#!/usr/bin/env python3
"""
Debug the active_only parameter issue - why inactive tiers aren't being returned
"""
import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text, select
from app.core.config import settings
from app.models.payment import CreditTier


async def debug_active_only():
    """Debug the active_only parameter logic"""
    
    engine = create_async_engine(settings.DATABASE_URL)
    
    async with engine.begin() as conn:
        print("🔍 Testing database queries directly:\n")
        
        # Test 1: Get all tiers (no filter)
        print("1️⃣ Query: SELECT * FROM credit_tiers ORDER BY sort_order")
        result = await conn.execute(text("""
            SELECT name, is_active, sort_order 
            FROM credit_tiers 
            ORDER BY sort_order, created_at
        """))
        all_tiers = result.fetchall()
        
        print(f"   Total tiers found: {len(all_tiers)}")
        for name, is_active, sort_order in all_tiers:
            status = "✅ Active" if is_active else "❌ Inactive"
            print(f"   - {name:<18} {status:<12} Sort: {sort_order}")
        
        # Test 2: Get only active tiers
        print(f"\n2️⃣ Query: WHERE is_active = true")
        result = await conn.execute(text("""
            SELECT name, is_active, sort_order 
            FROM credit_tiers 
            WHERE is_active = true
            ORDER BY sort_order, created_at
        """))
        active_tiers = result.fetchall()
        
        print(f"   Active tiers found: {len(active_tiers)}")
        for name, is_active, sort_order in active_tiers:
            print(f"   - {name}")
        
        # Test 3: Get only inactive tiers 
        print(f"\n3️⃣ Query: WHERE is_active = false")
        result = await conn.execute(text("""
            SELECT name, is_active, sort_order 
            FROM credit_tiers 
            WHERE is_active = false
            ORDER BY sort_order, created_at
        """))
        inactive_tiers = result.fetchall()
        
        print(f"   Inactive tiers found: {len(inactive_tiers)}")
        for name, is_active, sort_order in inactive_tiers:
            print(f"   - {name}")
        
        # Test 4: Test the SQLAlchemy query logic
        print(f"\n4️⃣ Testing SQLAlchemy select logic:")
        
        # Simulate active_only = False (should return all)
        print("   active_only = False:")
        query = select(CreditTier)
        # No where clause should be added for active_only=False
        print(f"   Query (no filter): {query}")
        
        # Simulate active_only = True (should filter to active only)
        print("   active_only = True:")
        query_active = select(CreditTier).where(CreditTier.is_active == True)
        print(f"   Query (active only): {query_active}")
        
        print(f"\n🤔 Analysis:")
        print(f"   - Database has {len(all_tiers)} total tiers")
        print(f"   - Database has {len(active_tiers)} active tiers")
        print(f"   - Database has {len(inactive_tiers)} inactive tiers")
        print(f"   - For active_only=false, API should return {len(all_tiers)} tiers")
        print(f"   - For active_only=true, API should return {len(active_tiers)} tiers")
    
    await engine.dispose()


if __name__ == "__main__":
    print("🐛 Debugging active_only Parameter")
    print("=" * 50)
    
    try:
        asyncio.run(debug_active_only())
        
    except Exception as e:
        print(f"❌ Error during debug: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)