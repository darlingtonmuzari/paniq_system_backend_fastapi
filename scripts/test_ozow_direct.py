#!/usr/bin/env python3
"""
Direct test of OZOW payment integration without API authentication
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


async def test_ozow_direct():
    """Test OZOW payment integration directly"""

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

        print("🧪 Testing OZOW Direct Integration")
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

            # Test 2: Create payment request
            print("\n2. Testing OZOW Payment Request...")
            try:
                payment_url, transaction_id = await ozow_service.create_payment_request(
                    db=session, invoice=invoice
                )
                print(f"✅ Payment request created successfully!")
                print(f"   Transaction ID: {transaction_id}")
                print(f"   Payment URL: {payment_url}")
                print(f"   OZOW Reference: {invoice.ozow_reference}")
                
                # Check bank reference length
                bank_ref_length = len(invoice.ozow_reference.split('-')[-1]) if invoice.ozow_reference else 0
                print(f"   Bank Reference Length: {bank_ref_length} chars (max 20)")
                
            except Exception as e:
                print(f"❌ Payment request failed: {str(e)}")
                
                # If OZOW API is having issues, test with mock mode
                if "500" in str(e) or "HTTP error" in str(e):
                    print("\n   🔄 Testing with Mock Mode (OZOW API seems down)...")
                    ozow_service.enable_mock_mode()
                    
                    try:
                        payment_url, transaction_id = await ozow_service.create_payment_request(
                            db=session, invoice=invoice
                        )
                        print(f"   ✅ Mock payment request created!")
                        print(f"   Transaction ID: {transaction_id}")
                        print(f"   Payment URL: {payment_url}")
                        print(f"   OZOW Reference: {invoice.ozow_reference}")
                    except Exception as mock_e:
                        print(f"   ❌ Mock mode also failed: {str(mock_e)}")
                
                # If it's still a bank reference error, let's debug
                elif "Bank Reference" in str(e):
                    print(f"   Invoice Number: {invoice.invoice_number} (length: {len(invoice.invoice_number)})")
                    bank_ref = invoice.invoice_number[-20:] if len(invoice.invoice_number) <= 20 else f"INV-{invoice.invoice_number.split('-')[-1]}"
                    print(f"   Generated Bank Ref: {bank_ref} (length: {len(bank_ref)})")

        except Exception as e:
            print(f"❌ Invoice creation failed: {str(e)}")

        # Test 3: Test with different amounts
        print("\n3. Testing Different Credit Amounts...")
        test_amounts = [Decimal("100.00"), Decimal("600.00"), Decimal("1000.00")]
        
        for amount in test_amounts:
            try:
                credits, exact_price = await ozow_service.get_credits_for_amount(session, amount)
                print(f"   R{amount} = {credits} credits")
            except ValueError as e:
                print(f"   R{amount}: ❌ {str(e)}")

    await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(test_ozow_direct())
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        sys.exit(1)