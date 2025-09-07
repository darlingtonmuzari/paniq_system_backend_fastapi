#!/usr/bin/env python3
"""
Debug script for subscription service issues
"""
import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.core.database import get_db
from app.services.subscription import SubscriptionService
from app.models.subscription import SubscriptionProduct
from sqlalchemy.ext.asyncio import AsyncSession


async def test_subscription_service():
    """Test the subscription service methods"""
    print("🔍 Testing Subscription Service...")
    
    try:
        # Get database session
        async for db in get_db():
            subscription_service = SubscriptionService(db)
            
            print("✅ Database connection established")
            
            # Test getting active products
            print("\n1. Testing get_active_products()...")
            try:
                products = await subscription_service.get_active_products()
                print(f"✅ Found {len(products)} active products")
                for product in products[:3]:  # Show first 3
                    print(f"   - {product.name} (ID: {product.id})")
            except Exception as e:
                print(f"❌ Error getting active products: {e}")
                import traceback
                traceback.print_exc()
            
            # Test getting a specific product (if any exist)
            if products:
                print(f"\n2. Testing get_product_by_id() with ID: {products[0].id}")
                try:
                    product = await subscription_service.get_product_by_id(str(products[0].id))
                    if product:
                        print(f"✅ Retrieved product: {product.name}")
                        print(f"   - Firm ID: {product.firm_id}")
                        print(f"   - Price: ${product.price}")
                        print(f"   - Max Users: {product.max_users}")
                        print(f"   - Active: {product.is_active}")
                    else:
                        print("❌ Product not found")
                except Exception as e:
                    print(f"❌ Error getting product by ID: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Test getting firm products
            if products:
                firm_id = str(products[0].firm_id)
                print(f"\n3. Testing get_firm_products() for firm: {firm_id}")
                try:
                    firm_products = await subscription_service.get_firm_products(firm_id)
                    print(f"✅ Found {len(firm_products)} products for firm")
                except Exception as e:
                    print(f"❌ Error getting firm products: {e}")
                    import traceback
                    traceback.print_exc()
            
            break  # Exit the async generator
            
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        import traceback
        traceback.print_exc()


async def test_database_direct():
    """Test direct database queries"""
    print("\n🔍 Testing Direct Database Queries...")
    
    try:
        from sqlalchemy import select
        
        async for db in get_db():
            # Test basic query
            print("1. Testing basic subscription_products query...")
            try:
                result = await db.execute(select(SubscriptionProduct).limit(5))
                products = result.scalars().all()
                print(f"✅ Found {len(products)} products in database")
                
                for product in products:
                    print(f"   - {product.name} (ID: {product.id}, Firm: {product.firm_id})")
                    
            except Exception as e:
                print(f"❌ Database query error: {e}")
                import traceback
                traceback.print_exc()
            
            break
            
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("🚀 Starting Subscription Service Debug")
    print("=" * 50)
    
    asyncio.run(test_database_direct())
    asyncio.run(test_subscription_service())
    
    print("\n" + "=" * 50)
    print("🎉 Debug Complete!")