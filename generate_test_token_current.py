#!/usr/bin/env python3
"""
Generate a test token for the firm supervisor user
"""

import asyncio
import sys
import os
from uuid import UUID

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.core.database import AsyncSessionLocal
from app.models.security_firm import FirmPersonnel
from app.services.auth import JWTTokenService
from sqlalchemy import select

async def generate_token():
    """Generate token for the firm supervisor"""
    
    user_id = "f8a30919-5ed5-46af-95d6-3afa4da634da"
    
    async with AsyncSessionLocal() as db:
        # Get the user from database
        result = await db.execute(
            select(FirmPersonnel).where(FirmPersonnel.id == UUID(user_id))
        )
        agent = result.scalar_one_or_none()
        
        if not agent:
            print("User not found!")
            return
            
        print(f"Generating token for: {agent.first_name} {agent.last_name}")
        print(f"Email: {agent.email}")
        print(f"Role: {agent.role}")
        print(f"Firm ID: {agent.firm_id}")
        
        # Create JWT service
        jwt_service = JWTTokenService()
        
        # Create token payload
        payload = {
            "sub": str(agent.id),
            "user_type": "firm_personnel",
            "email": agent.email,
            "permissions": ["request:view", "request:accept"],
            "firm_id": str(agent.firm_id),
            "role": agent.role
        }
        
        # Generate token
        token = await jwt_service.create_access_token(payload)
        
        print(f"\n🔑 Access Token:")
        print(f"{token}")
        
        print(f"\n📋 Test Command:")
        print(f"curl -H 'Authorization: Bearer {token}' -H 'X-Mobile-App-Attestation: mobile-app-test' 'http://localhost:8000/api/v1/emergency/agent/requests?limit=50&offset=0'")

if __name__ == "__main__":
    asyncio.run(generate_token())