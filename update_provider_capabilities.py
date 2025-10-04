#!/usr/bin/env python3
"""
Update existing emergency providers with sample capabilities based on their provider type
"""

import asyncio
import asyncpg

# Database connection
DATABASE_URL = "postgresql://postgres:password@localhost:5433/panic_system"

# Capabilities mapping by provider type
PROVIDER_CAPABILITIES = {
    'SECURITY': [
        'armed_response',
        'patrol_services', 
        'alarm_response',
        'escort_services',
        'crowd_control',
        'access_control',
        'surveillance'
    ],
    'TOW_TRUCK': [
        'vehicle_towing',
        'roadside_assistance',
        'jump_start',
        'tire_change',
        'lockout_service',
        'fuel_delivery',
        'accident_recovery',
        'heavy_vehicle_towing'
    ],
    'AMBULANCE': [
        'emergency_medical_transport',
        'basic_life_support',
        'advanced_life_support',
        'cardiac_care',
        'trauma_care',
        'patient_stabilization',
        'medical_equipment',
        'inter_hospital_transfer'
    ],
    'FIRE_DEPARTMENT': [
        'fire_suppression',
        'rescue_operations',
        'hazmat_response',
        'emergency_medical_services',
        'vehicle_extrication',
        'search_and_rescue',
        'water_rescue',
        'technical_rescue'
    ],
    'MEDICAL': [
        'emergency_medical_services',
        'patient_assessment',
        'first_aid',
        'medical_transport',
        'vital_signs_monitoring',
        'medication_administration',
        'wound_care',
        'emergency_stabilization'
    ],
    'POLICE': [
        'law_enforcement',
        'emergency_response',
        'crime_investigation',
        'traffic_control',
        'crowd_control',
        'public_safety',
        'crisis_intervention',
        'emergency_coordination'
    ]
}

async def update_capabilities():
    """Update emergency providers with capabilities"""
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # Get all emergency providers
        providers = await conn.fetch("""
            SELECT id, name, provider_type, capabilities 
            FROM emergency_providers 
            WHERE firm_id = 'e178e9f4-01cb-4c8e-910f-9586516172d6'
        """)
        
        print(f"Found {len(providers)} emergency providers to update")
        
        updated_count = 0
        
        for provider in providers:
            provider_type = provider['provider_type'].upper()
            current_capabilities = provider['capabilities'] or []
            
            # Get capabilities for this provider type
            new_capabilities = PROVIDER_CAPABILITIES.get(provider_type, [])
            
            if not new_capabilities:
                print(f"No capabilities defined for provider type: {provider_type}")
                continue
            
            # Only update if capabilities are empty or different
            if not current_capabilities or set(current_capabilities) != set(new_capabilities):
                await conn.execute("""
                    UPDATE emergency_providers 
                    SET capabilities = $1, updated_at = now()
                    WHERE id = $2
                """, new_capabilities, provider['id'])
                
                updated_count += 1
                print(f"✅ Updated: {provider['name']} ({provider_type})")
                print(f"   Capabilities: {', '.join(new_capabilities)}")
            else:
                print(f"⏭️  Skipped: {provider['name']} - capabilities already up to date")
        
        print(f"\n🎉 Successfully updated {updated_count} providers!")
        
        # Verify updates
        updated_providers = await conn.fetch("""
            SELECT name, provider_type, capabilities 
            FROM emergency_providers 
            WHERE firm_id = 'e178e9f4-01cb-4c8e-910f-9586516172d6'
            ORDER BY name
        """)
        
        print(f"\nVerification - All providers with capabilities:")
        for provider in updated_providers:
            capabilities_str = ', '.join(provider['capabilities']) if provider['capabilities'] else 'None'
            print(f"  - {provider['name']} ({provider['provider_type']}): {capabilities_str}")
            
    except Exception as e:
        print(f"Error during update: {e}")
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(update_capabilities())