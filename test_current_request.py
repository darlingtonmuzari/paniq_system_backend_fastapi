#!/usr/bin/env python3
"""
Test the current request issue by checking token and parameters
"""
import requests
import json

# Test with different parameter variations
base_url = "http://localhost:8000/api/v1/credit-tiers/"

# You'll need to provide a valid admin token
token = input("Enter your admin token: ").strip()

if not token:
    print("❌ No token provided. Please provide a valid admin token.")
    exit(1)

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

print("🧪 Testing different parameter combinations:")
print("=" * 60)

test_cases = [
    {"url": base_url, "desc": "Default (no params)"},
    {"url": f"{base_url}?active_only=true", "desc": "active_only=true"},
    {"url": f"{base_url}?active_only=false", "desc": "active_only=false"},
    {"url": f"{base_url}?active_only=False", "desc": "active_only=False (capital F)"},
    {"url": f"{base_url}?active_only=0", "desc": "active_only=0"},
]

for test in test_cases:
    print(f"\n🔍 Testing: {test['desc']}")
    print(f"   URL: {test['url']}")
    
    try:
        response = requests.get(test['url'], headers=headers, timeout=10)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Results: {len(data)} tiers returned")
            
            active_count = sum(1 for tier in data if tier.get('is_active', True))
            inactive_count = len(data) - active_count
            
            print(f"   Active: {active_count}, Inactive: {inactive_count}")
            
            if inactive_count > 0:
                print(f"   ✅ Inactive tiers found!")
                for tier in data:
                    if not tier.get('is_active', True):
                        print(f"      - {tier['name']} (inactive)")
            else:
                print(f"   ⚠️  No inactive tiers returned")
                
        else:
            print(f"   Error: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Request failed: {str(e)}")

print(f"\n💡 Expected behavior:")
print(f"   - Default and active_only=true should return ~7 active tiers")
print(f"   - active_only=false should return ~8 tiers (including 'Sample Pack House' as inactive)")