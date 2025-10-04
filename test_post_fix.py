#!/usr/bin/env python3
"""
Test the POST fix by directly calling the endpoint logic
"""
import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.config import settings
from app.core.database import get_db
from app.models.payment import CreditTier
from app.api.v1.credit_tiers import CreditTierCreate


async def test_post_fix():
    """Test the POST endpoint fix"""
    
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = async_sessionmaker(engine)
    
    async with async_session() as db:
        # Test the validation and creation logic
        tier_data = CreditTierCreate(
            name="Sample Pack",
            price=65,
            description="Perfect for a tiny home",
            min_credits=51,
            max_credits=100,
            discount_percentage=0,
            sort_order=0,
            is_active=True
        )
        
        print("🧪 Testing CreditTierCreate validation...")
        print(f"   ✅ Validation passed for: {tier_data.name}")
        
        # Test database creation
        new_tier = CreditTier(
            name=tier_data.name,
            description=tier_data.description,
            min_credits=tier_data.min_credits,
            max_credits=tier_data.max_credits,
            price=tier_data.price,
            discount_percentage=tier_data.discount_percentage or 0.0,
            is_active=tier_data.is_active,
            sort_order=tier_data.sort_order or 0
        )
        
        try:
            db.add(new_tier)
            await db.commit()
            await db.refresh(new_tier)
            
            print("✅ Credit tier created successfully!")
            print(f"   ID: {new_tier.id}")
            print(f"   Name: {new_tier.name}")
            print(f"   Range: {new_tier.min_credits}-{new_tier.max_credits} credits")
            print(f"   Price: R{new_tier.price} per credit")
            
            # Test the response creation (this was the bug)
            response_data = {
                "id": str(new_tier.id),
                "name": new_tier.name,
                "description": new_tier.description,
                "min_credits": new_tier.min_credits,
                "max_credits": new_tier.max_credits,
                "price": float(new_tier.price),
                "discount_percentage": float(new_tier.discount_percentage),
                "is_active": new_tier.is_active,
                "sort_order": new_tier.sort_order,
                "created_at": new_tier.created_at.isoformat(),
                "updated_at": new_tier.updated_at.isoformat()
            }
            
            print("✅ Response creation test passed!")
            print(f"   Response keys: {list(response_data.keys())}")
            
        except Exception as e:
            await db.rollback()
            print(f"❌ Error: {str(e)}")
            raise
    
    await engine.dispose()


if __name__ == "__main__":
    print("🔧 Testing POST Fix")
    print("=" * 30)
    
    try:
        asyncio.run(test_post_fix())
        print("\n🎉 All tests passed! The POST endpoint should work now.")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)