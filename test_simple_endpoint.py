#!/usr/bin/env python3
"""
Test a simple endpoint to check if the basic FastAPI setup is working
"""

import asyncio
import httpx

async def test_simple_endpoint():
    """Test a simple endpoint that should respond quickly"""
    
    url = "http://localhost:8000/docs"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            print("Testing simple docs endpoint...")
            
            response = await client.get(url)
            
            print(f"Status Code: {response.status_code}")
            print(f"Response size: {len(response.text)} bytes")
            
            if response.status_code == 200:
                print("✅ Basic FastAPI is working")
            else:
                print("❌ Basic FastAPI issue")
                
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_simple_endpoint())