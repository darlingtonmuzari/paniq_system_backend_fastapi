#!/usr/bin/env python3

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.core.database import AsyncSessionLocal
from sqlalchemy import text

async def check_user_team():
    async with AsyncSessionLocal() as db:
        try:
            # Token user ID: a4ce8fc2-6a6e-47e3-b76e-29d53c3a627d
            user_id = 'a4ce8fc2-6a6e-47e3-b76e-29d53c3a627d'
            firm_id = '804972bd-f3c0-497f-aeee-254711fd107c'
            
            # Check if this user exists in firm_personnel
            result = await db.execute(text("""
                SELECT fp.id, fp.email, fp.role, fp.firm_id, fp.team_id,
                       t.name as team_name
                FROM firm_personnel fp
                LEFT JOIN teams t ON fp.team_id = t.id
                WHERE fp.id = :user_id
            """), {'user_id': user_id})
            
            user = result.fetchone()
            if user:
                print(f"Found user: {user.email}")
                print(f"Role: {user.role}")
                print(f"Firm ID: {user.firm_id}")
                print(f"Team ID: {user.team_id}")
                print(f"Team Name: {user.team_name}")
                
                # If they don't have a team, let's assign them to our test team
                if not user.team_id:
                    # Get the test team we created
                    result = await db.execute(text("""
                        SELECT id FROM teams WHERE firm_id = :firm_id AND name = 'Test Team Alpha'
                    """), {'firm_id': firm_id})
                    
                    team = result.fetchone()
                    if team:
                        await db.execute(text("""
                            UPDATE firm_personnel 
                            SET team_id = :team_id, updated_at = NOW()
                            WHERE id = :user_id
                        """), {
                            'team_id': team.id,
                            'user_id': user_id
                        })
                        
                        await db.commit()
                        print(f"✅ Assigned user to team {team.id}")
                    else:
                        print("❌ Test team not found")
                        
            else:
                print(f"❌ User {user_id} not found in firm_personnel table")
                
            # Now check all panic requests assigned to teams from this firm
            result = await db.execute(text("""
                SELECT pr.id, pr.service_type, pr.status, pr.description, pr.assigned_team_id,
                       t.name as team_name, t.firm_id
                FROM panic_requests pr
                JOIN teams t ON pr.assigned_team_id = t.id
                WHERE t.firm_id = :firm_id
                ORDER BY pr.created_at DESC
                LIMIT 5
            """), {'firm_id': firm_id})
            
            requests = result.fetchall()
            print(f"\nFound {len(requests)} panic requests for firm {firm_id}:")
            for req in requests:
                print(f"  - Request: {req.id}")
                print(f"    Service: {req.service_type}, Status: {req.status}")
                print(f"    Team: {req.team_name} ({req.assigned_team_id})")
                print(f"    Description: {req.description}")
                print()
                
        except Exception as e:
            await db.rollback()
            print(f"❌ Error: {e}")

asyncio.run(check_user_team())