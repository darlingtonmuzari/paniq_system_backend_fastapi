"""
OZOW Payment Service
"""
import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Optional, Tuple, List
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.payment import Invoice, CreditTier, PaymentNotification
from app.models.security_firm import SecurityFirm
from app.models.subscription import CreditTransaction


class OzowService:
    """OZOW payment integration service"""
    
    def __init__(self): 
        self.base_url = settings.OZOW_BASE_URL
        self.site_code = settings.OZOW_SITE_CODE
        self.private_key = settings.OZOW_PRIVATE_KEY
        self.api_key = settings.OZOW_API_KEY
        self.is_test = settings.OZOW_IS_TEST
        
        # URLs
        self.post_url = settings.OZOW_POST_URL if self.is_test else settings.OZOW_POST_LIVE_URL
        self.verify_url = settings.OZOW_VERIFY_TRANS_URL if self.is_test else settings.OZOW_VERIFY_TRANS_LIVE_URL
        
        # Callback URLs
        self.success_url = settings.OZOW_SUCCESS_URL
        self.cancel_url = settings.OZOW_CANCEL_URL
        self.error_url = settings.OZOW_ERROR_URL
        self.notify_url = settings.OZOW_NOTIFY_URL
        




    async def get_credit_price(self, db: AsyncSession, credits: int) -> Decimal:
        """Get price for specified number of credits"""
        result = await db.execute(
            select(CreditTier)
            .where(
                CreditTier.min_credits <= credits,
                CreditTier.max_credits >= credits,
                CreditTier.is_active == True
            )
        )
        tier = result.scalar_one_or_none()
        
        if not tier:
            raise ValueError(f"No pricing tier found for {credits} credits")
        
        return tier.price

    async def get_credits_for_amount(self, db: AsyncSession, amount: Decimal) -> Tuple[int, Decimal]:
        """Calculate credits based on amount using tier ranges"""
        
        # Get all active tiers ordered by price
        result = await db.execute(
            select(CreditTier)
            .where(CreditTier.is_active == True)
            .order_by(CreditTier.price)
        )
        tiers = result.scalars().all()
        
        if not tiers:
            raise ValueError("No credit tiers available")
        
        # Find the appropriate tier based on amount
        selected_tier = None
        
        # First, try to find exact price match
        for tier in tiers:
            if tier.price == amount:
                selected_tier = tier
                break
        
        # If no exact match, find the tier where amount falls within the price range
        if not selected_tier:
            # Calculate credits based on the tier structure
            # For amounts between tiers, use proportional calculation
            for i, tier in enumerate(tiers):
                if amount <= tier.price:
                    selected_tier = tier
                    break
            
            # If amount is higher than all tiers, use the highest tier
            if not selected_tier:
                selected_tier = tiers[-1]
        
        if not selected_tier:
            raise ValueError(f"Cannot calculate credits for amount R{amount}")
        
        # Calculate credits based on the tier
        # If exact price match, use max credits for that tier
        if selected_tier.price == amount:
            credits = selected_tier.max_credits
        else:
            # For non-exact amounts, calculate proportionally within the tier range
            # Use the max credits for the selected tier as base
            credits = selected_tier.max_credits
        
        return credits, amount  # Return the actual amount, not tier price

    async def get_available_amounts(self, db: AsyncSession) -> List[Decimal]:
        """Get list of available amounts"""
        result = await db.execute(
            select(CreditTier.price)
            .where(CreditTier.is_active == True)
            .order_by(CreditTier.price)
        )
        return [row[0] for row in result.fetchall()]

    async def create_invoice(
        self, 
        db: AsyncSession, 
        firm_id: uuid.UUID, 
        amount: Decimal
    ) -> Tuple[Invoice, int]:
        """Create an invoice for credit purchase based on amount"""
        
        # Validate minimum amount
        if amount <= 0:
            raise ValueError("Amount must be greater than 0")
        
        # Calculate credits for specified amount
        final_credits, final_amount = await self.get_credits_for_amount(db, amount)
        
        # Generate invoice number
        invoice_number = f"INV-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
        
        # Create invoice
        invoice = Invoice(
            firm_id=firm_id,
            invoice_number=invoice_number,
            credits_amount=final_credits,
            total_amount=final_amount,  # Use the actual amount provided
            status="pending",
            payment_method="ozow",
            expires_at=datetime.utcnow() + timedelta(hours=24),  # 24 hour expiry
            description=f"Purchase of {final_credits} credits for R{final_amount}"
        )
        
        db.add(invoice)
        await db.commit()
        await db.refresh(invoice)
        
        return invoice, final_credits

    def _generate_hash_check(self, payment_data: Dict) -> str:
        """Generate OZOW hash check using the exact algorithm from working example"""
        # OZOW hash generation follows a specific order:
        # siteCode + countryCode + currencyCode + amount + transactionReference + bankReference + 
        # cancelUrl + errorUrl + successUrl + notifyUrl + isTest + privateKey
        
        # Use the exact same logic as ozow.py - convert boolean to string then lowercase
        is_test_value = payment_data.get("isTest")
        if isinstance(is_test_value, bool):
            # Convert boolean False to "false", True to "true" (matching ozow.py logic)
            is_test_str = str(is_test_value).lower()
        else:
            is_test_str = str(is_test_value).lower()
        
        input_string = (
            str(payment_data.get("siteCode", "")) +
            str(payment_data.get("countryCode", "")) +
            str(payment_data.get("currencyCode", "")) +
            str(payment_data.get("amount", "")) +
            str(payment_data.get("transactionReference", "")) +
            str(payment_data.get("bankReference", "")) +
            str(payment_data.get("cancelUrl", "")) +
            str(payment_data.get("errorUrl", "")) +
            str(payment_data.get("successUrl", "")) +
            str(payment_data.get("notifyUrl", "")) +
            is_test_str +
            self.private_key
        )
        
        # Convert to lowercase as per OZOW specification
        input_string = input_string.lower()
        print("############################################")
        print(f"Hash input string: {input_string}")
        
        # Generate SHA512 hash - exact method from working example
        sha = hashlib.sha512()
        sha.update(input_string.encode())
        hash_result = sha.hexdigest()
        
        print(f"Generated hash: {hash_result}")
        print("############################################")
        
        return hash_result

    async def create_payment_request(
        self, 
        db: AsyncSession, 
        invoice: Invoice
    ) -> Dict:
        """Create OZOW payment request and return raw OZOW response plus processed data"""
        
        # Get firm details
        result = await db.execute(
            select(SecurityFirm).where(SecurityFirm.id == invoice.firm_id)
        )
        firm = result.scalar_one()
        
        # Prepare payment data
        transaction_reference = f"TXN-{invoice.invoice_number}"
        
        # Create shorter bank reference (max 20 chars) - use last 8 chars of invoice number
        bank_reference = invoice.invoice_number[-20:] if len(invoice.invoice_number) <= 20 else f"INV-{invoice.invoice_number.split('-')[-1]}"
        
        # OZOW API uses camelCase field names - exact format from ozow.py
        payment_data = {
            "countryCode": "ZA",
            "amount": str(invoice.total_amount),
            "transactionReference": transaction_reference,
            "bankReference": bank_reference,
            "cancelUrl": self.cancel_url,
            "currencyCode": "ZAR",
            "errorUrl": self.error_url,
            "isTest": self.is_test,  # Keep as boolean for hash generation
            "notifyUrl": self.notify_url,
            "siteCode": self.site_code,
            "successUrl": self.success_url
        }
        
        # Generate hash check
        payment_data["hashCheck"] = self._generate_hash_check(payment_data)
        
        try:
            print(f"OZOW Request URL: {self.post_url}")
            print(f"OZOW Request Data: {payment_data}")
            

            async with httpx.AsyncClient(verify=False) as client:
                # Convert boolean to string for JSON - matching ozow.py exactly
                json_data = payment_data.copy()
                json_data["isTest"] = "true" if self.is_test else "false"
                
                # Use live API URL consistently
                api_url = "https://api.ozow.com/postpaymentrequest"
                
                print(f"🔍 OZOW REQUEST (matching ozow.py):")
                print(f"   URL: {api_url}")
                print(f"   Data: {json_data}")
                
                # Use JSON format as per OZOW specification - matching ozow.py exactly
                response = await client.post(
                    api_url,
                    json=json_data,
                    headers={
                        "Accept": "application/json",
                        "ApiKey": self.api_key,
                        "Content-Type": "application/json"
                    }
                )
                
                print(f"🔍 OZOW RESPONSE DETAILS:")
                print(f"   Status Code: {response.status_code}")
                print(f"   Headers: {dict(response.headers)}")
                print(f"   Raw Response: {response.text}")
                print(f"   Content Type: {response.headers.get('content-type', 'unknown')}")
                print(f"   Content Length: {response.headers.get('content-length', 'unknown')}")
                
                # Try to parse JSON response for more details
                try:
                    if response.headers.get('content-type', '').startswith('application/json'):
                        response_data = response.json()
                        print(f"   Parsed JSON: {json.dumps(response_data, indent=2)}")
                    else:
                        print(f"   Non-JSON Response: {response.text}")
                except Exception as json_error:
                    print(f"   JSON Parse Error: {str(json_error)}")
                    print(f"   Raw Text: {response.text}")
                
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                        print(f"   Success Response Data: {response_data}")
                        
                        # Handle the actual OZOW response format as shown in ozow.py
                        payment_request_id = response_data.get("paymentRequestId")
                        payment_url = response_data.get("url")
                        error_message = response_data.get("errorMessage")
                        
                        if payment_request_id and payment_url and not error_message:
                            print(f"   ✅ OZOW Success: URL={payment_url}, PaymentRequestId={payment_request_id}")
                            
                            # Update invoice with OZOW details
                            invoice.ozow_transaction_id = payment_request_id
                            invoice.ozow_payment_request_id = payment_request_id  # Store paymentRequestId
                            invoice.ozow_reference = transaction_reference
                            invoice.ozow_payment_url = payment_url
                            
                            await db.commit()
                            
                            return {
                                "payment_request_id": payment_request_id,
                                "url": payment_url,
                                "error": None,
                                "raw_ozow_response": response_data,
                                "ozow_success": True
                            }
                        else:
                            # Handle error case where errorMessage is present
                            error_msg = error_message or "Unknown payment error occurred"
                            
                            print(f"   ❌ OZOW API Error: {error_msg}")
                            print(f"   Full Error Response: {response_data}")
                            
                            # Update invoice status to failed
                            invoice.status = "failed"
                            invoice.notes = f"OZOW API error: {error_msg}"
                            await db.commit()
                            
                            return {
                                "payment_request_id": None,
                                "url": None,
                                "error": error_msg,
                                "raw_ozow_response": response_data,
                                "ozow_success": False
                            }
                    except Exception as parse_error:
                        print(f"   ❌ Error parsing 200 response: {str(parse_error)}")
                        error_message = f"HTTP 200 but invalid JSON: {response.text}"
                        
                        # Update invoice status to failed
                        invoice.status = "failed"
                        invoice.notes = f"Payment request failed: {error_message}"
                        await db.commit()
                        
                        return {
                            "payment_request_id": None,
                            "url": None,
                            "error": error_message,
                            "raw_ozow_response": response.text,
                            "ozow_success": False
                        }
                else:
                    print(f"   ❌ HTTP Error Response:")
                    print(f"      Status: {response.status_code}")
                    print(f"      Reason: {response.reason_phrase if hasattr(response, 'reason_phrase') else 'Unknown'}")
                    print(f"      Headers: {dict(response.headers)}")
                    print(f"      Body: {response.text}")
                    
                    # Log the 500 error but don't fall back to mock mode
                    
                    # Try to extract more error details from non-200 responses
                    error_details = []
                    error_details.append(f"HTTP {response.status_code}")
                    
                    if response.text:
                        error_details.append(response.text)
                    
                    if response.headers.get('cf-ray'):
                        error_details.append(f"CloudFlare Ray: {response.headers.get('cf-ray')}")
                    
                    if response.headers.get('server'):
                        error_details.append(f"Server: {response.headers.get('server')}")
                    
                    error_message = " - ".join(error_details)
                    
                    print(f"   Compiled Error Message: {error_message}")
                    
                    # Update invoice status to failed
                    invoice.status = "failed"
                    invoice.notes = f"Payment request failed: {error_message}"
                    await db.commit()
                    
                    return {
                        "payment_request_id": None,
                        "url": None,
                        "error": error_message,
                        "raw_ozow_response": response.text,
                        "ozow_success": False,
                        "http_status": response.status_code
                    }
                    
        except Exception as e:
            print(f"🚨 EXCEPTION IN OZOW PAYMENT REQUEST:")
            print(f"   Exception Type: {type(e).__name__}")
            print(f"   Exception Message: {str(e)}")
            print(f"   Exception Args: {e.args}")
            
            # Additional details for specific exception types
            if hasattr(e, 'response'):
                print(f"   HTTP Response Status: {getattr(e.response, 'status_code', 'unknown')}")
                print(f"   HTTP Response Text: {getattr(e.response, 'text', 'unknown')}")
            
            if hasattr(e, 'request'):
                print(f"   HTTP Request URL: {getattr(e.request, 'url', 'unknown')}")
                print(f"   HTTP Request Method: {getattr(e.request, 'method', 'unknown')}")
            
            # Import traceback for full stack trace
            import traceback
            print(f"   Full Traceback:")
            traceback.print_exc()
            
            error_message = f"Payment request failed: {str(e)}"
            
            # Update invoice status to failed
            invoice.status = "failed"
            invoice.notes = error_message
            await db.commit()
            
            return {
                "payment_request_id": None,
                "url": None,
                "error": error_message,
                "raw_ozow_response": None,
                "ozow_success": False,
                "exception": str(e)
            }



    async def verify_payment(
        self, 
        db: AsyncSession, 
        transaction_id: str
    ) -> Dict:
        """Verify payment status with OZOW using GetTransaction endpoint"""
        
        params = {
            "siteCode": self.site_code,
            "transactionId": transaction_id
        }
        
        headers = {
            "ApiKey": self.api_key
        }
        
        print(f"🔍 OZOW VERIFY REQUEST:")
        print(f"   URL: {self.verify_url}/GetTransaction")
        print(f"   Params: {params}")
        print(f"   Headers: {headers}")
        
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(
                "https://api.ozow.com/GetTransaction",
                params=params,
                headers=headers
            )
            
            print(f"   Response Status: {response.status_code}")
            print(f"   Response Body: {response.text}")
            
            if response.status_code == 200:
                print(response.text)

                return response.json()
            else:
                print(response.text)
                raise Exception(f"Verification failed: {response.status_code} - {response.text}")

    async def process_webhook(
        self, 
        db: AsyncSession, 
        webhook_data: Dict
    ) -> bool:
        """Process OZOW webhook notification"""
        
        try:
            # Extract key fields
            transaction_id = webhook_data.get("TransactionId")
            status = webhook_data.get("Status")
            amount = Decimal(str(webhook_data.get("Amount", "0")))
            reference = webhook_data.get("TransactionReference")
            
            # Find invoice by OZOW transaction ID, payment request ID, or reference
            result = await db.execute(
                select(Invoice).where(
                    (Invoice.ozow_transaction_id == transaction_id) |
                    (Invoice.ozow_payment_request_id == transaction_id) |
                    (Invoice.ozow_reference == reference)
                )
            )
            invoice = result.scalar_one_or_none()
            
            if not invoice:
                # Log unknown transaction
                notification = PaymentNotification(
                    invoice_id=None,
                    provider="ozow",
                    transaction_id=transaction_id,
                    status=status,
                    amount=amount,
                    reference=reference,
                    raw_data=json.dumps(webhook_data),
                    processed=False
                )
                db.add(notification)
                await db.commit()
                return False
            
            # Create notification record
            notification = PaymentNotification(
                invoice_id=invoice.id,
                provider="ozow",
                transaction_id=transaction_id,
                status=status,
                amount=amount,
                reference=reference,
                raw_data=json.dumps(webhook_data),
                processed=False
            )
            db.add(notification)
            
            # Process successful payment
            if status.lower() in ["complete", "successful", "paid"]:
                await self._process_successful_payment(db, invoice, notification)
            elif status.lower() in ["cancelled", "failed", "error"]:
                invoice.status = "failed"
                invoice.cancelled_at = datetime.utcnow()
                invoice.notes = f"Payment {status.lower()}: {webhook_data.get('StatusMessage', '')}"
            
            notification.processed = True
            notification.processed_at = datetime.utcnow()
            
            await db.commit()
            return True
            
        except Exception as e:
            # Log error but don't fail the webhook
            print(f"Webhook processing error: {str(e)}")
            return False

    async def _process_successful_payment(
        self, 
        db: AsyncSession, 
        invoice: Invoice, 
        notification: PaymentNotification
    ):
        """Process successful payment - update invoice and add credits"""
        
        # Update invoice status
        invoice.status = "paid"
        invoice.paid_at = datetime.utcnow()
        
        # Add credits to firm
        result = await db.execute(
            select(SecurityFirm).where(SecurityFirm.id == invoice.firm_id)
        )
        firm = result.scalar_one()
        firm.credit_balance += invoice.credits_amount
        
        # Create credit transaction record
        credit_transaction = CreditTransaction(
            firm_id=invoice.firm_id,
            transaction_type="purchase",
            amount=invoice.credits_amount,
            description=f"Credit purchase via OZOW - Invoice {invoice.invoice_number}",
            reference_id=str(invoice.id)
        )
        db.add(credit_transaction)

    async def get_transaction_status(self, db: AsyncSession, transaction_id: str) -> Dict:
        """Get transaction status from OZOW GetTransaction API"""
        
        # Use live API URL
        url = "https://api.ozow.com/GetTransaction"
        
        params = {
            "siteCode": self.site_code,
            "transactionId": transaction_id
        }
        
        headers = {
            "ApiKey": self.api_key
        }
        
        try:
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.get(url, params=params, headers=headers)
                
                print(f"🔍 OZOW GetTransaction Response:")
                print(f"   URL: {url}")
                print(f"   Params: {params}")
                print(f"   Status Code: {response.status_code}")
                print(f"   Response: {response.text}")
                
                if response.status_code == 200:
                    return response.json()
                else:
                    raise Exception(f"OZOW API error: {response.status_code} - {response.text}")
                    
        except Exception as e:
            print(f"Error fetching transaction status: {str(e)}")
            raise

    async def process_transaction_status(self, db: AsyncSession, transaction_id: str, transaction_data: Dict) -> Dict:
        """Process transaction status and update database accordingly"""
        
        try:
            status = transaction_data.get("status", "").lower()
            amount = Decimal(str(transaction_data.get("amount", "0")))
            
            # Find invoice by OZOW transaction ID or payment request ID
            result = await db.execute(
                select(Invoice).where(
                    (Invoice.ozow_transaction_id == transaction_id) |
                    (Invoice.ozow_payment_request_id == transaction_id)
                )
            )
            invoice = result.scalar_one_or_none()
            
            if not invoice:
                return {
                    "processed": False,
                    "message": f"No invoice found for transaction ID: {transaction_id}"
                }
            
            # Create or update payment notification
            result = await db.execute(
                select(PaymentNotification).where(
                    PaymentNotification.transaction_id == transaction_id
                )
            )
            notification = result.scalar_one_or_none()
            
            if not notification:
                notification = PaymentNotification(
                    invoice_id=invoice.id,
                    provider="ozow",
                    transaction_id=transaction_id,
                    status=status,
                    amount=amount,
                    raw_data=json.dumps(transaction_data),
                    processed=False
                )
                db.add(notification)
            else:
                # Update existing notification
                notification.status = status
                notification.amount = amount
                notification.raw_data = json.dumps(transaction_data)
                notification.processed = False
            
            # Process based on status
            if status == "complete":
                # Payment was successful
                if invoice.status != "paid":
                    await self._process_successful_payment(db, invoice, notification)
                    await db.commit()
                    
                    return {
                        "processed": True,
                        "message": "Payment completed successfully",
                        "invoice_id": str(invoice.id),
                        "credits_added": invoice.credits_amount
                    }
                else:
                    return {
                        "processed": False,
                        "message": "Payment already processed",
                        "invoice_id": str(invoice.id)
                    }
                    
            elif status in ["cancelled", "error", "abandoned"]:
                # Payment failed/cancelled
                invoice.status = "failed"
                invoice.cancelled_at = datetime.utcnow()
                invoice.notes = f"Payment {status}: {transaction_data.get('statusMessage', '')}"
                
                notification.processed = True
                notification.processed_at = datetime.utcnow()
                
                await db.commit()
                
                return {
                    "processed": True,
                    "message": f"Payment {status}",
                    "invoice_id": str(invoice.id)
                }
                
            elif status in ["pendinginvestigation", "pending"]:
                # Payment pending
                invoice.status = "pending"
                invoice.notes = f"Payment {status}: Manual verification may be required"
                
                notification.processed = False  # Keep as unprocessed for pending
                
                await db.commit()
                
                return {
                    "processed": True,
                    "message": f"Payment {status} - awaiting confirmation",
                    "invoice_id": str(invoice.id)
                }
            
            else:
                # Unknown status
                invoice.notes = f"Unknown payment status: {status}"
                notification.processed = False
                
                await db.commit()
                
                return {
                    "processed": False,
                    "message": f"Unknown payment status: {status}",
                    "invoice_id": str(invoice.id)
                }
                
        except Exception as e:
            print(f"Error processing transaction status: {str(e)}")
            raise

    async def initialize_credit_tiers(self, db: AsyncSession):
        """Initialize default credit tiers"""
        
        # Check if tiers already exist
        result = await db.execute(select(CreditTier))
        existing_tiers = result.scalars().all()
        
        if existing_tiers:
            return  # Tiers already exist
        
        # Default credit tiers
        default_tiers = [
            {"min_credits": 0, "max_credits": 50, "price": Decimal("100.00")},
            {"min_credits": 51, "max_credits": 100, "price": Decimal("150.00")},
            {"min_credits": 101, "max_credits": 500, "price": Decimal("600.00")},
            {"min_credits": 501, "max_credits": 1000, "price": Decimal("1000.00")},
            {"min_credits": 1001, "max_credits": 5000, "price": Decimal("4500.00")},
            {"min_credits": 5001, "max_credits": 10000, "price": Decimal("8000.00")},
        ]
        
        for tier_data in default_tiers:
            tier = CreditTier(**tier_data)
            db.add(tier)
        
        await db.commit()