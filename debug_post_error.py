#!/usr/bin/env python3
"""
Debug the POST endpoint error
"""
import asyncio
import sys
import os
import json

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings


async def debug_post_error():
    """Debug the POST endpoint issue"""
    
    engine = create_async_engine(settings.DATABASE_URL)
    
    async with engine.begin() as conn:
        # Check if "Sample Pack" already exists
        result = await conn.execute(
            text("SELECT name FROM credit_tiers WHERE name = :name"),
            {"name": "Sample Pack"}
        )
        existing = result.scalar()
        
        if existing:
            print("❌ Issue found: 'Sample Pack' already exists in database")
            print("   This would cause a unique constraint violation")
        else:
            print("✅ 'Sample Pack' name is available")
        
        # Check all existing names
        result = await conn.execute(text("SELECT name FROM credit_tiers ORDER BY name"))
        names = [row[0] for row in result.fetchall()]
        
        print(f"\n📊 Existing tier names:")
        for i, name in enumerate(names, 1):
            print(f"  {i}. '{name}' (length: {len(name)})")
        
        # Test the validation logic manually - using actual payload
        test_data = {
            "name": "Sample Pack",
            "price": 65,
            "description": "Perfect for a tiny home",
            "min_credits": 51,
            "max_credits": 100,
            "discount_percentage": 0,
            "sort_order": 0,
            "is_active": True
        }
        
        print(f"\n🧪 Testing validation logic:")
        print(f"  min_credits: {test_data['min_credits']}")
        print(f"  max_credits: {test_data['max_credits']}")
        print(f"  min <= max? {test_data['min_credits'] <= test_data['max_credits']}")
        
        if test_data['min_credits'] > test_data['max_credits']:
            print("❌ Credits range validation would fail")
        else:
            print("✅ Credits range validation would pass")
        
        # Check if this range overlaps with existing ranges
        result = await conn.execute(text("""
            SELECT name, min_credits, max_credits 
            FROM credit_tiers 
            WHERE (min_credits <= :max_credits AND max_credits >= :min_credits)
        """), {
            "min_credits": test_data['min_credits'],
            "max_credits": test_data['max_credits']
        })
        
        overlapping = result.fetchall()
        
        if overlapping:
            print(f"\n⚠️  Range {test_data['min_credits']}-{test_data['max_credits']} overlaps with:")
            for name, min_c, max_c in overlapping:
                print(f"    {name}: {min_c}-{max_c}")
        else:
            print(f"\n✅ Range {test_data['min_credits']}-{test_data['max_credits']} doesn't overlap")
    
    await engine.dispose()
    
    print(f"\n🔍 Likely causes of 500 error:")
    print("1. Name already exists (unique constraint)")
    print("2. Missing sort_order field causing database error")
    print("3. Database constraint violation")
    print("4. Internal validation error")
    
    print(f"\n💡 Suggested fixes:")
    print("1. Add sort_order to payload: \"sort_order\": 7")
    print("2. Use a different name (avoid 'Sample ' if it exists)")
    print("3. Check for name uniqueness first")


if __name__ == "__main__":
    print("🐛 Debugging POST Credit Tier Error")
    print("=" * 45)
    
    try:
        asyncio.run(debug_post_error())
        
    except Exception as e:
        print(f"❌ Error during debug: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)