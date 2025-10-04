#!/usr/bin/env python3
"""
Add comprehensive sample data across all categories:
1. More emergency providers (different types and quantities)
2. Multiple security firms
3. Sample users and personnel
4. Sample emergency requests
"""
import asyncio
import sys
import os
from uuid import uuid4
from datetime import datetime, timedelta
from faker import Faker
import random

# Add the app directory to Python path
sys.path.append('/home/melcy/Programming/kiro/paniq_system')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text
from app.models.emergency_provider import ProviderType, ProviderStatus

fake = Faker()

# Sample data configurations
CAPE_TOWN_AREAS = [
    {"name": "Cape Town City Centre", "lat": -33.9249, "lon": 18.4241},
    {"name": "Sea Point", "lat": -33.9248, "lon": 18.3777},
    {"name": "Camps Bay", "lat": -33.9481, "lon": 18.3773},
    {"name": "Hout Bay", "lat": -34.0451, "lon": 18.3563},
    {"name": "Constantia", "lat": -34.0257, "lon": 18.4278},
    {"name": "Observatory", "lat": -33.9361, "lon": 18.4814},
    {"name": "Woodstock", "lat": -33.9261, "lon": 18.4456},
    {"name": "Bellville", "lat": -33.8803, "lon": 18.6292},
    {"name": "Parow", "lat": -33.8908, "lon": 18.6169},
    {"name": "Durbanville", "lat": -33.8294, "lon": 18.6446},
    {"name": "Milnerton", "lat": -33.8769, "lon": 18.4859},
    {"name": "Table View", "lat": -33.8173, "lon": 18.4906}
]

PROVIDER_TYPES_DATA = [
    {
        "type": ProviderType.AMBULANCE,
        "names": ["Metro Ambulance", "Life Response", "Guardian Medical", "Swift Care Ambulance", "Emergency Medical Services"],
        "equipment": ["ALS equipment", "BLS equipment", "Cardiac monitor", "Ventilator", "Defibrillator", "Oxygen tanks"],
        "capacity": ["2 patients", "1 critical patient", "4 patients", "2 stretchers"],
        "coverage": (15, 35)
    },
    {
        "type": ProviderType.TOW_TRUCK,
        "names": ["AA Towing", "Quick Recovery", "Highway Heroes", "Cape Tow Services", "Breakdown Rescue"],
        "equipment": ["Flatbed tow truck", "Heavy duty winch", "Recovery straps", "Hydraulic lift", "Tool kit"],
        "capacity": ["Up to 3500kg", "Up to 5000kg", "Motorcycles only", "Heavy vehicles", "Light vehicles"],
        "coverage": (30, 60)
    },
    {
        "type": ProviderType.FIRE_DEPARTMENT,
        "names": ["City Fire Station", "Metro Fire", "Volunteer Fire Brigade", "Industrial Fire Unit", "Airport Fire Service"],
        "equipment": ["Fire truck", "Ladder truck", "Rescue equipment", "Breathing apparatus", "Foam equipment"],
        "capacity": ["6 firefighters", "4 firefighters", "8 firefighters", "Specialized rescue team"],
        "coverage": (10, 25)
    },
    {
        "type": ProviderType.POLICE,
        "names": ["SAPS Metro", "Provincial Police", "Highway Patrol", "K9 Unit", "Tactical Response"],
        "equipment": ["Patrol vehicle", "Motorcycle unit", "K9 vehicle", "Tactical equipment", "Traffic enforcement"],
        "capacity": ["2 officers", "1 officer", "4 officers", "Specialized unit"],
        "coverage": (20, 50)
    },
    {
        "type": ProviderType.SECURITY,
        "names": ["Elite Security", "Guardian Response", "Rapid Security", "Shield Protection", "Safe Guard Services"],
        "equipment": ["Armed response vehicle", "Communication equipment", "Surveillance gear", "Access control", "Patrol equipment"],
        "capacity": ["2 officers", "1 officer", "4 officers", "Security team"],
        "coverage": (15, 40)
    },
    {
        "type": ProviderType.MEDICAL,
        "names": ["Private Medical", "Clinic Response", "Mobile Medical", "Health Services", "Emergency Doctors"],
        "equipment": ["Medical equipment", "Diagnostic tools", "First aid supplies", "Mobile clinic", "Telemedicine"],
        "capacity": ["1 doctor", "2 medics", "Medical team", "Mobile unit"],
        "coverage": (10, 30)
    },
    {
        "type": ProviderType.ROADSIDE_ASSISTANCE,
        "names": ["AA Roadside", "Highway Help", "Breakdown Support", "Mobile Mechanic", "Rescue Services"],
        "equipment": ["Service vehicle", "Jump starter", "Tire repair kit", "Fuel delivery", "Mobile workshop"],
        "capacity": ["Mechanical repairs", "Basic service", "Fuel delivery", "Tire service"],
        "coverage": (40, 80)
    }
]

