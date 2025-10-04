#!/usr/bin/env python3
"""
Insert sample emergency provider data into the database
"""
import asyncio
import sys
import os
from uuid import uuid4
from datetime import datetime

# Add the app directory to Python path
sys.path.append('/home/melcy/Programming/kiro/paniq_system')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text
from app.models.emergency_provider import EmergencyProvider, EmergencyProviderType, ProviderType, ProviderStatus

async def insert_sample_data():
    """Insert sample emergency provider data"""
    
    print("🚑 Inserting Emergency Provider Sample Data")
    print("=" * 60)
    
    DATABASE_URL = "postgresql+asyncpg://postgres:password@localhost:5433/panic_system"
    
    try:
        engine = create_async_engine(DATABASE_URL)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as session:
            # First check if we need a firm_id (get existing security firm)
            result = await session.execute(text("SELECT id FROM security_firms LIMIT 1"))
            firm_row = result.fetchone()
            
            if not firm_row:
                print("❌ No security firm found. Creating a sample firm...")
                firm_id = str(uuid4())
                await session.execute(text("""
                    INSERT INTO security_firms (id, name, email, phone, address, city, province, country, postal_code, is_active)
                    VALUES (:firm_id, 'Sample Security Firm', 'admin@sample.com', '+27123456789', 
                           '123 Main St', 'Cape Town', 'Western Cape', 'South Africa', '8001', true)
                """), {'firm_id': firm_id})
                await session.commit()
                print(f"✅ Created sample firm: {firm_id}")
            else:
                firm_id = str(firm_row[0])
                print(f"✅ Using existing firm: {firm_id}")
            
            # Get provider type IDs
            result = await session.execute(text("SELECT id, code FROM emergency_provider_types WHERE is_active = true"))
            provider_types = {row[1]: str(row[0]) for row in result.fetchall()}
            
            if not provider_types:
                print("❌ No provider types found")
                return False
            
            print(f"📋 Found provider types: {list(provider_types.keys())}")
            
            # Sample emergency providers data
            sample_providers = [
                {
                    'name': 'Rapid Response Ambulance',
                    'provider_type': ProviderType.AMBULANCE,
                    'provider_type_id': provider_types.get('ambulance'),
                    'license_number': 'AMB001',
                    'contact_phone': '+27821234567',
                    'contact_email': 'dispatch@rapidresponse.co.za',
                    'street_address': '45 Medical Centre Drive',
                    'city': 'Cape Town',
                    'province': 'Western Cape',
                    'country': 'South Africa',
                    'postal_code': '7700',
                    'current_latitude': -33.9249,
                    'current_longitude': 18.4241,
                    'base_latitude': -33.9249,
                    'base_longitude': 18.4241,
                    'coverage_radius_km': 25.0,
                    'description': 'Advanced life support ambulance service',
                    'equipment_details': 'ALS equipment, cardiac monitor, ventilator',
                    'capacity': '2 patients',
                    'status': ProviderStatus.AVAILABLE
                },
                {
                    'name': 'City Tow Truck Services',
                    'provider_type': ProviderType.TOW_TRUCK,
                    'provider_type_id': provider_types.get('tow_truck'),
                    'license_number': 'TOW001',
                    'contact_phone': '+27821234568',
                    'contact_email': 'dispatch@citytow.co.za',
                    'street_address': '123 Industrial Road',
                    'city': 'Cape Town',
                    'province': 'Western Cape',
                    'country': 'South Africa',
                    'postal_code': '7800',
                    'current_latitude': -33.9352,
                    'current_longitude': 18.4742,
                    'base_latitude': -33.9352,
                    'base_longitude': 18.4742,
                    'coverage_radius_km': 50.0,
                    'description': 'Heavy duty tow truck and recovery service',
                    'equipment_details': 'Flatbed tow truck, winch system',
                    'capacity': 'Up to 3500kg',
                    'status': ProviderStatus.AVAILABLE
                },
                {
                    'name': 'Metro Fire Station 7',
                    'provider_type': ProviderType.FIRE_DEPARTMENT,
                    'provider_type_id': provider_types.get('fire_department'),
                    'license_number': 'FIRE007',
                    'contact_phone': '+27821234569',
                    'contact_email': 'station7@metrofire.gov.za',
                    'street_address': '78 Fire Station Road',
                    'city': 'Cape Town',
                    'province': 'Western Cape',
                    'country': 'South Africa',
                    'postal_code': '7900',
                    'current_latitude': -33.9567,
                    'current_longitude': 18.4891,
                    'base_latitude': -33.9567,
                    'base_longitude': 18.4891,
                    'coverage_radius_km': 15.0,
                    'description': 'Municipal fire and rescue service',
                    'equipment_details': 'Fire truck, ladder truck, rescue equipment',
                    'capacity': '6 firefighters',
                    'status': ProviderStatus.AVAILABLE
                },
                {
                    'name': 'Elite Security Response Team',
                    'provider_type': ProviderType.SECURITY,
                    'provider_type_id': provider_types.get('security'),
                    'license_number': 'SEC001',
                    'contact_phone': '+27821234570',
                    'contact_email': 'ops@elitesecurity.co.za',
                    'street_address': '234 Security Avenue',
                    'city': 'Cape Town',
                    'province': 'Western Cape',
                    'country': 'South Africa',
                    'postal_code': '8000',
                    'current_latitude': -33.9150,
                    'current_longitude': 18.4240,
                    'base_latitude': -33.9150,
                    'base_longitude': 18.4240,
                    'coverage_radius_km': 30.0,
                    'description': 'Armed response and security patrol service',
                    'equipment_details': 'Armed response vehicle, communication equipment',
                    'capacity': '2 officers',
                    'status': ProviderStatus.AVAILABLE
                }
            ]
            
            inserted_count = 0
            for provider_data in sample_providers:
                # Check if provider type exists
                if not provider_data['provider_type_id']:
                    print(f"⚠️  Skipping {provider_data['name']} - provider type not found")
                    continue
                
                # Create the provider
                provider = EmergencyProvider(
                    id=uuid4(),
                    firm_id=firm_id,
                    **provider_data
                )
                
                session.add(provider)
                inserted_count += 1
                print(f"✅ Added: {provider_data['name']} ({provider_data['provider_type'].value})")
            
            await session.commit()
            print(f"\n🎉 Successfully inserted {inserted_count} emergency providers!")
            
        await engine.dispose()
        return True
        
    except Exception as e:
        print(f"❌ Error inserting sample data: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Starting emergency provider sample data insertion...")
    
    result = asyncio.run(insert_sample_data())
    exit(0 if result else 1)