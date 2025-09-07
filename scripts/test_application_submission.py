#!/usr/bin/env python3
"""
Test application submission to see if it recognizes uploaded documents
"""
import asyncio
import sys
import os

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import get_db
from app.services.security_firm import SecurityFirmService

async def test_application_submission():
    """Test if application submission now works with uploaded documents"""
    
    print("🔍 Testing application submission...")
    
    firm_id = "e178e9f4-01cb-4c8e-910f-9586516172d6"
    
    # Get database session
    async for db in get_db():
        try:
            # Get the user ID for the firm admin
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
            
            # Check current documents
            result = await db.execute(text("""
                SELECT document_type, file_name 
                FROM firm_documents 
                WHERE firm_id = :firm_id
            """), {"firm_id": firm_id})
            
            documents = result.fetchall()
            print(f"📄 Current documents for firm:")
            for doc in documents:
                print(f"   - {doc[0]}: {doc[1]}")
            
            # Check required documents
            from app.services.document_type import DocumentTypeService
            doc_type_service = DocumentTypeService(db)
            required_docs = await doc_type_service.get_required_documents()
            
            print(f"📋 Required documents:")
            for doc_type in required_docs:
                print(f"   - {doc_type.code}: {doc_type.name}")
            
            # Test application submission
            service = SecurityFirmService(db)
            
            print("🚀 Attempting application submission...")
            
            try:
                application = await service.submit_application(
                    firm_id=firm_id,
                    user_id=user_id
                )
                
                print("✅ Application submitted successfully!")
                print(f"   Application ID: {application.id}")
                print(f"   Status: {application.status}")
                print(f"   Submitted at: {application.submitted_at}")
                
                # Check firm status
                result = await db.execute(text("SELECT verification_status FROM security_firms WHERE id = :firm_id"), {"firm_id": firm_id})
                firm_status = result.scalar()
                print(f"   Firm status: {firm_status}")
                
                return True
                
            except ValueError as e:
                print(f"❌ Application submission failed: {e}")
                
                # Let's debug what's missing
                print("\n🔍 Debugging missing documents...")
                
                # Get uploaded document types
                uploaded_types = [doc[0] for doc in documents]
                required_codes = [doc_type.code for doc_type in required_docs]
                
                missing_docs = [code for code in required_codes if code not in uploaded_types]
                
                print(f"   Uploaded types: {uploaded_types}")
                print(f"   Required codes: {required_codes}")
                print(f"   Missing: {missing_docs}")
                
                return False
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            await db.close()
        
        break

if __name__ == "__main__":
    success = asyncio.run(test_application_submission())
    
    if success:
        print("\n🎉 Application submission successful!")
        print("💡 The document upload and application submission are now working correctly.")
    else:
        print("\n❌ Application submission failed.")
        print("💡 Check the error messages above for details.")
    
    sys.exit(0 if success else 1)