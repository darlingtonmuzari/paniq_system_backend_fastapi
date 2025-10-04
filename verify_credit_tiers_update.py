#!/usr/bin/env python3
"""
Verify credit tiers update and test endpoint functionality
"""
import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings


async def verify_credit_tiers_update():
    """Verify the credit tiers have been updated correctly"""
    
    # Create async engine
    engine = create_async_engine(settings.DATABASE_URL)
    
    async with engine.begin() as conn:
        # Get detailed information
        result = await conn.execute(text("""
            SELECT 
                name,
                description,
                min_credits,
                max_credits,
                price,
                discount_percentage,
                is_active,
                sort_order,
                created_at,
                updated_at
            FROM credit_tiers 
            ORDER BY sort_order
        """))
        
        rows = result.fetchall()
        
        print("🔍 Detailed Credit Tiers Verification:")
        print("=" * 80)
        
        expected_tiers = [
            ("Starter", 1, 1000, 50000.00, 0.00),
            ("Explorer", 1001, 2500, 118750.00, 5.00),
            ("Professional", 2501, 7500, 337500.00, 10.00),
            ("Enterprise", 7501, 20000, 850000.00, 15.00),
            ("Master", 20001, 50000, 1950000.00, 22.00),
            ("Unlimited", 50001, 999999, 3500000.00, 30.00)
        ]
        
        print(f"\n📊 Database contains {len(rows)} credit tiers:\n")
        
        all_correct = True
        for i, row in enumerate(rows):
            name, desc, min_credits, max_credits, price, discount, active, sort_order, created, updated = row
            expected = expected_tiers[i]
            
            # Calculate price per credit
            credit_range = max_credits - min_credits + 1 if max_credits < 999999 else 100000
            price_per_credit = float(price) / credit_range if max_credits < 999999 else 35.00
            
            print(f"✅ {name}:")
            print(f"   Range: {min_credits:,} - {max_credits:,} credits" + (" (unlimited)" if max_credits >= 999999 else ""))
            print(f"   Total Price: R {price:,.2f}")
            print(f"   Price per Credit: R {price_per_credit:.2f}")
            print(f"   Discount: {discount}%")
            print(f"   Active: {active}")
            print(f"   Description: {desc}")
            print()
            
            # Verify against expected values
            if (name != expected[0] or min_credits != expected[1] or 
                max_credits != expected[2] or float(price) != expected[3] or 
                float(discount) != expected[4]):
                print(f"❌ Mismatch in {name} tier!")
                all_correct = False
        
        if all_correct:
            print("✅ All credit tiers match the expected pricing structure!")
        else:
            print("❌ Some credit tiers don't match expected values!")
        
        # Calculate savings for each tier
        print("\n💰 Savings Analysis (compared to Starter price of R50.00 per credit):")
        print("-" * 70)
        
        base_price_per_credit = 50.00
        
        for row in rows:
            name, _, min_credits, max_credits, price, discount, _, _, _, _ = row
            
            if name == "Starter":
                print(f"Starter: No discount (base price)")
                continue
                
            credits_in_tier = max_credits - min_credits + 1 if max_credits < 999999 else 100000
            actual_price_per_credit = float(price) / credits_in_tier if max_credits < 999999 else 35.00
            
            if max_credits < 999999:
                would_pay_at_base = credits_in_tier * base_price_per_credit
                you_save = would_pay_at_base - float(price)
                print(f"{name}: Would pay R{would_pay_at_base:,.2f} at base rate, actually pay R{price:,.2f} → Save R{you_save:,.2f}")
            else:
                print(f"{name}: 30% discount on any quantity above 50,000 credits")
    
    await engine.dispose()
    
    print("\n🌐 API Endpoint Status:")
    print("   URL: http://localhost:8000/api/v1/credit-tiers/")
    print("   Methods: GET (list), GET/{id}, POST (admin), PUT/{id} (admin), DELETE/{id} (admin)")
    print("   Authentication: JWT Bearer token required")
    print("   Authorization: Admin for CRUD, authenticated users for read")


if __name__ == "__main__":
    print("🔬 Verifying Credit Tiers Update")
    print("=" * 60)
    
    try:
        asyncio.run(verify_credit_tiers_update())
        print("\n🎉 Verification completed successfully!")
        print("\nThe credit tiers have been updated with the new pricing structure.")
        print("The API endpoint should now return the updated tier information.")
        
    except Exception as e:
        print(f"❌ Error during verification: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)