async def add_comprehensive_sample_data():
    """Add comprehensive sample data across all categories"""
    
    print("🚀 Adding Comprehensive Sample Data to Panic System")
    print("=" * 70)
    
    DATABASE_URL = "postgresql+asyncpg://postgres:password@localhost:5433/panic_system"
    
    try:
        engine = create_async_engine(DATABASE_URL)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as session:
            
            # 1. Add multiple security firms
            print("1️⃣ Adding Security Firms...")
            firms = await add_security_firms(session)
            
            # 2. Add more emergency providers
            print("\n2️⃣ Adding Emergency Providers...")
            providers = await add_emergency_providers(session, firms)
            
            # 3. Add sample users and personnel
            print("\n3️⃣ Adding Users and Personnel...")
            personnel = await add_users_and_personnel(session, firms)
            
            # 4. Add sample emergency requests
            print("\n4️⃣ Adding Emergency Requests...")
            requests = await add_emergency_requests(session, firms, providers)
            
            await session.commit()
            
            print(f"\n🎉 Sample Data Added Successfully!")
            print(f"   📊 {len(firms)} Security Firms")
            print(f"   🚑 {len(providers)} Emergency Providers") 
            print(f"   👥 {len(personnel)} Personnel Members")
            print(f"   🚨 {len(requests)} Emergency Requests")
        
        await engine.dispose()
        return True
        
    except Exception as e:
        print(f"❌ Error adding sample data: {e}")
        import traceback
        traceback.print_exc()
        return False

async def add_security_firms(session):
    """Add multiple security firms"""
    firms = []
    
    firm_names = [
        "SecureGuard Solutions", "Protector Services", "SafeZone Security", 
        "Guardian Protection", "Shield Defense", "Watchman Security", 
        "Fortress Protection", "Alert Response", "Sentinel Services"
    ]
    
    for i, name in enumerate(firm_names):
        area = random.choice(CAPE_TOWN_AREAS)
        
        firm_data = {
            'id': str(uuid4()),
            'name': name,
            'registration_number': f"SEC{2024000 + i}",
            'email': f"info@{name.lower().replace(' ', '')}.co.za",
            'phone': f"+2782{random.randint(1000000, 9999999)}",
            'address': f"{random.randint(100, 999)} {fake.street_name()}, Cape Town, {random.randint(7000, 8999)}",
            'province': 'Western Cape',
            'country': 'South Africa',
            'vat_number': f"VAT{random.randint(1000000000, 9999999999)}",
            'verification_status': random.choice(['pending', 'approved', 'approved', 'approved']),  # Mostly approved
            'credit_balance': random.randint(1000, 50000),
            'is_locked': False
        }
        
        await session.execute(text("""
            INSERT INTO security_firms (
                id, name, registration_number, email, phone, address, 
                province, country, vat_number, verification_status, 
                credit_balance, is_locked
            ) VALUES (
                :id, :name, :registration_number, :email, :phone, :address,
                :province, :country, :vat_number, :verification_status,
                :credit_balance, :is_locked
            )
        """), firm_data)
        
        firms.append(firm_data)
        print(f"   ✅ Added firm: {name}")
    
    return firms

