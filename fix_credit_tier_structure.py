#!/usr/bin/env python3
"""
Fix credit tier structure:
- price = unit price per credit
- min_credits/max_credits = range boundaries for the tier
"""
import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings


async def fix_credit_tier_structure():
    """Fix credit tier structure with proper unit pricing and ranges"""
    
    engine = create_async_engine(settings.DATABASE_URL)
    
    async with engine.begin() as conn:
        # Clear existing data to start fresh
        await conn.execute(text("DELETE FROM credit_tiers"))
        print("✅ Cleared existing credit tiers")
        
        # Insert tiers with correct structure:
        # price = unit price per credit
        # min_credits/max_credits = tier boundaries
        tiers = [
            {
                "name": "Starter",
                "description": "Basic tier - R50.00 per credit (0% discount)",
                "min_credits": 1,
                "max_credits": 1000,
                "price": 50.00,  # Unit price per credit
                "discount_percentage": 0.00,
                "sort_order": 1
            },
            {
                "name": "Explorer", 
                "description": "Growing business tier - R47.50 per credit (5% discount)",
                "min_credits": 1001,
                "max_credits": 2500,
                "price": 47.50,  # Unit price per credit
                "discount_percentage": 5.00,
                "sort_order": 2
            },
            {
                "name": "Professional",
                "description": "Professional tier - R45.00 per credit (10% discount)",
                "min_credits": 2501,
                "max_credits": 7500,
                "price": 45.00,  # Unit price per credit
                "discount_percentage": 10.00,
                "sort_order": 3
            },
            {
                "name": "Enterprise",
                "description": "Enterprise tier - R42.50 per credit (15% discount)",
                "min_credits": 7501,
                "max_credits": 20000,
                "price": 42.50,  # Unit price per credit
                "discount_percentage": 15.00,
                "sort_order": 4
            },
            {
                "name": "Master",
                "description": "Master tier - R39.00 per credit (22% discount)",
                "min_credits": 20001,
                "max_credits": 50000,
                "price": 39.00,  # Unit price per credit
                "discount_percentage": 22.00,
                "sort_order": 5
            },
            {
                "name": "Unlimited",
                "description": "Unlimited tier - R35.00 per credit (30% discount)",
                "min_credits": 50001,
                "max_credits": 999999,  # Very high number for "unlimited"
                "price": 35.00,  # Unit price per credit
                "discount_percentage": 30.00,
                "sort_order": 6
            }
        ]
        
        # Insert each tier
        for tier in tiers:
            await conn.execute(text("""
                INSERT INTO credit_tiers 
                (name, description, min_credits, max_credits, price, discount_percentage, is_active, sort_order)
                VALUES 
                (:name, :description, :min_credits, :max_credits, :price, :discount_percentage, true, :sort_order)
            """), tier)
            
            print(f"✅ Added {tier['name']}: {tier['min_credits']:,}-{tier['max_credits']:,} credits at R{tier['price']:.2f} per credit")
        
        # Verify the structure
        result = await conn.execute(text("""
            SELECT 
                name,
                min_credits,
                max_credits, 
                price,
                discount_percentage,
                sort_order
            FROM credit_tiers 
            ORDER BY sort_order
        """))
        
        rows = result.fetchall()
        
        print(f"\n📊 Credit Tier Structure (Unit Pricing):")
        print("Tier Name      Range                    Unit Price    Discount")
        print("-" * 70)
        
        for row in rows:
            name, min_credits, max_credits, price, discount, sort_order = row
            
            if max_credits >= 999999:
                range_str = f"{min_credits:,}+"
            else:
                range_str = f"{min_credits:,} - {max_credits:,}"
            
            print(f"{name:<14} {range_str:<23} R {price:>6.2f}       {discount:>4.1f}%")
        
        print(f"\n💡 Usage Examples:")
        print("- Purchase 500 credits → Starter tier → 500 × R50.00 = R25,000")
        print("- Purchase 1,500 credits → Explorer tier → 1,500 × R47.50 = R71,250")
        print("- Purchase 10,000 credits → Enterprise tier → 10,000 × R42.50 = R425,000")
        print("- Purchase 75,000 credits → Unlimited tier → 75,000 × R35.00 = R2,625,000")
    
    await engine.dispose()


if __name__ == "__main__":
    print("🔧 Fixing Credit Tier Structure")
    print("=" * 50)
    
    try:
        asyncio.run(fix_credit_tier_structure())
        print("\n🎉 Credit tier structure fixed successfully!")
        print("\nKey changes:")
        print("✅ price = unit price per credit (not total)")
        print("✅ min_credits/max_credits = tier range boundaries")
        print("✅ Overlapping ranges removed")
        print("✅ Proper tier progression")
        
    except Exception as e:
        print(f"❌ Error fixing structure: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)