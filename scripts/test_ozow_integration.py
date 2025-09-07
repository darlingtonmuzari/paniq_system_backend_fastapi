#!/usr/bin/env python3
"""
Test OZOW payment integration
"""
import asyncio
import sys
import os
from decimal import Decimal

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.core.config import settings
from app.models.security_firm import SecurityFirm
from app.models.payment import CreditTier
from app.services.ozow_service import OzowService


async def test_ozow_integration():
    """Test OZOW payment integration"""

    # Create async engine
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
    )

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        ozow_service = OzowService()

        print("🧪 Testing OZOW Integration")
        print("=" * 40)

        # Test 1: Check credit tiers
        print("\n1. Testing Credit Tiers...")
        result = await session.execute(select(CreditTier).where(CreditTier.is_active == True))
        tiers = result.scalars().all()

        if tiers:
            print(f"✅ Found {len(tiers)} active credit tiers:")
            for tier in tiers:
                print(f"   - {tier.min_credits}-{tier.max_credits} credits: R{tier.price}")
        else:
            print("❌ No credit tiers found")
            return

        # Test 2: Test pricing calculation
        print("\n2. Testing Price Calculation...")
        test_credits = [25, 75, 200, 750, 2000, 7500]

        for credits in test_credits:
            try:
                price = await ozow_service.get_credit_price(session, credits)
                print(f"   - {credits} credits: R{price}")
            except ValueError as e:
                print(f"   - {credits} credits: ❌ {str(e)}")

        # Test 3: Check if we have any security firms to test with
        print("\n3. Checking Security Firms...")
        result = await session.execute(select(SecurityFirm).limit(1))
        firm = result.scalar_one_or_none()

        if firm:
            print(f"✅ Found test firm: {firm.name}")
            print(f"   Current credit balance: {firm.credit_balance}")

            # Test 4: Create test invoice (without payment)
            print("\n4. Testing Invoice Creation...")
            try:
                invoice, credits = await ozow_service.create_invoice(
                    db=session, firm_id=firm.id, amount=Decimal("150.00")
                )
                print(f"✅ Created test invoice: {invoice.invoice_number}")
                print(f"   Credits: {invoice.credits_amount}")
                print(f"   Amount: R{invoice.total_amount}")
                print(f"   Status: {invoice.status}")
                print(f"   Expires: {invoice.expires_at}")

            except Exception as e:
                print(f"❌ Invoice creation failed: {str(e)}")
        else:
            print("❌ No security firms found for testing")

        # Test 5: Test OZOW configuration
        print("\n5. Testing OZOW Configuration...")
        print(f"   Base URL: {ozow_service.base_url}")
        print(f"   Site Code: {ozow_service.site_code}")
        print(f"   Is Test Mode: {ozow_service.is_test}")
        print(f"   Post URL: {ozow_service.post_url}")
        print(f"   Success URL: {ozow_service.success_url}")
        print(f"   Webhook URL: {ozow_service.notify_url}")

        print("\n✅ OZOW Integration Test Completed!")
        print("\nNext Steps:")
        print("1. Start the API server: make dev")
        print("2. Test endpoints at: http://localhost:8000/docs")
        print("3. Key endpoints:")
        print("   - GET /api/v1/payments/credit-tiers")
        print("   - POST /api/v1/payments/purchase-credits")
        print("   - GET /api/v1/payments/credit-balance")

    await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(test_ozow_integration())
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        sys.exit(1)
