"""
Cache warming service for pre-populating critical data
"""
import asyncio
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.cache import enhanced_cache, CacheKey
from app.core.database import get_db
from app.models.security_firm import SecurityFirm, CoverageArea
from app.models.subscription import SubscriptionProduct
from app.models.user import RegisteredUser, UserGroup
import structlog

logger = structlog.get_logger()


class CacheWarmingService:
    """Service for warming critical cache data"""
    
    def __init__(self):
        self.warming_functions = {
            "active_products": self._warm_active_products,
            "coverage_areas": self._warm_coverage_areas,
            "user_groups": self._warm_user_groups,
            "subscription_products": self._warm_subscription_products
        }
    
    async def warm_all_caches(self):
        """Warm all registered caches"""
        logger.info("Starting cache warming process")
        
        async for db in get_db():
            try:
                for cache_name, warming_func in self.warming_functions.items():
                    try:
                        await warming_func(db)
                        logger.info("Cache warmed successfully", cache_name=cache_name)
                    except Exception as e:
                        logger.error("Cache warming failed", 
                                   cache_name=cache_name, 
                                   error=str(e))
                
                logger.info("Cache warming process completed")
            except Exception as e:
                logger.error("Cache warming process failed", error=str(e))
            finally:
                await db.close()
    
    async def warm_specific_cache(self, cache_name: str):
        """Warm a specific cache"""
        if cache_name not in self.warming_functions:
            raise ValueError(f"Unknown cache: {cache_name}")
        
        async for db in get_db():
            try:
                await self.warming_functions[cache_name](db)
                logger.info("Cache warmed successfully", cache_name=cache_name)
            except Exception as e:
                logger.error("Cache warming failed", 
                           cache_name=cache_name, 
                           error=str(e))
            finally:
                await db.close()
    
    async def _warm_active_products(self, db: AsyncSession):
        """Warm active subscription products cache"""
        result = await db.execute(
            select(SubscriptionProduct)
            .options(selectinload(SubscriptionProduct.firm))
            .where(SubscriptionProduct.is_active == True)
            .order_by(SubscriptionProduct.price)
        )
        products = result.scalars().all()
        
        # Cache the active products list
        cache_key = CacheKey.generate("active_products")
        await enhanced_cache.set(cache_key, products, expire=1800)
        
        # Cache individual products
        for product in products:
            product_key = CacheKey.generate("product_by_id", str(product.id))
            await enhanced_cache.set(product_key, product, expire=3600)
        
        logger.info("Active products cache warmed", count=len(products))
    
    async def _warm_coverage_areas(self, db: AsyncSession):
        """Warm coverage areas cache for all firms"""
        result = await db.execute(
            select(SecurityFirm)
            .options(selectinload(SecurityFirm.coverage_areas))
            .where(SecurityFirm.verification_status == "approved")
        )
        firms = result.scalars().all()
        
        for firm in firms:
            cache_key = CacheKey.coverage_areas(firm.id)
            coverage_data = [
                {
                    "id": str(area.id),
                    "name": area.name,
                    "boundary": str(area.boundary)  # Convert geometry to string
                }
                for area in firm.coverage_areas
            ]
            await enhanced_cache.set(cache_key, coverage_data, expire=3600)
        
        logger.info("Coverage areas cache warmed", firms_count=len(firms))
    
    async def _warm_user_groups(self, db: AsyncSession):
        """Warm user groups cache for active users"""
        # Get users with active subscriptions
        result = await db.execute(
            select(RegisteredUser)
            .options(selectinload(RegisteredUser.groups))
            .where(RegisteredUser.is_suspended == False)
            .limit(1000)  # Limit to prevent memory issues
        )
        users = result.scalars().all()
        
        for user in users:
            if user.groups:
                cache_key = CacheKey.generate("user_groups", str(user.id))
                groups_data = [
                    {
                        "id": str(group.id),
                        "name": group.name,
                        "address": group.address,
                        "subscription_expires_at": group.subscription_expires_at.isoformat() if group.subscription_expires_at else None
                    }
                    for group in user.groups
                ]
                await enhanced_cache.set(cache_key, groups_data, expire=1800)
        
        logger.info("User groups cache warmed", users_count=len(users))
    
    async def _warm_subscription_products(self, db: AsyncSession):
        """Warm subscription products cache by firm"""
        result = await db.execute(
            select(SecurityFirm)
            .options(selectinload(SecurityFirm.subscription_products))
            .where(SecurityFirm.verification_status == "approved")
        )
        firms = result.scalars().all()
        
        for firm in firms:
            cache_key = CacheKey.generate("firm_products", str(firm.id))
            products_data = [
                {
                    "id": str(product.id),
                    "name": product.name,
                    "description": product.description,
                    "max_users": product.max_users,
                    "price": float(product.price),
                    "is_active": product.is_active
                }
                for product in firm.subscription_products
            ]
            await enhanced_cache.set(cache_key, products_data, expire=1800)
        
        logger.info("Subscription products cache warmed", firms_count=len(firms))
    
    async def schedule_periodic_warming(self, interval_hours: int = 6):
        """Schedule periodic cache warming"""
        logger.info("Starting periodic cache warming", interval_hours=interval_hours)
        
        while True:
            try:
                await asyncio.sleep(interval_hours * 3600)  # Convert hours to seconds
                await self.warm_all_caches()
            except Exception as e:
                logger.error("Periodic cache warming failed", error=str(e))
                # Continue the loop even if warming fails
                await asyncio.sleep(300)  # Wait 5 minutes before retrying
    
    async def warm_critical_data_on_startup(self):
        """Warm critical data that should be available immediately on startup"""
        logger.info("Warming critical startup data")
        
        critical_caches = ["active_products", "coverage_areas"]
        
        async for db in get_db():
            try:
                for cache_name in critical_caches:
                    await self.warming_functions[cache_name](db)
                    logger.info("Critical cache warmed", cache_name=cache_name)
                
                logger.info("Critical startup data warming completed")
            except Exception as e:
                logger.error("Critical data warming failed", error=str(e))
            finally:
                await db.close()
    
    async def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache statistics and health information"""
        stats = {
            "cache_keys_count": 0,
            "memory_usage": "unknown",
            "hit_rate": "unknown",
            "warming_functions": list(self.warming_functions.keys())
        }
        
        try:
            # Get basic Redis info
            redis_client = enhanced_cache.client
            if redis_client:
                info = await redis_client.info()
                stats.update({
                    "memory_usage": info.get("used_memory_human", "unknown"),
                    "connected_clients": info.get("connected_clients", 0),
                    "total_commands_processed": info.get("total_commands_processed", 0)
                })
                
                # Count keys (be careful with this in production)
                keys = await redis_client.keys("*")
                stats["cache_keys_count"] = len(keys)
        
        except Exception as e:
            logger.error("Failed to get cache statistics", error=str(e))
        
        return stats


# Global cache warming service instance
cache_warming_service = CacheWarmingService()


async def start_cache_warming_background_task():
    """Start background task for periodic cache warming"""
    asyncio.create_task(cache_warming_service.schedule_periodic_warming())


async def warm_critical_caches():
    """Warm critical caches on application startup"""
    await cache_warming_service.warm_critical_data_on_startup()