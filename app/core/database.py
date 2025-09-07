"""
Database configuration and connection management
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData, text
import structlog

from app.core.config import settings

logger = structlog.get_logger()

# Database engine
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    echo=settings.DEBUG,
    future=True
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


class Base(DeclarativeBase):
    """Base class for all database models"""
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s"
        }
    )


async def get_db() -> AsyncSession:
    """Dependency to get database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database connection"""
    try:
        # Test SQLAlchemy connection
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        
        # Initialize asyncpg pool
        from app.core.db_utils import create_db_pool, check_db_connection
        await create_db_pool()
        
        if await check_db_connection():
            logger.info("Database connections established (SQLAlchemy + asyncpg)")
        else:
            raise Exception("Database connection check failed")
            
    except Exception as e:
        logger.error("Failed to connect to database", error=str(e))
        raise