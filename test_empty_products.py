#!/usr/bin/env python3
"""
Test script to verify empty product list handling
"""
import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.core.database import get_db
from app.services.subscription import SubscriptionService


async def test_empty_products():
    """Test that service methods return empty lists when no products exist"""
    print("🔍 Testing Empty Product List Handling...")
    
    try:
        async for db in get_db():
            subscription_service = SubscriptionService(db)
            
            # Test get_active_products
            print("\n1. Testing get_active_products()...")
            try:
                products = await subscription_service.get_active_products()
                print(f"✅ get_active_products() returned: {type(products)} with {len(products)} items")
                if isinstance(products, list):
                    print("✅ Correctly returns a list")
                else:
                    print("❌ Should return a list")
            except Exception as e:
                print(f"❌ Error in get_active_products(): {e}")
            
            # Test get_firm_products with a non-existent firm
            print("\n2. Testing get_firm_products() with non-existent firm...")
            try:
                fake_firm_id = "00000000-0000-0000-0000-000000000000"
                products = await subscription_service.get_firm_products(fake_firm_id)
                print(f"✅ get_firm_products() returned: {type(products)} with {len(products)} items")
                if isinstance(products, list):
                    print("✅ Correctly returns a list")
                else:
                    print("❌ Should return a list")
            except Exception as e:
                print(f"❌ Error in get_firm_products(): {e}")
            
            # Test get_product_by_id with non-existent product
            print("\n3. Testing get_product_by_id() with non-existent product...")
            try:
                fake_product_id = "00000000-0000-0000-0000-000000000000"
                product = await subscription_service.get_product_by_id(fake_product_id)
                print(f"✅ get_product_by_id() returned: {product}")
                if product is None:
                    print("✅ Correctly returns None for non-existent product")
                else:
                    print("❌ Should return None for non-existent product")
            except Exception as e:
                print(f"❌ Error in get_product_by_id(): {e}")
            
            break
            
    except Exception as e:
        print(f"❌ Database connection error: {e}")


if __name__ == "__main__":
    print("🚀 Testing Empty Product List Handling")
    print("=" * 50)
    
    asyncio.run(test_empty_products())
    
    print("\n" + "=" * 50)
    print("🎉 Test Complete!")