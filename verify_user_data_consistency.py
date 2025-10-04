#!/usr/bin/env python3
"""
Verify user data consistency in panic_requests table
"""
import asyncio
from app.core.database import AsyncSessionLocal
from sqlalchemy import select, text

async def verify_data_consistency():
    """Verify that panic_requests have correct user_id for requester_phone"""
    
    async with AsyncSessionLocal() as db:
        try:
            # Check for any mismatched phone numbers and user IDs
            query = text("""
                SELECT 
                    pr.id,
                    pr.requester_phone,
                    pr.user_id as panic_request_user_id,
                    ru_correct.id as correct_user_id,
                    ru_correct.first_name as correct_first_name,
                    ru_correct.last_name as correct_last_name,
                    ru_wrong.first_name as wrong_first_name,
                    ru_wrong.last_name as wrong_last_name
                FROM panic_requests pr
                LEFT JOIN registered_users ru_correct ON pr.requester_phone = ru_correct.phone
                LEFT JOIN registered_users ru_wrong ON pr.user_id = ru_wrong.id
                WHERE pr.user_id != ru_correct.id
                ORDER BY pr.requester_phone;
            """)
            
            result = await db.execute(query)
            mismatches = result.fetchall()
            
            if mismatches:
                print("❌ DATA INCONSISTENCIES FOUND:")
                print("-" * 80)
                for mismatch in mismatches:
                    print(f"Request ID: {mismatch.id}")
                    print(f"Phone: {mismatch.requester_phone}")
                    print(f"Current user_id points to: {mismatch.wrong_first_name} {mismatch.wrong_last_name}")
                    print(f"Should point to: {mismatch.correct_first_name} {mismatch.correct_last_name}")
                    print(f"Correct user_id: {mismatch.correct_user_id}")
                    print("-" * 40)
            else:
                print("✅ ALL DATA IS CONSISTENT!")
                
            # Show summary of phone number ownership
            summary_query = text("""
                SELECT 
                    pr.requester_phone,
                    ru.first_name || ' ' || ru.last_name as owner_name,
                    ru.email,
                    COUNT(*) as request_count
                FROM panic_requests pr
                LEFT JOIN registered_users ru ON pr.user_id = ru.id
                GROUP BY pr.requester_phone, ru.first_name, ru.last_name, ru.email
                ORDER BY pr.requester_phone;
            """)
            
            summary_result = await db.execute(summary_query)
            summary_data = summary_result.fetchall()
            
            print("\n📊 PHONE NUMBER OWNERSHIP SUMMARY:")
            print("-" * 60)
            for row in summary_data:
                print(f"{row.requester_phone} → {row.owner_name} ({row.email}) - {row.request_count} requests")
                
        except Exception as e:
            print(f"❌ Verification failed with error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify_data_consistency())