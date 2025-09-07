#!/usr/bin/env python3
"""
Debug document upload issues
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
from app.services.s3_service import S3Service
from app.core.config import settings
from fastapi import UploadFile
import io

async def debug_upload():
    """Debug the upload process step by step"""
    
    print("🔍 Debugging document upload process...")
    
    # Test S3 connection first
    print("\n1. Testing S3 connection...")
    try:
        s3_service = S3Service()
        print(f"✅ S3 service initialized successfully")
        print(f"   Bucket: {settings.AWS_S3_BUCKET}")
        print(f"   Region: {settings.AWS_REGION_NAME}")
    except Exception as e:
        print(f"❌ S3 service initialization failed: {e}")
        return False
    
    # Test file upload to S3 directly
    print("\n2. Testing direct S3 upload...")
    try:
        test_content = b"Test document content for debugging"
        
        # Create a mock UploadFile
        class MockUploadFile:
            def __init__(self, content, filename, content_type):
                self.file = io.BytesIO(content)
                self.filename = filename
                self.content_type = content_type
            
            async def read(self):
                return self.file.getvalue()
        
        mock_file = MockUploadFile(test_content, "test_debug.pdf", "application/pdf")
        
        s3_key, file_size = await s3_service.upload_file(
            mock_file, 
            "debug_test", 
            "test_document"
        )
        
        print(f"✅ Direct S3 upload successful")
        print(f"   S3 Key: {s3_key}")
        print(f"   File Size: {file_size}")
        
        # Clean up test file
        s3_service.delete_file(s3_key)
        print(f"✅ Test file cleaned up")
        
    except Exception as e:
        print(f"❌ Direct S3 upload failed: {e}")
        return False
    
    # Test database connection
    print("\n3. Testing database connection...")
    try:
        async for db in get_db():
            service = SecurityFirmService(db)
            print("✅ Database connection successful")
            
            # Test if we can query firm documents
            from sqlalchemy import select, text
            result = await db.execute(text("SELECT COUNT(*) FROM firm_documents"))
            count = result.scalar()
            print(f"✅ Current documents in database: {count}")
            
            await db.close()
            break
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
    
    print("\n4. Testing configuration...")
    print(f"   AWS_S3_BUCKET: {settings.AWS_S3_BUCKET}")
    print(f"   AWS_ACCESS_KEY_ID: {settings.AWS_ACCESS_KEY_ID[:10]}..." if settings.AWS_ACCESS_KEY_ID else "   AWS_ACCESS_KEY_ID: Not set")
    print(f"   AWS_SECRET_ACCESS_KEY: {'Set' if settings.AWS_SECRET_ACCESS_KEY else 'Not set'}")
    print(f"   AWS_REGION_NAME: {settings.AWS_REGION_NAME}")
    
    print("\n✅ All components are working individually!")
    print("The issue might be in the API endpoint or authentication.")
    
    return True

if __name__ == "__main__":
    success = asyncio.run(debug_upload())
    sys.exit(0 if success else 1)