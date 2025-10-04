#!/usr/bin/env python3
"""
Test script to check all credit tiers including inactive ones
"""
import requests
import json

# Your current token (firm_personnel, no role)
CURRENT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhNGNlOGZjMi02YTZlLTQ3ZTMtYjc2ZS0yOWQ1M2MzYTYyN2QiLCJ1c2VyX3R5cGUiOiJmaXJtX3BlcnNvbm5lbCIsImVtYWlsIjoiIiwicGVybWlzc2lvbnMiOltdLCJleHAiOjE3NTgxODE5MTAsImlhdCI6MTc1ODE4MDExMCwianRpIjoiOTU3MDdjNTAtYmY3NC00Nzk2LTk3YWQtNDA0ODE5NzU1N2Y3IiwidG9rZW5fdHlwZSI6ImFjY2VzcyJ9.OAmMopDj0R-KocCqsm8wJiCnRoexMVoncdzsyw1iKJM"

BASE_URL = "http://localhost:8000/api/v1/credit-tiers"

def test_credit_tiers():
    headers = {
        "Authorization": f"Bearer {CURRENT_TOKEN}",
        "Content-Type": "application/json"
    }
    
    print("Credit Tiers API Test")
    print("=" * 50)
    
    # Test 1: Get all tiers (default behavior for non-admin)
    print("\n1. Getting all tiers (non-admin default):")
    response = requests.get(BASE_URL, headers=headers)
    if response.status_code == 200:
        tiers = response.json()
        print(f"   Found {len(tiers)} tiers")
        for tier in tiers:
            print(f"   - {tier['name']}: {tier['min_credits']}-{tier['max_credits']} credits, Active: {tier['is_active']}")
    else:
        print(f"   Error: {response.status_code} - {response.text}")
    
    # Test 2: Try to get inactive tiers (should still return active only for non-admin)
    print("\n2. Attempting to get inactive tiers (active_only=false):")
    response = requests.get(f"{BASE_URL}?active_only=false", headers=headers)
    if response.status_code == 200:
        tiers = response.json()
        print(f"   Found {len(tiers)} tiers")
        for tier in tiers:
            print(f"   - {tier['name']}: {tier['min_credits']}-{tier['max_credits']} credits, Active: {tier['is_active']}")
    else:
        print(f"   Error: {response.status_code} - {response.text}")
    
    # Test 3: Try to get all tiers explicitly
    print("\n3. Attempting to get all tiers (no parameter):")
    response = requests.get(f"{BASE_URL}/", headers=headers)
    if response.status_code == 200:
        tiers = response.json()
        print(f"   Found {len(tiers)} tiers")
        for tier in tiers:
            print(f"   - {tier['name']}: {tier['min_credits']}-{tier['max_credits']} credits, Active: {tier['is_active']}")
    else:
        print(f"   Error: {response.status_code} - {response.text}")

if __name__ == "__main__":
    test_credit_tiers()