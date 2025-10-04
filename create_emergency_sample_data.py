#!/usr/bin/env python3
"""
Create sample emergency providers data for testing
"""
import sys
import os
import asyncio
from uuid import uuid4

# Add the app directory to Python path
sys.path.append('/home/melcy/Programming/kiro/paniq_system')

from app.services.auth import JWTTokenService
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.models.emergency_provider import EmergencyProviderType, EmergencyProvider, ProviderType, ProviderStatus
from app.models.security_firm import SecurityFirm

async def create_sample_data():
    """Create sample emergency provider data"""
    
    # Database connection
    DATABASE_URL = "postgresql+asyncpg://manica_dev_admin:M1n931solutions*b0b5@postgresql-184662-0.cloudclusters.net:10024/panic_system_dev"
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session() as session:
            # First, let's find or create a security firm
            result = await session.execute(select(SecurityFirm).limit(1))
            firm = result.scalar_one_or_none()
            
            if not firm:
                print("No security firm found. Creating one...")
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
                print(f"Created firm: {firm.name} (ID: {firm.id})")
            else:
                print(f"Using existing firm: {firm.name} (ID: {firm.id})")

            # Create emergency provider types
            provider_types_data = [
                {
                    "name": "Ambulance Service",
                    "code": "ambulance",
                    "description": "Emergency medical transport services",
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
            
            created_types = []
            for type_data in provider_types_data:
                # Check if type already exists
                result = await session.execute(
                    select(EmergencyProviderType).where(EmergencyProviderType.code == type_data["code"])
                )
                existing_type = result.scalar_one_or_none()
                
                if not existing_type:
                    provider_type = EmergencyProviderType(**type_data)
                    session.add(provider_type)
                    created_types.append(provider_type)
                    print(f"Created provider type: {type_data['name']}")
                else:
                    created_types.append(existing_type)
                    print(f"Using existing provider type: {type_data['name']}")
            
            await session.commit()
            
            # Refresh created types to get their IDs
            for provider_type in created_types:
                await session.refresh(provider_type)

            # Create sample emergency providers
            providers_data = [
                {
                    "name": "Cape Town Emergency Medical",
                    "provider_type": ProviderType.AMBULANCE,
                    "provider_type_id": created_types[0].id,  # Ambulance Service
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
                    "provider_type_id": created_types[1].id,  # Tow Truck Service
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
                    "provider_type_id": created_types[2].id,  # Security Response
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
                    "provider_type_id": created_types[0].id,  # Ambulance Service
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
                print(f"Created provider: {provider_data['name']}")
            
            await session.commit()
            
            print(f"\n✅ Successfully created:")
            print(f"   - {len(created_types)} emergency provider types")
            print(f"   - {len(created_providers)} emergency providers")
            print(f"   - Associated with firm: {firm.name}")
            
            # Generate a token with firm_admin role and firm_id
            jwt_service = JWTTokenService()
            
            admin_token = jwt_service.create_access_token(
                user_id=uuid4(),
                user_type="firm_personnel",
                email="admin@ctss.co.za",
                permissions=[],
                firm_id=firm.id,  # Include firm_id
                role="firm_admin"  # Use firm_admin role
            )
            
            print(f"\n🔑 Admin Token for Testing:")
            print("=" * 80)
            print(admin_token)
            print()
            print("📋 Test Commands:")
            print("=" * 80)
            print(f'# List all emergency providers:')
            print(f'curl -H "Authorization: Bearer {admin_token}" \\')
            print(f'     "http://localhost:8000/api/v1/emergency-providers/"')
            print()
            print(f'# List only ambulances:')
            print(f'curl -H "Authorization: Bearer {admin_token}" \\')
            print(f'     "http://localhost:8000/api/v1/emergency-providers/?provider_type=ambulance"')
            print()
            print(f'# List only available providers:')
            print(f'curl -H "Authorization: Bearer {admin_token}" \\')
            print(f'     "http://localhost:8000/api/v1/emergency-providers/?status=available"')
            
    except Exception as e:
        print(f"Error creating sample data: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(create_sample_data())