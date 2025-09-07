#!/usr/bin/env python3
"""
Test the firm applications list endpoint to debug why it returns empty
"""
import asyncio
import sys
import os

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import get_db
from app.api.v1.firm_applications import list_firm_applications
from app.services.auth import UserContext
from uuid import UUID

async def test_firm_applications_list():
    """Test the firm applications list endpoint"""
    
    print("🔍 Testing firm applications list endpoint...")
    
    # Get database session
    async for db in get_db():
        try:
            from sqlalchemy import text
            
            # Step 1: Check what applications exist in database
            print("\n1️⃣ Checking existing applications in database...")
            result = await db.execute(text("""
                SELECT fa.id, fa.firm_id, fa.status, sf.name as firm_name
                FROM firm_applications fa
                JOIN security_firms sf ON fa.firm_id = sf.id
                ORDER BY fa.created_at DESC
            """))
            
            applications = result.fetchall()
            print(f"   📊 Found {len(applications)} applications in database:")
            for app in applications:
                print(f"      - {app[0]} | {app[3]} | {app[2]}")
            
            if not applications:
                print("   ❌ No applications found in database")
                return False
            
            # Step 2: Check firm users
            print("\n2️⃣ Checking firm users...")
            result = await db.execute(text("""
                SELECT fu.user_id, fu.firm_id, fu.role, fu.status, ru.email
                FROM firm_users fu
                JOIN registered_users ru ON fu.user_id = ru.id
                ORDER BY fu.created_at DESC
            """))
            
            firm_users = result.fetchall()
            print(f"   👥 Found {len(firm_users)} firm users:")
            for user in firm_users:
                print(f"      - {user[4]} | {user[1]} | {user[2]} | {user[3]}")
            
            # Step 3: Test with admin user context
            print("\n3️⃣ Testing with admin user context...")
            admin_user = UserContext(
                user_id=UUID("8e107be0-7477-4fe8-8103-490d55351738"),
                user_type="registered_user",
                email="admin@paniq.co.za",
                permissions=["admin:all"],
                role="admin"
            )
            
            print(f"   Admin permissions: {admin_user.permissions}")
            print(f"   Has admin:all: {admin_user.has_permission('admin:all')}")
            
            try:
                admin_result = await list_firm_applications(
                    page=1,
                    per_page=10,
                    status_filter=None,
                    firm_id=None,
                    current_user=admin_user,
                    db=db
                )
                
                print(f"   ✅ Admin result: {len(admin_result.applications)} applications")
                print(f"      Total: {admin_result.total}")
                for app in admin_result.applications:
                    print(f"         - {app.id} | {app.firm_name} | {app.status}")
                
            except Exception as e:
                print(f"   ❌ Admin test failed: {e}")
                import traceback
                traceback.print_exc()
            
            # Step 4: Test with regular user context
            print("\n4️⃣ Testing with regular user context...")
            regular_user = UserContext(
                user_id=UUID("8e107be0-7477-4fe8-8103-490d55351738"),
                user_type="registered_user",
                email="darlington@manicasolutions.com",
                permissions=[],
                role="user"
            )
            
            print(f"   Regular permissions: {regular_user.permissions}")
            print(f"   Has admin:all: {regular_user.has_permission('admin:all')}")
            
            try:
                regular_result = await list_firm_applications(
                    page=1,
                    per_page=10,
                    status_filter=None,
                    firm_id=None,
                    current_user=regular_user,
                    db=db
                )
                
                print(f"   ✅ Regular user result: {len(regular_result.applications)} applications")
                print(f"      Total: {regular_result.total}")
                for app in regular_result.applications:
                    print(f"         - {app.id} | {app.firm_name} | {app.status}")
                
            except Exception as e:
                print(f"   ❌ Regular user test failed: {e}")
                import traceback
                traceback.print_exc()
            
            # Step 5: Test authorization logic manually
            print("\n5️⃣ Testing authorization logic manually...")
            
            # Check what firm IDs the user has access to
            from app.models.security_firm import FirmUser
            from sqlalchemy import select, and_
            
            user_firms_query = select(FirmUser.firm_id).where(
                and_(
                    FirmUser.user_id == regular_user.user_id,
                    FirmUser.status == "active"
                )
            )
            user_firm_ids = (await db.execute(user_firms_query)).scalars().all()
            
            print(f"   User firm IDs: {[str(fid) for fid in user_firm_ids]}")
            
            if user_firm_ids:
                # Check applications for these firms
                from app.models.security_firm import FirmApplication
                apps_query = select(FirmApplication).where(
                    FirmApplication.firm_id.in_(user_firm_ids)
                )
                user_apps = (await db.execute(apps_query)).scalars().all()
                
                print(f"   Applications for user's firms: {len(user_apps)}")
                for app in user_apps:
                    print(f"      - {app.id} | {app.firm_id} | {app.status}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error during testing: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            await db.close()
        
        break

if __name__ == "__main__":
    success = asyncio.run(test_firm_applications_list())
    
    if success:
        print("\n🎉 FIRM APPLICATIONS LIST TEST COMPLETED!")
        print("💡 Check the results above to see why the endpoint returns empty.")
    else:
        print("\n❌ FIRM APPLICATIONS LIST TEST FAILED!")
        print("💡 Check the error messages above for details.")
    
    sys.exit(0 if success else 1)