async def add_emergency_providers(session, firms):
    """Add more emergency providers across all types"""
    providers = []
    
    # Get provider type IDs
    result = await session.execute(text("SELECT id, code FROM emergency_provider_types WHERE is_active = true"))
    provider_types = {row[1]: str(row[0]) for row in result.fetchall()}
    
    for provider_type_info in PROVIDER_TYPES_DATA:
        provider_type = provider_type_info["type"]
        
        # Add 2-4 providers per type
        for i in range(random.randint(2, 4)):
            firm = random.choice(firms)
            area = random.choice(CAPE_TOWN_AREAS)
            
            # Small random offset for location variety
            lat_offset = random.uniform(-0.01, 0.01)
            lon_offset = random.uniform(-0.01, 0.01)
            
            provider_data = {
                'id': str(uuid4()),
                'firm_id': firm['id'],
                'name': f"{random.choice(provider_type_info['names'])} {i+1}",
                'provider_type': provider_type.value.upper(),
                'provider_type_id': provider_types.get(provider_type.value),
                'license_number': f"{provider_type.value.upper()[:3]}{random.randint(100, 999)}",
                'contact_phone': f"+2782{random.randint(1000000, 9999999)}",
                'contact_email': f"dispatch{i+1}@{firm['name'].lower().replace(' ', '')}.co.za",
                'current_latitude': area['lat'] + lat_offset,
                'current_longitude': area['lon'] + lon_offset,
                'base_latitude': area['lat'],
                'base_longitude': area['lon'],
                'coverage_radius_km': random.randint(*provider_type_info['coverage']),
                'status': random.choice(['AVAILABLE', 'AVAILABLE', 'AVAILABLE', 'BUSY']),  # Mostly available
                'is_active': True,
                'description': f"Professional {provider_type.value.replace('_', ' ')} service in {area['name']}",
                'equipment_details': ", ".join(random.sample(provider_type_info['equipment'], random.randint(2, 4))),
                'capacity': random.choice(provider_type_info['capacity'])
            }
            
            if not provider_data['provider_type_id']:
                print(f"   ⚠️  Skipping {provider_data['name']} - provider type not found")
                continue
            
            await session.execute(text("""
                INSERT INTO emergency_providers (
                    id, firm_id, name, provider_type, provider_type_id, license_number,
                    contact_phone, contact_email, current_latitude, current_longitude,
                    base_latitude, base_longitude, coverage_radius_km, status, is_active,
                    description, equipment_details, capacity
                ) VALUES (
                    :id, :firm_id, :name, :provider_type, :provider_type_id, :license_number,
                    :contact_phone, :contact_email, :current_latitude, :current_longitude,
                    :base_latitude, :base_longitude, :coverage_radius_km, :status, :is_active,
                    :description, :equipment_details, :capacity
                )
            """), provider_data)
            
            providers.append(provider_data)
            print(f"   ✅ Added: {provider_data['name']} ({provider_type.value})")
    
    return providers

