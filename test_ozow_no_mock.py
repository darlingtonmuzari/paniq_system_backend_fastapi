#!/usr/bin/env python3
"""
Test OZOW payment using exact implementation from ozow.txt without mocking
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


async def test_ozow_no_mock():
    """Test OZOW payment without any mocking"""

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

        print("🧪 Testing OZOW Without Mocking")
        print("=" * 40)

        # Get test firm
        result = await session.execute(select(SecurityFirm).limit(1))
        firm = result.scalar_one_or_none()

        if not firm:
            print("❌ No security firms found for testing")
            return

        print(f"✅ Using test firm: {firm.name}")

        # Test 1: Create Invoice
        print("\n1. Testing Invoice Creation...")
        try:
            invoice, credits = await ozow_service.create_invoice(
                db=session, firm_id=firm.id, amount=Decimal("150.00")
            )
            print(f"✅ Created invoice: {invoice.invoice_number}")
            print(f"   Credits: {invoice.credits_amount}")
            print(f"   Amount: R{invoice.total_amount}")
            print(f"   Status: {invoice.status}")

            # Test 2: Create Payment Request (No Mock Fallback)
            print("\n2. Testing OZOW Payment Request (No Mock)...")
            try:
                payment_result = await ozow_service.create_payment_request(
                    db=session, invoice=invoice
                )
                
                if payment_result.get("error"):
                    print(f"❌ Payment request failed: {payment_result['error']}")
                    print(f"   HTTP Status: {payment_result.get('http_status', 'Unknown')}")
                    print(f"   Raw Response: {payment_result.get('raw_ozow_response', 'None')}")
                else:
                    print(f"✅ Payment request successful!")
                    print(f"   Transaction ID: {payment_result['payment_request_id']}")
                    print(f"   Payment URL: {payment_result['url']}")
                    print(f"   OZOW Success: {payment_result.get('ozow_success', False)}")
                    
                    # Test 3: Verify Payment
                    if payment_result['payment_request_id']:
                        print(f"\n3. Testing Payment Verification...")
                        try:
                            verification_result = await ozow_service.verify_payment(
                                session, payment_result['payment_request_id']
                            )
                            print(f"✅ Verification successful!")
                            print(f"   Verification Result: {verification_result}")
                        except Exception as verify_error:
                            print(f"❌ Verification failed: {str(verify_error)}")
                    
            except Exception as e:
                print(f"❌ Payment request failed with exception: {str(e)}")

        except Exception as e:
            print(f"❌ Invoice creation failed: {str(e)}")

        # Test 4: Configuration Check
        print("\n4. Configuration Check...")
        print(f"   Site Code: {ozow_service.site_code}")
        print(f"   Is Test Mode: {ozow_service.is_test}")
        print(f"   Post URL: {ozow_service.post_url}")
        print(f"   Verify URL: {ozow_service.verify_url}")
        print(f"   Success URL: {ozow_service.success_url}")

    await engine.dispose()
    print("\n✅ Testing completed (no mocking used)!")


if __name__ == "__main__":
    try:
        asyncio.run(test_ozow_no_mock())
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        sys.exit(1)