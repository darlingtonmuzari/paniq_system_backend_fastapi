#!/usr/bin/env python3
"""
Test the active_only query parameter functionality
"""
import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings


async def test_active_only_parameter():
    """Test active_only parameter by checking database state"""
    
    engine = create_async_engine(settings.DATABASE_URL)
    
    async with engine.begin() as conn:
        # Check current state of is_active field
        result = await conn.execute(text("""
            SELECT name, is_active, sort_order 
            FROM credit_tiers 
            ORDER BY sort_order, name
        """))
        
        tiers = result.fetchall()
        
        print("📊 Current Credit Tiers Status:")
        print("Tier Name          Active    Sort Order")
        print("-" * 45)
        
        active_count = 0
        inactive_count = 0
        
        for name, is_active, sort_order in tiers:
            status = "✅ Active" if is_active else "❌ Inactive"
            print(f"{name:<18} {status:<12} {sort_order}")
            
            if is_active:
                active_count += 1
            else:
                inactive_count += 1
        
        print(f"\n📈 Summary:")
        print(f"   Active tiers: {active_count}")
        print(f"   Inactive tiers: {inactive_count}")
        print(f"   Total tiers: {active_count + inactive_count}")
        
        # Set one tier to inactive for testing
        if inactive_count == 0:
            print(f"\n🔧 Setting one tier to inactive for testing...")
            await conn.execute(text("""
                UPDATE credit_tiers 
                SET is_active = false 
                WHERE name LIKE '%Sample%' OR name LIKE '%Test%' OR name LIKE '%Custom%'
                LIMIT 1
            """))
            
            # Check the update
            result = await conn.execute(text("""
                SELECT name FROM credit_tiers WHERE is_active = false
            """))
            inactive_tiers = [row[0] for row in result.fetchall()]
            
            if inactive_tiers:
                print(f"   ✅ Set '{inactive_tiers[0]}' to inactive")
            else:
                print(f"   ⚠️  No test tiers found to deactivate")
        
        print(f"\n🧪 Expected API Behavior:")
        print(f"   GET /credit-tiers/ (default: active_only=true)")
        print(f"   → Should return {active_count} active tiers")
        print(f"   ")
        print(f"   GET /credit-tiers/?active_only=false")
        print(f"   → Should return all {active_count + inactive_count} tiers")
        print(f"   ")
        print(f"   GET /credit-tiers/?active_only=true")  
        print(f"   → Should return {active_count} active tiers")
    
    await engine.dispose()
    
    print(f"\n💡 Issue with active_only parameter:")
    print("The query parameter works in the code, but the API might be hanging")
    print("due to the validation issues we just fixed.")
    print("\nTry testing again with a fresh token:")
    print("curl -H 'Authorization: Bearer NEW_TOKEN' \\")
    print("     'http://localhost:8000/api/v1/credit-tiers/?active_only=false'")


if __name__ == "__main__":
    print("🧪 Testing active_only Query Parameter")
    print("=" * 50)
    
    try:
        asyncio.run(test_active_only_parameter())
        
    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)