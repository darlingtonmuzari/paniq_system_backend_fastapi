#!/usr/bin/env python3
"""
Debug script to create just the credit_tiers table and test the endpoint
"""
import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.core.config import settings
from app.models.payment import CreditTier
from decimal import Decimal


async def create_credit_tiers_table():
    """Create credit_tiers table and add sample data"""
    
    # Create async engine
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=True
    )
    
    # Create the credit_tiers table manually
    async with engine.begin() as conn:
        # Drop table if exists
        await conn.execute(text("DROP TABLE IF EXISTS credit_tiers CASCADE"))
        
        # Create the table
        create_table_sql = """
        CREATE TABLE credit_tiers (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL UNIQUE,
            description TEXT,
            min_credits INTEGER NOT NULL,
            max_credits INTEGER NOT NULL,
            price DECIMAL(10, 2) NOT NULL,
            discount_percentage DECIMAL(5, 2) DEFAULT 0.00,
            is_active BOOLEAN DEFAULT TRUE NOT NULL,
            sort_order INTEGER DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
        )
        """
        await conn.execute(text(create_table_sql))
        print("✅ Credit tiers table created successfully")
    
    # Insert sample data
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # Sample credit tiers
        tiers = [
            CreditTier(
                name="Starter",
                description="Basic credit package for small firms",
                min_credits=1,
                max_credits=50,
                price=Decimal("100.00"),
                discount_percentage=Decimal("0.00"),
                sort_order=1
            ),
            CreditTier(
                name="Business",
                description="Medium credit package for growing firms",
                min_credits=51,
                max_credits=200,
                price=Decimal("350.00"),
                discount_percentage=Decimal("5.00"),
                sort_order=2
            ),
            CreditTier(
                name="Enterprise",
                description="Large credit package for enterprise firms",
                min_credits=201,
                max_credits=1000,
                price=Decimal("1500.00"),
                discount_percentage=Decimal("10.00"),
                sort_order=3
            )
        ]
        
        for tier in tiers:
            session.add(tier)
        
        await session.commit()
        print(f"✅ {len(tiers)} credit tiers added successfully")
    
    await engine.dispose()
    print("✅ Database setup completed")


if __name__ == "__main__":
    print("🚀 Setting up credit tiers table...")
    print("=" * 50)
    
    try:
        asyncio.run(create_credit_tiers_table())
        print("\n🎉 Credit tiers setup completed successfully!")
        print("\nCreated tiers:")
        print("- Starter: 1-50 credits, R100.00")
        print("- Business: 51-200 credits, R350.00 (5% discount)")
        print("- Enterprise: 201-1000 credits, R1500.00 (10% discount)")
        
    except Exception as e:
        print(f"❌ Error setting up credit tiers: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)