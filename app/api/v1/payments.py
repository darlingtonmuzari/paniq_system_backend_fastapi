"""
Payment API endpoints
"""
import json
from datetime import datetime
from decimal import Decimal
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_db
from app.core.auth import get_current_firm_personnel
from app.core.config import settings
from app.models.payment import CreditTier, Invoice, PaymentNotification
from app.models.security_firm import SecurityFirm
from app.models.subscription import CreditTransaction
from app.schemas.payment import (
    CreditTierResponse,
    CreditPurchaseRequest,
    InvoiceResponse,
    PaymentInitiationResponse,
    PaymentWebhookRequest,
    PaymentStatusResponse,
    CreditBalanceResponse,
    CreditTransactionResponse,
    TransactionProcessResponse,
    PaymentRequestVerificationResponse,
    PaymentRequestProcessResponse,
    OzowPaymentStatusResponse,
    OzowPaymentDataRequest
)
from app.services.ozow_service import OzowService

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/debug/current-user")
async def debug_current_user(
    current_user = Depends(get_current_firm_personnel),
    db: AsyncSession = Depends(get_db)
):
    """Debug endpoint to check current user details"""
    return {
        "user_id": str(current_user.user_id),
        "user_type": current_user.user_type,
        "email": current_user.email,
        "firm_id": str(current_user.firm_id) if current_user.firm_id else None,
        "role": current_user.role,
        "permissions": current_user.permissions,
        "is_firm_personnel": current_user.is_firm_personnel(),
        "is_registered_user": current_user.is_registered_user()
    }


@router.get("/debug/ozow-config")
async def debug_ozow_config():
    """Debug endpoint to check OZOW configuration"""
    ozow_service = OzowService()
    return {
        "base_url": ozow_service.base_url,
        "site_code": ozow_service.site_code,
        "is_test": ozow_service.is_test,
        "post_url": ozow_service.post_url,
        "success_url": ozow_service.success_url,
        "cancel_url": ozow_service.cancel_url,
        "error_url": ozow_service.error_url,
        "notify_url": ozow_service.notify_url,
        "verify_url": ozow_service.verify_url
    }


@router.post("/debug/init-credit-tiers")
async def debug_init_credit_tiers(
    db: AsyncSession = Depends(get_db)
):
    """Debug endpoint to initialize credit tiers"""
    ozow_service = OzowService()
    await ozow_service.initialize_credit_tiers(db)
    
    # Return available tiers
    result = await db.execute(
        select(CreditTier)
        .where(CreditTier.is_active == True)
        .order_by(CreditTier.min_credits)
    )
    tiers = result.scalars().all()
    
    return {
        "message": "Credit tiers initialized",
        "tiers": [
            {
                "id": str(tier.id),
                "min_credits": tier.min_credits,
                "max_credits": tier.max_credits,
                "price": float(tier.price)
            }
            for tier in tiers
        ]
    }


@router.post("/debug/calculate-credits")
async def debug_calculate_credits(
    request: dict,
    db: AsyncSession = Depends(get_db)
):
    """Debug endpoint to test credit calculation for different amounts"""
    
    try:
        amount = Decimal(str(request.get("amount", 0)))
        
        ozow_service = OzowService()
        await ozow_service.initialize_credit_tiers(db)
        
        # Calculate credits
        credits, final_amount = await ozow_service.get_credits_for_amount(db, amount)
        
        return {
            "input_amount": float(amount),
            "calculated_credits": credits,
            "final_amount": float(final_amount)
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "input_amount": request.get("amount")
        }


@router.post("/debug/test-purchase")
async def debug_test_purchase(
    db: AsyncSession = Depends(get_db)
):
    """Debug endpoint to test purchase flow with hardcoded values"""
    
    # First ensure credit tiers exist
    ozow_service = OzowService()
    await ozow_service.initialize_credit_tiers(db)
    
    # Create a test firm if it doesn't exist
    from app.models.security_firm import SecurityFirm
    result = await db.execute(select(SecurityFirm).limit(1))
    firm = result.scalar_one_or_none()
    
    if not firm:
        return {"error": "No security firm found in database. Please create a firm first."}
    
    try:
        # Test with R100 (should give 50 credits)
        invoice, calculated_credits = await ozow_service.create_invoice(
            db=db,
            firm_id=firm.id,
            amount=Decimal("100.00")
        )
        
        return {
            "message": "Invoice created successfully",
            "invoice_id": str(invoice.id),
            "invoice_number": invoice.invoice_number,
            "amount": float(invoice.total_amount),
            "credits": invoice.credits_amount,
            "calculated_credits": calculated_credits,
            "firm_id": str(firm.id)
        }
        
    except Exception as e:
        return {
            "error": f"Failed to create invoice: {str(e)}",
            "error_type": type(e).__name__
        }


@router.post("/debug/test-ozow-payment")
async def debug_test_ozow_payment(
    db: AsyncSession = Depends(get_db)
):
    """Debug endpoint to test full OZOW payment flow"""
    
    # First ensure credit tiers exist
    ozow_service = OzowService()
    await ozow_service.initialize_credit_tiers(db)
    
    # Get a test firm
    from app.models.security_firm import SecurityFirm
    result = await db.execute(select(SecurityFirm).limit(1))
    firm = result.scalar_one_or_none()
    
    if not firm:
        return {"error": "No security firm found in database. Please create a firm first."}
    
    try:
        # Create invoice
        invoice, calculated_credits = await ozow_service.create_invoice(
            db=db,
            firm_id=firm.id,
            amount=Decimal("100.00")
        )
        
        # Create payment request
        payment_result = await ozow_service.create_payment_request(
            db=db,
            invoice=invoice
        )
        
        return {
            "message": "Payment request created",
            "invoice_id": str(invoice.id),
            "payment_result": payment_result
        }
        
    except Exception as e:
        import traceback
        return {
            "error": f"Failed to create payment: {str(e)}",
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc()
        }


