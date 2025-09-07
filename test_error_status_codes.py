#!/usr/bin/env python3
"""
Test to verify that API returns HTTP 400 when errorMessage is not null
"""
import requests
import json

def test_error_status_codes():
    """Test that API returns proper HTTP status codes"""
    print("🧪 Testing HTTP Status Codes for Error Responses")
    print("=" * 60)
    
    # Test cases that should return 400 status
    test_cases = [
        {
            "name": "Invalid Amount",
            "data": {"firm_id": "123e4567-e89b-12d3-a456-426614174000", "amount": 175.00},
            "expected_error": "No credit tier found for amount"
        },
        {
            "name": "Invalid Firm ID Format", 
            "data": {"firm_id": "invalid-uuid", "amount": 100.00},
            "expected_error": "validation error"
        }
    ]
    
    base_url = "http://localhost:8000/api/v1/payments"
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"{i}️⃣  Testing: {test_case['name']}")
        
        try:
            # Test the main endpoint
            response = requests.post(
                f"{base_url}/purchase-credits",
                json=test_case["data"],
                headers={"Authorization": "Bearer fake-token-for-testing"}
            )
            
            print(f"   Status Code: {response.status_code}")
            print(f"   Response: {response.text}")
            
            if response.status_code == 400:
                print("   ✅ Correct: Returns HTTP 400 for error")
                
                # Check response format
                try:
                    response_data = response.json()
                    required_keys = {"paymentRequestId", "url", "errorMessage"}
                    actual_keys = set(response_data.keys())
                    
                    if required_keys == actual_keys:
                        print("   ✅ Correct: Response format matches OZOW spec")
                        
                        if (response_data["paymentRequestId"] is None and 
                            response_data["url"] is None and 
                            response_data["errorMessage"] is not None):
                            print("   ✅ Correct: Error fields are properly set")
                        else:
                            print("   ❌ Incorrect: Error fields not properly set")
                    else:
                        print("   ❌ Incorrect: Response format doesn't match OZOW spec")
                        
                except json.JSONDecodeError:
                    print("   ❌ Incorrect: Response is not valid JSON")
                    
            elif response.status_code == 200:
                print("   ❌ Incorrect: Should return HTTP 400, not 200")
            else:
                print(f"   ❓ Unexpected status code: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print("   ⚠️  Cannot connect to API server (not running?)")
        except Exception as e:
            print(f"   ❌ Test failed with exception: {e}")
            
        print()
    
    print("=" * 60)
    print("📋 Expected Behavior:")
    print("   ✅ HTTP 200: When paymentRequestId and url are present, errorMessage is null")
    print("   ❌ HTTP 400: When errorMessage is not null (paymentRequestId and url are null)")
    print()
    print("📋 Response Format (always the same):")
    print("   {")
    print('     "paymentRequestId": "uuid-or-null",')
    print('     "url": "payment-url-or-null",')
    print('     "errorMessage": "error-message-or-null"')
    print("   }")

if __name__ == "__main__":
    test_error_status_codes()