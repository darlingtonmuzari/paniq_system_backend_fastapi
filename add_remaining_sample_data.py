#!/usr/bin/env python3

import asyncio
import asyncpg
import bcrypt
from faker import Faker
from datetime import datetime, timedelta
from uuid import uuid4
import random
import json

# Database connection
DATABASE_URL = "postgresql://postgres:password@localhost:5433/panic_system"

fake = Faker()

async def main():
    """Add remaining sample data: users, personnel, and emergency requests"""
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        print("Connected to database successfully!")
        
        # Get existing security firm IDs
        existing_firms = await conn.fetch("SELECT id, name FROM security_firms LIMIT 10")
        if not existing_firms:
            print("No security firms found. Please run the comprehensive sample data script first.")
            return
            
        print(f"Found {len(existing_firms)} security firms to work with")
        
        # 1. Add registered users
        print("\n=== Adding Registered Users ===")
        users_added = 0
        user_ids = []
        
        for i in range(20):  # Add 20 users
            try:
                user_id = str(uuid4())
                first_name = fake.first_name()
                last_name = fake.last_name()
                email = f"{first_name.lower()}.{last_name.lower()}@example.com"
                phone = f"+2782{random.randint(1000000, 9999999)}"
                
                # Hash a simple password
                password_hash = bcrypt.hashpw("password123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                
                await conn.execute("""
                    INSERT INTO registered_users (
                        id, email, phone, first_name, last_name, password_hash,
                        is_verified, prank_flags, total_fines, is_suspended, 
                        is_locked, failed_login_attempts, role
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                """, user_id, email, phone, first_name, last_name, password_hash,
                True, 0, 0.0, False, False, 0, 'user')
                
                user_ids.append(user_id)
                users_added += 1
                print(f"Added user: {first_name} {last_name} ({email})")
                
            except Exception as e:
                if "duplicate key" in str(e):
                    print(f"Skipped duplicate user: {email}")
                    continue
                else:
                    print(f"Error adding user {i+1}: {str(e)}")
        
        print(f"Successfully added {users_added} users")
        
        # 2. Add user groups
        print("\n=== Adding User Groups ===")
        groups_added = 0
        group_ids = []
        
        for i in range(10):  # Add 10 user groups
            try:
                group_id = str(uuid4())
                user_id = random.choice(user_ids)
                group_name = f"{fake.last_name()} Family"
                address = f"{random.randint(1, 999)} {fake.street_name()}, {fake.city()}, {random.randint(1000, 9999)}"
                
                # Cape Town coordinates with some variation
                lat = -33.9249 + random.uniform(-0.5, 0.5)
                lon = 18.4241 + random.uniform(-0.5, 0.5)
                
                await conn.execute("""
                    INSERT INTO user_groups (
                        id, user_id, name, address, location,
                        subscription_expires_at
                    ) VALUES ($1, $2, $3, $4, ST_SetSRID(ST_MakePoint($5, $6), 4326), $7)
                """, group_id, user_id, group_name, address, lon, lat, 
                datetime.now() + timedelta(days=random.randint(30, 365)))
                
                group_ids.append(group_id)
                groups_added += 1
                print(f"Added group: {group_name}")
                
            except Exception as e:
                print(f"Error adding group {i+1}: {str(e)}")
        
        print(f"Successfully added {groups_added} user groups")
        
        # 3. Add firm personnel
        print("\n=== Adding Firm Personnel ===")
        personnel_added = 0
        
        for firm in existing_firms:
            firm_id = firm['id']
            firm_name = firm['name']
            
            # Add 2-4 personnel per firm
            personnel_count = random.randint(2, 4)
            
            for i in range(personnel_count):
                try:
                    personnel_id = str(uuid4())
                    first_name = fake.first_name()
                    last_name = fake.last_name()
                    email = f"{first_name.lower()}.{last_name.lower()}@{firm_name.lower().replace(' ', '').replace(',', '')}.co.za"
                    phone = f"+2782{random.randint(1000000, 9999999)}"
                    role = random.choice(['admin', 'operator', 'supervisor', 'agent'])
                    
                    # Hash password
                    password_hash = bcrypt.hashpw("password123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    
                    await conn.execute("""
                        INSERT INTO firm_personnel (
                            id, firm_id, email, phone, first_name, last_name,
                            role, is_active, password_hash, is_locked
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    """, personnel_id, str(firm_id), email, phone, first_name, last_name,
                    role, True, password_hash, False)
                    
                    personnel_added += 1
                    print(f"Added personnel: {first_name} {last_name} ({role}) to {firm_name}")
                    
                except Exception as e:
                    if "duplicate key" in str(e):
                        print(f"Skipped duplicate personnel: {email}")
                        continue
                    else:
                        print(f"Error adding personnel for {firm_name}: {str(e)}")
        
        print(f"Successfully added {personnel_added} personnel")
        
        # 4. Add panic requests
        print("\n=== Adding Panic Requests ===")
        requests_added = 0
        
        service_types = ['security', 'medical', 'fire', 'police', 'roadside']
        status_options = ['pending', 'accepted', 'dispatched', 'arrived', 'completed', 'cancelled']
        
        for i in range(15):  # Add 15 panic requests
            try:
                request_id = str(uuid4())
                group_id = random.choice(group_ids) if group_ids else str(uuid4())
                
                # Get a random phone number
                phone = f"+2782{random.randint(1000000, 9999999)}"
                service_type = random.choice(service_types)
                status = random.choice(status_options)
                
                # Random location in Cape Town area
                lat = -33.9249 + random.uniform(-0.2, 0.2)
                lon = 18.4241 + random.uniform(-0.2, 0.2)
                address = f"{random.randint(1, 999)} {fake.street_name()}, {fake.city()}"
                description = f"Emergency {service_type} assistance needed - {fake.sentence()}"
                
                # Set timestamps based on status
                created_at = datetime.now() - timedelta(hours=random.randint(1, 72))
                accepted_at = None
                arrived_at = None
                completed_at = None
                
                if status in ['accepted', 'dispatched', 'arrived', 'completed']:
                    accepted_at = created_at + timedelta(minutes=random.randint(1, 15))
                    
                if status in ['arrived', 'completed']:
                    arrived_at = accepted_at + timedelta(minutes=random.randint(5, 30))
                    
                if status == 'completed':
                    completed_at = arrived_at + timedelta(minutes=random.randint(10, 60))
                
                await conn.execute("""
                    INSERT INTO panic_requests (
                        id, group_id, requester_phone, service_type, location,
                        address, description, status, accepted_at, arrived_at,
                        completed_at, created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, ST_SetSRID(ST_MakePoint($5, $6), 4326),
                              $7, $8, $9, $10, $11, $12, $13, $14)
                """, request_id, group_id, phone, service_type, lon, lat,
                address, description, status, accepted_at, arrived_at,
                completed_at, created_at, datetime.now())
                
                requests_added += 1
                print(f"Added request: {service_type} - {status} - {address[:50]}...")
                
            except Exception as e:
                print(f"Error adding panic request {i+1}: {str(e)}")
                # Don't break, continue with next request
                continue
        
        print(f"Successfully added {requests_added} panic requests")
        
        # Summary
        print("\n" + "="*50)
        print("SAMPLE DATA ADDITION COMPLETE")
        print("="*50)
        print(f"✅ Users added: {users_added}")
        print(f"✅ User groups added: {groups_added}")  
        print(f"✅ Personnel added: {personnel_added}")
        print(f"✅ Panic requests added: {requests_added}")
        print("\nSample data is ready for testing!")
        
    except Exception as e:
        print(f"Database error: {str(e)}")
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())