#!/usr/bin/env python3
"""
Generate a debug token for testing the agent requests endpoint
"""
import asyncio
from app.core.database import AsyncSessionLocal
from app.core.auth import create_access_token
from sqlalchemy import select
from app.models.security_firm import FirmPersonnel

async def generate_token_for_firm_personnel():
    """Generate a token for a firm personnel to test the endpoint"""
    
    async with AsyncSessionLocal() as db:
        # Get a firm personnel user
        result = await db.execute(
            select(FirmPersonnel).where(FirmPersonnel.email == 'darlington@manicasolutions.com')
        )
        
        firm_user = result.scalar_one_or_none()
        
        if firm_user:
            # Create access token
            token = create_access_token(
                data={
                    "sub": str(firm_user.id),
                    "user_type": "firm_personnel",
                    "firm_id": str(firm_user.firm_id) if firm_user.firm_id else None,
                    "role": firm_user.role
                }
            )
            
            print(f"User ID: {firm_user.id}")
            print(f"Email: {firm_user.email}")
            print(f"Role: {firm_user.role}")
            print(f"Firm ID: {firm_user.firm_id}")
            print(f"Team ID: {firm_user.team_id}")
            print(f"Token: {token}")
            return token
        else:
            print("No firm personnel found")
            return None

if __name__ == "__main__":
    asyncio.run(generate_token_for_firm_personnel())