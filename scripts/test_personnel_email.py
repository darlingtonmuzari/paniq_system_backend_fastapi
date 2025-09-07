#!/usr/bin/env python3
"""
Test script for personnel credentials email functionality
"""
import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.otp_delivery import OTPDeliveryService

async def test_personnel_email(email: str):
    """Test sending personnel credentials email"""
    
    print("=" * 60)
    print("TESTING PERSONNEL CREDENTIALS EMAIL")
    print("=" * 60)
    
    # Create OTP delivery service
    email_service = OTPDeliveryService()
    
    # Test data
    first_name = "Mahobho"
    last_name = "Test"
    password = "TempPass123!"
    firm_name = "Test Security Firm"
    role = "firm_staff"
    
    print(f"Sending personnel credentials email to: {email}")
    print(f"Personnel: {first_name} {last_name}")
    print(f"Firm: {firm_name}")
    print(f"Role: {role}")
    print(f"Generated Password: {password}")
    print()
    
    try:
        success = await email_service.send_personnel_credentials_email(
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password,
            firm_name=firm_name,
            role=role
        )
        
        print("=" * 60)
        if success:
            print("✅ SUCCESS: Personnel credentials email sent successfully!")
            print(f"📧 Check {email} for the credentials email.")
            print("🎉 The personnel enrollment email system is working!")
        else:
            print("❌ FAILED: Could not send personnel credentials email.")
            print("Check the error messages above.")
        print("=" * 60)
        
        return success
        
    except Exception as e:
        print(f"❌ Error testing personnel email: {str(e)}")
        return False

async def main():
    if len(sys.argv) != 2:
        print("Usage: python test_personnel_email.py <email_address>")
        print("Example: python test_personnel_email.py test.manicasolutions@gmail.com")
        sys.exit(1)
    
    email = sys.argv[1]
    await test_personnel_email(email)

if __name__ == "__main__":
    asyncio.run(main())