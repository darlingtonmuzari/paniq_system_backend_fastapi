#!/usr/bin/env python3
"""
Migrate service providers to emergency providers table
"""

import asyncio
import asyncpg
import uuid
from typing import Dict, Any

# Database connection
DATABASE_URL = "postgresql://postgres:password@localhost:5433/panic_system"

# Service type mapping to emergency provider types
SERVICE_TYPE_MAPPING = {
    'security': 'd3cfde69-cb37-4e6f-ad90-e0c5ae5db956',      # Security
    'roadside': '6d44c983-f688-435e-9473-814ee0c3ccdd',      # Roadside Assistance  
    'ambulance': '3518e746-40d3-4a47-ac05-9b29d1a0a74f',    # Ambulance
    'medical': 'a66e6f1c-4a46-4afb-a2a3-d8ddd5534b63',      # Medical
    'fire': '2c5360c5-d6de-490b-ab37-cd59e7eecc31',         # Fire Department
}

# Provider type enum mapping
PROVIDER_TYPE_ENUM_MAPPING = {
    'security': 'SECURITY',
    'roadside': 'TOW_TRUCK',  # Map roadside to tow truck
    'ambulance': 'AMBULANCE',
    'medical': 'AMBULANCE',   # Map medical to ambulance
    'fire': 'FIRE_DEPARTMENT',
}

async def migrate_providers():
    """Migrate service providers to emergency providers"""
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # Get service providers for the specific firm
        firm_id = 'e178e9f4-01cb-4c8e-910f-9586516172d6'
        
        service_providers = await conn.fetch("""
            SELECT * FROM service_providers 
            WHERE firm_id = $1 AND is_active = true
        """, firm_id)
        
        print(f"Found {len(service_providers)} service providers to migrate")
        
        migrated_count = 0
        
        for sp in service_providers:
            # Check if already migrated
            existing = await conn.fetchval("""
                SELECT id FROM emergency_providers 
                WHERE name = $1 AND firm_id = $2
            """, sp['name'], sp['firm_id'])
            
            if existing:
                print(f"Skipping {sp['name']} - already exists in emergency_providers")
                continue
            
            # Get coordinates from PostGIS point
            coords = await conn.fetchrow("""
                SELECT ST_X(location) as longitude, ST_Y(location) as latitude
                FROM service_providers WHERE id = $1
            """, sp['id'])
            
            # Map service type to emergency provider type
            service_type = sp['service_type']
            provider_type_id = SERVICE_TYPE_MAPPING.get(service_type)
            provider_type_enum = PROVIDER_TYPE_ENUM_MAPPING.get(service_type)
            
            if not provider_type_id or not provider_type_enum:
                print(f"Unknown service type: {service_type} for {sp['name']}")
                continue
            
            # Create emergency provider record
            new_id = str(uuid.uuid4())
            
            await conn.execute("""
                INSERT INTO emergency_providers (
                    id, firm_id, name, provider_type, provider_type_id,
                    contact_phone, contact_email,
                    current_latitude, current_longitude,
                    base_latitude, base_longitude,
                    coverage_radius_km, status, is_active,
                    description, created_at, updated_at, last_location_update
                ) VALUES (
                    $1, $2, $3, $4, $5,
                    $6, $7,
                    $8, $9,
                    $10, $11,
                    $12, $13, $14,
                    $15, $16, $17, $18
                )
            """, 
                new_id,                               # id
                sp['firm_id'],                        # firm_id  
                sp['name'],                           # name
                provider_type_enum,                   # provider_type (enum)
                provider_type_id,                     # provider_type_id (UUID)
                sp['phone'],                          # contact_phone
                sp['email'],                          # contact_email
                coords['latitude'],                   # current_latitude
                coords['longitude'],                  # current_longitude
                coords['latitude'],                   # base_latitude (same as current)
                coords['longitude'],                  # base_longitude (same as current)
                50.0,                                 # coverage_radius_km (default)
                'AVAILABLE',                          # status
                sp['is_active'],                      # is_active
                f"Migrated from service_providers - {sp['address']}", # description
                sp['created_at'],                     # created_at
                sp['updated_at'],                     # updated_at
                sp['updated_at']                      # last_location_update
            )
            
            migrated_count += 1
            print(f"✅ Migrated: {sp['name']} ({service_type} -> {provider_type_enum})")
        
        print(f"\n🎉 Successfully migrated {migrated_count} providers!")
        
        # Verify migration
        emergency_providers = await conn.fetch("""
            SELECT name, provider_type FROM emergency_providers 
            WHERE firm_id = $1
        """, firm_id)
        
        print(f"\nVerification - Emergency providers for firm:")
        for ep in emergency_providers:
            print(f"  - {ep['name']} ({ep['provider_type']})")
            
    except Exception as e:
        print(f"Error during migration: {e}")
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(migrate_providers())