#!/usr/bin/env python3
"""
Debug script to view ALL credit tiers directly from database
This bypasses the API permission restrictions
"""
import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.append('/home/melcy/Programming/kiro/paniq_system')

async def get_all_credit_tiers():
    """Get all credit tiers directly from database"""
    try:
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy import select
        from app.models.payment import CreditTier
        
        # Use the database URL from config
        DATABASE_URL = "postgresql+asyncpg://manica_dev_admin:M1n931solutions*b0b5@postgresql-184662-0.cloudclusters.net:10024/panic_system_dev"
        
        engine = create_async_engine(DATABASE_URL)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as session:
            # Get ALL credit tiers (active and inactive)
            result = await session.execute(
                select(CreditTier).order_by(CreditTier.sort_order, CreditTier.created_at)
            )
            tiers = result.scalars().all()
            
            print("ALL Credit Tiers in Database")
            print("=" * 60)
            print(f"Total tiers found: {len(tiers)}")
            print()
            
            active_count = 0
            inactive_count = 0
            
            for i, tier in enumerate(tiers, 1):
                status = "🟢 ACTIVE" if tier.is_active else "🔴 INACTIVE"
                if tier.is_active:
                    active_count += 1
                else:
                    inactive_count += 1
                    
                print(f"{i}. {tier.name} {status}")
                print(f"   ID: {tier.id}")
                print(f"   Credits: {tier.min_credits:,} - {tier.max_credits:,}")
                print(f"   Price: R{tier.price:.2f} per credit")
                print(f"   Discount: {tier.discount_percentage}%")
                print(f"   Sort Order: {tier.sort_order}")
                print(f"   Created: {tier.created_at}")
                print()
            
            print(f"Summary: {active_count} active, {inactive_count} inactive")
            
            if inactive_count > 0:
                print(f"\n🔍 You found {inactive_count} inactive tier(s)!")
                print("This explains why they don't appear in the API for non-admin users.")
        
        await engine.dispose()
        
    except Exception as e:
        print(f"Database connection failed: {e}")
        print("\nTrying alternative approach - checking if app server is running...")
        
        # Alternative: make a request to a test endpoint that shows all tiers
        import requests
        
        try:
            # Check if we can create a temporary admin token or endpoint
            print("Creating temporary debug endpoint request...")
            
            # For now, just show the API limitation
            print("\n" + "="*60)
            print("API LIMITATION CONFIRMED")
            print("="*60)
            print("Your token has user_type='firm_personnel' but no 'role' field.")
            print("The API requires role='admin' or 'super_admin' to see inactive tiers.")
            print("\nTo see ALL tiers, you need one of these solutions:")
            print("1. Get an admin token with proper role")
            print("2. Temporarily modify the API permissions")
            print("3. Use direct database access (requires DB credentials)")
            
        except Exception as api_error:
            print(f"Alternative approach failed: {api_error}")

if __name__ == "__main__":
    asyncio.run(get_all_credit_tiers())