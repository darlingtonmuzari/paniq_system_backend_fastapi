#!/usr/bin/env python3
"""
Migrate existing capabilities data to the new capabilities table structure
"""

import asyncio
import asyncpg
import uuid
from typing import Dict, Any, List

# Database connection
DATABASE_URL = "postgresql://postgres:password@localhost:5433/panic_system"

# Capability definitions by category
CAPABILITIES_DATA = {
    "medical": [
        {
            "name": "Emergency Medical Transport",
            "code": "emergency_medical_transport",
            "description": "Provide emergency medical transportation services"
        },
        {
            "name": "Basic Life Support",
            "code": "basic_life_support",
            "description": "Provide basic life support care and interventions"
        },
        {
            "name": "Advanced Life Support",
            "code": "advanced_life_support", 
            "description": "Provide advanced life support care including medications and advanced procedures"
        },
        {
            "name": "Cardiac Care",
            "code": "cardiac_care",
            "description": "Specialized cardiac emergency care and monitoring"
        },
        {
            "name": "Trauma Care",
            "code": "trauma_care",
            "description": "Emergency trauma assessment and stabilization"
        },
        {
            "name": "Patient Stabilization",
            "code": "patient_stabilization",
            "description": "Stabilize patients for transport or treatment"
        },
        {
            "name": "Medical Equipment",
            "code": "medical_equipment",
            "description": "Use and maintain advanced medical equipment"
        },
        {
            "name": "Inter Hospital Transfer",
            "code": "inter_hospital_transfer",
            "description": "Safe transfer of patients between medical facilities"
        },
        {
            "name": "Emergency Medical Services",
            "code": "emergency_medical_services",
            "description": "General emergency medical services and care"
        }
    ],
    "security": [
        {
            "name": "Armed Response",
            "code": "armed_response",
            "description": "Armed security response and intervention services"
        },
        {
            "name": "Patrol Services", 
            "code": "patrol_services",
            "description": "Security patrol and monitoring services"
        },
        {
            "name": "Alarm Response",
            "code": "alarm_response",
            "description": "Respond to security and emergency alarms"
        },
        {
            "name": "Escort Services",
            "code": "escort_services",
            "description": "Personal and asset escort protection services"
        },
        {
            "name": "Crowd Control",
            "code": "crowd_control",
            "description": "Manage and control crowds during events or emergencies"
        },
        {
            "name": "Access Control",
            "code": "access_control",
            "description": "Control and monitor access to secure areas"
        },
        {
            "name": "Surveillance",
            "code": "surveillance",
            "description": "Security surveillance and monitoring operations"
        }
    ],
    "transport": [
        {
            "name": "Vehicle Towing",
            "code": "vehicle_towing",
            "description": "Tow vehicles of various sizes and types"
        },
        {
            "name": "Roadside Assistance",
            "code": "roadside_assistance",
            "description": "Provide roadside assistance and breakdown services"
        },
        {
            "name": "Jump Start",
            "code": "jump_start", 
            "description": "Jump start vehicles with dead batteries"
        },
        {
            "name": "Tire Change",
            "code": "tire_change",
            "description": "Change flat or damaged tires"
        },
        {
            "name": "Lockout Service",
            "code": "lockout_service",
            "description": "Help with vehicle lockout situations"
        },
        {
            "name": "Fuel Delivery",
            "code": "fuel_delivery",
            "description": "Deliver fuel to stranded vehicles"
        },
        {
            "name": "Accident Recovery",
            "code": "accident_recovery",
            "description": "Recovery services for accident scenes"
        },
        {
            "name": "Heavy Vehicle Towing",
            "code": "heavy_vehicle_towing",
            "description": "Specialized towing for heavy vehicles and equipment"
        }
    ],
    "emergency": [
        {
            "name": "Fire Suppression",
            "code": "fire_suppression",
            "description": "Fire fighting and suppression services"
        },
        {
            "name": "Rescue Operations",
            "code": "rescue_operations",
            "description": "Emergency rescue and extraction operations"
        },
        {
            "name": "Hazmat Response",
            "code": "hazmat_response",
            "description": "Hazardous materials response and containment"
        },
        {
            "name": "Vehicle Extrication",
            "code": "vehicle_extrication",
            "description": "Extract victims from vehicle accidents"
        },
        {
            "name": "Search and Rescue",
            "code": "search_and_rescue",
            "description": "Search and rescue operations for missing persons"
        },
        {
            "name": "Water Rescue",
            "code": "water_rescue",
            "description": "Water-based rescue and recovery operations"
        },
        {
            "name": "Technical Rescue",
            "code": "technical_rescue",
            "description": "Specialized technical rescue operations"
        }
    ],
    "law_enforcement": [
        {
            "name": "Law Enforcement",
            "code": "law_enforcement",
            "description": "General law enforcement services and operations"
        },
        {
            "name": "Emergency Response",
            "code": "emergency_response",
            "description": "Emergency response coordination and management"
        },
        {
            "name": "Crime Investigation",
            "code": "crime_investigation",
            "description": "Criminal investigation and evidence collection"
        },
        {
            "name": "Traffic Control",
            "code": "traffic_control",
            "description": "Traffic management and control services"
        },
        {
            "name": "Public Safety",
            "code": "public_safety",
            "description": "General public safety services and protection"
        },
        {
            "name": "Crisis Intervention",
            "code": "crisis_intervention",
            "description": "Crisis intervention and de-escalation services"
        },
        {
            "name": "Emergency Coordination",
            "code": "emergency_coordination",
            "description": "Coordinate emergency response efforts"
        }
    ]
}

