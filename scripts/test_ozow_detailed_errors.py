#!/usr/bin/env python3
"""
Test OZOW with detailed error logging
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


async def test_ozow_detailed_errors():
    """Test OZOW with detailed error logging"""

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

        print("🔍 OZOW Detailed Error Testing")
        print("=" * 50)

        # Get test firm
        result = await session.execute(select(SecurityFirm).limit(1))
        firm = result.scalar_one_or_none()

        if not firm:
            print("❌ No security firms found for testing")
            return

        print(f"✅ Using test firm: {firm.name}")
        print(f"✅ OZOW Configuration:")
        print(f"   Site Code: {ozow_service.site_code}")
        print(f"   API Key: {ozow_service.api_key[:10]}...")
        print(f"   Private Key: {ozow_service.private_key[:10]}...")
        print(f"   Is Test: {ozow_service.is_test}")
        print(f"   Post URL: {ozow_service.post_url}")

        try:
            # Create invoice
            print(f"\n📋 Creating invoice for R150...")
            invoice, credits = await ozow_service.create_invoice(
                db=session, firm_id=firm.id, amount=Decimal("150.00")
            )
            print(f"✅ Invoice created: {invoice.invoice_number}")

            # Create payment request with detailed error logging
            print(f"\n🔄 Creating payment request with detailed error logging...")
            print(f"=" * 50)
            
            payment_result = await ozow_service.create_payment_request(
                db=session, invoice=invoice
            )
            
            print(f"=" * 50)
            print(f"📊 FINAL PAYMENT RESULT:")
            print(f"   Type: {type(payment_result)}")
            print(f"   Keys: {list(payment_result.keys())}")
            print(f"   payment_request_id: {payment_result.get('payment_request_id')}")
            print(f"   url: {payment_result.get('url')}")
            print(f"   error: {payment_result.get('error')}")
            
            if payment_result.get("error"):
                print(f"\n❌ PAYMENT FAILED:")
                print(f"   Error Message: {payment_result['error']}")
                print(f"   Error Length: {len(payment_result['error'])} characters")
            else:
                print(f"\n✅ PAYMENT SUCCESSFUL:")
                print(f"   Payment URL: {payment_result['url']}")
                print(f"   Transaction ID: {payment_result['payment_request_id']}")

        except Exception as e:
            print(f"\n🚨 OUTER EXCEPTION CAUGHT:")
            print(f"   Exception Type: {type(e).__name__}")
            print(f"   Exception Message: {str(e)}")
            
            import traceback
            print(f"   Full Traceback:")
            traceback.print_exc()

        print(f"\n✅ Detailed Error Test Completed!")

    await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(test_ozow_detailed_errors())
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)