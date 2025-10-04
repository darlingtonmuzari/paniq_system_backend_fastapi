#!/usr/bin/env python3
"""
Test CORS configuration for port range 4000-4099
"""
import requests

def test_port_range():
    """Test various ports in the 4000-4099 range"""
    test_ports = [4000, 4010, 4020, 4050, 4099]
    
    print("Testing CORS for ports 4000-4099...")
    print("=" * 50)
    
    for port in test_ports:
        origin = f"http://localhost:{port}"
        print(f"\nTesting origin: {origin}")
        
        headers = {
            'Origin': origin,
            'Content-Type': 'application/json'
        }
        
        try:
            # Test subscription products endpoint
            response = requests.get(
                'http://localhost:8000/api/v1/subscription-products/my-products',
                headers=headers
            )
            
            cors_origin = response.headers.get('access-control-allow-origin')
            
            if cors_origin == origin:
                print(f"  ✅ CORS working! Origin allowed: {cors_origin}")
            elif cors_origin:
                print(f"  ⚠️  CORS present but different origin: {cors_origin}")
            else:
                print(f"  ❌ No CORS headers found")
                
            print(f"  Status: {response.status_code}")
            
        except Exception as e:
            print(f"  ❌ Error: {e}")

def test_emergency_endpoint():
    """Test emergency endpoint with different origins"""
    test_origins = [
        "http://localhost:4000",
        "http://localhost:4050", 
        "http://localhost:4099",
        "http://localhost:3000"
    ]
    
    print("\n\nTesting Emergency Endpoint CORS...")
    print("=" * 50)
    
    for origin in test_origins:
        print(f"\nTesting origin: {origin}")
        
        headers = {
            'Origin': origin,
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get(
                'http://localhost:8000/api/v1/emergency/agent/requests?limit=50&offset=0',
                headers=headers
            )
            
            cors_origin = response.headers.get('access-control-allow-origin')
            
            if cors_origin == origin:
                print(f"  ✅ CORS working! Origin allowed: {cors_origin}")
            elif cors_origin:
                print(f"  ⚠️  CORS present but different origin: {cors_origin}")
            else:
                print(f"  ❌ No CORS headers found")
                
            print(f"  Status: {response.status_code}")
            
        except Exception as e:
            print(f"  ❌ Error: {e}")

if __name__ == "__main__":
    print("CORS Port Range Test (4000-4099)")
    print("=" * 50)
    
    test_port_range()
    test_emergency_endpoint()
    
    print("\n\nSummary:")
    print("- Ports 4000-4099 should now be allowed for admin endpoints")
    print("- Ports 3000-3999 are allowed for regular endpoints") 
    print("- The API server should automatically reload with the new CORS settings")