@router.post("/purchase-credits-simple")
async def purchase_credits_simple(
    request: dict,
    db: AsyncSession = Depends(get_db)
):
    """Simple credit purchase endpoint using amount field"""
    
    try:
        amount = Decimal(str(request.get("amount", 0)))
        
        if amount <= 0:
            raise ValueError("Amount must be greater than 0")
        
        # Initialize credit tiers if needed
        ozow_service = OzowService()
        await ozow_service.initialize_credit_tiers(db)
        
        # Get a test firm (for testing purposes)
        from app.models.security_firm import SecurityFirm
        result = await db.execute(select(SecurityFirm).limit(1))
        firm = result.scalar_one_or_none()
        
        if not firm:
            return {"error": "No security firm found in database. Please create a firm first."}
        
        # Create invoice
        invoice, calculated_credits = await ozow_service.create_invoice(
            db=db,
            firm_id=firm.id,
            amount=amount
        )
        
        # Create payment request
        payment_result = await ozow_service.create_payment_request(
            db=db,
            invoice=invoice
        )
        
        return {
            "paymentRequestId": payment_result.get("payment_request_id"),
            "url": payment_result.get("url"),
            "errorMessage": payment_result.get("error"),
            "invoice_id": str(invoice.id),
            "amount": float(amount),
            "credits": calculated_credits
        }
        
    except Exception as e:
        return {
            "paymentRequestId": None,
            "url": None,
            "errorMessage": str(e)
        }


