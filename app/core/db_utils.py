"""
Database utilities and connection pooling
"""
import asyncpg
import asyncio
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
import structlog
from app.core.config import settings

logger = structlog.get_logger()

# Connection pool
_pool: Optional[asyncpg.Pool] = None
_pool_stats: Dict[str, Any] = {}


async def create_db_pool() -> asyncpg.Pool:
    """Create optimized database connection pool"""
    global _pool
    
    if _pool is None:
        # Convert SQLAlchemy URL to asyncpg format
        db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
        
        # Optimized pool settings
        min_size = max(5, settings.DATABASE_POOL_SIZE // 4)
        max_size = settings.DATABASE_POOL_SIZE
        
        _pool = await asyncpg.create_pool(
            db_url,
            min_size=min_size,
            max_size=max_size,
            max_queries=50000,  # Maximum queries per connection before recycling
            max_inactive_connection_lifetime=300,  # 5 minutes
            command_timeout=60,
            server_settings={
                'jit': 'off',  # Disable JIT for better performance with short queries
                'effective_cache_size': '1GB',
                'random_page_cost': '1.1',  # SSD optimized
                'seq_page_cost': '1.0',
                'work_mem': '16MB',
                'maintenance_work_mem': '256MB'
            },
            setup=_setup_connection
        )
        
        logger.info(
            "optimized_database_pool_created",
            min_size=min_size,
            max_size=max_size,
            max_queries=50000,
            max_inactive_lifetime=300
        )
    
    return _pool


async def _setup_connection(connection: asyncpg.Connection):
    """Setup individual database connections with optimizations"""
    # Enable PostGIS extension if not already enabled
    try:
        await connection.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    except Exception as e:
        logger.warning("failed_to_setup_postgis_extension", error=str(e))
    
    # Try to enable pg_stat_statements if available
    try:
        await connection.execute("CREATE EXTENSION IF NOT EXISTS pg_stat_statements")
    except Exception as e:
        logger.warning("failed_to_setup_pg_stat_statements_extension", error=str(e))
    
    # Set connection-specific optimizations
    await connection.execute("SET timezone = 'UTC'")
    await connection.execute("SET statement_timeout = '30s'")
    await connection.execute("SET lock_timeout = '10s'")
    await connection.execute("SET idle_in_transaction_session_timeout = '60s'")
    
    # Optimize for spatial queries
    await connection.execute("SET enable_seqscan = off")  # Prefer index scans
    await connection.execute("SET enable_bitmapscan = on")
    await connection.execute("SET enable_hashjoin = on")
    await connection.execute("SET enable_mergejoin = on")
    await connection.execute("SET enable_nestloop = on")


async def get_db_pool() -> asyncpg.Pool:
    """Get database connection pool"""
    if _pool is None:
        return await create_db_pool()
    return _pool


async def close_db_pool():
    """Close database connection pool"""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Database connection pool closed")


async def execute_query(query: str, *args) -> list:
    """Execute a query and return results"""
    pool = await get_db_pool()
    async with pool.acquire() as connection:
        return await connection.fetch(query, *args)


async def execute_command(query: str, *args) -> str:
    """Execute a command and return status"""
    pool = await get_db_pool()
    async with pool.acquire() as connection:
        return await connection.execute(query, *args)


async def check_db_connection() -> bool:
    """Check if database connection is working"""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as connection:
            await connection.fetchval("SELECT 1")
        return True
    except Exception as e:
        logger.error("Database connection check failed", error=str(e))
        return False


@asynccontextmanager
async def get_optimized_connection():
    """Get an optimized database connection with monitoring"""
    pool = await get_db_pool()
    connection = None
    start_time = asyncio.get_event_loop().time()
    
    try:
        connection = await pool.acquire()
        acquire_time = asyncio.get_event_loop().time() - start_time
        
        if acquire_time > 0.1:  # Log slow connection acquisitions
            logger.warning(
                "slow_connection_acquisition",
                acquire_time_ms=acquire_time * 1000,
                pool_size=pool.get_size(),
                pool_idle=pool.get_idle_size()
            )
        
        yield connection
        
    finally:
        if connection:
            await pool.release(connection)


async def execute_optimized_query(
    query: str, 
    *args, 
    query_name: str = "unknown",
    use_cache: bool = False,
    cache_ttl: int = 300
) -> List[asyncpg.Record]:
    """
    Execute a query with optimization and monitoring
    
    Args:
        query: SQL query string
        *args: Query parameters
        query_name: Name for monitoring purposes
        use_cache: Whether to use query result caching
        cache_ttl: Cache time-to-live in seconds
        
    Returns:
        Query results
    """
    from app.core.query_optimizer import query_optimizer
    
    async with query_optimizer.monitor_query(query_name, query, {"args": args}):
        async with get_optimized_connection() as conn:
            return await conn.fetch(query, *args)


async def execute_optimized_command(
    query: str, 
    *args, 
    query_name: str = "unknown"
) -> str:
    """
    Execute a command with optimization and monitoring
    
    Args:
        query: SQL command string
        *args: Query parameters
        query_name: Name for monitoring purposes
        
    Returns:
        Command status
    """
    from app.core.query_optimizer import query_optimizer
    
    async with query_optimizer.monitor_query(query_name, query, {"args": args}):
        async with get_optimized_connection() as conn:
            return await conn.execute(query, *args)


async def get_pool_statistics() -> Dict[str, Any]:
    """Get detailed connection pool statistics"""
    global _pool_stats
    
    if not _pool:
        return {"error": "Pool not initialized"}
    
    current_stats = {
        "pool_size": _pool.get_size(),
        "pool_min_size": _pool.get_min_size(),
        "pool_max_size": _pool.get_max_size(),
        "pool_idle_size": _pool.get_idle_size(),
        "pool_used_size": _pool.get_size() - _pool.get_idle_size(),
        "pool_utilization_percent": ((_pool.get_size() - _pool.get_idle_size()) / _pool.get_max_size()) * 100
    }
    
    # Update historical stats
    _pool_stats.update(current_stats)
    _pool_stats["last_updated"] = asyncio.get_event_loop().time()
    
    return current_stats


async def analyze_slow_queries() -> List[Dict[str, Any]]:
    """Analyze slow queries using pg_stat_statements"""
    try:
        async with get_optimized_connection() as conn:
            # Get slow queries from pg_stat_statements
            slow_queries = await conn.fetch("""
                SELECT 
                    query,
                    calls,
                    total_time,
                    mean_time,
                    max_time,
                    rows,
                    100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
                FROM pg_stat_statements 
                WHERE mean_time > 100  -- Queries with mean time > 100ms
                ORDER BY mean_time DESC 
                LIMIT 20
            """)
            
            return [
                {
                    "query": row["query"][:200] + "..." if len(row["query"]) > 200 else row["query"],
                    "calls": row["calls"],
                    "total_time_ms": float(row["total_time"]),
                    "mean_time_ms": float(row["mean_time"]),
                    "max_time_ms": float(row["max_time"]),
                    "avg_rows": float(row["rows"]) / row["calls"] if row["calls"] > 0 else 0,
                    "cache_hit_percent": float(row["hit_percent"]) if row["hit_percent"] else 0
                }
                for row in slow_queries
            ]
            
    except Exception as e:
        logger.error("failed_to_analyze_slow_queries", error=str(e))
        return []


async def optimize_database_settings() -> Dict[str, Any]:
    """Analyze and suggest database optimization settings"""
    try:
        async with get_optimized_connection() as conn:
            # Get current database settings
            settings_query = """
                SELECT name, setting, unit, context, short_desc
                FROM pg_settings 
                WHERE name IN (
                    'shared_buffers', 'effective_cache_size', 'work_mem', 
                    'maintenance_work_mem', 'random_page_cost', 'seq_page_cost',
                    'checkpoint_completion_target', 'wal_buffers', 'max_connections'
                )
                ORDER BY name
            """
            
            current_settings = await conn.fetch(settings_query)
            
            # Get database size and statistics
            db_stats = await conn.fetchrow("""
                SELECT 
                    pg_size_pretty(pg_database_size(current_database())) as db_size,
                    (SELECT count(*) FROM pg_stat_activity WHERE state = 'active') as active_connections,
                    (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') as max_connections
            """)
            
            recommendations = []
            
            # Analyze settings and provide recommendations
            for setting in current_settings:
                if setting["name"] == "work_mem":
                    current_mb = int(setting["setting"]) // 1024  # Convert KB to MB
                    if current_mb < 16:
                        recommendations.append({
                            "setting": "work_mem",
                            "current": f"{current_mb}MB",
                            "recommended": "16MB",
                            "reason": "Increase for better sort and hash operations"
                        })
                
                elif setting["name"] == "random_page_cost":
                    current_cost = float(setting["setting"])
                    if current_cost > 1.5:
                        recommendations.append({
                            "setting": "random_page_cost",
                            "current": str(current_cost),
                            "recommended": "1.1",
                            "reason": "Optimize for SSD storage"
                        })
            
            return {
                "current_settings": [
                    {
                        "name": s["name"],
                        "value": s["setting"],
                        "unit": s["unit"],
                        "description": s["short_desc"]
                    }
                    for s in current_settings
                ],
                "database_stats": {
                    "size": db_stats["db_size"],
                    "active_connections": db_stats["active_connections"],
                    "max_connections": db_stats["max_connections"],
                    "connection_utilization": (db_stats["active_connections"] / db_stats["max_connections"]) * 100
                },
                "recommendations": recommendations
            }
            
    except Exception as e:
        logger.error("failed_to_analyze_database_settings", error=str(e))
        return {"error": str(e)}