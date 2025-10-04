#!/usr/bin/env python3

import asyncio
import asyncpg
import json

# Database connection
DATABASE_URL = "postgresql://postgres:password@localhost:5433/panic_system"

async def main():
    """Test accessing service providers data"""
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        print("=" * 60)
        print("SERVICE PROVIDERS DATA ACCESS TEST")
        print("=" * 60)
        
        # Get all service providers with their firm information
        query = """
        SELECT 
            sp.id,
            sp.name,
            sp.service_type,
            sp.email,
            sp.phone,
            sp.address,
            sp.is_active,
            sf.name as firm_name,
            sf.verification_status,
            ST_X(sp.location) as longitude,
            ST_Y(sp.location) as latitude,
            sp.created_at
        FROM service_providers sp
        JOIN security_firms sf ON sp.firm_id = sf.id
        ORDER BY sp.service_type, sp.name
        """
        
        results = await conn.fetch(query)
        
        print(f"📊 Found {len(results)} service providers\n")
        
        # Group by service type
        service_types = {}
        for row in results:
            service_type = row['service_type']
            if service_type not in service_types:
                service_types[service_type] = []
            service_types[service_type].append(dict(row))
        
        # Display grouped results
        for service_type, providers in service_types.items():
            print(f"🏷️  {service_type.upper()} SERVICES ({len(providers)} providers)")
            print("-" * 50)
            for provider in providers:
                status = "🟢 Active" if provider['is_active'] else "🔴 Inactive"
                print(f"   • {provider['name']}")
                print(f"     📞 {provider['phone']} | ✉️  {provider['email']}")
                print(f"     🏢 {provider['firm_name']}")
                print(f"     📍 {provider['address']}")
                print(f"     🌍 Lat: {provider['latitude']:.4f}, Lon: {provider['longitude']:.4f}")
                print(f"     {status}")
                print()
        
        # Test specific service type queries
        print("=" * 60)
        print("SERVICE TYPE SPECIFIC QUERIES")
        print("=" * 60)
        
        security_providers = await conn.fetch("""
            SELECT sp.name, sp.phone, sf.name as firm_name
            FROM service_providers sp
            JOIN security_firms sf ON sp.firm_id = sf.id
            WHERE sp.service_type = 'security' AND sp.is_active = true
        """)
        
        print(f"🛡️  SECURITY PROVIDERS ({len(security_providers)} active):")
        for provider in security_providers:
            print(f"   • {provider['name']} - {provider['firm_name']} ({provider['phone']})")
        
        medical_providers = await conn.fetch("""
            SELECT sp.name, sp.phone, sf.name as firm_name
            FROM service_providers sp
            JOIN security_firms sf ON sp.firm_id = sf.id
            WHERE sp.service_type IN ('medical', 'ambulance') AND sp.is_active = true
        """)
        
        print(f"\n🏥 MEDICAL PROVIDERS ({len(medical_providers)} active):")
        for provider in medical_providers:
            print(f"   • {provider['name']} - {provider['firm_name']} ({provider['phone']})")
        
        # Get statistics
        print("\n" + "=" * 60)
        print("STATISTICS")
        print("=" * 60)
        
        stats = await conn.fetch("""
            SELECT 
                sp.service_type,
                COUNT(*) as total_providers,
                COUNT(CASE WHEN sp.is_active THEN 1 END) as active_providers,
                sf.name as firm_name,
                COUNT(*) OVER (PARTITION BY sf.name) as providers_per_firm
            FROM service_providers sp
            JOIN security_firms sf ON sp.firm_id = sf.id
            GROUP BY sp.service_type, sf.name
            ORDER BY sp.service_type
        """)
        
        print("📈 Providers by Service Type:")
        current_type = None
        for stat in stats:
            if stat['service_type'] != current_type:
                current_type = stat['service_type']
                total = sum(s['total_providers'] for s in stats if s['service_type'] == current_type)
                active = sum(s['active_providers'] for s in stats if s['service_type'] == current_type)
                print(f"\n   {current_type.upper()}: {total} total ({active} active)")
            print(f"     - {stat['firm_name']}: {stat['total_providers']} providers")
        
        print(f"\n✅ Service providers data is accessible and working correctly!")
        print(f"💡 This data can be used by emergency request allocation systems")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())