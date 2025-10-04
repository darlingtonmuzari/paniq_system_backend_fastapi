#!/usr/bin/env python3
"""
Update credit tiers with new pricing structure
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


async def update_credit_tiers():
    """Update credit tiers with new pricing structure"""
    
    # Create async engine
    engine = create_async_engine(settings.DATABASE_URL)
    
    async with engine.begin() as conn:
        # Clear existing data
        await conn.execute(text("DELETE FROM credit_tiers"))
        print("✅ Existing credit tiers cleared")
        
        # Insert new pricing structure
        insert_sql = """
        INSERT INTO credit_tiers (id, name, description, min_credits, max_credits, price, discount_percentage, is_active, sort_order)
        VALUES 
            (:starter_id, 'Starter', 'Basic credit package - 1,000 credits at R50.00 per credit', 1, 1000, 50000.00, 0.00, true, 1),
            (:explorer_id, 'Explorer', 'Growing business package - 2,500 credits at R47.50 per credit (5% discount)', 1001, 2500, 118750.00, 5.00, true, 2),
            (:professional_id, 'Professional', 'Professional package - 7,500 credits at R45.00 per credit (10% discount)', 2501, 7500, 337500.00, 10.00, true, 3),
            (:enterprise_id, 'Enterprise', 'Enterprise package - 20,000 credits at R42.50 per credit (15% discount)', 7501, 20000, 850000.00, 15.00, true, 4),
            (:master_id, 'Master', 'Master package - 50,000 credits at R39.00 per credit (22% discount)', 20001, 50000, 1950000.00, 22.00, true, 5),
            (:unlimited_id, 'Unlimited', 'Unlimited package - 100,000+ credits at R35.00 or less per credit (30% discount)', 50001, 999999, 3500000.00, 30.00, true, 6)
        """
        
        await conn.execute(text(insert_sql), {
            'starter_id': str(uuid.uuid4()),
            'explorer_id': str(uuid.uuid4()),
            'professional_id': str(uuid.uuid4()),
            'enterprise_id': str(uuid.uuid4()),
            'master_id': str(uuid.uuid4()),
            'unlimited_id': str(uuid.uuid4())
        })
        
        print("✅ New credit tiers pricing structure inserted")
        
        # Verify the data
        result = await conn.execute(text("""
            SELECT name, min_credits, max_credits, price, discount_percentage 
            FROM credit_tiers 
            ORDER BY sort_order
        """))
        
        rows = result.fetchall()
        print("\n📊 Updated Credit Tiers:")
        print("Tier Name       Credits Range         Total Price      Discount")
        print("-" * 65)
        
        for row in rows:
            name, min_credits, max_credits, price, discount = row
            if max_credits >= 999999:
                credits_range = f"{min_credits:,}+"
            else:
                credits_range = f"{min_credits:,} - {max_credits:,}"
            
            print(f"{name:<15} {credits_range:<20} R {price:,.2f}     {discount:.0f}%")
    
    await engine.dispose()


if __name__ == "__main__":
    print("🚀 Updating Credit Tiers with New Pricing Structure")
    print("=" * 60)
    
    try:
        asyncio.run(update_credit_tiers())
        print("\n🎉 Credit tiers updated successfully!")
        print("\nPrice per credit breakdown:")
        print("- Starter: R50.00 per credit (0% discount)")
        print("- Explorer: R47.50 per credit (5% discount, save R6,250)")
        print("- Professional: R45.00 per credit (10% discount, save R37,500)")
        print("- Enterprise: R42.50 per credit (15% discount, save R150,000)")
        print("- Master: R39.00 per credit (22% discount, save R550,000)")
        print("- Unlimited: R35.00 or less per credit (30% discount)")
        
    except Exception as e:
        print(f"❌ Error updating credit tiers: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)