# Map old capability codes to new capability IDs
CAPABILITY_MAPPING = {}

async def migrate_capabilities():
    """Migrate to new capabilities table structure"""
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        print("🔄 MIGRATING TO CAPABILITIES TABLE STRUCTURE")
        print("=" * 60)
        
        # Step 1: Create capabilities in the database
        print("\n📝 Step 1: Creating capabilities in database...")
        
        for category, capabilities in CAPABILITIES_DATA.items():
            print(f"\n   📂 Category: {category.title()}")
            
            for cap_data in capabilities:
                capability_id = str(uuid.uuid4())
                
                await conn.execute("""
                    INSERT INTO capabilities (id, name, code, description, category, is_active)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (code) DO NOTHING
                """, 
                    capability_id,
                    cap_data["name"],
                    cap_data["code"],
                    cap_data["description"],
                    category,
                    True
                )
                
                # Store mapping for later use
                CAPABILITY_MAPPING[cap_data["code"]] = capability_id
                print(f"      ✅ {cap_data['name']} ({cap_data['code']})")
        
        # Step 2: Get all capability IDs from database (in case some existed)
        print(f"\n📋 Step 2: Loading capability IDs from database...")
        
        capabilities_from_db = await conn.fetch("""
            SELECT id, code FROM capabilities WHERE is_active = true
        """)
        
        for row in capabilities_from_db:
            CAPABILITY_MAPPING[row['code']] = str(row['id'])
        
        print(f"      ✅ Loaded {len(CAPABILITY_MAPPING)} capabilities")
        
        # Step 3: Migrate existing provider capabilities
        print(f"\n🔄 Step 3: Migrating existing provider capabilities...")
        
        # Get providers with existing capabilities
        providers_with_caps = await conn.fetch("""
            SELECT id, name, provider_type, capabilities 
            FROM emergency_providers 
            WHERE capabilities IS NOT NULL AND array_length(capabilities, 1) > 0
        """)
        
        migrated_assignments = 0
        
        for provider in providers_with_caps:
            print(f"\n   🏢 {provider['name']} ({provider['provider_type']})")
            
            if provider['capabilities']:
                for old_capability_code in provider['capabilities']:
                    if old_capability_code in CAPABILITY_MAPPING:
                        capability_id = CAPABILITY_MAPPING[old_capability_code]
                        
                        # Insert provider capability assignment
                        try:
                            await conn.execute("""
                                INSERT INTO provider_capabilities (id, provider_id, capability_id, proficiency_level)
                                VALUES ($1, $2, $3, $4)
                                ON CONFLICT (provider_id, capability_id) DO NOTHING
                            """,
                                str(uuid.uuid4()),
                                provider['id'],
                                capability_id,
                                'standard'
                            )
                            
                            migrated_assignments += 1
                            capability_name = next((cap['name'] for cat_caps in CAPABILITIES_DATA.values() 
                                                  for cap in cat_caps if cap['code'] == old_capability_code), old_capability_code)
                            print(f"      ✅ {capability_name}")
                            
                        except Exception as e:
                            print(f"      ❌ Failed to assign {old_capability_code}: {e}")
                    else:
                        print(f"      ⚠️  Unknown capability: {old_capability_code}")
        
        # Step 4: Verification
        print(f"\n✅ Step 4: Verification...")
        
        total_capabilities = await conn.fetchval("SELECT COUNT(*) FROM capabilities WHERE is_active = true")
        total_assignments = await conn.fetchval("SELECT COUNT(*) FROM provider_capabilities")
        
        print(f"      📊 Total capabilities: {total_capabilities}")
        print(f"      📊 Total provider assignments: {total_assignments}")
        print(f"      📊 Migrated assignments: {migrated_assignments}")
        
        # Show sample of migrated data
        print(f"\n📋 Sample migrated data:")
        sample_data = await conn.fetch("""
            SELECT 
                ep.name as provider_name,
                c.name as capability_name,
                c.category,
                pc.proficiency_level
            FROM provider_capabilities pc
            JOIN emergency_providers ep ON pc.provider_id = ep.id
            JOIN capabilities c ON pc.capability_id = c.id
            WHERE ep.firm_id = 'e178e9f4-01cb-4c8e-910f-9586516172d6'
            ORDER BY ep.name, c.category, c.name
            LIMIT 10
        """)
        
        for row in sample_data:
            print(f"      • {row['provider_name']}: {row['capability_name']} ({row['category']}) - {row['proficiency_level']}")
        
        print(f"\n🎉 MIGRATION COMPLETED SUCCESSFULLY!")
        print("✅ Capabilities table populated")
        print("✅ Provider capabilities migrated")
        print("✅ Relationships established")
        print("\n🔗 New API endpoints available at:")
        print("   - GET    /api/v1/capabilities/")
        print("   - POST   /api/v1/capabilities/ (admin only)")
        print("   - PUT    /api/v1/capabilities/{id} (admin only)")
        print("   - DELETE /api/v1/capabilities/{id} (admin only)")
        print("   - GET    /api/v1/capabilities/provider-capabilities/{provider_id}")
        print("   - POST   /api/v1/capabilities/provider-capabilities (admin only)")
        
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(migrate_capabilities())