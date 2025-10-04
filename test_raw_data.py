#!/usr/bin/env python3

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.core.database import AsyncSessionLocal
from sqlalchemy import text

async def create_test_data():
    async with AsyncSessionLocal() as db:
        try:
            # Check if we have any user groups and users
            result = await db.execute(text("""
                SELECT ug.id as group_id, ru.first_name, ru.last_name, ru.email
                FROM user_groups ug 
                JOIN registered_users ru ON ug.user_id = ru.id 
                LIMIT 3
            """))
            groups = result.fetchall()
            
            if not groups:
                print("No user groups found!")
                return
                
            print(f"Found {len(groups)} user groups:")
            for group in groups:
                print(f"  - Group: {group.group_id}, User: {group.first_name} {group.last_name} ({group.email})")
                
            # Check if we have any teams
            result = await db.execute(text("""
                SELECT id, name, firm_id
                FROM teams
                WHERE is_active = true
                LIMIT 3
            """))
            teams = result.fetchall()
            
            print(f"\nFound {len(teams)} active teams:")
            for team in teams:
                print(f"  - Team: {team.id}, Name: {team.name}, Firm: {team.firm_id}")
                
            if groups and teams:
                # Create a test panic request
                group = groups[0]
                team = teams[0]
                
                await db.execute(text("""
                    INSERT INTO panic_requests 
                    (id, group_id, requester_phone, service_type, location, address, description, status, assigned_team_id, created_at, updated_at)
                    VALUES 
                    (gen_random_uuid(), :group_id, '+27823456789', 'security', ST_GeomFromText('POINT(28.0473 -26.2041)', 4326), 'Test Address, Johannesburg', 'Test panic request for requester_name field', 'assigned', :team_id, NOW(), NOW())
                """), {
                    'group_id': group.group_id,
                    'team_id': team.id
                })
                
                await db.commit()
                print(f"\n✅ Created test panic request for group {group.group_id} assigned to team {team.id}")
                
            else:
                print("Cannot create test request - missing groups or teams")
                
        except Exception as e:
            await db.rollback()
            print(f"❌ Error: {e}")

asyncio.run(create_test_data())