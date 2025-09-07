#!/usr/bin/env python3
"""
Test script for firm admin product management functionality
"""
import asyncio
import httpx
import json
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

class FirmAdminProductTester:
    def __init__(self):
        self.client = httpx.AsyncClient()
        self.auth_token = None
        self.firm_admin_headers = {}
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def authenticate_firm_admin(self, email: str, password: str) -> bool:
        """Authenticate as a firm admin"""
        try:
            response = await self.client.post(
                f"{API_BASE}/auth/login",
                json={"email": email, "password": password}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                self.firm_admin_headers = {
                    "Authorization": f"Bearer {self.auth_token}",
                    "Content-Type": "application/json"
                }
                print(f"✅ Successfully authenticated as firm admin: {email}")
                return True
            else:
                print(f"❌ Authentication failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    async def create_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new product"""
        try:
            response = await self.client.post(
                f"{API_BASE}/subscription-products/",
                json=product_data,
                headers=self.firm_admin_headers
            )
            
            if response.status_code == 200:
                product = response.json()
                print(f"✅ Product created successfully: {product['name']} (ID: {product['id']})")
                return product
            else:
                print(f"❌ Product creation failed: {response.status_code} - {response.text}")
                return {}
        except Exception as e:
            print(f"❌ Product creation error: {e}")
            return {}
    
    async def get_my_products(self, include_inactive: bool = False) -> list:
        """Get all products for the current firm"""
        try:
            params = {"include_inactive": include_inactive}
            response = await self.client.get(
                f"{API_BASE}/subscription-products/my-products",
                params=params,
                headers=self.firm_admin_headers
            )
            
            if response.status_code == 200:
                data = response.json()
                products = data.get("products", [])
                print(f"✅ Retrieved {len(products)} products for firm")
                return products
            else:
                print(f"❌ Failed to get products: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            print(f"❌ Get products error: {e}")
            return []
    
    async def get_product(self, product_id: str) -> Dict[str, Any]:
        """Get a specific product by ID"""
        try:
            response = await self.client.get(
                f"{API_BASE}/subscription-products/{product_id}",
                headers=self.firm_admin_headers
            )
            
            if response.status_code == 200:
                product = response.json()
                print(f"✅ Retrieved product: {product['name']}")
                return product
            else:
                print(f"❌ Failed to get product: {response.status_code} - {response.text}")
                return {}
        except Exception as e:
            print(f"❌ Get product error: {e}")
            return {}
    
    async def update_product(self, product_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a product"""
        try:
            response = await self.client.put(
                f"{API_BASE}/subscription-products/{product_id}",
                json=update_data,
                headers=self.firm_admin_headers
            )
            
            if response.status_code == 200:
                product = response.json()
                print(f"✅ Product updated successfully: {product['name']}")
                return product
            else:
                print(f"❌ Product update failed: {response.status_code} - {response.text}")
                return {}
        except Exception as e:
            print(f"❌ Product update error: {e}")
            return {}
    
    async def delete_product(self, product_id: str) -> bool:
        """Delete a product"""
        try:
            response = await self.client.delete(
                f"{API_BASE}/subscription-products/{product_id}",
                headers=self.firm_admin_headers
            )
            
            if response.status_code == 200:
                print(f"✅ Product deleted successfully")
                return True
            else:
                print(f"❌ Product deletion failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"❌ Product deletion error: {e}")
            return False
    
    async def get_product_statistics(self, product_id: str) -> Dict[str, Any]:
        """Get product statistics"""
        try:
            response = await self.client.get(
                f"{API_BASE}/subscription-products/{product_id}/statistics",
                headers=self.firm_admin_headers
            )
            
            if response.status_code == 200:
                stats = response.json()
                print(f"✅ Retrieved product statistics")
                return stats
            else:
                print(f"❌ Failed to get statistics: {response.status_code} - {response.text}")
                return {}
        except Exception as e:
            print(f"❌ Get statistics error: {e}")
            return {}


async def run_tests():
    """Run comprehensive tests for firm admin product management"""
    print("🚀 Starting Firm Admin Product Management Tests")
    print("=" * 60)
    
    async with FirmAdminProductTester() as tester:
        # Step 1: Authenticate as firm admin
        print("\n1. Authenticating as firm admin...")
        # You'll need to replace these with actual firm admin credentials
        authenticated = await tester.authenticate_firm_admin(
            email="admin@securityfirm.com",  # Replace with actual firm admin email
            password="password123"  # Replace with actual password
        )
        
        if not authenticated:
            print("❌ Cannot proceed without authentication")
            return
        
        # Step 2: Create a new product
        print("\n2. Creating a new product...")
        product_data = {
            "name": "Premium Security Package",
            "description": "24/7 monitoring with rapid response team",
            "max_users": 10,
            "price": 299.99,
            "credit_cost": 50
        }
        
        created_product = await tester.create_product(product_data)
        if not created_product:
            print("❌ Cannot proceed without creating a product")
            return
        
        product_id = created_product["id"]
        
        # Step 3: Get all products for the firm
        print("\n3. Retrieving all firm products...")
        products = await tester.get_my_products(include_inactive=True)
        
        # Step 4: Get specific product
        print("\n4. Retrieving specific product...")
        product = await tester.get_product(product_id)
        
        # Step 5: Update the product
        print("\n5. Updating product...")
        update_data = {
            "name": "Premium Security Package - Updated",
            "description": "Enhanced 24/7 monitoring with rapid response team and mobile app",
            "price": 349.99,
            "is_active": True
        }
        
        updated_product = await tester.update_product(product_id, update_data)
        
        # Step 6: Get product statistics
        print("\n6. Getting product statistics...")
        stats = await tester.get_product_statistics(product_id)
        if stats:
            print(f"   - Total purchases: {stats.get('total_purchases', 0)}")
            print(f"   - Applied subscriptions: {stats.get('applied_subscriptions', 0)}")
            print(f"   - Total revenue: ${stats.get('total_revenue', 0):.2f}")
        
        # Step 7: Try to delete the product
        print("\n7. Attempting to delete product...")
        deleted = await tester.delete_product(product_id)
        
        if deleted:
            print("✅ Product deleted successfully (it had no subscriptions)")
        else:
            print("ℹ️  Product could not be deleted (likely has subscriptions)")
        
        # Step 8: Create another product and deactivate it
        print("\n8. Creating and deactivating a product...")
        basic_product_data = {
            "name": "Basic Security Package",
            "description": "Standard monitoring service",
            "max_users": 5,
            "price": 149.99,
            "credit_cost": 25
        }
        
        basic_product = await tester.create_product(basic_product_data)
        if basic_product:
            # Deactivate the product
            deactivate_data = {"is_active": False}
            await tester.update_product(basic_product["id"], deactivate_data)
            
            # Try to delete the inactive product
            print("\n9. Attempting to delete inactive product...")
            await tester.delete_product(basic_product["id"])
        
        print("\n" + "=" * 60)
        print("🎉 Firm Admin Product Management Tests Completed!")


if __name__ == "__main__":
    asyncio.run(run_tests())