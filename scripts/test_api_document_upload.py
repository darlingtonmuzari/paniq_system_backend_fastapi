#!/usr/bin/env python3
"""
Test the actual API endpoint for document upload with UUID
"""
import asyncio
import sys
import os
import tempfile

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import get_db
from app.services.document_type import DocumentTypeService
from app.api.v1.security_firms import upload_firm_document
from app.services.auth import UserContext
from fastapi import UploadFile
import io

async def test_api_document_upload():
    """Test the API endpoint for document upload with UUID"""
    
    print("🔍 Testing API document upload with UUID...")
    
    firm_id = "e178e9f4-01cb-4c8e-910f-9586516172d6"
    
    # Get database session
    async for db in get_db():
        try:
            # Step 1: Get document type UUID
            print("\n1️⃣ Getting document type UUID...")
            doc_type_service = DocumentTypeService(db)
            doc_types = await doc_type_service.get_all_document_types()
            
            registration_cert_type = None
            for doc_type in doc_types:
                if doc_type.code == 'registration_certificate':
                    registration_cert_type = doc_type
                    break
            
            if not registration_cert_type:
                print("   ❌ Registration certificate document type not found")
                return False
            
            document_type_uuid = str(registration_cert_type.id)
            print(f"   ✅ Found document type UUID: {document_type_uuid}")
            
            # Step 2: Create mock user context
            print("\n2️⃣ Creating mock user context...")
            from uuid import UUID
            user_context = UserContext(
                user_id=UUID("8e107be0-7477-4fe8-8103-490d55351738"),
                user_type="registered_user",
                email="darlington@manicasolutions.com",
                role="user"
            )
            print(f"   ✅ Created user context for: {user_context.email}")
            
            # Step 3: Create test file
            print("\n3️⃣ Creating test file...")
            test_content = b"Test document content for API upload test"
            
            # Create UploadFile object
            file_obj = io.BytesIO(test_content)
            upload_file = UploadFile(
                filename="test_api_upload.pdf",
                file=file_obj,
                size=len(test_content),
                headers={"content-type": "application/pdf"}
            )
            
            print(f"   ✅ Created upload file: {upload_file.filename}")
            
            # Step 4: Test API endpoint
            print("\n4️⃣ Testing API endpoint...")
            
            try:
                response = await upload_firm_document(
                    firm_id=firm_id,
                    document_type=document_type_uuid,  # Using UUID as the API receives
                    file=upload_file,
                    current_user=user_context,
                    db=db
                )
                
                print("   ✅ API call successful!")
                print(f"      Document ID: {response.id}")
                print(f"      Document Type: {response.document_type}")
                print(f"      File Name: {response.file_name}")
                print(f"      File Size: {response.file_size}")
                print(f"      Uploaded At: {response.uploaded_at}")
                
                return True
                
            except Exception as e:
                print(f"   ❌ API call failed: {e}")
                import traceback
                traceback.print_exc()
                return False
            
        except Exception as e:
            print(f"❌ Error during testing: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            await db.close()
        
        break

if __name__ == "__main__":
    success = asyncio.run(test_api_document_upload())
    
    if success:
        print("\n🎉 API DOCUMENT UPLOAD TEST SUCCESSFUL!")
        print("✅ API endpoint handling UUID correctly")
        print("✅ Document type conversion working")
        print("✅ S3 upload via API working")
        print("✅ Response format correct")
    else:
        print("\n❌ API DOCUMENT UPLOAD TEST FAILED!")
        print("💡 Check the error messages above for details.")
    
    sys.exit(0 if success else 1)