async def add_users_and_personnel(session, firms):
    """Add sample users and personnel"""
    personnel = []
    
    # Check if firm_personnel table exists
    result = await session.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'firm_personnel'
        );
    """))
    table_exists = result.scalar()
    
    if not table_exists:
        print("   ⚠️  firm_personnel table doesn't exist, skipping personnel creation")
        return personnel
    
    roles = ['admin', 'operator', 'dispatcher', 'supervisor', 'technician']
    
    for firm in firms[:5]:  # Add personnel to first 5 firms
        # Add 2-5 personnel per firm
        for i in range(random.randint(2, 5)):
            first_name = fake.first_name()
            last_name = fake.last_name()
            
            personnel_data = {
                'id': str(uuid4()),
                'firm_id': firm['id'],
                'first_name': first_name,
                'last_name': last_name,
                'email': f"{first_name.lower()}.{last_name.lower()}@{firm['name'].lower().replace(' ', '')}.co.za",
                'phone': f"+2782{random.randint(1000000, 9999999)}",
                'role': random.choice(roles),
                'is_active': True,
                'can_dispatch': random.choice([True, False]),
                'last_login': datetime.utcnow() - timedelta(days=random.randint(0, 30))
            }
            
            try:
                await session.execute(text("""
                    INSERT INTO firm_personnel (
                        id, firm_id, first_name, last_name, email, phone, role, 
                        is_active, can_dispatch, last_login
                    ) VALUES (
                        :id, :firm_id, :first_name, :last_name, :email, :phone, :role,
                        :is_active, :can_dispatch, :last_login
                    )
                """), personnel_data)
                
                personnel.append(personnel_data)
                print(f"   ✅ Added: {first_name} {last_name} ({personnel_data['role']})")
                
            except Exception as e:
                print(f"   ⚠️  Could not add personnel: {e}")
                # Continue with other personnel
                continue
    
    return personnel

async def add_emergency_requests(session, firms, providers):
    """Add sample emergency requests"""
    requests = []
    
    # Check if panic_requests table exists
    result = await session.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'panic_requests'
        );
    """))
    table_exists = result.scalar()
    
    if not table_exists:
        print("   ⚠️  panic_requests table doesn't exist, skipping emergency requests")
        return requests
    
    # Check if user_groups table exists
    result = await session.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'user_groups'
        );
    """))
    groups_exist = result.scalar()
    
    if not groups_exist:
        print("   ⚠️  user_groups table doesn't exist, creating sample groups first")
        # Create sample user groups
        groups = []
        for i in range(5):
            group_data = {
                'id': str(uuid4()),
                'name': f"Sample Group {i+1}",
                'description': f"Sample user group for testing emergency requests",
                'is_active': True
            }
            
            try:
                await session.execute(text("""
                    INSERT INTO user_groups (id, name, description, is_active)
                    VALUES (:id, :name, :description, :is_active)
                """), group_data)
                groups.append(group_data)
            except Exception as e:
                print(f"   ⚠️  Could not create user group: {e}")
                continue
    else:
        # Get existing groups
        result = await session.execute(text("SELECT id FROM user_groups WHERE is_active = true LIMIT 5"))
        groups = [{'id': str(row[0])} for row in result.fetchall()]
    
    if not groups:
        print("   ⚠️  No user groups available, skipping emergency requests")
        return requests
    
    service_types = ['call', 'security', 'ambulance', 'fire', 'towing']
    statuses = ['pending', 'accepted', 'completed', 'cancelled']
    
    # Create 10-15 emergency requests
    for i in range(random.randint(10, 15)):
        area = random.choice(CAPE_TOWN_AREAS)
        group = random.choice(groups)
        
        # Small random offset for location variety
        lat_offset = random.uniform(-0.005, 0.005)
        lon_offset = random.uniform(-0.005, 0.005)
        
        # Random time in the past 30 days
        created_time = datetime.utcnow() - timedelta(
            days=random.randint(0, 30),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )
        
        request_data = {
            'id': str(uuid4()),
            'group_id': group['id'],
            'requester_phone': f"+2782{random.randint(1000000, 9999999)}",
            'service_type': random.choice(service_types),
            'address': f"{area['name']}, Cape Town",
            'description': fake.text(max_nb_chars=200),
            'status': random.choice(statuses),
            'created_at': created_time
        }
        
        # Add location using PostGIS if available
        try:
            await session.execute(text("""
                INSERT INTO panic_requests (
                    id, group_id, requester_phone, service_type, location, address,
                    description, status, created_at
                ) VALUES (
                    :id, :group_id, :requester_phone, :service_type, 
                    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326),
                    :address, :description, :status, :created_at
                )
            """), {
                **request_data,
                'lat': area['lat'] + lat_offset,
                'lon': area['lon'] + lon_offset
            })
            
            requests.append(request_data)
            print(f"   ✅ Added emergency request: {request_data['service_type']} in {area['name']}")
            
        except Exception as e:
            print(f"   ⚠️  Could not add emergency request: {e}")
            continue
    
    return requests

if __name__ == "__main__":
    print("Starting comprehensive sample data insertion...")
    
    result = asyncio.run(add_comprehensive_sample_data())
    exit(0 if result else 1)