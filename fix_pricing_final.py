#!/usr/bin/env python3
"""
Fix the pricing values in the database to match the specification exactly
"""
import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings


async def fix_pricing():
    """Fix pricing values to match specifications"""
    
    engine = create_async_engine(settings.DATABASE_URL)
    
    async with engine.begin() as conn:
        # Update pricing to correct values
        updates = [
            ("Starter", 50000.00, 1000, 1000),  # 1,000 credits × R50.00 = R50,000
            ("Explorer", 118750.00, 2500, 2500),  # 2,500 credits × R47.50 = R118,750
            ("Professional", 337500.00, 7500, 7500),  # 7,500 credits × R45.00 = R337,500
            ("Enterprise", 850000.00, 20000, 20000),  # 20,000 credits × R42.50 = R850,000
            ("Master", 1950000.00, 50000, 50000),  # 50,000 credits × R39.00 = R1,950,000
            ("Unlimited", 3500000.00, 100000, 999999),  # 100,000+ credits at R35.00 base
        ]
        
        for name, price, min_credits, max_credits in updates:
            await conn.execute(
                text("UPDATE credit_tiers SET price = :price, min_credits = :min_credits, max_credits = :max_credits WHERE name = :name"),
                {"price": price, "min_credits": min_credits, "max_credits": max_credits, "name": name}
            )
            print(f"✅ Updated {name}: {min_credits:,}-{max_credits:,} credits, R{price:,.2f}")
        
        # Verify the updates
        result = await conn.execute(text("""
            SELECT name, min_credits, max_credits, price, 
                   CASE 
                       WHEN max_credits >= 999999 THEN 35.00
                       ELSE ROUND(price / min_credits, 2)
                   END as price_per_credit
            FROM credit_tiers 
            ORDER BY sort_order
        """))
        
        rows = result.fetchall()
        
        print(f"\n📊 Updated Credit Tiers:")
        print("Tier Name      Credits          Total Price      Price/Credit")
        print("-" * 65)
        
        for row in rows:
            name, min_credits, max_credits, price, price_per_credit = row
            if max_credits >= 999999:
                credits_str = f"{min_credits:,}+"
            else:
                credits_str = f"{min_credits:,}"
            
            print(f"{name:<14} {credits_str:<15} R {price:>10,.2f}   R {price_per_credit:>6.2f}")
    
    await engine.dispose()


if __name__ == "__main__":
    print("🔧 Fixing Credit Tiers Pricing")
    print("=" * 40)
    
    try:
        asyncio.run(fix_pricing())
        print("\n🎉 Pricing fixed successfully!")
        print("The credit tiers now have the correct total prices.")
        print("Try the GET endpoint again to see the updated values.")
        
    except Exception as e:
        print(f"❌ Error fixing pricing: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)