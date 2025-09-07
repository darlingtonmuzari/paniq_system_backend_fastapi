#!/usr/bin/env python3
"""
Debug the empty error message issue
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


async def debug_error():
    """Debug the error handling"""

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

        print("🐛 Debugging Error Handling")
        print("=" * 40)

        # Get test firm
        result = await session.execute(select(SecurityFirm).limit(1))
        firm = result.scalar_one_or_none()

        if not firm:
            print("❌ No security firms found for testing")
            return

        print(f"✅ Using test firm: {firm.name}")

        try:
            # Create invoice
            print("\n1. Creating invoice...")
            invoice, credits = await ozow_service.create_invoice(
                db=session, firm_id=firm.id, amount=Decimal("150.00")
            )
            print(f"✅ Invoice created: {invoice.invoice_number}")

            # Create payment request
            print("\n2. Creating payment request...")
            payment_result = await ozow_service.create_payment_request(
                db=session, invoice=invoice
            )
            
            print(f"✅ Payment result type: {type(payment_result)}")
            print(f"✅ Payment result keys: {list(payment_result.keys())}")
            print(f"✅ Payment result: {payment_result}")
            
            # Check error field specifically
            error_field = payment_result.get("error")
            print(f"✅ Error field: '{error_field}'")
            print(f"✅ Error field type: {type(error_field)}")
            print(f"✅ Error field length: {len(str(error_field)) if error_field else 0}")
            print(f"✅ Error field is None: {error_field is None}")
            print(f"✅ Error field is empty string: {error_field == ''}")
            print(f"✅ Error field stripped: '{error_field.strip() if error_field else 'None'}'")
            
            if payment_result.get("error"):
                print(f"❌ Error detected: {payment_result['error']}")
            else:
                print(f"✅ No error detected")

        except Exception as e:
            print(f"❌ Exception occurred: {str(e)}")
            print(f"❌ Exception type: {type(e)}")

    await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(debug_error())
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        sys.exit(1)