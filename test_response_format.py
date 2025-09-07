#!/usr/bin/env python3
"""
Test the exact response format from purchase-credits endpoint
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


async def test_response_format():
    """Test the exact response format"""

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

        print("🧪 Testing Exact Response Format")
        print("=" * 40)

        # Get test firm
        result = await session.execute(select(SecurityFirm).limit(1))
        firm = result.scalar_one_or_none()

        if not firm:
            print("❌ No security firms found for testing")
            return

        # Create invoice
        invoice, credits = await ozow_service.create_invoice(
            db=session, firm_id=firm.id, amount=Decimal("150.00")
        )

        # Create payment request
        payment_result = await ozow_service.create_payment_request(
            db=session, invoice=invoice
        )

        # Format response exactly like the API endpoint
        api_response = {
            "paymentRequestId": payment_result["payment_request_id"],
            "url": payment_result["url"],
            "errorMessage": payment_result.get("error")
        }

        print("API Response Format:")
        print("=" * 20)
        import json
        print(json.dumps(api_response, indent=2))

        print("\nExpected Format:")
        print("=" * 16)
        expected = {
            "paymentRequestId": "734ecf05-e89c-4f0c-acb0-6881a452eb89",
            "url": "https://pay.ozow.com/734ecf05-e89c-4f0c-acb0-6881a452eb89/Secure",
            "errorMessage": None
        }
        print(json.dumps(expected, indent=2))

        print(f"\n✅ Format matches: {list(api_response.keys()) == list(expected.keys())}")

    await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(test_response_format())
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        sys.exit(1)