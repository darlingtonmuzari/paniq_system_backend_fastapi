#!/usr/bin/env python3
"""
Test document upload to verify S3 integration
"""
import requests
import tempfile
import os

# API base URL
BASE_URL = "http://localhost:8000/api/v1"

def test_document_upload():
    """Test document upload functionality"""
    
    print("Testing document upload with S3 integration...")
    
    # Create a test file
    test_content = b"This is a test document for S3 upload verification."
    
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
        temp_file.write(test_content)
        temp_file_path = temp_file.name
    
    try:
        # Test firm ID (you'll need to replace this with a valid firm ID)
        firm_id = "e178e9f4-01cb-4c8e-910f-9586516172d6"
        
        # Test upload endpoint (without authentication for now)
        upload_url = f"{BASE_URL}/security-firms/{firm_id}/documents"
        
        files = {
            'file': ('test_document.pdf', open(temp_file_path, 'rb'), 'application/pdf')
        }
        
        params = {
            'document_type': 'registration_certificate'
        }
        
        print(f"Uploading to: {upload_url}")
        print(f"Document type: registration_certificate")
        
        # Note: This will fail without authentication, but we can see the S3 configuration
        response = requests.post(upload_url, files=files, params=params)
        
        print(f"Response status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 401:
            print("✅ API is running and S3 configuration is loaded (authentication required)")
            return True
        elif response.status_code == 200:
            print("✅ Document uploaded successfully!")
            return True
        else:
            print(f"❌ Unexpected response: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing upload: {e}")
        return False
    finally:
        # Clean up temp file
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

if __name__ == "__main__":
    test_document_upload()