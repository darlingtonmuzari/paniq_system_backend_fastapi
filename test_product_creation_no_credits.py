#!/usr/bin/env python3
"""
Test product creation without requiring credits upfront
"""
import requests
import json

BASE_URL = "http://localhost:8000"

# Use the fresh token we generated earlier
ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI4NjBmZmJiMS05NjkyLTRkYTEtYjBlYy1hNDNlZDdiZDQ1ZjciLCJ1c2VyX3R5cGUiOiJmaXJtX3BlcnNvbm5lbCIsImVtYWlsIjoiZGFybGluZ3RvbkBtYW5pY2Fzb2x1dGlvbnMuY29tIiwicGVybWlzc2lvbnMiOlsicmVxdWVzdDp2aWV3IiwicmVxdWVzdDphY2NlcHQiXSwiZXhwIjoxNzU3MTM2MTE2LCJpYXQiOjE3NTcwNDk3MTYsImp0aSI6InRlc3QtdG9rZW4tODYwZmZiYjEiLCJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZmlybV9pZCI6ImUxNzhlOWY0LTAxY2ItNGM4ZS05MTBmLTk1ODY1MTYxNzJkNiIsInJvbGUiOiJmaXJtX2FkbWluIn0.iZbEu7nSsJxqeA1-bNuWVrD7THAgCHRIQ_Q9wnj9LII"

def test_create_product():
    """Test creating a product without requiring credits upfront"""
    url = f"{BASE_URL}/api/v1/subscription-products/"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Test product data
    product_data = {
        "name": "Test Security Package",
        "description": "A test security package for validation",
        "max_users": 10,
        "price": 199.99,
        "credit_cost": 25
    }
    
    print(f"Creating product: {product_data['name']}")
    print(f"URL: {url}")
    
    try:
        response = requests.post(url, headers=headers, json=product_data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success! Created product with ID: {data['id']}")
            return data['id']
        else:
            print(f"❌ Failed to create product")
            return None
            
    except Exception as e:
        print(f"Request failed: {e}")
        return None

def test_get_my_products():
    """Test getting the firm's products after creation"""
    url = f"{BASE_URL}/api/v1/subscription-products/my-products"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    print(f"\nGetting firm products...")
    
    try:
        response = requests.get(url, headers=headers, params={"include_inactive": "false"})
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success! Found {len(data['products'])} products")
            for product in data['products']:
                print(f"  - {product['name']} (${product['price']}, {product['max_users']} users)")
        else:
            print(f"❌ Failed to get products: {response.text}")
            
    except Exception as e:
        print(f"Request failed: {e}")

def test_create_multiple_products():
    """Test creating multiple products to verify no credit limitations"""
    products_to_create = [
        {
            "name": "Basic Home Security",
            "description": "Basic security monitoring for homes",
            "max_users": 5,
            "price": 99.99,
            "credit_cost": 15
        },
        {
            "name": "Premium Business Security",
            "description": "Advanced security for business premises",
            "max_users": 20,
            "price": 399.99,
            "credit_cost": 50
        },
        {
            "name": "Enterprise Security Suite",
            "description": "Complete security solution for large enterprises",
            "max_users": 100,
            "price": 999.99,
            "credit_cost": 100
        }
    ]
    
    print(f"\nCreating {len(products_to_create)} products...")
    
    created_products = []
    for product_data in products_to_create:
        print(f"\nCreating: {product_data['name']}")
        
        url = f"{BASE_URL}/api/v1/subscription-products/"
        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(url, headers=headers, json=product_data)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Created: {data['name']} (ID: {data['id']})")
                created_products.append(data)
            else:
                print(f"❌ Failed: {response.text}")
                
        except Exception as e:
            print(f"Request failed: {e}")
    
    print(f"\n🎉 Successfully created {len(created_products)} products!")
    return created_products

if __name__ == "__main__":
    print("🧪 Testing Product Creation Without Credits...")
    
    # Test single product creation
    product_id = test_create_product()
    
    # Test getting products
    test_get_my_products()
    
    # Test creating multiple products
    test_create_multiple_products()
    
    # Final check
    test_get_my_products()