#!/usr/bin/env python3
"""
Direct database insertion of emergency provider sample data
This bypasses the API issues and inserts data directly into the database
"""
import asyncio
import sys
import os
from uuid import uuid4, UUID

# Add the app directory to Python path
sys.path.append('/home/melcy/Programming/kiro/paniq_system')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text
from app.models.emergency_provider import EmergencyProviderType, EmergencyProvider, ProviderType, ProviderStatus
from app.models.security_firm import SecurityFirm

async def create_emergency_sample_data():
    """Create sample emergency provider data directly in database"""
    
    print("🚑 Creating Emergency Provider Sample Data (Direct DB)")
    print("=" * 70)
    
    # Multiple database URL options to try
    db_urls = [
        "postgresql+asyncpg://manica_dev_admin:M1n931solutions*b0b5@postgresql-184662-0.cloudclusters.net:10024/panic_system_dev",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/panic_system",
        "postgresql+asyncpg://user:password@localhost:5432/paniq_db",
        "postgresql+asyncpg://postgres:@localhost:5432/panic_system"
    ]
    
    engine = None
    successful_url = None
    
    for db_url in db_urls:
        try:
            print(f"Trying database connection: {db_url.split('@')[1]}")
            engine = create_async_engine(db_url)
            
            # Test connection
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            
            successful_url = db_url
            print(f"✅ Connected successfully!")
            break
            
        except Exception as e:
            print(f"❌ Failed: {e}")
            if engine:
                await engine.dispose()
            continue
    
    if not engine:
        print("\n💔 Could not connect to database with any URL")
        print("The following sample data would be created:")
        print_sample_data_summary()
        return
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session() as session:
            # First, find or create a security firm
            result = await session.execute(select(SecurityFirm).limit(1))
            firm = result.scalar_one_or_none()
            
            if not firm:
                print("\n🏢 Creating Security Firm...")
                firm = SecurityFirm(
                    name="Cape Town Security Services",
                    registration_number="REG123456", 
                    contact_phone="+27218001234",
                    contact_email="info@ctss.co.za",
                    street_address="123 Main Street",
                    city="Cape Town",
                    province="Western Cape",
                    country="South Africa",
                    postal_code="8001"
                )
                session.add(firm)
                await session.commit()
                await session.refresh(firm)
                print(f"   ✅ Created: {firm.name} (ID: {firm.id})")
            else:
                print(f"\n🏢 Using existing firm: {firm.name} (ID: {firm.id})")

            # Create emergency provider types
            print(f"\n📋 Creating Emergency Provider Types...")
            
            provider_types_data = [
                {
                    "name": "Ambulance Service",
                    "code": "ambulance",
                    "description": "Emergency medical transport and first aid services",
                    "requires_license": True,
                    "default_coverage_radius_km": 30.0,
                    "icon": "ambulance",
                    "color": "#FF6B6B",
                    "priority_level": "critical"
                },
                {
                    "name": "Tow Truck Service",
                    "code": "tow_truck", 
                    "description": "Vehicle recovery and roadside assistance",
                    "requires_license": True,
                    "default_coverage_radius_km": 50.0,
                    "icon": "truck",
                    "color": "#4ECDC4",
                    "priority_level": "medium"
                },
                {
                    "name": "Security Response",
                    "code": "security",
                    "description": "Armed and unarmed security response teams",
                    "requires_license": True,
                    "default_coverage_radius_km": 25.0,
                    "icon": "shield",
                    "color": "#45B7D1",
                    "priority_level": "high"
                }
            ]
            
            created_types = {}
            for type_data in provider_types_data:
                # Check if type already exists
                result = await session.execute(
                    select(EmergencyProviderType).where(EmergencyProviderType.code == type_data["code"])
                )
                existing_type = result.scalar_one_or_none()
                
                if not existing_type:
                    provider_type = EmergencyProviderType(**type_data)
                    session.add(provider_type)
                    created_types[type_data["code"]] = provider_type
                    print(f"   ✅ Created: {type_data['name']}")
                else:
                    created_types[type_data["code"]] = existing_type
                    print(f"   📋 Using existing: {type_data['name']}")
            
            await session.commit()
            
            # Refresh created types to get their IDs
            for provider_type in created_types.values():
                await session.refresh(provider_type)

            # Create emergency providers
            print(f"\n🚑 Creating Emergency Providers...")
            
            providers_data = [
                {
                    "name": "Cape Town Emergency Medical",
                    "provider_type": ProviderType.AMBULANCE,
                    "provider_type_id": created_types["ambulance"].id,
                    "license_number": "AMB-CT-001",
                    "contact_phone": "+27214567890",
                    "contact_email": "dispatch@ctem.co.za",
                    "street_address": "45 Hospital Road",
                    "city": "Cape Town",
                    "province": "Western Cape",
                    "country": "South Africa",
                    "postal_code": "8001",
                    "current_latitude": -33.9249,
                    "current_longitude": 18.4241,
                    "base_latitude": -33.9249,
                    "base_longitude": 18.4241,
                    "coverage_radius_km": 30.0,
                    "status": ProviderStatus.AVAILABLE,
                    "description": "24/7 emergency medical response with advanced life support",
                    "equipment_details": '{"vehicles": 3, "paramedics": 6, "equipment": ["defibrillator", "oxygen", "stretcher"]}',
                    "capacity": "2 patients per vehicle"
                },
                {
                    "name": "Atlantic Towing Services",
                    "provider_type": ProviderType.TOW_TRUCK,
                    "provider_type_id": created_types["tow_truck"].id,
                    "license_number": "TOW-AT-002",
                    "contact_phone": "+27213456789",
                    "contact_email": "operations@atlantictowing.co.za",
                    "street_address": "78 Industrial Avenue",
                    "city": "Cape Town",
                    "province": "Western Cape",
                    "country": "South Africa",
                    "postal_code": "7925",
                    "current_latitude": -33.9352,
                    "current_longitude": 18.4392,
                    "base_latitude": -33.9352,
                    "base_longitude": 18.4392,
                    "coverage_radius_km": 50.0,
                    "status": ProviderStatus.AVAILABLE,
                    "description": "Heavy duty towing and vehicle recovery services",
                    "equipment_details": '{"trucks": 5, "capacity": "up to 8 tons", "equipment": ["winch", "flatbed", "crane"]}',
                    "capacity": "Up to 8 ton vehicles"
                },
                {
                    "name": "Metro Security Response Unit",
                    "provider_type": ProviderType.SECURITY,
                    "provider_type_id": created_types["security"].id,
                    "license_number": "SEC-MSR-003",
                    "contact_phone": "+27219876543",
                    "contact_email": "control@metrosecurity.co.za",
                    "street_address": "12 Security Plaza",
                    "city": "Cape Town",
                    "province": "Western Cape",
                    "country": "South Africa",
                    "postal_code": "8005",
                    "current_latitude": -33.9258,
                    "current_longitude": 18.4232,
                    "base_latitude": -33.9258,
                    "base_longitude": 18.4232,
                    "coverage_radius_km": 25.0,
                    "status": ProviderStatus.AVAILABLE,
                    "description": "Armed response and security services",
                    "equipment_details": '{"vehicles": 8, "officers": 16, "equipment": ["firearms", "radios", "body_armor"]}',
                    "capacity": "2 officers per vehicle"
                },
                {
                    "name": "Southern Suburbs Ambulance",
                    "provider_type": ProviderType.AMBULANCE,
                    "provider_type_id": created_types["ambulance"].id,
                    "license_number": "AMB-SS-004",
                    "contact_phone": "+27215551234",
                    "contact_email": "emergency@ssambulance.co.za",
                    "street_address": "89 Wynberg Road",
                    "city": "Wynberg",
                    "province": "Western Cape",
                    "country": "South Africa",
                    "postal_code": "7800",
                    "current_latitude": -34.0187,
                    "current_longitude": 18.4632,
                    "base_latitude": -34.0187,
                    "base_longitude": 18.4632,
                    "coverage_radius_km": 35.0,
                    "status": ProviderStatus.BUSY,
                    "description": "Emergency medical services for southern suburbs",
                    "equipment_details": '{"vehicles": 2, "paramedics": 4, "equipment": ["defibrillator", "trauma_kit"]}',
                    "capacity": "1 patient per vehicle"
                }
            ]
            
            created_providers = []
            for provider_data in providers_data:
                provider = EmergencyProvider(
                    firm_id=firm.id,
                    **provider_data
                )
                session.add(provider)
                created_providers.append(provider)
                print(f"   ✅ Created: {provider_data['name']} ({provider_data['provider_type'].value})")
            
            await session.commit()
            
            # Final count verification
            result = await session.execute(select(EmergencyProvider))
            total_providers = len(result.scalars().all())
            
            result = await session.execute(select(EmergencyProviderType))
            total_types = len(result.scalars().all())
            
            print(f"\n🎉 Success! Created sample data:")
            print(f"   - {total_types} emergency provider types")
            print(f"   - {total_providers} emergency providers")
            print(f"   - Associated with firm: {firm.name}")
            
            # Generate new token for the actual firm
            print(f"\n🔑 Updated 1-Hour Token for Firm {firm.id}:")
            print("=" * 70)
            
            from app.services.auth import JWTTokenService
            from datetime import timedelta
            
            jwt_service = JWTTokenService()
            
            new_token = jwt_service.create_access_token(
                user_id=UUID("a4ce8fc2-6a6e-47e3-b76e-29d53c3a627d"),
                user_type="firm_personnel",
                email="",
                permissions=[],
                firm_id=firm.id,  # Use the actual firm ID
                role="firm_admin",
                expires_delta=timedelta(hours=1)
            )
            
            print(new_token)
            print()
            
            print(f"📋 Test the API now:")
            print("=" * 70)
            print(f'export TOKEN="{new_token}"')
            print()
            print('curl -H "Authorization: Bearer $TOKEN" \\')
            print('     "http://localhost:8000/api/v1/emergency-providers/" | python3 -m json.tool')
            
    except Exception as e:
        print(f"\n❌ Error creating sample data: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await engine.dispose()

def print_sample_data_summary():
    """Print what sample data would be created"""
    print("\n📋 Sample Data That Would Be Created:")
    print("=" * 50)
    print("Emergency Provider Types:")
    print("  - Ambulance Service (critical priority)")
    print("  - Tow Truck Service (medium priority)")
    print("  - Security Response (high priority)")
    print()
    print("Emergency Providers:")
    print("  - Cape Town Emergency Medical (ambulance, available)")
    print("  - Atlantic Towing Services (tow truck, available)")
    print("  - Metro Security Response Unit (security, available)")
    print("  - Southern Suburbs Ambulance (ambulance, busy)")

if __name__ == "__main__":
    asyncio.run(create_emergency_sample_data())