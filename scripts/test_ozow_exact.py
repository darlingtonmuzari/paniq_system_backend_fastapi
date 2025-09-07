#!/usr/bin/env python3
"""
Test OZOW payment using the exact implementation from the working example
"""
import hashlib
import json
import requests
import os
import sys

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    from app.core.config import settings
    # Use settings from config
    OZOW_BASE_URL = settings.OZOW_BASE_URL
    OZOW_SITE_CODE = settings.OZOW_SITE_CODE
    OZOW_PRIVATE_KEY = settings.OZOW_PRIVATE_KEY
    OZOW_API_KEY = settings.OZOW_API_KEY
    OZOW_POST_URL = settings.OZOW_POST_URL
    OZOW_POST_LIVE_URL = settings.OZOW_POST_LIVE_URL
    OZOW_IS_TEST = settings.OZOW_IS_TEST
    OZOW_SUCCESS_URL = settings.OZOW_SUCCESS_URL
    OZOW_CANCEL_URL = settings.OZOW_CANCEL_URL
    OZOW_ERROR_URL = settings.OZOW_ERROR_URL
    OZOW_NOTIFY_URL = settings.OZOW_NOTIFY_URL
except ImportError:
    # Fallback to hardcoded values from your example
    OZOW_BASE_URL = "https://api-v3.manicasolutions.dev"
    OZOW_SITE_CODE = "MOF-MOF-002"
    OZOW_PRIVATE_KEY = "40481eb78f0648f0894dd394f87a9cf2"
    OZOW_API_KEY = "d1784bcb43db4869b786901bc7a87577"
    OZOW_POST_URL = "https://stagingapi.ozow.com/postpaymentrequest"
    OZOW_POST_LIVE_URL = "https://api.ozow.com/postpaymentrequest"
    OZOW_IS_TEST = True
    OZOW_SUCCESS_URL = "https://api-v2.manicasolutions.dev/api/v1.0/payments/ozow/success"
    OZOW_CANCEL_URL = "https://api-v2.manicasolutions.dev/api/v1.0/payments/ozow/cancel"
    OZOW_ERROR_URL = "https://api-v2.manicasolutions.dev/api/v1.0/payments/ozow/error"
    OZOW_NOTIFY_URL = "https://api-v2.manicasolutions.dev/api/v1.0/payments/ozow/webhooks"


def generate_request_hash():
    """Generate hash exactly as in working example"""
    site_code = OZOW_SITE_CODE
    country_code = 'ZA'
    currency_code = 'ZAR'
    amount = 25.01
    transaction_reference = 'transaction_reference_123'
    bank_reference = 'bank_reference_123'
    cancel_url = OZOW_CANCEL_URL
    error_url = OZOW_ERROR_URL
    success_url = OZOW_SUCCESS_URL
    notify_url = OZOW_NOTIFY_URL
    private_key = OZOW_PRIVATE_KEY
    is_test = False  # Set to False as in working example

    input_string = (
        site_code + country_code + currency_code + str(amount) + 
        transaction_reference + bank_reference + cancel_url + error_url + 
        success_url + notify_url + str(is_test) + private_key
    )
    input_string = input_string.lower()
    calculated_hash_result = generate_request_hash_check(input_string)
    print(f"Hashcheck: {calculated_hash_result}")
    return calculated_hash_result


def generate_request_hash_check(input_string):
    """Generate hash check exactly as in working example"""
    print(f"Before Hashcheck: {input_string}")
    return get_sha512_hash(input_string)


def get_sha512_hash(input_string):
    """Generate SHA512 hash exactly as in working example"""
    sha = hashlib.sha512()
    sha.update(input_string.encode())
    return sha.hexdigest()


def test_ozow_payment():
    """Test OZOW payment with exact implementation"""
    print("🧪 Testing OZOW Payment with Exact Implementation")
    print("=" * 50)
    
    # Generate hash
    hash_code = generate_request_hash()
    
    # Use staging URL for test
    url = OZOW_POST_URL
    
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
        "cancelUrl": OZOW_CANCEL_URL,
        "currencyCode": "ZAR",
        "errorUrl": OZOW_ERROR_URL,
        "isTest": "false",  # Match working example
        "notifyUrl": OZOW_NOTIFY_URL,
        "siteCode": OZOW_SITE_CODE,
        "successUrl": OZOW_SUCCESS_URL,
        "hashCheck": hash_code
    }
    
    print(f"Request URL: {url}")
    print(f"Request Headers: {headers}")
    print(f"Request Data: {json.dumps(data, indent=2)}")
    
    try:
        response = requests.post(url, headers=headers, json=data)
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Text: {response.text}")
        
        if response.status_code == 200:
            try:
                response_data = response.json()
                print(f"Response JSON: {json.dumps(response_data, indent=2)}")
                
                if response_data.get("IsSuccessful"):
                    print(f"✅ SUCCESS!")
                    print(f"Payment URL: {response_data.get('Url')}")
                    print(f"Transaction ID: {response_data.get('TransactionId')}")
                else:
                    print(f"❌ OZOW API Error: {response_data.get('ErrorMessage')}")
            except json.JSONDecodeError:
                print(f"❌ Invalid JSON response")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Request failed: {str(e)}")


if __name__ == "__main__":
    test_ozow_payment()