@router.post("/debug/test-ozow-exact")
async def debug_test_ozow_exact():
    """Debug endpoint that exactly matches ozow.py implementation"""
    
    import httpx
    import hashlib
    
    # Exact values from ozow.py
    OZOW_SITE_CODE = "MOF-MOF-002"
    OZOW_PRIVATE_KEY = "40481eb78f0648f0894dd394f87a9cf2"
    OZOW_API_KEY = "d1784bcb43db4869b786901bc7a87577"
    
    # Generate hash exactly like ozow.py
    site_code = OZOW_SITE_CODE
    country_code = 'ZA'
    currency_code = 'ZAR'
    amount = 25.01
    transaction_reference = 'transaction_reference_123'
    bank_reference = 'bank_reference_123'
    cancel_url = 'https://great-utterly-owl.ngrok-free.app/cancel.html'
    error_url = 'https://great-utterly-owl.ngrok-free.app/error.html'
    success_url = 'https://great-utterly-owl.ngrok-free.app/success.html'
    notify_url = 'https://great-utterly-owl.ngrok-free.app/notify.html'
    private_key = OZOW_PRIVATE_KEY
    is_test = False
    
    input_string = site_code + country_code + currency_code + str(amount) + transaction_reference + bank_reference + cancel_url + error_url + success_url + notify_url + str(is_test) + private_key
    input_string = input_string.lower()
    
    sha = hashlib.sha512()
    sha.update(input_string.encode())
    hash_code = sha.hexdigest()
    
    # Exact request like ozow.py
    url = "https://api.ozow.com/postpaymentrequest"
    
    headers = {
        "Accept": "application/json",
        "ApiKey": OZOW_API_KEY,
        "Content-Type": "application/json"
    }
    
    data = {
        "countryCode": "ZA",
        "amount": "25.01",
        "transactionReference": "transaction_reference_123",
        "bankReference": "bank_reference_123",
        "cancelUrl": "https://great-utterly-owl.ngrok-free.app/cancel.html",
        "currencyCode": "ZAR",
        "errorUrl": "https://great-utterly-owl.ngrok-free.app/error.html",
        "isTest": "false",
        "notifyUrl": "https://great-utterly-owl.ngrok-free.app/notify.html",
        "siteCode": OZOW_SITE_CODE,
        "successUrl": "https://great-utterly-owl.ngrok-free.app/success.html",
        "hashCheck": hash_code
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            # Use live API URL as requested
            live_url = "https://api.ozow.com/postpaymentrequest"
            
            print(f"Trying live URL: {live_url}")
            response = await client.post(live_url, headers=headers, json=data)
            
            return {
                "url_used": live_url,
                "status_code": response.status_code,
                "response_text": response.text,
                "request_data": data,
                "hash_input": input_string,
                "generated_hash": hash_code
            }
    except Exception as e:
        return {
            "error": str(e),
            "error_type": type(e).__name__
        }


@router.get("/credit-tiers", response_model=List[CreditTierResponse])
async def get_credit_tiers(
    db: AsyncSession = Depends(get_db)
):
    """Get available credit pricing tiers"""
    result = await db.execute(
        select(CreditTier)
        .where(CreditTier.is_active == True)
        .order_by(CreditTier.min_credits)
    )
    tiers = result.scalars().all()
    return tiers


@router.post("/test-purchase-credits", response_model=PaymentInitiationResponse)
async def test_purchase_credits(
    request: CreditPurchaseRequest,
    current_user = Depends(get_current_firm_personnel),
    db: AsyncSession = Depends(get_db)
):
    """Test credit purchase with mock payment (for development)"""
    
    ozow_service = OzowService()
    
    try:
        # Validate that the firm_id in request matches user's firm or user has permission
        user_firm_id = current_user.firm_id
        
        if not user_firm_id:
            # If firm_id is not in token, try to look it up from database
            if current_user.user_type == "firm_personnel":
                from app.models.security_firm import FirmPersonnel
                result = await db.execute(
                    select(FirmPersonnel.firm_id).where(FirmPersonnel.id == current_user.user_id)
                )
                firm_record = result.scalar_one_or_none()
                if firm_record:
                    user_firm_id = firm_record
            
            if not user_firm_id:
                raise HTTPException(
                    status_code=400, 
                    detail="User is not associated with a firm. Please contact support."
                )
        
        # Verify that the requested firm_id matches the user's firm
        if str(user_firm_id) != str(request.firm_id):
            raise HTTPException(
                status_code=403,
                detail="You can only purchase credits for your own firm."
            )
        
        # Create invoice and get calculated credits
        invoice, calculated_credits = await ozow_service.create_invoice(
            db=db,
            firm_id=request.firm_id,
            amount=request.amount
        )
        
        # Create payment request
        payment_result = await ozow_service.create_payment_request(
            db=db,
            invoice=invoice
        )
        
        # Check if there was an error
        if payment_result.get("error"):
            error_msg = payment_result["error"]
            if not error_msg or error_msg.strip() == "":
                error_msg = "Unknown payment error occurred"
            raise HTTPException(status_code=500, detail=f"Payment initiation failed: {error_msg}")
        
        return PaymentInitiationResponse(
            invoice=InvoiceResponse.from_orm(invoice),
            payment_url=payment_result["url"],
            transaction_id=payment_result["payment_request_id"],
            expires_at=invoice.expires_at,
            calculated_credits=calculated_credits
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payment initiation failed: {str(e)}")


@router.post("/purchase-credits-raw")
async def purchase_credits_raw(
    request: CreditPurchaseRequest,
    current_user = Depends(get_current_firm_personnel),
    db: AsyncSession = Depends(get_db)
):
    """Initiate credit purchase via OZOW - Returns raw OZOW response"""
    
    ozow_service = OzowService()
    
    try:
        # Validate that the firm_id in request matches user's firm or user has permission
        user_firm_id = current_user.firm_id
        
        if not user_firm_id:
            # If firm_id is not in token, try to look it up from database
            if current_user.user_type == "firm_personnel":
                from app.models.security_firm import FirmPersonnel
                result = await db.execute(
                    select(FirmPersonnel.firm_id).where(FirmPersonnel.id == current_user.user_id)
                )
                firm_record = result.scalar_one_or_none()
                if firm_record:
                    user_firm_id = firm_record
            
            if not user_firm_id:
                raise HTTPException(
                    status_code=400, 
                    detail="User is not associated with a firm. Please contact support."
                )
        
        # Verify that the requested firm_id matches the user's firm
        if str(user_firm_id) != str(request.firm_id):
            raise HTTPException(
                status_code=403,
                detail="You can only purchase credits for your own firm."
            )
        
        # Create invoice and get calculated credits
        invoice, calculated_credits = await ozow_service.create_invoice(
            db=db,
            firm_id=request.firm_id,
            amount=request.amount
        )
        
        # Create payment request
        payment_result = await ozow_service.create_payment_request(
            db=db,
            invoice=invoice
        )
        
        # Check if there's an error and return appropriate status
        error_message = payment_result.get("error")
        response_data = {
            "paymentRequestId": payment_result["payment_request_id"],
            "url": payment_result["url"],
            "errorMessage": error_message
        }
        
        # Return HTTP 400 if there's an error, otherwise 200
        if error_message:
            from fastapi import Response
            import json
            return Response(
                content=json.dumps(response_data),
                status_code=400,
                media_type="application/json"
            )
        
        return response_data
        
    except ValueError as e:
        # Return validation errors in OZOW format with 400 status
        from fastapi import Response
        import json
        response_data = {
            "paymentRequestId": None,
            "url": None,
            "errorMessage": str(e)
        }
        return Response(
            content=json.dumps(response_data),
            status_code=400,
            media_type="application/json"
        )
    except Exception as e:
        # Return system errors in OZOW format with 400 status
        from fastapi import Response
        import json
        response_data = {
            "paymentRequestId": None,
            "url": None,
            "errorMessage": f"Payment initiation failed: {str(e)}"
        }
        return Response(
            content=json.dumps(response_data),
            status_code=400,
            media_type="application/json"
        )


@router.post("/purchase-credits")
async def purchase_credits(
    request: CreditPurchaseRequest,
    current_user = Depends(get_current_firm_personnel),
    db: AsyncSession = Depends(get_db)
):
    """Initiate credit purchase via OZOW - Returns raw OZOW response"""
    
    ozow_service = OzowService()
    
    try:
        # Validate that the firm_id in request matches user's firm or user has permission
        user_firm_id = current_user.firm_id
        
        if not user_firm_id:
            # If firm_id is not in token, try to look it up from database
            if current_user.user_type == "firm_personnel":
                from app.models.security_firm import FirmPersonnel
                result = await db.execute(
                    select(FirmPersonnel.firm_id).where(FirmPersonnel.id == current_user.user_id)
                )
                firm_record = result.scalar_one_or_none()
                if firm_record:
                    user_firm_id = firm_record
            
            if not user_firm_id:
                raise HTTPException(
                    status_code=400, 
                    detail="User is not associated with a firm. Please contact support."
                )
        
        # Verify that the requested firm_id matches the user's firm
        if str(user_firm_id) != str(request.firm_id):
            raise HTTPException(
                status_code=403,
                detail="You can only purchase credits for your own firm."
            )
        
        # Create invoice and get calculated credits
        invoice, calculated_credits = await ozow_service.create_invoice(
            db=db,
            firm_id=request.firm_id,
            amount=request.amount
        )
        
        # Create payment request
        payment_result = await ozow_service.create_payment_request(
            db=db,
            invoice=invoice
        )
        
        # Check if there's an error and return appropriate status
        error_message = payment_result.get("error")
        response_data = {
            "paymentRequestId": payment_result["payment_request_id"],
            "url": payment_result["url"],
            "errorMessage": error_message
        }
        
        # Return HTTP 400 if there's an error, otherwise 200
        if error_message:
            from fastapi import Response
            import json
            return Response(
                content=json.dumps(response_data),
                status_code=400,
                media_type="application/json"
            )
        
        return response_data
        
    except ValueError as e:
        # Return validation errors in OZOW format with 400 status
        from fastapi import Response
        import json
        response_data = {
            "paymentRequestId": None,
            "url": None,
            "errorMessage": str(e)
        }
        return Response(
            content=json.dumps(response_data),
            status_code=400,
            media_type="application/json"
        )
    except Exception as e:
        # Return system errors in OZOW format with 400 status
        from fastapi import Response
        import json
        response_data = {
            "paymentRequestId": None,
            "url": None,
            "errorMessage": f"Payment initiation failed: {str(e)}"
        }
        return Response(
            content=json.dumps(response_data),
            status_code=400,
            media_type="application/json"
        )


@router.get("/invoices", response_model=List[InvoiceResponse])
async def get_invoices(
    current_user = Depends(get_current_firm_personnel),
    db: AsyncSession = Depends(get_db)
):
    """Get firm's invoices"""
    result = await db.execute(
        select(Invoice)
        .where(Invoice.firm_id == current_user.firm_id)
        .order_by(desc(Invoice.created_at))
    )
    invoices = result.scalars().all()
    return invoices


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: UUID,
    current_user = Depends(get_current_firm_personnel),
    db: AsyncSession = Depends(get_db)
):
    """Get specific invoice"""
    result = await db.execute(
        select(Invoice)
        .where(
            Invoice.id == invoice_id,
            Invoice.firm_id == current_user.firm_id
        )
    )
    invoice = result.scalar_one_or_none()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    return invoice


@router.get("/status/{invoice_id}", response_model=PaymentStatusResponse)
async def get_payment_status(
    invoice_id: UUID,
    current_user = Depends(get_current_firm_personnel),
    db: AsyncSession = Depends(get_db)
):
    """Get payment status for an invoice"""
    result = await db.execute(
        select(Invoice)
        .where(
            Invoice.id == invoice_id,
            Invoice.firm_id == current_user.firm_id
        )
    )
    invoice = result.scalar_one_or_none()
    
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    return PaymentStatusResponse(
        invoice_id=invoice.id,
        status=invoice.status,
        amount=invoice.total_amount,
        credits=invoice.credits_amount,
        paid_at=invoice.paid_at,
        transaction_id=invoice.ozow_transaction_id
    )


@router.get("/credit-balance", response_model=CreditBalanceResponse)
async def get_credit_balance(
    current_user = Depends(get_current_firm_personnel),
    db: AsyncSession = Depends(get_db)
):
    """Get firm's current credit balance and recent transactions"""
    
    # Get firm details
    result = await db.execute(
        select(SecurityFirm).where(SecurityFirm.id == current_user.firm_id)
    )
    firm = result.scalar_one()
    
    # Get recent transactions
    result = await db.execute(
        select(CreditTransaction)
        .where(CreditTransaction.firm_id == current_user.firm_id)
        .order_by(desc(CreditTransaction.created_at))
        .limit(10)
    )
    transactions = result.scalars().all()
    
    return CreditBalanceResponse(
        firm_id=firm.id,
        current_balance=firm.credit_balance,
        recent_transactions=[
            {
                "id": str(t.id),
                "type": t.transaction_type,
                "amount": t.amount,
                "description": t.description,
                "created_at": t.created_at.isoformat()
            }
            for t in transactions
        ]
    )


@router.get("/transactions", response_model=List[CreditTransactionResponse])
async def get_credit_transactions(
    current_user = Depends(get_current_firm_personnel),
    db: AsyncSession = Depends(get_db)
):
    """Get firm's credit transaction history"""
    result = await db.execute(
        select(CreditTransaction)
        .where(CreditTransaction.firm_id == current_user.firm_id)
        .order_by(desc(CreditTransaction.created_at))
    )
    transactions = result.scalars().all()
    return transactions


# OZOW Webhook endpoints
@router.post("/ozow/webhooks")
async def ozow_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Handle OZOW payment webhooks"""
    
    try:
        # Get raw form data
        form_data = await request.form()
        webhook_data = dict(form_data)
        
        # Process webhook in background
        background_tasks.add_task(
            process_ozow_webhook,
            webhook_data,
            db
        )
        
        return {"status": "received"}
        
    except Exception as e:
        print(f"Webhook error: {str(e)}")
        return {"status": "error", "message": str(e)}


async def process_ozow_webhook(webhook_data: dict, db: AsyncSession):
    """Background task to process OZOW webhook"""
    ozow_service = OzowService()
    await ozow_service.process_webhook(db, webhook_data)


@router.get("/ozow/success")
async def ozow_success(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Handle OZOW success redirect"""
    
    # Get query parameters
    params = dict(request.query_params)
    transaction_id = params.get("TransactionId")
    
    if transaction_id:
        # Find invoice and redirect to appropriate page
        result = await db.execute(
            select(Invoice).where(Invoice.ozow_transaction_id == transaction_id)
        )
        invoice = result.scalar_one_or_none()
        
        if invoice:
            return {
                "status": "success",
                "message": "Payment successful",
                "invoice_id": str(invoice.id),
                "credits": invoice.credits_amount
            }
    
    return {"status": "success", "message": "Payment completed"}


@router.get("/ozow/cancel")
async def ozow_cancel(request: Request):
    """Handle OZOW cancel redirect"""
    return {
        "status": "cancelled",
        "message": "Payment was cancelled"
    }


@router.get("/ozow/error")
async def ozow_error(request: Request):
    """Handle OZOW error redirect"""
    params = dict(request.query_params)
    error_message = params.get("ErrorMessage", "Payment failed")
    
    return {
        "status": "error",
        "message": error_message
    }


@router.get("/verify/{transaction_id}")
async def verify_payment(
    transaction_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Verify payment status with OZOW"""
    
    ozow_service = OzowService()
    
    try:
        # Check if the provided ID is an invoice ID (UUID format) or actual Ozow transaction ID
        actual_transaction_id = transaction_id
        
        # Try to parse as UUID to see if it's an invoice ID
        try:
            from uuid import UUID
            invoice_uuid = UUID(transaction_id)
            
            # If it's a valid UUID, look up the invoice to get the Ozow transaction ID
            result = await db.execute(
                select(Invoice).where(Invoice.id == invoice_uuid)
            )
            invoice = result.scalar_one_or_none()
            
            if invoice and (invoice.ozow_payment_request_id or invoice.ozow_transaction_id):
                # Prefer payment_request_id if available, fallback to transaction_id
                actual_transaction_id = invoice.ozow_payment_request_id or invoice.ozow_transaction_id
                print(f"🔍 Converted invoice ID {transaction_id} to Ozow transaction ID: {actual_transaction_id}")
            elif invoice:
                raise HTTPException(status_code=400, detail="Invoice found but no Ozow transaction ID associated")
            else:
                raise HTTPException(status_code=404, detail="Invoice not found")
                
        except ValueError:
            # Not a UUID, assume it's already an Ozow transaction ID
            print(f"🔍 Using provided transaction ID directly: {transaction_id}")
        
        # Verify payment with OZOW using the actual transaction ID
        verification_result = await ozow_service.verify_payment(db, actual_transaction_id)
        
        return {
            "provided_id": transaction_id,
            "ozow_transaction_id": actual_transaction_id,
            "verification_result": verification_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")


@router.post("/process-transaction/{transaction_id}", response_model=TransactionProcessResponse)
async def process_transaction(
    transaction_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Process transaction by ID - fetch status from OZOW and update database"""
    
    ozow_service = OzowService()
    
    try:
        # Check if the provided ID is an invoice ID (UUID format) or actual Ozow transaction ID
        actual_transaction_id = transaction_id
        
        # Try to parse as UUID to see if it's an invoice ID
        try:
            from uuid import UUID
            invoice_uuid = UUID(transaction_id)
            
            # If it's a valid UUID, look up the invoice to get the Ozow transaction ID
            result = await db.execute(
                select(Invoice).where(Invoice.id == invoice_uuid)
            )
            invoice = result.scalar_one_or_none()
            
            if invoice and (invoice.ozow_payment_request_id or invoice.ozow_transaction_id):
                # Prefer payment_request_id if available, fallback to transaction_id
                actual_transaction_id = invoice.ozow_payment_request_id or invoice.ozow_transaction_id
                print(f"🔍 Converted invoice ID {transaction_id} to Ozow transaction ID: {actual_transaction_id}")
            elif invoice:
                raise HTTPException(status_code=400, detail="Invoice found but no Ozow transaction ID associated")
            else:
                raise HTTPException(status_code=404, detail="Invoice not found")
                
        except ValueError:
            # Not a UUID, assume it's already an Ozow transaction ID
            print(f"🔍 Using provided transaction ID directly: {transaction_id}")
        
        # Get transaction status from OZOW using the actual transaction ID
        transaction_status = await ozow_service.get_transaction_status(db, actual_transaction_id)
        
        # Process the status and update database
        result = await ozow_service.process_transaction_status(db, actual_transaction_id, transaction_status)
        
        return {
            "transaction_id": actual_transaction_id,
            "status": transaction_status.get("status"),
            "processed": result["processed"],
            "message": result["message"],
            "invoice_id": result.get("invoice_id"),
            "credits_added": result.get("credits_added")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transaction processing failed: {str(e)}")


@router.get("/verify-by-payment-request/{payment_request_id}", response_model=PaymentRequestVerificationResponse)
async def verify_payment_by_request_id(
    payment_request_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Verify payment status using payment request ID, check with Ozow, and update invoice if Complete"""
    
    ozow_service = OzowService()
    
    try:
        # Step 1: Find invoice by payment_request_id (first try as payment request ID, then as invoice ID)
        invoice = None
        
        # First, try to find by ozow_payment_request_id
        result = await db.execute(
            select(Invoice).where(Invoice.ozow_payment_request_id == payment_request_id)
        )
        invoice = result.scalar_one_or_none()
        
        # If not found, check if it's a UUID (invoice ID)
        if not invoice:
            try:
                from uuid import UUID
                invoice_uuid = UUID(payment_request_id)
                
                # Look up by invoice ID
                result = await db.execute(
                    select(Invoice).where(Invoice.id == invoice_uuid)
                )
                invoice = result.scalar_one_or_none()
                
                if invoice:
                    print(f"🔍 Found invoice by ID: {payment_request_id}")
                        
            except ValueError:
                # Not a UUID, continue
                pass
        else:
            print(f"🔍 Found invoice by payment request ID: {payment_request_id}")
        
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found for the given payment request ID")
        
        print("###############START_VERIFY###################")
        # Step 2: Use ozow_transaction_id to get status from Ozow
        ozow_transaction_id = invoice.ozow_transaction_id
        if not ozow_transaction_id:
            raise HTTPException(status_code=400, detail="Invoice found but no Ozow transaction ID available")
        
        print(f"🔍 Using Ozow transaction ID for API call: {ozow_transaction_id}")
        
        # Step 3: Get transaction status from Ozow
        transaction_status = await ozow_service.get_transaction_status(db, ozow_transaction_id)
        
        print(f"🔍 Ozow transaction status: {transaction_status}")
        
        # Step 4: Check if status is Complete and update invoice
        status = transaction_status.get("status", "").lower()
        invoice_updated = False
        
        if status == "complete" and invoice.status != "paid":
            print(f"🔍 Payment is complete, updating invoice {invoice.id}")
            
            # Process successful payment
            await ozow_service._process_successful_payment(db, invoice, None)
            await db.commit()
            await db.refresh(invoice)
            
            invoice_updated = True
            print(f"✅ Invoice {invoice.id} updated to paid status")
        print("###############END_VERIFY###################")

        return {
            "payment_request_id": payment_request_id,
            "invoice_id": str(invoice.id),
            "invoice_number": invoice.invoice_number,
            "invoice_status": invoice.status,
            "verification_result": {
                "ozow_transaction_id": ozow_transaction_id,
                "ozow_status": status,
                "transaction_data": transaction_status,
                "invoice_updated": invoice_updated
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payment verification failed: {str(e)}")


@router.post("/process-by-payment-request/{payment_request_id}", response_model=PaymentRequestProcessResponse)
async def process_payment_by_request_id_with_payload(
    payment_request_id: str,
    payment_data: OzowPaymentDataRequest,
    db: AsyncSession = Depends(get_db)
):
    """Process payment status using Ozow payment request ID with payment data payload"""
    
    ozow_service = OzowService()
    
    try:
        print(f"🔍 Processing payment with payload for payment_request_id: {payment_request_id}")
        print(f"🔍 Payment data: {payment_data.dict()}")
        
        # Convert Pydantic model to dict for easier access
        payment_dict = payment_data.dict()
        
        # Find invoice by payment request ID
        invoice = None
        actual_payment_request_id = payment_request_id
        
        # First, try to find by payment request ID
        result = await db.execute(
            select(Invoice).where(Invoice.ozow_payment_request_id == payment_request_id)
        )
        invoice = result.scalar_one_or_none()
        
        # If not found, check if it's a UUID (invoice ID)
        if not invoice:
            try:
                from uuid import UUID
                invoice_uuid = UUID(payment_request_id)
                
                # Look up by invoice ID
                result = await db.execute(
                    select(Invoice).where(Invoice.id == invoice_uuid)
                )
                invoice = result.scalar_one_or_none()
                
                if invoice:
                    # Use the actual payment request ID from the invoice
                    if invoice.ozow_payment_request_id:
                        actual_payment_request_id = invoice.ozow_payment_request_id
                        print(f"🔍 Converted invoice ID {payment_request_id} to payment request ID: {actual_payment_request_id}")
                    elif invoice.ozow_transaction_id:
                        actual_payment_request_id = invoice.ozow_transaction_id
                        print(f"🔍 Using transaction ID as fallback: {actual_payment_request_id}")
                    else:
                        raise HTTPException(status_code=400, detail="Invoice found but no Ozow payment identifiers available")
                        
            except ValueError:
                # Not a UUID, continue with original logic
                pass
        
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found for the given payment request ID or invoice ID")
        
        print(f"🔍 Found invoice {invoice.id} using identifier: {payment_request_id}")
        
        # Extract payment status from the payload
        transaction_id = payment_dict.get("TransactionId", "")
        transaction_reference = payment_dict.get("TransactionReference", "")
        amount = float(payment_dict.get("Amount", "0"))
        status = payment_dict.get("Status", "")
        currency_code = payment_dict.get("CurrencyCode", "")
        is_test = str(payment_dict.get("IsTest", "")).lower()
        received_hash = payment_dict.get("Hash", "")
        sub_status = payment_dict.get("SubStatus", "")
        masked_account_number = payment_dict.get("MaskedAccountNumber", "")
        bank_name = payment_dict.get("BankName", "")
        site_code = payment_dict.get("SiteCode", "")
        
        print(f"🔍 Extracted payment details:")
        print(f"   TransactionId: {transaction_id}")
        print(f"   Status: {status}")
        print(f"   Amount: {amount}")
        print(f"   BankName: {bank_name}")
        
        # Verify hash if provided
        if received_hash:
            from app.core.config import settings
            private_key = settings.OZOW_PRIVATE_KEY
            
            # Build hash string for verification
            input_string = "{}{}{}{}{}{}{}{}{}{}{}{}{}{}".format(
                site_code,
                transaction_id,
                transaction_reference,
                "{:.2f}".format(amount),
                status,
                payment_dict.get("Optional1", ""),
                payment_dict.get("Optional2", ""),
                payment_dict.get("Optional3", ""),
                payment_dict.get("Optional4", ""),
                payment_dict.get("Optional5", ""),
                currency_code,
                is_test,
                payment_dict.get("StatusMessage", ""),
                private_key
            )
            
            input_string = input_string.lower()
            
            # Generate hash
            import hashlib
            sha = hashlib.sha512()
            sha.update(input_string.encode())
            calculated_hash = sha.hexdigest()
            
            # Remove leading zeros for comparison
            rx_hash = received_hash.lstrip('0')
            calculated_hash_clean = calculated_hash.lstrip('0')
            
            if calculated_hash_clean != rx_hash:
                print("❌ HASH_MISMATCH")
                raise HTTPException(status_code=400, detail="Hash verification failed")
            
            print("✅ HASH_MATCH")
        
        # Create payment notification record
        notification = PaymentNotification(
            invoice_id=invoice.id,
            provider="ozow",
            transaction_id=transaction_id,
            status=status,
            amount=Decimal(str(amount)),
            reference=transaction_reference,
            raw_data=json.dumps(payment_dict),
            processed=False
        )
        db.add(notification)
        
        # Process based on status
        if status.lower() == "complete":
            print(f"🔍 Payment complete, processing invoice {invoice.id}")
            
            if invoice.status != "paid":
                # Process successful payment
                await ozow_service._process_successful_payment(db, invoice, notification)
                notification.processed = True
                notification.processed_at = datetime.utcnow()
                
                await db.commit()
                await db.refresh(invoice)
                
                print(f"✅ Invoice {invoice.id} updated to paid status")
                
                return {
                    "payment_request_id": actual_payment_request_id,
                    "invoice_id": str(invoice.id),
                    "invoice_number": invoice.invoice_number,
                    "status": "complete",
                    "processed": True,
                    "message": "Payment processed successfully",
                    "credits_added": invoice.credits_amount
                }
            else:
                print(f"ℹ️ Invoice {invoice.id} already paid")
                notification.processed = True
                notification.processed_at = datetime.utcnow()
                await db.commit()
                
                return {
                    "payment_request_id": actual_payment_request_id,
                    "invoice_id": str(invoice.id),
                    "invoice_number": invoice.invoice_number,
                    "status": "complete",
                    "processed": True,
                    "message": "Payment already processed"
                }
                
        elif status.lower() in ["cancelled", "failed", "error", "abandoned"]:
            print(f"🔍 Payment {status.lower()}, updating invoice {invoice.id}")
            
            # Update invoice to failed/cancelled
            invoice.status = "failed"
            invoice.cancelled_at = datetime.utcnow()
            invoice.notes = f"Payment {status.lower()}: {payment_dict.get('StatusMessage', '')}"
            
            notification.processed = True
            notification.processed_at = datetime.utcnow()
            
            await db.commit()
            
            return {
                "payment_request_id": actual_payment_request_id,
                "invoice_id": str(invoice.id),
                "invoice_number": invoice.invoice_number,
                "status": status.lower(),
                "processed": True,
                "message": f"Payment {status.lower()} processed"
            }
            
        else:
            # Keep as pending or unknown status
            invoice.notes = f"Payment status: {status} - {payment_dict.get('StatusMessage', '')}"
            await db.commit()
            
            return {
                "payment_request_id": actual_payment_request_id,
                "invoice_id": str(invoice.id),
                "invoice_number": invoice.invoice_number,
                "status": status.lower(),
                "processed": False,
                "message": f"Payment status: {status}"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Payment processing failed: {str(e)}")


@router.get("/process-by-payment-request-get/{payment_request_id}", response_model=PaymentRequestProcessResponse)
async def process_payment_by_request_id_get(
    payment_request_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Process payment status using Ozow payment request ID or invoice ID (GET method for backward compatibility)"""
    
    ozow_service = OzowService()
    
    try:
        invoice = None
        actual_payment_request_id = payment_request_id
        
        # First, try to find by payment request ID
        result = await db.execute(
            select(Invoice).where(Invoice.ozow_payment_request_id == payment_request_id)
        )
        invoice = result.scalar_one_or_none()
        
        # If not found, check if it's a UUID (invoice ID)
        if not invoice:
            try:
                from uuid import UUID
                invoice_uuid = UUID(payment_request_id)
                
                # Look up by invoice ID
                result = await db.execute(
                    select(Invoice).where(Invoice.id == invoice_uuid)
                )
                invoice = result.scalar_one_or_none()
                
                if invoice:
                    # Use the actual payment request ID from the invoice
                    if invoice.ozow_payment_request_id:
                        actual_payment_request_id = invoice.ozow_payment_request_id
                        print(f"🔍 Converted invoice ID {payment_request_id} to payment request ID: {actual_payment_request_id}")
                    elif invoice.ozow_transaction_id:
                        actual_payment_request_id = invoice.ozow_transaction_id
                        print(f"🔍 Using transaction ID as fallback: {actual_payment_request_id}")
                    else:
                        raise HTTPException(status_code=400, detail="Invoice found but no Ozow payment identifiers available")
                        
            except ValueError:
                # Not a UUID, continue with original logic
                pass
        
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found for the given payment request ID or invoice ID")
        
        print(f"🔍 Found invoice {invoice.id} using identifier: {payment_request_id}")
        
        # Get transaction status from OZOW using the actual payment request ID
        transaction_status = await ozow_service.get_transaction_status(db, actual_payment_request_id)
        
        # Process the status and update database
        result = await ozow_service.process_transaction_status(db, actual_payment_request_id, transaction_status)
        
        return {
            "payment_request_id": actual_payment_request_id,
            "invoice_id": str(invoice.id),
            "invoice_number": invoice.invoice_number,
            "status": transaction_status.get("status"),
            "processed": result["processed"],
            "message": result["message"],
            "credits_added": result.get("credits_added")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payment processing failed: {str(e)}")


@router.get("/invoice-by-payment-request/{payment_request_id}", response_model=InvoiceResponse)
async def get_invoice_by_payment_request_id(
    payment_request_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get invoice details using Ozow payment request ID"""
    
    try:
        # Find invoice by payment request ID
        result = await db.execute(
            select(Invoice).where(Invoice.ozow_payment_request_id == payment_request_id)
        )
        invoice = result.scalar_one_or_none()
        
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found for the given payment request ID")
        
        return invoice
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve invoice: {str(e)}")


@router.get("/debug/invoice-details/{invoice_id}")
async def debug_invoice_details(
    invoice_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Debug endpoint to check invoice details"""
    
    try:
        # Try to parse as UUID
        from uuid import UUID
        invoice_uuid = UUID(invoice_id)
        
        # Look up the invoice
        result = await db.execute(
            select(Invoice).where(Invoice.id == invoice_uuid)
        )
        invoice = result.scalar_one_or_none()
        
        if not invoice:
            return {"error": "Invoice not found", "invoice_id": invoice_id}
        
        return {
            "invoice_id": str(invoice.id),
            "invoice_number": invoice.invoice_number,
            "status": invoice.status,
            "ozow_transaction_id": invoice.ozow_transaction_id,
            "ozow_payment_request_id": invoice.ozow_payment_request_id,
            "ozow_reference": invoice.ozow_reference,
            "ozow_payment_url": invoice.ozow_payment_url,
            "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
            "paid_at": invoice.paid_at.isoformat() if invoice.paid_at else None
        }
        
    except ValueError:
        return {"error": "Invalid UUID format", "invoice_id": invoice_id}
    except Exception as e:
        return {"error": str(e), "invoice_id": invoice_id}


@router.post("/ozow/process-payment-status", response_model=OzowPaymentStatusResponse)
async def process_ozow_payment_status(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Process Ozow payment status with hash verification"""
    
    ozow_service = OzowService()
    
    try:
        # Get form data from request
        form_data = await request.form()
        
        # Extract required fields
        site_code = form_data.get("SiteCode", "")
        transaction_id = form_data.get("TransactionId", "")
        transaction_reference = form_data.get("TransactionReference", "")
        amount = float(form_data.get("Amount", "0"))
        status = form_data.get("Status", "")
        currency_code = form_data.get("CurrencyCode", "")
        is_test = str(form_data.get("IsTest", "")).lower()
        status_message = form_data.get("StatusMessage", "")
        received_hash = form_data.get("Hash", "")
        bank_name = form_data.get("BankName", "")
        
        # Extract optional fields
        optional1 = form_data.get("Optional1", "")
        optional2 = form_data.get("Optional2", "")
        optional3 = form_data.get("Optional3", "")
        optional4 = form_data.get("Optional4", "")
        optional5 = form_data.get("Optional5", "")
        
        print(f"🔍 Processing Ozow payment status:")
        print(f"   SiteCode: {site_code}")
        print(f"   TransactionId: {transaction_id}")
        print(f"   TransactionReference: {transaction_reference}")
        print(f"   Amount: {amount}")
        print(f"   Status: {status}")
        print(f"   IsTest: {is_test}")
        print(f"   StatusMessage: {status_message}")
        print(f"   ReceivedHash: {received_hash}")
        
        # Step 1: Verify hash
        private_key = settings.OZOW_PRIVATE_KEY
        
        # Build hash string according to Ozow specification
        input_string = "{}{}{}{}{}{}{}{}{}{}{}{}{}{}".format(
            site_code,
            transaction_id,
            transaction_reference,
            "{:.2f}".format(amount),
            status,
            optional1,
            optional2,
            optional3,
            optional4,
            optional5,
            currency_code,
            is_test,
            status_message,
            private_key
        )
        
        input_string = input_string.lower()
        print(f"🔍 Hash input string: {input_string}")
        
        # Generate hash
        import hashlib
        sha = hashlib.sha512()
        sha.update(input_string.encode())
        calculated_hash = sha.hexdigest()
        
        # Remove leading zeros for comparison
        rx_hash = received_hash.lstrip('0')
        calculated_hash_clean = calculated_hash.lstrip('0')
        
        print(f"🔍 Received hash: {rx_hash}")
        print(f"🔍 Calculated hash: {calculated_hash_clean}")
        
        # Verify hash
        if calculated_hash_clean != rx_hash:
            print("❌ HASH_MISMATCH")
            return {
                "status": "error",
                "message": "Hash verification failed",
                "transaction_id": transaction_id
            }
        
        print("✅ HASH_MATCH")
        
        # Step 2: Find invoice by transaction ID or reference
        result = await db.execute(
            select(Invoice).where(
                (Invoice.ozow_transaction_id == transaction_id) |
                (Invoice.ozow_payment_request_id == transaction_id) |
                (Invoice.ozow_reference == transaction_reference)
            )
        )
        invoice = result.scalar_one_or_none()
        
        if not invoice:
            print(f"❌ Invoice not found for transaction ID: {transaction_id}")
            return {
                "status": "error",
                "message": "Invoice not found",
                "transaction_id": transaction_id
            }
        
        print(f"✅ Found invoice: {invoice.id} ({invoice.invoice_number})")
        
        # Step 3: Create payment notification record
        notification = PaymentNotification(
            invoice_id=invoice.id,
            provider="ozow",
            transaction_id=transaction_id,
            status=status,
            amount=Decimal(str(amount)),
            reference=transaction_reference,
            raw_data=json.dumps(dict(form_data)),
            processed=False
        )
        db.add(notification)
        
        # Step 4: Process based on status
        if status.lower() == "complete":
            print(f"🔍 Payment complete, processing invoice {invoice.id}")
            
            if invoice.status != "paid":
                # Process successful payment
                await ozow_service._process_successful_payment(db, invoice, notification)
                notification.processed = True
                notification.processed_at = datetime.utcnow()
                
                await db.commit()
                await db.refresh(invoice)
                
                print(f"✅ Invoice {invoice.id} updated to paid status")
                
                return {
                    "status": "success",
                    "message": "Payment processed successfully",
                    "transaction_id": transaction_id,
                    "invoice_id": str(invoice.id),
                    "invoice_status": "paid",
                    "credits_added": invoice.credits_amount
                }
            else:
                print(f"ℹ️ Invoice {invoice.id} already paid")
                notification.processed = True
                notification.processed_at = datetime.utcnow()
                await db.commit()
                
                return {
                    "status": "success",
                    "message": "Payment already processed",
                    "transaction_id": transaction_id,
                    "invoice_id": str(invoice.id),
                    "invoice_status": "paid"
                }
                
        elif status.lower() in ["cancelled", "failed", "error", "abandoned"]:
            print(f"🔍 Payment {status.lower()}, updating invoice {invoice.id}")
            
            # Update invoice to failed/cancelled
            invoice.status = "failed"
            invoice.cancelled_at = datetime.utcnow()
            invoice.notes = f"Payment {status.lower()}: {status_message}"
            
            notification.processed = True
            notification.processed_at = datetime.utcnow()
            
            await db.commit()
            
            return {
                "status": "success",
                "message": f"Payment {status.lower()} processed",
                "transaction_id": transaction_id,
                "invoice_id": str(invoice.id),
                "invoice_status": "failed"
            }
            
        elif status.lower() in ["pending", "pendinginvestigation"]:
            print(f"🔍 Payment {status.lower()}, keeping invoice pending")
            
            # Keep as pending
            invoice.status = "pending"
            invoice.notes = f"Payment {status.lower()}: {status_message}"
            
            # Don't mark notification as processed for pending status
            await db.commit()
            
            return {
                "status": "success",
                "message": f"Payment {status.lower()} - awaiting confirmation",
                "transaction_id": transaction_id,
                "invoice_id": str(invoice.id),
                "invoice_status": "pending"
            }
            
        else:
            print(f"🔍 Unknown payment status: {status}")
            
            # Unknown status
            invoice.notes = f"Unknown payment status: {status} - {status_message}"
            await db.commit()
            
            return {
                "status": "warning",
                "message": f"Unknown payment status: {status}",
                "transaction_id": transaction_id,
                "invoice_id": str(invoice.id),
                "invoice_status": invoice.status
            }
        
    except Exception as e:
        print(f"❌ Error processing Ozow payment status: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            "status": "error",
            "message": f"Processing failed: {str(e)}",
            "transaction_id": form_data.get("TransactionId", "") if 'form_data' in locals() else ""
        }