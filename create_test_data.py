#!/usr/bin/env python3
"""
Create test data for subscription products
"""
import asyncio
import sys
import os
from decimal import Decimal
from uuid import uuid4

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.core.database import get_db
from app.models.subscription import SubscriptionProduct
from app.models.security_firm import SecurityFirm
from app.models.user import RegisteredUser


async def create_test_data():
    """Create test data for subscription products"""
    print("🚀 Creating Test Data...")
    
    try:
        async for db in get_db():
            # First, let's check if we have any security firms
            from sqlalchemy import select
            
            print("1. Checking for existing security firms...")
            result = await db.execute(select(SecurityFirm).limit(5))
            firms = result.scalars().all()
            
            if not firms:
                print("❌ No security firms found. Creating a test firm...")
                
                # Create a test security firm
                test_firm = SecurityFirm(
                    name="Test Security Firm",
                    registration_number="TSF001",
                    email="admin@testsecurity.com",
                    phone="+27123456789",
                    address="123 Test Street, Test City",
                    province="Gauteng",
                    country="South Africa",
                    verification_status="approved",
                    credit_balance=1000
                )
                
                db.add(test_firm)
                await db.flush()
                firms = [test_firm]
                print(f"✅ Created test firm: {test_firm.name} (ID: {test_firm.id})")
            else:
                print(f"✅ Found {len(firms)} existing firms")
                for firm in firms:
                    print(f"   - {firm.name} (ID: {firm.id}, Status: {firm.verification_status})")
            
            # Use the first approved firm or make the first firm approved
            firm = firms[0]
            if firm.verification_status != "approved":
                print(f"📝 Updating firm status to approved...")
                firm.verification_status = "approved"
                firm.credit_balance = 1000
            
            print(f"\n2. Creating test products for firm: {firm.name}")
            
            # Create test products
            test_products = [
                {
                    "name": "Basic Security Package",
                    "description": "Standard monitoring service with 24/7 support",
                    "max_users": 5,
                    "price": Decimal("149.99"),
                    "credit_cost": 25,
                    "is_active": True
                },
                {
                    "name": "Premium Security Package", 
                    "description": "Enhanced monitoring with rapid response team",
                    "max_users": 10,
                    "price": Decimal("299.99"),
                    "credit_cost": 50,
                    "is_active": True
                },
                {
                    "name": "Enterprise Security Package",
                    "description": "Full-scale security solution for large organizations",
                    "max_users": 25,
                    "price": Decimal("599.99"),
                    "credit_cost": 100,
                    "is_active": True
                },
                {
                    "name": "Inactive Test Package",
                    "description": "This package is inactive for testing purposes",
                    "max_users": 3,
                    "price": Decimal("99.99"),
                    "credit_cost": 15,
                    "is_active": False
                }
            ]
            
            created_products = []
            for product_data in test_products:
                product = SubscriptionProduct(
                    firm_id=firm.id,
                    **product_data
                )
                db.add(product)
                await db.flush()
                created_products.append(product)
                
                print(f"✅ Created product: {product.name} (ID: {product.id})")
                print(f"   - Price: ${product.price}")
                print(f"   - Max Users: {product.max_users}")
                print(f"   - Active: {product.is_active}")
            
            # Commit all changes
            await db.commit()
            
            print(f"\n🎉 Successfully created {len(created_products)} test products!")
            print(f"📊 Firm credit balance: {firm.credit_balance}")
            
            # Display summary
            print("\n📋 Test Data Summary:")
            print(f"Firm: {firm.name} (ID: {firm.id})")
            print("Products:")
            for product in created_products:
                status = "🟢 Active" if product.is_active else "🔴 Inactive"
                print(f"  - {product.name} | ${product.price} | {product.max_users} users | {status}")
            
            break
            
    except Exception as e:
        print(f"❌ Error creating test data: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(create_test_data())