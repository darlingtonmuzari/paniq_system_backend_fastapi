#!/usr/bin/env python3
"""
Update existing credit tiers to correct unit pricing structure without clearing
"""
import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings


async def update_existing_tiers():
    """Update existing tiers to have correct unit pricing"""
    
    engine = create_async_engine(settings.DATABASE_URL)
    
    async with engine.begin() as conn:
        # Get current tiers
        result = await conn.execute(text("SELECT name, price FROM credit_tiers ORDER BY sort_order"))
        current_tiers = result.fetchall()
        
        print("📊 Current tiers before update:")
        for name, price in current_tiers:
            print(f"  {name}: R{price:.2f}")
        
        # Update unit prices for the main tiers only
        tier_updates = {
            "Starter": 50.00,
            "Explorer": 47.50, 
            "Professional": 45.00,
            "Enterprise": 42.50,
            "Master": 39.00,
            "Unlimited": 35.00
        }
        
        print(f"\n🔧 Updating tier prices to unit pricing...")
        
        for tier_name, unit_price in tier_updates.items():
            # Check if tier exists
            check_result = await conn.execute(
                text("SELECT COUNT(*) FROM credit_tiers WHERE name = :name"),
                {"name": tier_name}
            )
            exists = check_result.scalar() > 0
            
            if exists:
                await conn.execute(
                    text("UPDATE credit_tiers SET price = :price WHERE name = :name"),
                    {"price": unit_price, "name": tier_name}
                )
                print(f"  ✅ Updated {tier_name}: R{unit_price:.2f} per credit")
            else:
                print(f"  ⚠️  {tier_name} not found - skipping")
        
        # Show final state
        result = await conn.execute(text("""
            SELECT name, min_credits, max_credits, price, discount_percentage
            FROM credit_tiers 
            ORDER BY sort_order
        """))
        
        final_tiers = result.fetchall()
        
        print(f"\n📊 Final tier structure:")
        print("Tier Name      Range                Unit Price    Discount")
        print("-" * 65)
        
        for name, min_credits, max_credits, price, discount in final_tiers:
            if max_credits >= 999999:
                range_str = f"{min_credits:,}+"
            else:
                range_str = f"{min_credits:,} - {max_credits:,}"
            
            print(f"{name:<14} {range_str:<15} R {price:>6.2f}       {discount:>4.1f}%")
    
    await engine.dispose()


if __name__ == "__main__":
    print("🔧 Updating Existing Credit Tiers (No Clear)")
    print("=" * 55)
    
    try:
        asyncio.run(update_existing_tiers())
        print("\n🎉 Existing tiers updated successfully!")
        print("✅ Main tiers now have correct unit pricing")
        print("✅ Test/custom tiers preserved")
        
    except Exception as e:
        print(f"❌ Error updating tiers: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)