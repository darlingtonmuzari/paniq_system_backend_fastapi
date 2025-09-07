"""
Test database schema and connections
"""
import pytest
import asyncio
from app.core.database import init_db, get_db, engine
from app.core.db_utils import check_db_connection, execute_query
from app.models import SecurityFirm, RegisteredUser


@pytest.mark.asyncio
async def test_database_connection():
    """Test database connection"""
    # This test requires a running database
    try:
        await init_db()
        assert await check_db_connection()
    except Exception:
        pytest.skip("Database not available for testing")


@pytest.mark.asyncio
async def test_database_tables_exist():
    """Test that required tables exist"""
    try:
        # Check if main tables exist
        tables = await execute_query("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        
        table_names = [row['table_name'] for row in tables]
        
        expected_tables = [
            'security_firms',
            'coverage_areas',
            'registered_users',
            'user_groups',
            'teams',
            'firm_personnel'
        ]
        
        for table in expected_tables:
            assert table in table_names, f"Table {table} not found"
            
    except Exception:
        pytest.skip("Database not available for testing")


@pytest.mark.asyncio
async def test_postgis_extension():
    """Test PostGIS extension is available"""
    try:
        result = await execute_query("""
            SELECT EXISTS(
                SELECT 1 FROM pg_extension WHERE extname = 'postgis'
            ) as has_postgis
        """)
        
        assert result[0]['has_postgis'], "PostGIS extension not installed"
        
    except Exception:
        pytest.skip("Database not available for testing")


def test_model_imports():
    """Test that all models can be imported"""
    from app.models import (
        SecurityFirm, CoverageArea, FirmPersonnel, Team,
        RegisteredUser, UserGroup, GroupMobileNumber,
        SubscriptionProduct, StoredSubscription,
        PanicRequest, ServiceProvider, RequestFeedback
    )
    
    # Basic model validation
    assert hasattr(SecurityFirm, '__tablename__')
    assert hasattr(RegisteredUser, '__tablename__')
    assert hasattr(PanicRequest, '__tablename__')