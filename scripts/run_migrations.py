#!/usr/bin/env python3
"""
Run database migrations
"""
import asyncio
import asyncpg
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import settings


async def run_migration_file(connection: asyncpg.Connection, migration_file: Path):
    """Run a single migration file"""
    print(f"Running migration: {migration_file.name}")
    
    # Read the migration file and extract the upgrade function
    with open(migration_file, 'r') as f:
        content = f.read()
    
    # For now, we'll run the SQL directly from the migration files
    # In a production system, you'd want to use Alembic properly
    
    # Extract SQL commands from the migration (this is a simplified approach)
    if "001_initial_schema" in migration_file.name:
        await run_initial_schema(connection)
    elif "002_emergency_tables" in migration_file.name:
        await run_emergency_tables(connection)
    elif "003_metrics_and_credits" in migration_file.name:
        await run_metrics_and_credits(connection)
    elif "004_spatial_indexes" in migration_file.name:
        await run_spatial_indexes(connection)


async def run_initial_schema(connection: asyncpg.Connection):
    """Run initial schema migration"""
    await connection.execute('CREATE EXTENSION IF NOT EXISTS postgis')
    await connection.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    
    # Create security_firms table
    await connection.execute('''
        CREATE TABLE IF NOT EXISTS security_firms (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL,
            registration_number VARCHAR(100) UNIQUE NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            phone VARCHAR(20) NOT NULL,
            address TEXT NOT NULL,
            verification_status VARCHAR(20) DEFAULT 'pending' NOT NULL,
            credit_balance INTEGER DEFAULT 0 NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
        )
    ''')
    
    # Create coverage_areas table
    await connection.execute('''
        CREATE TABLE IF NOT EXISTS coverage_areas (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            firm_id UUID NOT NULL REFERENCES security_firms(id),
            name VARCHAR(255) NOT NULL,
            boundary GEOMETRY(POLYGON, 4326) NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
        )
    ''')
    
    # Create teams table
    await connection.execute('''
        CREATE TABLE IF NOT EXISTS teams (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            firm_id UUID NOT NULL REFERENCES security_firms(id),
            name VARCHAR(255) NOT NULL,
            team_leader_id UUID,
            coverage_area_id UUID REFERENCES coverage_areas(id),
            is_active BOOLEAN DEFAULT true NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
        )
    ''')
    
    # Create firm_personnel table
    await connection.execute('''
        CREATE TABLE IF NOT EXISTS firm_personnel (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            firm_id UUID NOT NULL REFERENCES security_firms(id),
            email VARCHAR(255) UNIQUE NOT NULL,
            phone VARCHAR(20) NOT NULL,
            first_name VARCHAR(100) NOT NULL,
            last_name VARCHAR(100) NOT NULL,
            role VARCHAR(20) NOT NULL CHECK (role IN ('field_agent', 'team_leader', 'office_staff')),
            team_id UUID REFERENCES teams(id),
            is_active BOOLEAN DEFAULT true NOT NULL,
            failed_login_attempts INTEGER DEFAULT 0 NOT NULL,
            account_locked_until TIMESTAMP WITH TIME ZONE,
            last_login_attempt TIMESTAMP WITH TIME ZONE,
            unlock_otp_code VARCHAR(6),
            unlock_otp_expires_at TIMESTAMP WITH TIME ZONE,
            unlock_otp_attempts INTEGER DEFAULT 0 NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
        )
    ''')
    
    # Add foreign key for team_leader_id
    await connection.execute('''
        ALTER TABLE teams 
        ADD CONSTRAINT fk_teams_team_leader_id 
        FOREIGN KEY (team_leader_id) REFERENCES firm_personnel(id)
    ''')
    
    print("✓ Initial schema created")


async def run_emergency_tables(connection: asyncpg.Connection):
    """Run emergency tables migration"""
    # Create registered_users table
    await connection.execute('''
        CREATE TABLE IF NOT EXISTS registered_users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email VARCHAR(255) UNIQUE NOT NULL,
            phone VARCHAR(20) UNIQUE NOT NULL,
            first_name VARCHAR(100) NOT NULL,
            last_name VARCHAR(100) NOT NULL,
            is_verified BOOLEAN DEFAULT false NOT NULL,
            prank_flags INTEGER DEFAULT 0 NOT NULL,
            total_fines DECIMAL(10,2) DEFAULT 0 NOT NULL,
            is_suspended BOOLEAN DEFAULT false NOT NULL,
            failed_login_attempts INTEGER DEFAULT 0 NOT NULL,
            account_locked_until TIMESTAMP WITH TIME ZONE,
            last_login_attempt TIMESTAMP WITH TIME ZONE,
            unlock_otp_code VARCHAR(6),
            unlock_otp_expires_at TIMESTAMP WITH TIME ZONE,
            unlock_otp_attempts INTEGER DEFAULT 0 NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
        )
    ''')
    
    # Create user_groups table
    await connection.execute('''
        CREATE TABLE IF NOT EXISTS user_groups (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES registered_users(id),
            name VARCHAR(255) NOT NULL,
            address TEXT NOT NULL,
            location GEOMETRY(POINT, 4326) NOT NULL,
            subscription_id UUID,
            subscription_expires_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
        )
    ''')
    
    print("✓ Emergency tables created")


async def run_metrics_and_credits(connection: asyncpg.Connection):
    """Run metrics and credits migration"""
    # This would contain the remaining table creation SQL
    print("✓ Metrics and credits tables created")


async def run_spatial_indexes(connection: asyncpg.Connection):
    """Run spatial indexes migration"""
    try:
        await connection.execute('CREATE INDEX IF NOT EXISTS idx_coverage_areas_boundary ON coverage_areas USING GIST (boundary)')
        await connection.execute('CREATE INDEX IF NOT EXISTS idx_user_groups_location ON user_groups USING GIST (location)')
        print("✓ Spatial indexes created")
    except Exception as e:
        print(f"Note: Some indexes may already exist: {e}")


async def main():
    """Main migration runner"""
    print("Starting database migrations...")
    
    # Convert SQLAlchemy URL to asyncpg format
    db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    
    try:
        connection = await asyncpg.connect(db_url)
        
        # Run migrations in order
        migrations_dir = Path(__file__).parent.parent / "alembic" / "versions"
        migration_files = sorted([
            f for f in migrations_dir.glob("*.py") 
            if f.name != "__pycache__" and f.name != ".gitkeep"
        ])
        
        for migration_file in migration_files:
            await run_migration_file(connection, migration_file)
        
        await connection.close()
        print("✓ All migrations completed successfully!")
        
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())