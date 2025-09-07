#!/usr/bin/env python3
"""
Check existing users and their credentials
"""
import asyncio
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.core.database import get_db
from sqlalchemy import select, text

async def check_users():
    """Check existing users in the database"""
    print("Checking existing users...")
    
    async for db in get_db():
        try:
            # Check firm personnel (your user type)
            print("\n1. Checking firm personnel...")
            result = await db.execute(text("""
                SELECT id, first_name, last_name, email, role, firm_id, is_active
                FROM firm_personnel 
                WHERE role = 'firm_admin'
                LIMIT 10
            """))
            
            firm_personnel = result.fetchall()
            
            if firm_personnel:
                print(f"Found {len(firm_personnel)} firm admin users:")
                for user in firm_personnel:
                    print(f"  - {user.first_name} {user.last_name} ({user.email})")
                    print(f"    ID: {user.id}, Firm ID: {user.firm_id}, Active: {user.is_active}")
            else:
                print("No firm admin users found")
            
            # Check registered users
            print("\n2. Checking registered users...")
            result = await db.execute(text("""
                SELECT id, first_name, last_name, email, is_active
                FROM registered_users 
                LIMIT 10
            """))
            
            registered_users = result.fetchall()
            
            if registered_users:
                print(f"Found {len(registered_users)} registered users:")
                for user in registered_users:
                    print(f"  - {user.first_name} {user.last_name} ({user.email})")
                    print(f"    ID: {user.id}, Active: {user.is_active}")
            else:
                print("No registered users found")
            
            # Check security firms
            print("\n3. Checking security firms...")
            result = await db.execute(text("""
                SELECT id, name, email, verification_status, credit_balance
                FROM security_firms 
                LIMIT 10
            """))
            
            firms = result.fetchall()
            
            if firms:
                print(f"Found {len(firms)} security firms:")
                for firm in firms:
                    print(f"  - {firm.name} ({firm.email})")
                    print(f"    ID: {firm.id}, Status: {firm.verification_status}, Credits: {firm.credit_balance}")
            else:
                print("No security firms found")
                
        except Exception as e:
            print(f"Error checking users: {e}")
            import traceback
            traceback.print_exc()
        
        break

if __name__ == "__main__":
    asyncio.run(check_users())