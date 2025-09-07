#!/usr/bin/env python3
"""
Test API endpoints for empty product list handling
"""
import asyncio
import sys
import os
from unittest.mock import AsyncMock, MagicMock

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.api.v1.subscription_products import get_active_products, get_my_products
from app.services.subscription import SubscriptionService
from app.core.auth import UserContext
from uuid import UUID


async def test_api_empty_responses():
    """Test API endpoints with empty product lists"""
    print("🔍 Testing API Empty Response Handling...")
    
    # Mock database session
    mock_db = AsyncMock()
    
    # Mock subscription service that returns empty lists
    mock_service = AsyncMock(spec=SubscriptionService)
    mock_service.get_active_products.return_value = []
    mock_service.get_firm_products.return_value = []
    
    # Mock current user for firm admin endpoints
    mock_user = MagicMock(spec=UserContext)
    mock_user.firm_id = UUID("12345678-1234-1234-1234-123456789012")
    
    print("\n1. Testing get_active_products() with empty list...")
    try:
        # Mock the SubscriptionService constructor
        original_service_init = SubscriptionService.__init__
        SubscriptionService.__init__ = lambda self, db: None
        SubscriptionService.get_active_products = AsyncMock(return_value=[])
        
        response = await get_active_products(current_user=mock_user, db=mock_db)
        
        print(f"✅ Response type: {type(response)}")
        print(f"✅ Products count: {response.total_count}")
        print(f"✅ Products list: {response.products}")
        
        if response.total_count == 0 and response.products == []:
            print("✅ Correctly returns empty list response")
        else:
            print("❌ Should return empty list response")
            
        # Restore original
        SubscriptionService.__init__ = original_service_init
        
    except Exception as e:
        print(f"❌ Error in get_active_products(): {e}")
        import traceback
        traceback.print_exc()
    
    print("\n2. Testing get_my_products() with empty list...")
    try:
        # Mock the SubscriptionService constructor
        original_service_init = SubscriptionService.__init__
        SubscriptionService.__init__ = lambda self, db: None
        SubscriptionService.get_firm_products = AsyncMock(return_value=[])
        
        response = await get_my_products(
            include_inactive=False, 
            current_user=mock_user, 
            db=mock_db
        )
        
        print(f"✅ Response type: {type(response)}")
        print(f"✅ Products count: {response.total_count}")
        print(f"✅ Products list: {response.products}")
        
        if response.total_count == 0 and response.products == []:
            print("✅ Correctly returns empty list response")
        else:
            print("❌ Should return empty list response")
            
        # Restore original
        SubscriptionService.__init__ = original_service_init
        
    except Exception as e:
        print(f"❌ Error in get_my_products(): {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("🚀 Testing API Empty Response Handling")
    print("=" * 50)
    
    asyncio.run(test_api_empty_responses())
    
    print("\n" + "=" * 50)
    print("🎉 API Test Complete!")