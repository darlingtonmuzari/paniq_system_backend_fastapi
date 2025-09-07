#!/usr/bin/env python3
"""
Test to demonstrate the HTTP status code behavior based on errorMessage
"""
import json

def demonstrate_status_code_logic():
    """Demonstrate when to return 200 vs 400"""
    print("🧪 HTTP Status Code Logic")
    print("=" * 60)
    
    print("📋 Status Code Rules:")
    print("   ✅ HTTP 200: When errorMessage is null (successful payment)")
    print("   ❌ HTTP 400: When errorMessage is not null (any error)")
    print()
    
    # Test cases
    test_cases = [
        {
            "name": "Successful Payment",
            "response": {
                "paymentRequestId": "734ecf05-e89c-4f0c-acb0-6881a452eb89",
                "url": "https://pay.ozow.com/734ecf05-e89c-4f0c-acb0-6881a452eb89/Secure",
                "errorMessage": None
            },
            "expected_status": 200,
            "reason": "errorMessage is null"
        },
        {
            "name": "OZOW API Error",
            "response": {
                "paymentRequestId": None,
                "url": None,
                "errorMessage": "HTTP 500 - An unexpected error occurred. Please try again later."
            },
            "expected_status": 400,
            "reason": "errorMessage is not null"
        },
        {
            "name": "Validation Error",
            "response": {
                "paymentRequestId": None,
                "url": None,
                "errorMessage": "No credit tier found for amount R175.00"
            },
            "expected_status": 400,
            "reason": "errorMessage is not null"
        },
        {
            "name": "Authorization Error",
            "response": {
                "paymentRequestId": None,
                "url": None,
                "errorMessage": "You can only purchase credits for your own firm."
            },
            "expected_status": 400,
            "reason": "errorMessage is not null"
        },
        {
            "name": "System Error",
            "response": {
                "paymentRequestId": None,
                "url": None,
                "errorMessage": "Payment initiation failed: Connection timeout"
            },
            "expected_status": 400,
            "reason": "errorMessage is not null"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"{i}️⃣  {test_case['name']}:")
        print(f"   Response: {json.dumps(test_case['response'], indent=13)}")
        print(f"   Expected Status: HTTP {test_case['expected_status']}")
        print(f"   Reason: {test_case['reason']}")
        
        # Show the logic
        error_message = test_case['response']['errorMessage']
        if error_message is None:
            status_icon = "✅"
            status_text = "200 OK"
        else:
            status_icon = "❌"
            status_text = "400 Bad Request"
            
        print(f"   Result: {status_icon} HTTP {status_text}")
        print()
    
    print("=" * 60)
    print("🔧 Implementation Logic:")
    print("   ```python")
    print("   error_message = payment_result.get('error')")
    print("   response_data = {")
    print('       "paymentRequestId": payment_result["payment_request_id"],')
    print('       "url": payment_result["url"],')
    print('       "errorMessage": error_message')
    print("   }")
    print("   ")
    print("   if error_message:")
    print("       return Response(")
    print("           content=json.dumps(response_data),")
    print("           status_code=400,")
    print("           media_type='application/json'")
    print("       )")
    print("   ")
    print("   return response_data  # HTTP 200")
    print("   ```")
    
    print("\n✅ This ensures proper HTTP semantics while maintaining OZOW format!")

if __name__ == "__main__":
    demonstrate_status_code_logic()