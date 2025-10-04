#!/usr/bin/env python3
"""
Check if emergency provider database tables exist and create them if needed
"""
import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.append('/home/melcy/Programming/kiro/paniq_system')

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.database import Base
from app.models.emergency_provider import EmergencyProvider, EmergencyProviderType, ProviderAssignment

async def check_and_create_tables():
    """Check database tables and create if missing"""
    
    print("🔍 Checking Emergency Provider Database Tables")
    print("=" * 60)
    
    # Try the database URL from config
    DATABASE_URL = "postgresql+asyncpg://manica_dev_admin:M1n931solutions*b0b5@postgresql-184662-0.cloudclusters.net:10024/panic_system_dev"
    
    try:
        engine = create_async_engine(DATABASE_URL)
        
        async with engine.begin() as conn:
            # Check if tables exist
            tables_to_check = [
                'emergency_provider_types',
                'emergency_providers', 
                'provider_assignments'
            ]
            
            existing_tables = []
            missing_tables = []
            
            for table_name in tables_to_check:
                result = await conn.execute(text(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = '{table_name}'
                    );
                """))
                exists = result.scalar()
                
                if exists:
                    existing_tables.append(table_name)
                    print(f"✅ Table exists: {table_name}")
                else:
                    missing_tables.append(table_name)
                    print(f"❌ Table missing: {table_name}")
            
            if missing_tables:
                print(f"\n🔧 Creating missing tables...")
                
                # Create all tables from Base metadata
                await conn.run_sync(Base.metadata.create_all)
                
                print(f"✅ Created all emergency provider tables")
                
                # Verify tables were created
                print(f"\n🔍 Verifying table creation...")
                for table_name in tables_to_check:
                    result = await conn.execute(text(f"""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name = '{table_name}'
                        );
                    """))
                    exists = result.scalar()
                    
                    if exists:
                        print(f"✅ Verified: {table_name}")
                    else:
                        print(f"❌ Still missing: {table_name}")
            else:
                print(f"\n✅ All tables exist!")
        
        await engine.dispose()
        return True
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

async def insert_basic_provider_types():
    """Insert basic provider types if tables are empty"""
    
    print(f"\n📋 Checking Emergency Provider Types...")
    
    DATABASE_URL = "postgresql+asyncpg://manica_dev_admin:M1n931solutions*b0b5@postgresql-184662-0.cloudclusters.net:10024/panic_system_dev"
    
    try:
        engine = create_async_engine(DATABASE_URL)
        
        async with engine.begin() as conn:
            # Check if provider types exist
            result = await conn.execute(text("SELECT COUNT(*) FROM emergency_provider_types"))
            count = result.scalar()
            
            if count == 0:
                print(f"🔧 Inserting basic provider types...")
                
                # Insert basic provider types
                provider_types = [
                    ('ambulance', 'Ambulance Service', 'Emergency medical transport services', True, 30.0, 'ambulance', '#FF6B6B', 'critical'),
                    ('tow_truck', 'Tow Truck Service', 'Vehicle recovery and roadside assistance', True, 50.0, 'truck', '#4ECDC4', 'medium'),
                    ('security', 'Security Response', 'Armed and unarmed security response teams', True, 25.0, 'shield', '#45B7D1', 'high'),
                    ('fire_department', 'Fire Department', 'Fire suppression and emergency rescue services', True, 40.0, 'fire', '#FFA500', 'critical')
                ]
                
                for code, name, desc, req_license, radius, icon, color, priority in provider_types:
                    await conn.execute(text("""
                        INSERT INTO emergency_provider_types 
                        (id, code, name, description, requires_license, default_coverage_radius_km, 
                         icon, color, priority_level, is_active)
                        VALUES (gen_random_uuid(), :code, :name, :description, :requires_license, 
                                :radius, :icon, :color, :priority_level, true)
                    """), {
                        'code': code,
                        'name': name,
                        'description': desc,
                        'requires_license': req_license,
                        'radius': radius,
                        'icon': icon,
                        'color': color,
                        'priority_level': priority
                    })
                
                print(f"✅ Inserted {len(provider_types)} provider types")
            else:
                print(f"✅ Found {count} existing provider types")
        
        await engine.dispose()
        return True
        
    except Exception as e:
        print(f"❌ Error inserting provider types: {e}")
        return False

if __name__ == "__main__":
    print("Starting emergency provider database setup...")
    
    async def main():
        success = await check_and_create_tables()
        if success:
            await insert_basic_provider_types()
            print(f"\n🎉 Emergency provider database setup complete!")
            return True
        else:
            print(f"\n💔 Database setup failed")
            return False
    
    result = asyncio.run(main())
    exit(0 if result else 1)