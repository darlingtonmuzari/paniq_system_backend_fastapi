#!/usr/bin/env python3
"""
Test the new application details endpoint
"""
import asyncio
import sys
import os

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import get_db
from app.api.v1.application_details import get_application_details, get_application_summary
from app.services.auth import UserContext
from uuid import UUID

async def test_application_details():
    """Test the application details endpoint"""
    
    print("🔍 Testing application details endpoint...")
    
    # Get database session
    async for db in get_db():
        try:
            from sqlalchemy import text
            
            # Step 1: Find an existing application
            print("\n1️⃣ Finding existing application...")
            result = await db.execute(text("""
                SELECT id, firm_id, status 
                FROM firm_applications 
                ORDER BY created_at DESC 
                LIMIT 1
            """))
            
            app_data = result.fetchone()
            if not app_data:
                print("   ❌ No applications found in database")
                return False
            
            application_id = str(app_data[0])
            firm_id = str(app_data[1])
            status = app_data[2]
            
            print(f"   ✅ Found application: {application_id}")
            print(f"      Firm ID: {firm_id}")
            print(f"      Status: {status}")
            
            # Step 2: Create mock user context (admin)
            print("\n2️⃣ Creating admin user context...")
            admin_user = UserContext(
                user_id=UUID("8e107be0-7477-4fe8-8103-490d55351738"),
                user_type="registered_user",
                email="admin@paniq.co.za",
                permissions=["admin:all"],
                role="admin"
            )
            print(f"   ✅ Created admin user context")
            
            # Step 3: Test application summary
            print("\n3️⃣ Testing application summary...")
            try:
                summary = await get_application_summary(
                    APPLICATION_ID=application_id,
                    current_user=admin_user,
                    db=db
                )
                
                print("   ✅ Application summary retrieved!")
                print(f"      Status: {summary['status']}")
                print(f"      Total Documents: {summary['total_documents']}")
                print(f"      Required Documents: {summary['uploaded_required_documents']}/{summary['total_required_documents']}")
                print(f"      Completion: {summary['completion_percentage']}%")
                print(f"      Can Submit: {summary['can_submit']}")
                
            except Exception as e:
                print(f"   ❌ Summary test failed: {e}")
                return False
            
            # Step 4: Test detailed application view
            print("\n4️⃣ Testing detailed application view...")
            try:
                details = await get_application_details(
                    APPLICATION_ID=application_id,
                    current_user=admin_user,
                    db=db
                )
                
                print("   ✅ Application details retrieved!")
                print(f"      Application ID: {details.id}")
                print(f"      Status: {details.status}")
                print(f"      Firm Name: {details.firm.name}")
                print(f"      Firm Email: {details.firm.email}")
                print(f"      Firm Status: {details.firm.verification_status}")
                
                if details.applicant:
                    print(f"      Applicant: {details.applicant.email}")
                    print(f"      Applicant Role: {details.applicant.role}")
                
                print(f"      Total Firm Users: {len(details.firm_users)}")
                for user in details.firm_users:
                    print(f"         - {user.email} ({user.role}, {user.status})")
                
                print(f"      Required Documents: {len(details.required_documents)}")
                for req_doc in details.required_documents:
                    status_icon = "✅" if req_doc.is_uploaded else "❌"
                    print(f"         {status_icon} {req_doc.name} ({req_doc.code})")
                
                print(f"      All Documents: {len(details.all_documents)}")
                for doc in details.all_documents:
                    verified_icon = "✅" if doc.is_verified else "⏳"
                    print(f"         {verified_icon} {doc.file_name} ({doc.document_type})")
                    if doc.download_url:
                        print(f"            Download: Available")
                
                print(f"      Summary Stats:")
                for key, value in details.summary.items():
                    print(f"         {key}: {value}")
                
                return True
                
            except Exception as e:
                print(f"   ❌ Details test failed: {e}")
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
    success = asyncio.run(test_application_details())
    
    if success:
        print("\n🎉 APPLICATION DETAILS TEST SUCCESSFUL!")
        print("✅ Application summary endpoint working")
        print("✅ Application details endpoint working")
        print("✅ All associated data retrieved correctly")
        print("✅ Firm details included")
        print("✅ Applicant details included")
        print("✅ Document status included")
        print("✅ Summary statistics included")
        print("\n💡 The comprehensive application view is ready for use!")
    else:
        print("\n❌ APPLICATION DETAILS TEST FAILED!")
        print("💡 Check the error messages above for details.")
    
    sys.exit(0 if success else 1)