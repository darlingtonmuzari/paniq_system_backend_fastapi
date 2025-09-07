#!/usr/bin/env python3
"""
Test direct document upload bypassing authentication
"""
import asyncio
import sys
import os
import tempfile
from pathlib import Path

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import get_db
from app.services.security_firm import SecurityFirmService
from app.services.document_type import DocumentTypeService
from fastapi import UploadFile
import io

class MockUploadFile:
    """Mock UploadFile for testing"""
    def __init__(self, content, filename, content_type):
        self.file = io.BytesIO(content)
        self.filename = filename
        self.content_type = content_type
        self.size = len(content)
    
    async def read(self):
        return self.file.getvalue()

async def test_direct_upload():
    """Test document upload directly through the service"""
    
    print("🔍 Testing direct document upload...")
    
    # Test data
    firm_id = "e178e9f4-01cb-4c8e-910f-9586516172d6"
    user_id = None  # We need to get the actual user ID
    document_type = "registration_certificate"
    
    # Get database session
    async for db in get_db():
        try:
            # First, get the user ID for the firm admin
            from sqlalchemy import text
            result = await db.execute(text("""
                SELECT fu.user_id 
                FROM firm_users fu 
                WHERE fu.firm_id = :firm_id AND fu.role = 'firm_admin' AND fu.status = 'active'
                LIMIT 1
            """), {"firm_id": firm_id})
            
            user_data = result.fetchone()
            if not user_data:
                print("❌ No active firm admin found for this firm")
                return False
            
            user_id = str(user_data[0])
            print(f"✅ Found firm admin user: {user_id}")
            
            # Validate document type
            doc_type_service = DocumentTypeService(db)
            try:
                doc_type = await doc_type_service.validate_document_type(document_type)
                print(f"✅ Document type '{document_type}' is valid: {doc_type.name}")
            except ValueError as e:
                print(f"❌ Document type validation failed: {e}")
                return False
            
            # Create test file
            test_content = b"This is a test registration certificate document for S3 upload testing."
            mock_file = MockUploadFile(test_content, "test_registration_cert.pdf", "application/pdf")
            
            print(f"📄 Created test file: {mock_file.filename} ({len(test_content)} bytes)")
            
            # Test upload
            service = SecurityFirmService(db)
            
            print("🚀 Attempting document upload...")
            document = await service.upload_document(
                firm_id=firm_id,
                document_type=document_type,
                file=mock_file,
                user_id=user_id
            )
            
            print("✅ Document uploaded successfully!")
            print(f"   Document ID: {document.id}")
            print(f"   File name: {document.file_name}")
            print(f"   File path: {document.file_path}")
            print(f"   File size: {document.file_size}")
            print(f"   Document type: {document.document_type}")
            print(f"   Created at: {document.created_at}")
            
            # Verify it's in the database
            from sqlalchemy import text
            result = await db.execute(text("SELECT COUNT(*) FROM firm_documents WHERE firm_id = :firm_id"), {"firm_id": firm_id})
            doc_count = result.scalar()
            print(f"✅ Documents in database for this firm: {doc_count}")
            
            # Check if it's in S3
            if not document.file_path.startswith('uploads/'):
                print(f"✅ Document stored in S3: s3://{os.getenv('AWS_S3_BUCKET')}/{document.file_path}")
                
                # Test S3 access
                from app.services.s3_service import S3Service
                s3_service = S3Service()
                if s3_service.file_exists(document.file_path):
                    print("✅ File confirmed to exist in S3")
                    
                    # Generate download URL
                    download_url = s3_service.get_file_url(document.file_path)
                    print(f"✅ Generated download URL: {download_url[:50]}...")
                else:
                    print("❌ File not found in S3")
            else:
                print(f"✅ Document stored locally: {document.file_path}")
            
            await db.close()
            return True
            
        except Exception as e:
            print(f"❌ Upload failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        break

if __name__ == "__main__":
    success = asyncio.run(test_direct_upload())
    if success:
        print("\n🎉 Direct upload test successful! The upload functionality is working.")
        print("💡 The issue is likely in the API authentication or endpoint.")
    else:
        print("\n❌ Direct upload test failed. There's an issue with the upload logic.")
    
    sys.exit(0 if success else 1)