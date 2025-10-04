#!/usr/bin/env python3

import jwt
import json
from datetime import datetime, timedelta
from uuid import UUID

# Use the same secret from your config
SECRET_KEY = "jwt-secret-key-change-in-production"
ALGORITHM = "HS256"

# User data for testing (same user as before)
user_data = {
    "sub": "860ffbb1-9692-4da1-b0ec-a43ed7bd45f7",
    "user_type": "firm_personnel", 
    "email": "darlington@manicasolutions.com",
    "permissions": ["request:view", "request:accept"],
    "firm_id": "e178e9f4-01cb-4c8e-910f-9586516172d6",
    "role": "firm_admin",
    "token_type": "access",
    "jti": "new-test-token-id-123",
    "iat": datetime.utcnow(),
    "exp": datetime.utcnow() + timedelta(hours=24)  # 24 hours from now
}

# Convert datetime objects to timestamps
user_data["iat"] = int(user_data["iat"].timestamp())
user_data["exp"] = int(user_data["exp"].timestamp())

# Generate token
token = jwt.encode(user_data, SECRET_KEY, algorithm=ALGORITHM)

print("=== NEW TEST TOKEN ===")
print(token)
print()

# Verify it works
try:
    decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    print("✅ Token validation successful!")
    print(f"User: {decoded['email']}")
    print(f"Firm ID: {decoded['firm_id']}")
    print(f"Role: {decoded['role']}")
    print(f"Expires: {datetime.fromtimestamp(decoded['exp'])}")
except Exception as e:
    print(f"❌ Token validation failed: {e}")