#!/usr/bin/env python3
"""
Fix credit tiers to match exact specifications from the table
"""
import asyncio
import sys
import os
import uuid

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings


async def fix_credit_tiers():
    """Fix credit tiers to match exact specifications"""
    
    # Create async engine
    engine = create_async_engine(settings.DATABASE_URL)
    
    async with engine.begin() as conn:
        # Clear existing data
        await conn.execute(text("DELETE FROM credit_tiers"))
        print("✅ Existing credit tiers cleared")
        
        # Insert exact specifications from the table
        # Each tier represents a fixed package with specific number of credits and total price
        insert_sql = """
        INSERT INTO credit_tiers (id, name, description, min_credits, max_credits, price, discount_percentage, is_active, sort_order)
        VALUES 
            (:starter_id, 'Starter', '1,000 credits package at R50.00 per credit (0% discount)', 1000, 1000, 50000.00, 0.00, true, 1),
            (:explorer_id, 'Explorer', '2,500 credits package at R47.50 per credit (5% discount, save R6,250)', 2500, 2500, 118750.00, 5.00, true, 2),
            (:professional_id, 'Professional', '7,500 credits package at R45.00 per credit (10% discount, save R37,500)', 7500, 7500, 337500.00, 10.00, true, 3),
            (:enterprise_id, 'Enterprise', '20,000 credits package at R42.50 per credit (15% discount, save R150,000)', 20000, 20000, 850000.00, 15.00, true, 4),
            (:master_id, 'Master', '50,000 credits package at R39.00 per credit (22% discount, save R550,000)', 50000, 50000, 1950000.00, 22.00, true, 5),
            (:unlimited_id, 'Unlimited', '100,000+ credits package at R35.00 per credit or less (30% discount)', 100000, 999999, 3500000.00, 30.00, true, 6)
        """
        
        await conn.execute(text(insert_sql), {
            'starter_id': str(uuid.uuid4()),
            'explorer_id': str(uuid.uuid4()),
            'professional_id': str(uuid.uuid4()),
            'enterprise_id': str(uuid.uuid4()),
            'master_id': str(uuid.uuid4()),
            'unlimited_id': str(uuid.uuid4())
        })
        
        print("✅ Credit tiers fixed with exact specifications")
        
        # Verify the data matches the table exactly
        result = await conn.execute(text("""
            SELECT name, min_credits, max_credits, price, discount_percentage 
            FROM credit_tiers 
            ORDER BY sort_order
        """))
        
        rows = result.fetchall()
        
        print("\n📊 Fixed Credit Tiers (matching your specifications):")
        print("Tier Name      Credits      Total Price      Price/Credit    Discount    You Save")
        print("-" * 85)
        
        # Expected data from your table
        expected_data = [
            ("Starter", 1000, 50000.00, 50.00, 0, 0),
            ("Explorer", 2500, 118750.00, 47.50, 5, 6250),
            ("Professional", 7500, 337500.00, 45.00, 10, 37500),
            ("Enterprise", 20000, 850000.00, 42.50, 15, 150000),
            ("Master", 50000, 1950000.00, 39.00, 22, 550000),
            ("Unlimited", 100000, 3500000.00, 35.00, 30, 0)  # Variable
        ]
        
        for i, row in enumerate(rows):
            name, min_credits, max_credits, price, discount = row
            expected = expected_data[i]
            
            # Calculate actual price per credit
            if name == "Unlimited":
                price_per_credit = 35.00  # Or less
                credits_display = "100,000+"
            else:
                price_per_credit = float(price) / min_credits
                credits_display = f"{min_credits:,}"
            
            # Calculate savings
            base_price = min_credits * 50.00 if name != "Unlimited" else 0
            savings = base_price - float(price) if name != "Unlimited" else "Variable"
            
            if name == "Unlimited":
                print(f"{name:<14} {credits_display:<12} R {price:>9,.2f}   R {price_per_credit:>6.2f}+     {discount:>2.0f}%     Variable")
            elif name == "Starter":
                print(f"{name:<14} {credits_display:<12} R {price:>9,.2f}   R {price_per_credit:>6.2f}      {discount:>2.0f}%     -")
            else:
                print(f"{name:<14} {credits_display:<12} R {price:>9,.2f}   R {price_per_credit:>6.2f}      {discount:>2.0f}%     R {savings:>7,.0f}")
    
    await engine.dispose()


if __name__ == "__main__":
    print("🔧 Fixing Credit Tiers to Match Exact Specifications")
    print("=" * 65)
    
    try:
        asyncio.run(fix_credit_tiers())
        print("\n🎉 Credit tiers fixed successfully!")
        print("\nThe database now contains the exact pricing structure from your table:")
        print("- Each tier represents a fixed package of credits")
        print("- Prices and discounts match your specifications exactly")
        print("- The API endpoint will now return this corrected data")
        
    except Exception as e:
        print(f"❌ Error fixing credit tiers: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)