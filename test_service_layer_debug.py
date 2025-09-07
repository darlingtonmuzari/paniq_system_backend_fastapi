#!/usr/bin/env python3
"""
Test the subscription service layer directly to debug the 500 error
"""
import asyncio
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.services.subscription import SubscriptionService
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

async def test_service_layer():
    """Test the subscription service layer directly"""
    print("Testing subscription service layer...")
    
    # Get database session
    async for db in get_db():
        try:
            service = SubscriptionService(db)
            
            # Test with the firm ID from the JWT
            firm_id = "e178e9f4-01cb-4c8e-910f-9586516172d6"
            
            print(f"Testing get_firm_products for firm_id: {firm_id}")
            
            # Test the service method directly
            products = await service.get_firm_products(
                firm_id=firm_id,
                include_inactive=False
            )
            
            print(f"Service returned: {products}")
            print(f"Type: {type(products)}")
            print(f"Length: {len(products) if products else 'None'}")
            
            if products:
                for i, product in enumerate(products):
                    print(f"Product {i}: {product}")
                    print(f"Product type: {type(product)}")
                    print(f"Product attributes: {dir(product)}")
            else:
                print("No products returned - this should be handled gracefully")
                
        except Exception as e:
            print(f"Service layer error: {e}")
            import traceback
            traceback.print_exc()
        
        break  # Only use the first session

if __name__ == "__main__":
    asyncio.run(test_service_layer())