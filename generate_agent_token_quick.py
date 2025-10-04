#!/usr/bin/env python3
"""
Quick token generation for agent testing
"""
import asyncio
import uuid
from app.core.database import AsyncSessionLocal
from app.services.auth import auth_service

async def generate_token():
    """Generate a token for the test agent"""
    
    async with AsyncSessionLocal() as db:
        auth_service.db = db
        
        try:
            # Get the agent details first
            agent_id = uuid.UUID("a4ce8fc2-6a6e-47e3-b76e-29d53c3a627d")
            
            # Create access token directly with role and firm_id
            access_token = auth_service.jwt_service.create_access_token(
                user_id=agent_id,
                user_type="firm_personnel", 
                email="admin@paniq.co.za",
                role="admin",
                firm_id=uuid.UUID("249d03b8-fc0a-460b-82af-049445d15dbb")
            )
            
            print(f"Bearer {access_token}")
            
        except Exception as e:
            print(f"❌ Token generation failed with error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(generate_token())