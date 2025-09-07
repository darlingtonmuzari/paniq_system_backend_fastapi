#!/usr/bin/env python3
"""
Check and update firm status for coverage area testing
"""
import asyncio
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.core.database import get_db
from sqlalchemy import select, text

async def check_and_update_firm():
    """Check firm status and update if needed"""
    print("Checking firm status...")
    
    firm_id = "e178e9f4-01cb-4c8e-910f-9586516172d6"
    
    async for db in get_db():
        try:
            # Check current firm status
            result = await db.execute(text("""
                SELECT id, name, verification_status, credit_balance
                FROM security_firms 
                WHERE id = :firm_id
            """), {"firm_id": firm_id})
            
            firm = result.fetchone()
            
            if firm:
                print(f"Firm found: {firm.name}")
                print(f"Status: {firm.verification_status}")
                print(f"Credits: {firm.credit_balance}")
                
                if firm.verification_status != "approved":
                    print(f"\nUpdating firm status to 'approved'...")
                    await db.execute(text("""
                        UPDATE security_firms 
                        SET verification_status = 'approved'
                        WHERE id = :firm_id
                    """), {"firm_id": firm_id})
                    
                    await db.commit()
                    print("✅ Firm status updated to approved")
                else:
                    print("✅ Firm is already approved")
            else:
                print("❌ Firm not found")
                
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
        
        break

if __name__ == "__main__":
    asyncio.run(check_and_update_firm())