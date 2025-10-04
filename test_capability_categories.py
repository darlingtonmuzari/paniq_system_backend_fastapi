#!/usr/bin/env python3

import asyncio
import requests
import json
from datetime import datetime, timedelta
import jwt

# Configuration
API_BASE = "http://localhost:8000"
SECRET_KEY = "your-secret-key-here"  # This should match your app's secret key

def generate_admin_token():
    """Generate an admin token for testing"""
    payload = {
        "sub": "test-admin@example.com",
        "email": "test-admin@example.com", 
        "role": "admin",
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token

def test_capability_categories():
    """Test capability categories API endpoints"""
    
    # Use provided admin token
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhNGNlOGZjMi02YTZlLTQ3ZTMtYjc2ZS0yOWQ1M2MzYTYyN2QiLCJ1c2VyX3R5cGUiOiJmaXJtX3BlcnNvbm5lbCIsImVtYWlsIjoiYWRtaW5AcGFuaXEuY28uemEiLCJwZXJtaXNzaW9ucyI6WyJyZXF1ZXN0OnZpZXciLCJyZXF1ZXN0OmFjY2VwdCIsImFkbWluOmFsbCIsImZpcm06bWFuYWdlIiwidXNlcjptYW5hZ2UiLCJzeXN0ZW06bWFuYWdlIiwidGVhbTptYW5hZ2UiLCJwZXJzb25uZWw6bWFuYWdlIl0sImV4cCI6MTc1ODI1NTQxMywiaWF0IjoxNzU4MjUxODEzLCJqdGkiOiIwMzQ1YjU2Ny1lOGE4LTQ4ZGQtOWE0Ny05YzJjYTgxZTFkZTciLCJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZmlybV9pZCI6IjI0OWQwM2I4LWZjMGEtNDYwYi04MmFmLTA0OTQ0NWQxNWRiYiIsInJvbGUiOiJhZG1pbiJ9.i5TyYonHSiGZcZbQUeBjalxUwdyp4G2Aqf5lLyjvEu8"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print("🧪 Testing Capability Categories API")
    print("=" * 50)
    
    # Test 1: Get all capability categories
    print("\n1. Testing GET /api/v1/capability-categories/")
    response = requests.get(f"{API_BASE}/api/v1/capability-categories/", headers=headers)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Found {data['total_count']} categories:")
        for cat in data['categories'][:3]:  # Show first 3
            print(f"  - {cat['name']} ({cat['code']}) - Active: {cat['is_active']}")
        categories = data['categories']
    else:
        print(f"Error: {response.text}")
        return
    
    # Test 2: Get category statistics
    print("\n2. Testing GET /api/v1/capability-categories/stats")
    response = requests.get(f"{API_BASE}/api/v1/capability-categories/stats", headers=headers)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        stats = response.json()
        print(f"Total categories: {stats['total_categories']}")
        print(f"Active categories: {stats['active_categories']}")
        print(f"Categories breakdown: {len(stats.get('categories', []))} items")
    else:
        print(f"Error: {response.text}")
    
    # Test 3: Get a specific category
    if categories:
        category_id = categories[0]['id']
        print(f"\n3. Testing GET /api/v1/capability-categories/{category_id}")
        response = requests.get(f"{API_BASE}/api/v1/capability-categories/{category_id}", headers=headers)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            category = response.json()
            print(f"Category: {category['name']} - {category['description']}")
        else:
            print(f"Error: {response.text}")
    
    # Test 4: Test capabilities endpoint with new structure
    print("\n4. Testing GET /api/v1/capabilities/ (updated)")
    response = requests.get(f"{API_BASE}/api/v1/capabilities/", headers=headers)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Found {data['total_count']} capabilities:")
        for cap in data['capabilities'][:3]:  # Show first 3
            print(f"  - {cap['name']} (Category: {cap.get('category_name', 'N/A')})")
    else:
        print(f"Error: {response.text}")
    
    # Test 5: Filter capabilities by category
    if categories:
        test_category_id = categories[0]['id']
        print(f"\n5. Testing GET /api/v1/capabilities/?category_id={test_category_id}")
        response = requests.get(f"{API_BASE}/api/v1/capabilities/?category_id={test_category_id}", headers=headers)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Found {data['total_count']} capabilities in category {categories[0]['name']}")
        else:
            print(f"Error: {response.text}")
    
    # Test 6: Create a new category (admin only)
    print("\n6. Testing POST /api/v1/capability-categories/ (Create)")
    new_category = {
        "name": "Test Category",
        "code": "test_category",
        "description": "A test category for API testing",
        "icon": "test-icon",
        "color": "#FF5722",
        "is_active": True
    }
    
    response = requests.post(f"{API_BASE}/api/v1/capability-categories/", 
                           headers=headers, 
                           json=new_category)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        created_category = response.json()
        print(f"Created category: {created_category['name']} with ID: {created_category['id']}")
        
        # Test 7: Update the created category
        print("\n7. Testing PUT /api/v1/capability-categories/{id} (Update)")
        update_data = {
            "description": "Updated test category description",
            "color": "#4CAF50"
        }
        
        response = requests.put(f"{API_BASE}/api/v1/capability-categories/{created_category['id']}", 
                              headers=headers, 
                              json=update_data)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            updated_category = response.json()
            print(f"Updated category description: {updated_category['description']}")
        else:
            print(f"Error: {response.text}")
        
        # Test 8: Delete the created category
        print("\n8. Testing DELETE /api/v1/capability-categories/{id} (Delete)")
        response = requests.delete(f"{API_BASE}/api/v1/capability-categories/{created_category['id']}", 
                                 headers=headers)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Delete result: {result['message']}")
        else:
            print(f"Error: {response.text}")
    else:
        print(f"Error creating category: {response.text}")
    
    print("\n✅ Testing completed!")

if __name__ == "__main__":
    test_capability_categories()