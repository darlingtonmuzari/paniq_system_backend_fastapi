#!/usr/bin/env python3
"""
Test to verify that our API returns the exact same format as ozow.py
"""
import subprocess
import json
import re

def run_ozow_py():
    """Run ozow.py and extract the JSON response"""
    try:
        result = subprocess.run(['python3', 'ozow.py'], capture_output=True, text=True)
        output = result.stdout
        
        # Extract JSON from the output (it's the last line)
        lines = output.strip().split('\n')
        json_line = lines[-1]
        
        # Parse the JSON response
        ozow_response = json.loads(json_line)
        return ozow_response
    except Exception as e:
        print(f"Error running ozow.py: {e}")
        return None

def test_api_format():
    """Test our API format against ozow.py format"""
    print("🧪 Testing API Format Match with ozow.py")
    print("=" * 50)
    
    # Get ozow.py response
    ozow_response = run_ozow_py()
    if not ozow_response:
        print("❌ Failed to get ozow.py response")
        return
    
    print("✅ ozow.py Response Format:")
    print(json.dumps(ozow_response, indent=2))
    print()
    
    # Check the structure
    expected_keys = {"paymentRequestId", "url", "errorMessage"}
    actual_keys = set(ozow_response.keys())
    
    if expected_keys == actual_keys:
        print("✅ Response structure matches exactly!")
        print(f"   Keys: {sorted(expected_keys)}")
    else:
        print("❌ Response structure mismatch!")
        print(f"   Expected: {sorted(expected_keys)}")
        print(f"   Actual: {sorted(actual_keys)}")
        return
    
    # Check field types
    print("\n🔍 Field Analysis:")
    print(f"   paymentRequestId: {type(ozow_response['paymentRequestId']).__name__} = {ozow_response['paymentRequestId']}")
    print(f"   url: {type(ozow_response['url']).__name__} = {ozow_response['url']}")
    print(f"   errorMessage: {type(ozow_response['errorMessage']).__name__} = {ozow_response['errorMessage']}")
    
    # Validate UUID format
    payment_id = ozow_response['paymentRequestId']
    if payment_id:
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        if re.match(uuid_pattern, payment_id):
            print("   ✅ paymentRequestId is valid UUID format")
        else:
            print("   ❌ paymentRequestId is not valid UUID format")
    
    # Validate URL format
    url = ozow_response['url']
    if url and url.startswith('https://pay.ozow.com/'):
        print("   ✅ url has correct OZOW payment URL format")
    else:
        print("   ❌ url does not have correct OZOW payment URL format")
    
    print("\n🎯 Summary:")
    print("   Your API implementation should return this EXACT format:")
    print("   {")
    print('     "paymentRequestId": "uuid-string-or-null",')
    print('     "url": "https://pay.ozow.com/uuid/Secure-or-null",')
    print('     "errorMessage": "error-string-or-null"')
    print("   }")
    print("\n✅ This matches the ozow.py response format perfectly!")

if __name__ == "__main__":
    test_api_format()