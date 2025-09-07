import hashlib
import string

OZOW_BASE_URL="https://api-v3.manicasolutions.dev"
OZOW_SITE_CODE="MOF-MOF-002"
OZOW_PRIVATE_KEY="40481eb78f0648f0894dd394f87a9cf2"
OZOW_API_KEY="d1784bcb43db4869b786901bc7a87577"
OZOW_POST_URL="https://stagingapi.ozow.com/postpaymentrequest"
OZOW_POST_LIVE_URL="https://api.ozow.com/postpaymentrequest"
OZOW_IS_TEST="true"
OZOW_SUCCESS_URL="https://api-v2.manicasolutions.dev/api/v1.0/payments/ozow/success"
OZOW_CANCEL_URL="https://api-v2.manicasolutions.dev/api/v1.0/payments/ozow/cancel"
OZOW_ERROR_URL="https://api-v2.manicasolutions.dev/api/v1.0/payments/ozow/error"
OZOW_NOTIFY_URL="https://api-v2.manicasolutions.dev/api/v1.0/payments/ozow/webhooks"
OZOW_VERIFY_TRANS_URL="https://stagingapi.ozow.com"
OZOW_VERIFY_TRANS_LIVE_URL="https://api.ozow.com"

def generate_request_hash():
    site_code = OZOW_SITE_CODE
    country_code = 'ZA'
    currency_code = 'ZAR'
    amount = 25.01
    transaction_reference = 'transaction_reference_123'
    bank_reference = 'bank_reference_123'
    cancel_url = 'https://a5ae1db587fb.ngrok-free.app/cancel.html'
    error_url = 'https://a5ae1db587fb.ngrok-free.app/error.html'
    success_url = 'https://a5ae1db587fb.ngrok-free.app/success.html'
    notify_url = 'https://a5ae1db587fb.ngrok-free.app/notify.html'
    private_key = OZOW_PRIVATE_KEY
    is_test = False

    input_string = site_code + country_code + currency_code + str(amount) + transaction_reference + bank_reference + cancel_url + error_url + success_url + notify_url + str(is_test) + private_key
    input_string = input_string.lower()
    calculated_hash_result = generate_request_hash_check(input_string)
    # print(f"Hashcheck: {calculated_hash_result}")
    return calculated_hash_result

def generate_request_hash_check(input_string):
    # print(f"Before Hashcheck: {input_string}")
    return get_sha512_hash(input_string)

def get_sha512_hash(input_string):
    sha = hashlib.sha512()
    sha.update(input_string.encode())
    return sha.hexdigest()

hash_code = generate_request_hash()

import json
import requests

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
    "cancelUrl": "https://a5ae1db587fb.ngrok-free.app/cancel.html",
    "currencyCode": "ZAR",
    "errorUrl": "https://a5ae1db587fb.ngrok-free.app/error.html",
    "isTest": "false",
    "notifyUrl": "https://a5ae1db587fb.ngrok-free.app/notify.html",
    "siteCode": OZOW_SITE_CODE,
    "successUrl": "https://a5ae1db587fb.ngrok-free.app/success.html",
    "hashCheck": hash_code
}
# print(data)
response = requests.post(url, headers=headers, json=data)

print(response.text)
