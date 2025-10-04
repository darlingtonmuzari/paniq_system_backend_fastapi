#!/usr/bin/env python3
"""
Debug script for the agent requests endpoint error
"""
import requests
import json

def test_agent_requests_endpoint():
    """Test the failing agent requests endpoint"""
    
    try:
        # First, let's try to get a token for a firm personnel
        print("=== Testing Agent Requests Endpoint ===")
        
        # Get firm personnel user
        auth_response = requests.post(
            'http://localhost:8001/api/v1/auth/login',
            json={
                "email": "admin@paniq.co.za",  # admin user
                "password": "admin123"
            },
            timeout=10
        )
        
        print(f"Auth Status: {auth_response.status_code}")
        
        if auth_response.status_code == 200:
            token = auth_response.json().get('access_token')
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json',
                'X-Mobile-Attestation': 'debug-mobile-app-v1.0.0'  # Add mobile attestation
            }
            
            print("✅ Successfully authenticated")
            
            # Test the failing endpoint
            print("\n=== Testing /api/v1/emergency/agent/requests ===")
            response = requests.get(
                'http://localhost:8001/api/v1/emergency/agent/requests?limit=50&offset=0',
                headers=headers,
                timeout=30
            )
            
            print(f"Response Status: {response.status_code}")
            print(f"Response Body: {response.text[:500]}...")
            
            if response.status_code != 200:
                print("❌ Endpoint failed")
            else:
                print("✅ Endpoint successful")
                data = response.json()
                print(f"Number of requests: {len(data.get('requests', []))}")
                
        else:
            print("❌ Authentication failed")
            print(f"Response: {auth_response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_agent_requests_endpoint()