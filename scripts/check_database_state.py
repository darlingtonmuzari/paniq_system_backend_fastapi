#!/usr/bin/env python3
"""
Check database state for debugging
"""
import asyncio
import sys
import os

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import get_db
from sqlalchemy import select, text

async def check_database_state():
    """Check the current state of the database"""
    
    print("🔍 Checking database state...")
    
    async for db in get_db():
        try:
            # Check users (registered_users table)
            result = await db.execute(text("SELECT COUNT(*) FROM registered_users"))
            user_count = result.scalar()
            print(f"👥 Users in database: {user_count}")
            
            # Check security firms
            result = await db.execute(text("SELECT COUNT(*) FROM security_firms"))
            firm_count = result.scalar()
            print(f"🏢 Security firms in database: {firm_count}")
            
            # Check firm users (associations)
            result = await db.execute(text("SELECT COUNT(*) FROM firm_users"))
            firm_user_count = result.scalar()
            print(f"🔗 Firm-user associations: {firm_user_count}")
            
            # Check documents
            result = await db.execute(text("SELECT COUNT(*) FROM firm_documents"))
            doc_count = result.scalar()
            print(f"📄 Documents in database: {doc_count}")
            
            # Check document types
            result = await db.execute(text("SELECT COUNT(*) FROM document_types"))
            doc_type_count = result.scalar()
            print(f"📋 Document types configured: {doc_type_count}")
            
            if doc_type_count > 0:
                print("\n📋 Available document types:")
                result = await db.execute(text("SELECT code, name, is_required FROM document_types ORDER BY name"))
                for row in result.fetchall():
                    required = "✅ Required" if row[2] else "⚪ Optional"
                    print(f"   - {row[0]}: {row[1]} ({required})")
            
            # Check specific firm if it exists
            firm_id = "e178e9f4-01cb-4c8e-910f-9586516172d6"
            result = await db.execute(text("SELECT name, verification_status FROM security_firms WHERE id = :firm_id"), {"firm_id": firm_id})
            firm_data = result.fetchone()
            
            if firm_data:
                print(f"\n🏢 Firm {firm_id}:")
                print(f"   Name: {firm_data[0]}")
                print(f"   Status: {firm_data[1]}")
                
                # Check firm users
                result = await db.execute(text("""
                    SELECT u.email, fu.role, fu.status 
                    FROM firm_users fu 
                    JOIN registered_users u ON fu.user_id = u.id 
                    WHERE fu.firm_id = :firm_id
                """), {"firm_id": firm_id})
                
                firm_users = result.fetchall()
                if firm_users:
                    print(f"   👥 Users:")
                    for user in firm_users:
                        print(f"      - {user[0]} ({user[1]}, {user[2]})")
                else:
                    print(f"   👥 No users associated with this firm")
                
                # Check firm documents
                result = await db.execute(text("""
                    SELECT document_type, file_name, file_path, created_at 
                    FROM firm_documents 
                    WHERE firm_id = :firm_id 
                    ORDER BY created_at DESC
                """), {"firm_id": firm_id})
                
                firm_docs = result.fetchall()
                if firm_docs:
                    print(f"   📄 Documents:")
                    for doc in firm_docs:
                        print(f"      - {doc[0]}: {doc[1]} ({doc[2]}) - {doc[3]}")
                else:
                    print(f"   📄 No documents uploaded for this firm")
            else:
                print(f"\n❌ Firm {firm_id} not found in database")
            
            await db.close()
            
        except Exception as e:
            print(f"❌ Database error: {e}")
            return False
        
        break
    
    return True

if __name__ == "__main__":
    success = asyncio.run(check_database_state())
    sys.exit(0 if success else 1)