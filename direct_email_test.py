#!/usr/bin/env python3
"""
Direct test of email sending functionality bypassing the API endpoint
"""

import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, '/home/melcy/Programming/kiro/paniq_system')

from app.services.otp_delivery import OTPDeliveryService

async def send_direct_email():
    """Send password reset email directly using the service"""
    
    try:
        # Initialize the OTP delivery service
        otp_service = OTPDeliveryService()
        
        # Generate a simple OTP
        otp = "123456"
        email = "darlingtonmuzari@gmail.com"
        
        print(f"Attempting to send password reset email to {email}...")
        print(f"OTP: {otp}")
        print("-" * 50)
        
        # Send password reset email directly
        success = await otp_service.send_password_reset_email(email, otp)
        
        if success:
            print("✅ SUCCESS: Password reset email sent!")
            print(f"📧 Email sent to {email}")
            print(f"🔢 OTP: {otp}")
        else:
            print("❌ FAILED: Could not send password reset email")
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(send_direct_email())