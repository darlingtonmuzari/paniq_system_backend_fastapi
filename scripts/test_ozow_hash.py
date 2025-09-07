#!/usr/bin/env python3
"""
Test OZOW hash generation to match the official specification
"""
import hashlib
import sys
import os
from decimal import Decimal

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import settings
from app.services.ozow_service import OzowService


def test_ozow_hash_generation():
    """Test OZOW hash generation against the official algorithm"""
    
    print("🔐 Testing OZOW Hash Generation")
    print("=" * 40)
    
    # Test data similar to the provided example (using camelCase)
    test_data = {
        "siteCode": settings.OZOW_SITE_CODE,
        "countryCode": "ZA",
        "currencyCode": "ZAR",
        "amount": "150.00",
        "transactionReference": "TXN-TEST-123",
        "bankReference": "INV-TEST123",
        "cancelUrl": settings.OZOW_CANCEL_URL,
        "errorUrl": settings.OZOW_ERROR_URL,
        "successUrl": settings.OZOW_SUCCESS_URL,
        "notifyUrl": settings.OZOW_NOTIFY_URL,
        "isTest": True
    }
    
    print("Test Data:")
    for key, value in test_data.items():
        print(f"  {key}: {value}")
    print(f"  PrivateKey: {settings.OZOW_PRIVATE_KEY}")
    
    # Test our implementation
    print("\n1. Testing Our Implementation...")
    ozow_service = OzowService()
    our_hash = ozow_service._generate_hash_check(test_data)
    print(f"Our Hash: {our_hash}")
    
    # Test the official algorithm manually
    print("\n2. Testing Official Algorithm Manually...")
    is_test_str = "true" if test_data["isTest"] else "false"
    input_string = (
        test_data["siteCode"] +
        test_data["countryCode"] +
        test_data["currencyCode"] +
        test_data["amount"] +
        test_data["transactionReference"] +
        test_data["bankReference"] +
        test_data["cancelUrl"] +
        test_data["errorUrl"] +
        test_data["successUrl"] +
        test_data["notifyUrl"] +
        is_test_str +
        settings.OZOW_PRIVATE_KEY
    )
    
    input_string = input_string.lower()
    print(f"Manual Input String: {input_string}")
    
    sha = hashlib.sha512()
    sha.update(input_string.encode('utf-8'))
    manual_hash = sha.hexdigest()
    print(f"Manual Hash: {manual_hash}")
    
    # Compare results
    print("\n3. Comparison...")
    if our_hash == manual_hash:
        print("✅ Hash generation matches official algorithm!")
    else:
        print("❌ Hash generation does not match!")
        print(f"   Our hash:    {our_hash}")
        print(f"   Manual hash: {manual_hash}")
    
    print("\n4. Testing with Real Payment Data...")
    # Test with actual payment data structure
    real_payment_data = {
        "siteCode": settings.OZOW_SITE_CODE,
        "countryCode": "ZA", 
        "currencyCode": "ZAR",
        "amount": "150.00",
        "transactionReference": "TXN-INV-20250906-TEST123",
        "bankReference": "INV-TEST123",
        "successUrl": settings.OZOW_SUCCESS_URL,
        "cancelUrl": settings.OZOW_CANCEL_URL,
        "errorUrl": settings.OZOW_ERROR_URL,
        "notifyUrl": settings.OZOW_NOTIFY_URL,
        "isTest": True
    }
    
    real_hash = ozow_service._generate_hash_check(real_payment_data)
    print(f"Real Payment Hash: {real_hash}")
    
    print("\n✅ Hash Generation Test Completed!")


if __name__ == "__main__":
    test_ozow_hash_generation()