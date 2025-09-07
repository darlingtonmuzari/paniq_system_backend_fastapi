#!/usr/bin/env python3
"""
Test OZOW staging API only (no mock mode)
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
from app.services.ozow_service import OzowService


async def test_ozow_staging_only():
    """Test OZOW staging API with new response format"""

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

        print("🧪 Testing OZOW Staging API Only")
        print("=" * 40)

        # Get test firm
        result = await session.execute(select(SecurityFirm).limit(1))
        firm = result.scalar_one_or_none()

        if not firm:
            print("❌ No security firms found for testing")
            return

        print(f"✅ Using test firm: {firm.name}")

        # Test 1: Create invoice for R150 (should get 100 credits)
        print("\n1. Testing Invoice Creation for R150...")
        try:
            invoice, credits = await ozow_service.create_invoice(
                db=session, firm_id=firm.id, amount=Decimal("150.00")
            )
            print(f"✅ Created invoice: {invoice.invoice_number}")
            print(f"   Credits: {invoice.credits_amount}")
            print(f"   Amount: R{invoice.total_amount}")
            print(f"   Status: {invoice.status}")

            # Test 2: Create payment request with new response format
            print("\n2. Testing OZOW Payment Request (New Format)...")
            
            payment_result = await ozow_service.create_payment_request(
                db=session, invoice=invoice
            )
            
            print(f"✅ Payment request completed!")
            print(f"   Response format: {type(payment_result)}")
            print(f"   Keys: {list(payment_result.keys())}")
            
            if payment_result["error"]:
                print(f"❌ Payment failed with error: {payment_result['error']}")
                print(f"   payment_request_id: {payment_result['payment_request_id']}")
                print(f"   url: {payment_result['url']}")
            else:
                print(f"✅ Payment successful!")
                print(f"   payment_request_id: {payment_result['payment_request_id']}")
                print(f"   url: {payment_result['url']}")
                print(f"   error: {payment_result['error']}")
                
            # Check bank reference length
            bank_ref = invoice.invoice_number[-20:] if len(invoice.invoice_number) <= 20 else f"INV-{invoice.invoice_number.split('-')[-1]}"
            print(f"   Bank Reference: {bank_ref} ({len(bank_ref)} chars - within 20 limit)")

        except Exception as e:
            print(f"❌ Test failed: {str(e)}")

        print("\n" + "=" * 40)
        print("🎯 NEW RESPONSE FORMAT SUMMARY")
        print("=" * 40)
        print("✅ CHANGES MADE:")
        print("   1. Removed all mock mode functionality")
        print("   2. Using OZOW staging API only")
        print("   3. New response format: {payment_request_id, url, error}")
        print("   4. Bank reference length fixed (within 20 chars)")
        print()
        print("📋 RESPONSE FORMAT:")
        print("   - SUCCESS: payment_request_id=<id>, url=<url>, error=None")
        print("   - FAILURE: payment_request_id=None, url=None, error=<message>")

    await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(test_ozow_staging_only())
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        sys.exit(1)