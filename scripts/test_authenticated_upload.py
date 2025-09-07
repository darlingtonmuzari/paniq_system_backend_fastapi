#!/usr/bin/env python3
"""
Test document upload with authentication
"""
import requests
import tempfile
import json

# API base URL
BASE_URL = "http://localhost:8000/api/v1"

def get_auth_token():
    """Get authentication token (you'll need to replace with actual credentials)"""
    
    # First, let's try to register/login a test user
    # You'll need to replace these with actual credentials
    login_data = {
        "email": "test@example.com",
        "password": "testpassword123"
    }
    
    try:
        # Try to login
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        if response.status_code == 200:
            token_data = response.json()
            return token_data.get("access_token")
        else:
            print(f"Login failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Error during login: {e}")
        return None

def test_authenticated_upload():
    """Test document upload with authentication"""
    
    print("Testing authenticated document upload...")
    
    # Get auth token
    token = get_auth_token()
    if not token:
        print("❌ Could not get authentication token")
        print("💡 You need to create a test user and firm first")
        return False
    
    print(f"✅ Got authentication token: {token[:20]}...")
    
    # Create test file
    test_content = b"This is a test document for authenticated upload."
    
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
        temp_file.write(test_content)
        temp_file_path = temp_file.name
    
    try:
        firm_id = "e178e9f4-01cb-4c8e-910f-9586516172d6"  # Replace with actual firm ID
        
        # Prepare headers
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        # Prepare files and data
        files = {
            'file': ('test_document.pdf', open(temp_file_path, 'rb'), 'application/pdf')
        }
        
        params = {
            'document_type': 'registration_certificate'
        }
        
        upload_url = f"{BASE_URL}/security-firms/{firm_id}/documents"
        
        print(f"Uploading to: {upload_url}")
        print(f"Document type: registration_certificate")
        
        response = requests.post(upload_url, files=files, params=params, headers=headers)
        
        print(f"Response status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Document uploaded successfully!")
            
            # Parse response to get document info
            doc_data = response.json()
            print(f"Document ID: {doc_data.get('id')}")
            print(f"File name: {doc_data.get('file_name')}")
            print(f"File size: {doc_data.get('file_size')}")
            
            return True
        else:
            print(f"❌ Upload failed: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error details: {error_data}")
            except:
                print(f"Raw error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error during upload: {e}")
        return False
    finally:
        # Clean up temp file
        import os
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

def check_api_status():
    """Check if API is running and accessible"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ API is running and accessible")
            return True
        else:
            print(f"⚠️ API returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API - is it running?")
        return False
    except Exception as e:
        print(f"❌ Error checking API status: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Testing document upload with authentication...\n")
    
    # Check API status first
    if not check_api_status():
        print("\n💡 Make sure the API is running with: make dev")
        exit(1)
    
    # Test upload
    success = test_authenticated_upload()
    
    if not success:
        print("\n💡 Troubleshooting tips:")
        print("1. Make sure you have a valid user account")
        print("2. Make sure the firm exists and you're a member")
        print("3. Check the API logs for detailed error messages")
        print("4. Verify the document type 'registration_certificate' exists")
    
    exit(0 if success else 1)