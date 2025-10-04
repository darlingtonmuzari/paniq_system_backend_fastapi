#!/usr/bin/env python3

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.core.database import AsyncSessionLocal
from sqlalchemy import text

async def fix_test_data():
    async with AsyncSessionLocal() as db:
        try:
            # The token is for firm: 804972bd-f3c0-497f-aeee-254711fd107c
            firm_id = '804972bd-f3c0-497f-aeee-254711fd107c'
            
            # Check if this firm has any teams
            result = await db.execute(text("""
                SELECT id, name
                FROM teams
                WHERE firm_id = :firm_id AND is_active = true
                LIMIT 3
            """), {'firm_id': firm_id})
            
            teams = result.fetchall()
            print(f"Found {len(teams)} teams for firm {firm_id}:")
            for team in teams:
                print(f"  - Team: {team.id}, Name: {team.name}")
                
            if not teams:
                # Create a team for this firm
                await db.execute(text("""
                    INSERT INTO teams (id, firm_id, name, is_active, created_at, updated_at)
                    VALUES (gen_random_uuid(), :firm_id, 'Test Team Alpha', true, NOW(), NOW())
                """), {'firm_id': firm_id})
                
                # Get the created team
                result = await db.execute(text("""
                    SELECT id, name
                    FROM teams
                    WHERE firm_id = :firm_id AND name = 'Test Team Alpha'
                """), {'firm_id': firm_id})
                
                team = result.fetchone()
                print(f"Created new team: {team.id}, Name: {team.name}")
                teams = [team]
                
            # Now update the panic request to assign it to this firm's team
            team_id = teams[0].id
            
            # First, delete any existing test requests to avoid duplicates
            await db.execute(text("""
                DELETE FROM panic_requests 
                WHERE description LIKE '%requester_name field%'
            """))
            
            # Get a user group
            result = await db.execute(text("""
                SELECT ug.id as group_id, ru.first_name, ru.last_name, ru.email
                FROM user_groups ug 
                JOIN registered_users ru ON ug.user_id = ru.id 
                LIMIT 1
            """))
            group = result.fetchone()
            
            if group:
                # Create the test panic request assigned to the correct firm's team
                await db.execute(text("""
                    INSERT INTO panic_requests 
                    (id, group_id, requester_phone, service_type, location, address, description, status, assigned_team_id, created_at, updated_at)
                    VALUES 
                    (gen_random_uuid(), :group_id, '+27823456789', 'security', ST_GeomFromText('POINT(28.0473 -26.2041)', 4326), 'Test Address, Johannesburg', 'Test panic request for requester_name field', 'assigned', :team_id, NOW(), NOW())
                """), {
                    'group_id': group.group_id,
                    'team_id': team_id
                })
                
                await db.commit()
                print(f"✅ Created test panic request assigned to team {team_id} from firm {firm_id}")
                print(f"   Request by: {group.first_name} {group.last_name} ({group.email})")
            else:
                print("❌ No user groups found")
                
        except Exception as e:
            await db.rollback()
            print(f"❌ Error: {e}")

asyncio.run(fix_test_data())