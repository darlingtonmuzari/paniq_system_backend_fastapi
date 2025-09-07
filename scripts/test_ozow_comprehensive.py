#!/usr/bin/env python3
"""
Comprehensive OZOW payment testing
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


async def test_ozow_comprehensive():
    """Comprehensive OZOW payment testing"""

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

        print("🧪 Comprehensive OZOW Testing")
        print("=" * 50)

        # Get test firm
        result = await session.execute(select(SecurityFirm).limit(1))
        firm = result.scalar_one_or_none()

        if not firm:
            print("❌ No security firms found for testing")
            return

        print(f"✅ Using test firm: {firm.name}")

        # Test 1: Hash Generation Verification
        print("\n1. Testing Hash Generation...")
        test_payment_data = {
            "siteCode": settings.OZOW_SITE_CODE,
            "countryCode": "ZA",
            "currencyCode": "ZAR",
            "amount": "25.01",
            "transactionReference": "transaction_reference_123",
            "bankReference": "bank_reference_123",
            "cancelUrl": settings.OZOW_CANCEL_URL,
            "errorUrl": settings.OZOW_ERROR_URL,
            "successUrl": settings.OZOW_SUCCESS_URL,
            "notifyUrl": settings.OZOW_NOTIFY_URL,
            "isTest": "false"
        }
        
        hash_result = ozow_service._generate_hash_check(test_payment_data)
        print(f"✅ Hash generated: {hash_result[:32]}...")

        # Test 2: Create Invoice
        print("\n2. Testing Invoice Creation...")
        try:
            invoice, credits = await ozow_service.create_invoice(
                db=session, firm_id=firm.id, amount=Decimal("150.00")
            )
            print(f"✅ Created invoice: {invoice.invoice_number}")
            print(f"   Credits: {invoice.credits_amount}")
            print(f"   Amount: R{invoice.total_amount}")
            print(f"   Status: {invoice.status}")

            # Test 3: Real OZOW API Request
            print("\n3. Testing Real OZOW API...")
            try:
                payment_result = await ozow_service.create_payment_request(
                    db=session, invoice=invoice
                )
                
                if payment_result.get("error"):
                    print(f"❌ Real API failed: {payment_result['error']}")
                    
                    # Test 4: Mock Mode Fallback
                    print("\n4. Testing Mock Mode Fallback...")
                    ozow_service.enable_mock_mode()
                    
                    # Create new invoice for mock test
                    mock_invoice, mock_credits = await ozow_service.create_invoice(
                        db=session, firm_id=firm.id, amount=Decimal("100.00")
                    )
                    
                    mock_result = await ozow_service.create_payment_request(
                        db=session, invoice=mock_invoice
                    )
                    
                    if mock_result.get("error"):
                        print(f"❌ Mock mode failed: {mock_result['error']}")
                    else:
                        print(f"✅ Mock payment created successfully!")
                        print(f"   Transaction ID: {mock_result['payment_request_id']}")
                        print(f"   Payment URL: {mock_result['url']}")
                        print(f"   Invoice Reference: {mock_invoice.ozow_reference}")
                else:
                    print(f"✅ Real API payment created successfully!")
                    print(f"   Transaction ID: {payment_result['payment_request_id']}")
                    print(f"   Payment URL: {payment_result['url']}")
                    print(f"   Invoice Reference: {invoice.ozow_reference}")
                    
            except Exception as e:
                print(f"❌ Payment request failed: {str(e)}")

        except Exception as e:
            print(f"❌ Invoice creation failed: {str(e)}")

        # Test 5: Credit Tier Validation
        print("\n5. Testing Credit Tier Validation...")
        test_amounts = [Decimal("100.00"), Decimal("150.00"), Decimal("600.00")]
        
        for amount in test_amounts:
            try:
                credits, exact_price = await ozow_service.get_credits_for_amount(session, amount)
                print(f"   R{amount} = {credits} credits (exact price: R{exact_price})")
            except ValueError as e:
                print(f"   R{amount}: ❌ {str(e)}")

        # Test 6: Configuration Validation
        print("\n6. Testing Configuration...")
        print(f"   Site Code: {ozow_service.site_code}")
        print(f"   Is Test Mode: {ozow_service.is_test}")
        print(f"   Post URL: {ozow_service.post_url}")
        print(f"   Success URL: {ozow_service.success_url}")
        print(f"   API Key: {ozow_service.api_key[:8]}...")
        print(f"   Private Key: {ozow_service.private_key[:8]}...")

    await engine.dispose()
    print("\n✅ Comprehensive testing completed!")


if __name__ == "__main__":
    try:
        asyncio.run(test_ozow_comprehensive())
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        sys.exit(1)