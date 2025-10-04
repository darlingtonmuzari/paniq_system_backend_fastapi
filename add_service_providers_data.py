#!/usr/bin/env python3

import asyncio
import asyncpg
from faker import Faker
from uuid import uuid4
import random

# Database connection
DATABASE_URL = "postgresql://postgres:password@localhost:5433/panic_system"

fake = Faker()

async def main():
    """Add sample data to service_providers table"""
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        print("Connected to database successfully!")
        
        # Security firm IDs from the database
        firm_ids = [
            "249d03b8-fc0a-460b-82af-049445d15dbb",  # Platform Administration
            "e178e9f4-01cb-4c8e-910f-9586516172d6",  # Paniq Security Solutions
            "804972bd-f3c0-497f-aeee-254711fd107c"   # Manica Security Solutions
        ]
        
        # Service types available
        service_types = [
            'security', 'medical', 'fire', 'police', 'roadside', 
            'emergency', 'ambulance', 'towing', 'locksmith', 'electrician'
        ]
        
        # Sample service providers data
        service_providers = [
            {
                'id': str(uuid4()),
                'firm_id': firm_ids[0],  # Platform Administration
                'name': 'Metro Emergency Medical Services',
                'service_type': 'medical',
                'email': 'dispatch@metroemergency.co.za',
                'phone': '+27211234567',
                'address': '123 Emergency Drive, Cape Town, 8001',
                'lat': -33.9249,
                'lon': 18.4241,
                'is_active': True
            },
            {
                'id': str(uuid4()),
                'firm_id': firm_ids[0],  # Platform Administration
                'name': 'City Fire and Rescue',
                'service_type': 'fire',
                'email': 'emergency@cityfire.gov.za',
                'phone': '+27211234568',
                'address': '456 Fire Station Road, Cape Town, 8002',
                'lat': -33.9567,
                'lon': 18.4891,
                'is_active': True
            },
            {
                'id': str(uuid4()),
                'firm_id': firm_ids[1],  # Paniq Security Solutions
                'name': 'Elite Armed Response',
                'service_type': 'security',
                'email': 'ops@elitearmed.co.za',
                'phone': '+27821234570',
                'address': '789 Security Plaza, Johannesburg, 2000',
                'lat': -33.915,
                'lon': 18.424,
                'is_active': True
            },
            {
                'id': str(uuid4()),
                'firm_id': firm_ids[1],  # Paniq Security Solutions
                'name': 'Rapid Response Patrol',
                'service_type': 'security',
                'email': 'control@rapidresponse.co.za',
                'phone': '+27831234571',
                'address': '321 Patrol Avenue, Pretoria, 0001',
                'lat': -33.928,
                'lon': 18.417,
                'is_active': True
            },
            {
                'id': str(uuid4()),
                'firm_id': str(uuid4()),  # Random firm (will use existing firm)
                'name': 'Highway Towing Services',
                'service_type': 'roadside',
                'email': 'dispatch@highwaytowing.co.za',
                'phone': '+27841234572',
                'address': '654 Highway Junction, Durban, 4000',
                'lat': -33.945,
                'lon': 18.467,
                'is_active': True
            },
            {
                'id': str(uuid4()),
                'firm_id': firm_ids[2],  # Manica Security Solutions
                'name': 'Professional Locksmith Services',
                'service_type': 'locksmith',
                'email': 'help@prolocksmith.co.za',
                'phone': '+27851234573',
                'address': '987 Lock Street, Cape Town, 8003',
                'lat': -33.932,
                'lon': 18.435,
                'is_active': True
            },
            {
                'id': str(uuid4()),
                'firm_id': firm_ids[2],  # Manica Security Solutions
                'name': '24/7 Emergency Electricians',
                'service_type': 'electrician',
                'email': 'emergency@247electric.co.za',
                'phone': '+27861234574',
                'address': '111 Electric Avenue, Port Elizabeth, 6000',
                'lat': -33.925,
                'lon': 18.452,
                'is_active': True
            },
            {
                'id': str(uuid4()),
                'firm_id': firm_ids[0],  # Platform Administration
                'name': 'Metropolitan Police Services',
                'service_type': 'police',
                'email': 'control@metropolice.gov.za',
                'phone': '+27871234575',
                'address': '222 Justice Road, Cape Town, 8004',
                'lat': -33.918,
                'lon': 18.429,
                'is_active': True
            },
            {
                'id': str(uuid4()),
                'firm_id': firm_ids[1],  # Paniq Security Solutions
                'name': 'Premium Ambulance Services',
                'service_type': 'ambulance',
                'email': 'dispatch@premiumambulance.co.za',
                'phone': '+27881234576',
                'address': '333 Medical Centre, Stellenbosch, 7600',
                'lat': -33.938,
                'lon': 18.441,
                'is_active': True
            },
            {
                'id': str(uuid4()),
                'firm_id': firm_ids[2],  # Manica Security Solutions
                'name': 'General Emergency Response',
                'service_type': 'emergency',
                'email': 'response@generalemergency.co.za',
                'phone': '+27891234577',
                'address': '444 Response Plaza, Paarl, 7620',
                'lat': -33.942,
                'lon': 18.456,
                'is_active': True
            }
        ]
        
        # Use valid firm IDs for the one with random firm_id
        service_providers[4]['firm_id'] = firm_ids[1]  # Assign to Paniq Security Solutions
        
        print(f"\n=== Adding {len(service_providers)} Service Providers ===")
        
        providers_added = 0
        for provider in service_providers:
            try:
                await conn.execute("""
                    INSERT INTO service_providers (
                        id, firm_id, name, service_type, email, phone, address,
                        location, is_active, created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, 
                              ST_SetSRID(ST_MakePoint($8, $9), 4326), $10, NOW(), NOW())
                """, 
                    provider['id'],
                    provider['firm_id'],
                    provider['name'],
                    provider['service_type'],
                    provider['email'],
                    provider['phone'],
                    provider['address'],
                    provider['lon'],  # longitude first for ST_MakePoint
                    provider['lat'],  # latitude second
                    provider['is_active']
                )
                
                providers_added += 1
                print(f"✅ Added: {provider['name']} ({provider['service_type']})")
                
            except Exception as e:
                print(f"❌ Error adding {provider['name']}: {str(e)}")
        
        print(f"\n🎉 Successfully added {providers_added} service providers!")
        
        # Verify the data was added
        count_result = await conn.fetchval("SELECT COUNT(*) FROM service_providers")
        print(f"📊 Total service providers in database: {count_result}")
        
        # Show sample of added data
        sample_data = await conn.fetch("""
            SELECT sp.name, sp.service_type, sf.name as firm_name 
            FROM service_providers sp 
            JOIN security_firms sf ON sp.firm_id = sf.id 
            ORDER BY sp.created_at DESC 
            LIMIT 5
        """)
        
        print(f"\n📋 Sample of added service providers:")
        for row in sample_data:
            print(f"   • {row['name']} ({row['service_type']}) - {row['firm_name']}")
        
    except Exception as e:
        print(f"❌ Database error: {str(e)}")
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())