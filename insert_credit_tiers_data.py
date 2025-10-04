#!/usr/bin/env python3
"""
Simple script to insert credit tiers data using raw SQL
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


async def insert_credit_tiers_data():
    """Insert sample credit tiers data using raw SQL"""
    
    # Create async engine
    engine = create_async_engine(settings.DATABASE_URL)
    
    async with engine.begin() as conn:
        # Insert sample data
        insert_sql = """
        INSERT INTO credit_tiers (id, name, description, min_credits, max_credits, price, discount_percentage, is_active, sort_order)
        VALUES 
            (:starter_id, 'Starter', 'Basic credit package for small firms', 1, 50, 100.00, 0.00, true, 1),
            (:business_id, 'Business', 'Medium credit package for growing firms', 51, 200, 350.00, 5.00, true, 2),
            (:enterprise_id, 'Enterprise', 'Large credit package for enterprise firms', 201, 1000, 1500.00, 10.00, true, 3)
        """
        
        await conn.execute(text(insert_sql), {
            'starter_id': str(uuid.uuid4()),
            'business_id': str(uuid.uuid4()),
            'enterprise_id': str(uuid.uuid4())
        })
        
        print("✅ Credit tiers data inserted successfully")
    
    await engine.dispose()


if __name__ == "__main__":
    print("🚀 Inserting credit tiers data...")
    print("=" * 50)
    
    try:
        asyncio.run(insert_credit_tiers_data())
        print("\n🎉 Credit tiers data inserted successfully!")
        print("\nCreated tiers:")
        print("- Starter: 1-50 credits, R100.00")
        print("- Business: 51-200 credits, R350.00 (5% discount)")
        print("- Enterprise: 201-1000 credits, R1500.00 (10% discount)")
        
    except Exception as e:
        print(f"❌ Error inserting credit tiers data: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)