#!/usr/bin/env python3

import jwt
import json
from datetime import datetime

# The JWT token from the user
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI4NjBmZmJiMS05NjkyLTRkYTEtYjBlYy1hNDNlZDdiZDQ1ZjciLCJ1c2VyX3R5cGUiOiJmaXJtX3BlcnNvbm5lbCIsImVtYWlsIjoiZGFybGluZ3RvbkBtYW5pY2Fzb2x1dGlvbnMuY29tIiwicGVybWlzc2lvbnMiOlsicmVxdWVzdDp2aWV3IiwicmVxdWVzdDphY2NlcHQiXSwiZXhwIjoxNzU4MjE3ODY4LCJpYXQiOjE3NTgyMTQyNjgsImp0aSI6ImQ1ZGI5NmUwLTU3YzUtNDQ5NC04NjAxLTEwZTJjZjQzZjViNSIsInRva2VuX3R5cGUiOiJhY2Nlc3MiLCJmaXJtX2lkIjoiZTE3OGU5ZjQtMDFjYi00YzhlLTkxMGYtOTU4NjUxNjE3MmQ2Iiwicm9sZSI6ImZpcm1fYWRtaW4ifQ.yqXOayXPql0Zx4gU8AFwOl_C_E5ze1BbTW54o9lypBQ"

try:
    # Decode without verification to see the payload
    decoded = jwt.decode(token, options={"verify_signature": False})
    
    print("=== DECODED JWT TOKEN ===")
    print(json.dumps(decoded, indent=2))
    
    print("\n=== KEY INFORMATION ===")
    print(f"User ID: {decoded.get('sub')}")
    print(f"User Type: {decoded.get('user_type')}")
    print(f"Email: {decoded.get('email')}")
    print(f"Firm ID: {decoded.get('firm_id')}")
    print(f"Role: {decoded.get('role')}")
    print(f"Permissions: {decoded.get('permissions')}")
    
    # Check expiration
    exp_timestamp = decoded.get('exp')
    if exp_timestamp:
        exp_datetime = datetime.fromtimestamp(exp_timestamp)
        current_datetime = datetime.now()
        print(f"Expires: {exp_datetime}")
        print(f"Current: {current_datetime}")
        print(f"Is Expired: {current_datetime > exp_datetime}")
    
except Exception as e:
    print(f"Error decoding token: {e}")