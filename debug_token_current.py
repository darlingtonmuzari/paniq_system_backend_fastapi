#!/usr/bin/env python3
"""
Debug the current access token
"""

import jwt
import json

# The token from the error
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJmOGEzMDkxOS01ZWQ1LTQ2YWYtOTVkNi0zYWZhNGRhNjM0ZGEiLCJ1c2VyX3R5cGUiOiJmaXJtX3BlcnNvbm5lbCIsImVtYWlsIjoidGVzdC5tYW5pY2Fzb2x1dGlvbnNAZ21haWwuY29tIiwicGVybWlzc2lvbnMiOlsicmVxdWVzdDp2aWV3IiwicmVxdWVzdDphY2NlcHQiXSwiZXhwIjoxNzU4NzAzNDAyLCJpYXQiOjE3NTg2OTk4MDIsImp0aSI6IjBmOTZkOTZjLTA0ZmQtNDMzMy04MmI1LTY3NjdiNTc0ZTJmMyIsInRva2VuX3R5cGUiOiJhY2Nlc3MiLCJmaXJtX2lkIjoiZTE3OGU5ZjQtMDFjYi00YzhlLTkxMGYtOTU4NjUxNjE3MmQ2Iiwicm9sZSI6ImZpcm1fc3VwZXJ2aXNvciJ9.Up8m8igt8Hb4Pcsjprov1DAwTaY3nyFilb_L84DgSyw"

try:
    # Decode without verification to see contents
    decoded = jwt.decode(token, options={"verify_signature": False})
    print("Token contents:")
    print(json.dumps(decoded, indent=2))
    
    print(f"\nUser ID: {decoded['sub']}")
    print(f"User Type: {decoded['user_type']}")
    print(f"Role: {decoded['role']}")
    print(f"Firm ID: {decoded['firm_id']}")
    print(f"Email: {decoded['email']}")
    print(f"Permissions: {decoded['permissions']}")

except Exception as e:
    print(f"Error decoding token: {e}")