#!/usr/bin/env python3
"""
Database migration script to add is_active column to coverage_areas table
"""
import asyncio
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.core.database import get_db
from sqlalchemy import text

async def add_is_active_column():
    """Add is_active column to coverage_areas table"""
    print("Adding is_active column to coverage_areas table...")
    
    async for db in get_db():
        try:
            # Check if column already exists
            result = await db.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'coverage_areas' 
                AND column_name = 'is_active'
            """))
            
            existing_column = result.fetchone()
            
            if existing_column:
                print("✅ is_active column already exists")
            else:
                print("Adding is_active column...")
                
                # Add the column with default value True
                await db.execute(text("""
                    ALTER TABLE coverage_areas 
                    ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE
                """))
                
                await db.commit()
                print("✅ is_active column added successfully")
            
            # Check current coverage areas
            result = await db.execute(text("""
                SELECT id, name, is_active 
                FROM coverage_areas 
                ORDER BY created_at DESC
                LIMIT 10
            """))
            
            areas = result.fetchall()
            
            if areas:
                print(f"\nCurrent coverage areas (showing last 10):")
                for area in areas:
                    status = "🟢 Active" if area.is_active else "🔴 Inactive"
                    print(f"  - {area.name} - {status}")
            else:
                print("\nNo coverage areas found in database")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        break

if __name__ == "__main__":
    asyncio.run(add_is_active_column())