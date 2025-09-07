#!/usr/bin/env python3
"""
Script to update admin user password
"""
import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from passlib.context import CryptContext
from app.models.user import RegisteredUser
from app.core.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def update_admin_password():
    """Update admin user password"""
    
    # Create database engine
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False
    )
    
    # Create session
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        try:
            # Find admin user
            result = await session.execute(
                select(RegisteredUser).where(RegisteredUser.email == "admin@paniq.co.za")
            )
            admin_user = result.scalar_one_or_none()
            
            if not admin_user:
                print("Admin user not found. Creating new admin user...")
                
                # Create new admin user
                password_hash = pwd_context.hash("NewSecurePassword123!")
                admin_user = RegisteredUser(
                    email="admin@paniq.co.za",
                    phone="+27123456789",  # Default phone number
                    first_name="System",
                    last_name="Administrator",
                    password_hash=password_hash,
                    role="admin",
                    is_verified=True,
                    prank_flags=0,
                    total_fines=0,
                    is_suspended=False,
                    is_locked=False,
                    failed_login_attempts=0
                )
                
                session.add(admin_user)
                await session.commit()
                print("✅ Created new admin user: admin@paniq.co.za")
                print("✅ Password set to: NewSecurePassword123!")
                
            else:
                # Update existing admin user password
                password_hash = pwd_context.hash("NewSecurePassword123!")
                admin_user.password_hash = password_hash
                admin_user.role = "admin"  # Ensure role is admin
                admin_user.is_verified = True  # Ensure verified
                admin_user.is_locked = False  # Ensure not locked
                admin_user.failed_login_attempts = 0  # Reset failed attempts
                
                await session.commit()
                print("✅ Updated admin user password: admin@paniq.co.za")
                print("✅ Password set to: NewSecurePassword123!")
                
        except Exception as e:
            print(f"❌ Error updating admin password: {e}")
            await session.rollback()
            sys.exit(1)
        
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(update_admin_password())