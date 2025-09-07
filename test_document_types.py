#!/usr/bin/env python3
"""
Simple test script for document types API
"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

def test_document_types():
    """Test the document types endpoints"""
    
    print("Testing Document Types API")
    print("=" * 50)
    
    # Test getting all document types
    try:
        response = requests.get(f"{BASE_URL}/document-types/all")
        print(f"GET /document-types/all - Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Found {len(data)} document types")
            for doc_type in data[:3]:  # Show first 3
                print(f"  - {doc_type['name']} ({doc_type['code']})")
                print(f"    ID: {doc_type['id']} | Created by: {doc_type['created_by']}")
        else:
            print(f"Error: {response.text}")
    
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API. Make sure the server is running on port 8000")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False
    
    # Test getting all document types (updated endpoint)
    try:
        response = requests.get(f"{BASE_URL}/document-types/")
        print(f"\nGET /document-types/ - Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Found {len(data)} document types")
            for doc_type in data:
                required = "✓" if doc_type['is_required'] else "○"
                print(f"  {required} {doc_type['name']} ({doc_type['code']}) - ID: {doc_type['id']}")
                print(f"    Created by: {doc_type['created_by']}")
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    # Test getting document type by ID (if we have one)
    try:
        # First get all to find an ID
        response = requests.get(f"{BASE_URL}/document-types/all")
        if response.status_code == 200:
            data = response.json()
            if data:
                test_id = data[0]['id']
                test_code = data[0]['code']
                
                # Test by ID
                response = requests.get(f"{BASE_URL}/document-types/by-id/{test_id}")
                print(f"\nGET /document-types/by-id/{test_id} - Status: {response.status_code}")
                
                if response.status_code == 200:
                    doc_type = response.json()
                    print(f"✓ Found document type by ID: {doc_type['name']} ({doc_type['code']})")
                    print(f"  Created by: {doc_type['created_by']}")
                
                # Test by code
                response = requests.get(f"{BASE_URL}/document-types/by-code/{test_code}")
                print(f"GET /document-types/by-code/{test_code} - Status: {response.status_code}")
                
                if response.status_code == 200:
                    doc_type = response.json()
                    print(f"✓ Found document type by code: {doc_type['name']} (ID: {doc_type['id']})")
                    print(f"  Created by: {doc_type['created_by']}")
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    # Test getting required documents
    try:
        response = requests.get(f"{BASE_URL}/document-types/required")
        print(f"\nGET /document-types/required - Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Found {len(data)} required documents:")
            for doc_type in data:
                print(f"  ✓ {doc_type['name']} ({doc_type['code']}) - ID: {doc_type['id']}")
                print(f"    Created by: {doc_type['created_by']}")
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    # Test validation endpoint
    try:
        response = requests.post(
            f"{BASE_URL}/document-types/validate/registration_certificate"
        )
        print(f"\nPOST /document-types/validate/registration_certificate - Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('valid'):
                print("✓ Document type validation passed")
                doc_info = data.get('document_type', {})
                print(f"  Name: {doc_info.get('name')}")
            else:
                print(f"❌ Validation failed: {data.get('error')}")
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    print("\n" + "=" * 50)
    print("✅ Document Types API test completed!")
    return True


if __name__ == "__main__":
    test_document_types()