#!/usr/bin/env python3
"""
Create a super admin account for the panic system platform
"""
import asyncio
import sys
import secrets
import string
import uuid
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncpg
from passlib.context import CryptContext

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def generate_secure_password(length: int = 16) -> str:
    """Generate a secure random password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)

async def create_super_admin():
    """Create a super admin account using direct SQL"""
    print("Creating super admin account...")
    
    # Database connection URL
    db_url = "postgresql://postgres:password@localhost:5433/panic_system"
    
    try:
        # Connect to database
        conn = await asyncpg.connect(db_url)
        
        # Check if super admin firm already exists
        existing_firm = await conn.fetchrow(
            "SELECT id FROM security_firms WHERE name = $1", 
            "Platform Administration"
        )
        
        if existing_firm:
            print("❌ Super admin firm already exists!")
            await conn.close()
            return None, None
        
        # Generate secure password
        password = generate_secure_password()
        password_hash = hash_password(password)
        
        # Generate UUIDs
        firm_id = uuid.uuid4()
        admin_id = uuid.uuid4()
        
        # Create super admin security firm
        await conn.execute("""
            INSERT INTO security_firms (
                id, name, registration_number, email, phone, address, 
                verification_status, credit_balance, created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW())
        """, firm_id, "Platform Administration", "ADMIN-001", 
            "admin@paniq.co.za", "+1000000000", "Platform Headquarters",
            "verified", 999999)
        
        # Create super admin personnel
        await conn.execute("""
            INSERT INTO firm_personnel (
                id, firm_id, email, phone, first_name, last_name, 
                role, is_active, password_hash, created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW(), NOW())
        """, admin_id, firm_id, "admin@paniq.co.za", "+1000000001",
            "Super", "Admin", "admin", True, password_hash)
        
        await conn.close()
        
        print("✅ Super admin account created successfully!")
        print(f"📧 Email: admin@paniq.co.za")
        print(f"🔑 Password: {password}")
        print("⚠️  Please save this password securely and change it after first login!")
        
        return "admin@paniq.co.za", password
        
    except Exception as e:
        print(f"❌ Failed to create super admin: {e}")
        return None, None


async def main():
    """Main function"""
    print("🚀 Panic System Platform - Super Admin Creator")
    print("=" * 50)
    
    email, password = await create_super_admin()
    
    if email and password:
        print("\n" + "=" * 50)
        print("🎉 Super Admin Account Details:")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        print("=" * 50)
        print("\n📝 Next steps:")
        print("1. Save these credentials securely")
        print("2. Log in to the admin panel")
        print("3. Change the password immediately")
        print("4. Create additional admin accounts as needed")
    else:
        print("\n❌ Failed to create super admin account")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())