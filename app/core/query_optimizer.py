"""
Database query optimization utilities and performance monitoring
"""
import time
import asyncio
from typing import Any, Dict, List, Optional, Tuple, Union
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID
import asyncpg
import structlog
from sqlalchemy import text, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select
from geoalchemy2.functions import ST_Distance, ST_GeomFromText, ST_Contains, ST_DWithin

from app.core.db_utils import get_db_pool
from app.core.redis import cache
from app.core.config import settings

logger = structlog.get_logger()


@dataclass
class QueryPerformanceMetrics:
    """Query performance metrics data class"""
    query_hash: str
    execution_time_ms: float
    rows_returned: int
    query_type: str
    timestamp: datetime
    parameters: Optional[Dict[str, Any]] = None
    explain_plan: Optional[str] = None


class QueryOptimizer:
    """Database query optimization and performance monitoring"""
    
    def __init__(self):
        self.slow_query_threshold_ms = 1000  # 1 second
        self.cache_ttl = 300  # 5 minutes
        self.performance_metrics: List[QueryPerformanceMetrics] = []
        
    @asynccontextmanager
    async def monitor_query(
        self, 
        query_name: str, 
        query: Union[str, Select],
        parameters: Optional[Dict[str, Any]] = None
    ):
        """
        Context manager to monitor query performance
        
        Args:
            query_name: Human-readable query name
            query: SQL query string or SQLAlchemy Select object
            parameters: Query parameters
            
        Yields:
            Query execution context
        """
        start_time = time.time()
        query_str = str(query) if hasattr(query, '__str__') else query
        query_hash = str(hash(query_str))
        
        try:
            yield
            
        finally:
            execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Log slow queries
            if execution_time > self.slow_query_threshold_ms:
                logger.warning(
                    "slow_query_detected",
                    query_name=query_name,
                    execution_time_ms=execution_time,
                    query_hash=query_hash,
                    parameters=parameters
                )
            
            # Store performance metrics
            metrics = QueryPerformanceMetrics(
                query_hash=query_hash,
                execution_time_ms=execution_time,
                rows_returned=0,  # Will be updated by caller
                query_type=query_name,
                timestamp=datetime.utcnow(),
                parameters=parameters
            )
            
            self.performance_metrics.append(metrics)
            
            # Keep only last 1000 metrics in memory
            if len(self.performance_metrics) > 1000:
                self.performance_metrics = self.performance_metrics[-1000:]
    
    async def get_query_explain_plan(
        self, 
        query: str, 
        parameters: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Get EXPLAIN ANALYZE plan for a query
        
        Args:
            query: SQL query string
            parameters: Query parameters
            
        Returns:
            EXPLAIN ANALYZE output
        """
        pool = await get_db_pool()
        
        try:
            async with pool.acquire() as conn:
                explain_query = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}"
                
                if parameters:
                    result = await conn.fetchval(explain_query, *parameters.values())
                else:
                    result = await conn.fetchval(explain_query)
                
                return str(result)
                
        except Exception as e:
            logger.error("failed_to_get_explain_plan", error=str(e), query=query)
            return f"Error getting explain plan: {str(e)}"
    
    async def analyze_query_performance(
        self, 
        query_type: Optional[str] = None,
        hours_back: int = 24
    ) -> Dict[str, Any]:
        """
        Analyze query performance metrics
        
        Args:
            query_type: Optional filter by query type
            hours_back: Number of hours to analyze
            
        Returns:
            Performance analysis results
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        
        # Filter metrics
        filtered_metrics = [
            m for m in self.performance_metrics 
            if m.timestamp >= cutoff_time and (not query_type or m.query_type == query_type)
        ]
        
        if not filtered_metrics:
            return {"message": "No metrics available for the specified period"}
        
        # Calculate statistics
        execution_times = [m.execution_time_ms for m in filtered_metrics]
        
        analysis = {
            "total_queries": len(filtered_metrics),
            "avg_execution_time_ms": sum(execution_times) / len(execution_times),
            "min_execution_time_ms": min(execution_times),
            "max_execution_time_ms": max(execution_times),
            "slow_queries_count": len([t for t in execution_times if t > self.slow_query_threshold_ms]),
            "query_types": {},
            "slowest_queries": []
        }
        
        # Group by query type
        for metric in filtered_metrics:
            if metric.query_type not in analysis["query_types"]:
                analysis["query_types"][metric.query_type] = {
                    "count": 0,
                    "avg_time_ms": 0,
                    "total_time_ms": 0
                }
            
            analysis["query_types"][metric.query_type]["count"] += 1
            analysis["query_types"][metric.query_type]["total_time_ms"] += metric.execution_time_ms
        
        # Calculate averages for each query type
        for query_type_stats in analysis["query_types"].values():
            query_type_stats["avg_time_ms"] = (
                query_type_stats["total_time_ms"] / query_type_stats["count"]
            )
        
        # Get slowest queries
        sorted_metrics = sorted(filtered_metrics, key=lambda m: m.execution_time_ms, reverse=True)
        analysis["slowest_queries"] = [
            {
                "query_type": m.query_type,
                "execution_time_ms": m.execution_time_ms,
                "timestamp": m.timestamp.isoformat(),
                "query_hash": m.query_hash
            }
            for m in sorted_metrics[:10]
        ]
        
        return analysis


# Global query optimizer instance
query_optimizer = QueryOptimizer()


class OptimizedGeospatialQueries:
    """Optimized geospatial query implementations"""
    
    @staticmethod
    async def find_coverage_for_location(
        latitude: float, 
        longitude: float,
        firm_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """
        Optimized query to find coverage areas for a location
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            firm_id: Optional firm ID filter
            
        Returns:
            List of coverage areas that contain the location
        """
        pool = await get_db_pool()
        
        # Use spatial index for efficient point-in-polygon queries
        base_query = """
            SELECT 
                ca.id,
                ca.firm_id,
                ca.name,
                sf.name as firm_name,
                sf.verification_status,
                ST_Distance(
                    ca.boundary::geography,
                    ST_GeomFromText($1, 4326)::geography
                ) / 1000.0 as distance_km
            FROM coverage_areas ca
            JOIN security_firms sf ON ca.firm_id = sf.id
            WHERE ST_Contains(ca.boundary, ST_GeomFromText($1, 4326))
            AND sf.verification_status = 'approved'
        """
        
        params = [f"POINT({longitude} {latitude})"]
        
        if firm_id:
            base_query += " AND ca.firm_id = $2"
            params.append(str(firm_id))
        
        base_query += " ORDER BY distance_km ASC"
        
        async with query_optimizer.monitor_query("find_coverage_for_location", base_query, {"lat": latitude, "lon": longitude}):
            async with pool.acquire() as conn:
                rows = await conn.fetch(base_query, *params)
                
                return [
                    {
                        "coverage_area_id": str(row["id"]),
                        "firm_id": str(row["firm_id"]),
                        "coverage_area_name": row["name"],
                        "firm_name": row["firm_name"],
                        "verification_status": row["verification_status"],
                        "distance_km": float(row["distance_km"])
                    }
                    for row in rows
                ]
    
    @staticmethod
    async def find_nearest_service_providers(
        latitude: float,
        longitude: float,
        service_type: str,
        firm_id: UUID,
        max_distance_km: float = 50.0,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Optimized query to find nearest service providers using spatial index
        
        Args:
            latitude: Request location latitude
            longitude: Request location longitude
            service_type: Type of service needed
            firm_id: Security firm ID
            max_distance_km: Maximum search distance
            limit: Maximum number of providers to return
            
        Returns:
            List of nearest service providers with distances
        """
        pool = await get_db_pool()
        
        # Use ST_DWithin for efficient distance-based filtering with spatial index
        query = """
            SELECT 
                sp.id,
                sp.name,
                sp.service_type,
                sp.email,
                sp.phone,
                sp.address,
                ST_Y(sp.location) as latitude,
                ST_X(sp.location) as longitude,
                ST_Distance(
                    sp.location::geography,
                    ST_GeomFromText($1, 4326)::geography
                ) / 1000.0 as distance_km
            FROM service_providers sp
            WHERE sp.firm_id = $2
            AND sp.service_type = $3
            AND sp.is_active = true
            AND ST_DWithin(
                sp.location::geography,
                ST_GeomFromText($1, 4326)::geography,
                $4 * 1000
            )
            ORDER BY sp.location <-> ST_GeomFromText($1, 4326)
            LIMIT $5
        """
        
        params = [
            f"POINT({longitude} {latitude})",
            str(firm_id),
            service_type,
            max_distance_km,
            limit
        ]
        
        async with query_optimizer.monitor_query("find_nearest_service_providers", query, {
            "lat": latitude, "lon": longitude, "service_type": service_type, "firm_id": str(firm_id)
        }):
            async with pool.acquire() as conn:
                rows = await conn.fetch(query, *params)
                
                return [
                    {
                        "provider_id": str(row["id"]),
                        "name": row["name"],
                        "service_type": row["service_type"],
                        "email": row["email"],
                        "phone": row["phone"],
                        "address": row["address"],
                        "location": {
                            "latitude": float(row["latitude"]),
                            "longitude": float(row["longitude"])
                        },
                        "distance_km": float(row["distance_km"])
                    }
                    for row in rows
                ]
    
    @staticmethod
    async def get_zone_performance_metrics(
        firm_id: UUID,
        zone_name: Optional[str] = None,
        service_type: Optional[str] = None,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """
        Optimized query for zone performance metrics using indexes
        
        Args:
            firm_id: Security firm ID
            zone_name: Optional zone filter
            service_type: Optional service type filter
            days_back: Number of days to analyze
            
        Returns:
            Zone performance metrics
        """
        pool = await get_db_pool()
        
        # Use composite index on (zone_name, service_type) for efficient filtering
        base_query = """
            SELECT 
                rtm.zone_name,
                rtm.service_type,
                COUNT(*) as total_requests,
                AVG(rtm.response_time_minutes) as avg_response_time,
                MIN(rtm.response_time_minutes) as min_response_time,
                MAX(rtm.response_time_minutes) as max_response_time,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY rtm.response_time_minutes) as median_response_time,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY rtm.response_time_minutes) as p95_response_time
            FROM response_time_metrics rtm
            WHERE rtm.firm_id = $1
            AND rtm.created_at >= $2
        """
        
        params = [str(firm_id), datetime.utcnow() - timedelta(days=days_back)]
        param_count = 2
        
        if zone_name:
            param_count += 1
            base_query += f" AND rtm.zone_name = ${param_count}"
            params.append(zone_name)
        
        if service_type:
            param_count += 1
            base_query += f" AND rtm.service_type = ${param_count}"
            params.append(service_type)
        
        base_query += """
            GROUP BY rtm.zone_name, rtm.service_type
            ORDER BY avg_response_time DESC
        """
        
        async with query_optimizer.monitor_query("get_zone_performance_metrics", base_query, {
            "firm_id": str(firm_id), "zone_name": zone_name, "service_type": service_type
        }):
            async with pool.acquire() as conn:
                rows = await conn.fetch(base_query, *params)
                
                metrics = []
                for row in rows:
                    metrics.append({
                        "zone_name": row["zone_name"],
                        "service_type": row["service_type"],
                        "total_requests": row["total_requests"],
                        "avg_response_time_minutes": float(row["avg_response_time"]),
                        "min_response_time_minutes": float(row["min_response_time"]),
                        "max_response_time_minutes": float(row["max_response_time"]),
                        "median_response_time_minutes": float(row["median_response_time"]),
                        "p95_response_time_minutes": float(row["p95_response_time"])
                    })
                
                return {
                    "firm_id": str(firm_id),
                    "analysis_period_days": days_back,
                    "zone_metrics": metrics,
                    "total_zones": len(set(m["zone_name"] for m in metrics)),
                    "total_service_types": len(set(m["service_type"] for m in metrics))
                }


class OptimizedUserQueries:
    """Optimized user and subscription related queries"""
    
    @staticmethod
    async def get_user_active_subscriptions_with_groups(user_id: UUID) -> List[Dict[str, Any]]:
        """
        Optimized query to get user's active subscriptions with group details
        
        Args:
            user_id: User ID
            
        Returns:
            List of active subscriptions with group information
        """
        pool = await get_db_pool()
        
        # Use indexes on user_id, is_applied, and subscription_expires_at
        query = """
            SELECT 
                ss.id as subscription_id,
                ss.purchased_at,
                ss.applied_at,
                sp.name as product_name,
                sp.price,
                sp.max_users,
                sf.name as firm_name,
                sf.id as firm_id,
                ug.id as group_id,
                ug.name as group_name,
                ug.address as group_address,
                ug.subscription_expires_at,
                ST_Y(ug.location) as group_latitude,
                ST_X(ug.location) as group_longitude,
                COUNT(gmn.id) as mobile_numbers_count
            FROM stored_subscriptions ss
            JOIN subscription_products sp ON ss.product_id = sp.id
            JOIN security_firms sf ON sp.firm_id = sf.id
            LEFT JOIN user_groups ug ON ss.applied_to_group_id = ug.id
            LEFT JOIN group_mobile_numbers gmn ON ug.id = gmn.group_id AND gmn.is_verified = true
            WHERE ss.user_id = $1
            AND ss.is_applied = true
            AND (ug.subscription_expires_at IS NULL OR ug.subscription_expires_at > NOW())
            GROUP BY ss.id, sp.id, sf.id, ug.id
            ORDER BY ss.applied_at DESC
        """
        
        async with query_optimizer.monitor_query("get_user_active_subscriptions", query, {"user_id": str(user_id)}):
            async with pool.acquire() as conn:
                rows = await conn.fetch(query, str(user_id))
                
                return [
                    {
                        "subscription_id": str(row["subscription_id"]),
                        "purchased_at": row["purchased_at"].isoformat(),
                        "applied_at": row["applied_at"].isoformat() if row["applied_at"] else None,
                        "product": {
                            "name": row["product_name"],
                            "price": float(row["price"]),
                            "max_users": row["max_users"]
                        },
                        "firm": {
                            "id": str(row["firm_id"]),
                            "name": row["firm_name"]
                        },
                        "group": {
                            "id": str(row["group_id"]) if row["group_id"] else None,
                            "name": row["group_name"],
                            "address": row["group_address"],
                            "location": {
                                "latitude": float(row["group_latitude"]) if row["group_latitude"] else None,
                                "longitude": float(row["group_longitude"]) if row["group_longitude"] else None
                            },
                            "expires_at": row["subscription_expires_at"].isoformat() if row["subscription_expires_at"] else None,
                            "mobile_numbers_count": row["mobile_numbers_count"]
                        } if row["group_id"] else None
                    }
                    for row in rows
                ]
    
    @staticmethod
    async def get_firm_personnel_with_teams(firm_id: UUID, role_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Optimized query to get firm personnel with team information
        
        Args:
            firm_id: Security firm ID
            role_filter: Optional role filter
            
        Returns:
            List of personnel with team details
        """
        pool = await get_db_pool()
        
        # Use indexes on firm_id, role, and is_active
        base_query = """
            SELECT 
                fp.id,
                fp.email,
                fp.phone,
                fp.first_name,
                fp.last_name,
                fp.role,
                fp.is_active,
                fp.created_at,
                t.id as team_id,
                t.name as team_name,
                ca.name as coverage_area_name,
                leader.first_name as team_leader_first_name,
                leader.last_name as team_leader_last_name
            FROM firm_personnel fp
            LEFT JOIN teams t ON fp.team_id = t.id
            LEFT JOIN coverage_areas ca ON t.coverage_area_id = ca.id
            LEFT JOIN firm_personnel leader ON t.team_leader_id = leader.id
            WHERE fp.firm_id = $1
            AND fp.is_active = true
        """
        
        params = [str(firm_id)]
        
        if role_filter:
            base_query += " AND fp.role = $2"
            params.append(role_filter)
        
        base_query += " ORDER BY fp.role, fp.last_name, fp.first_name"
        
        async with query_optimizer.monitor_query("get_firm_personnel_with_teams", base_query, {
            "firm_id": str(firm_id), "role_filter": role_filter
        }):
            async with pool.acquire() as conn:
                rows = await conn.fetch(base_query, *params)
                
                return [
                    {
                        "personnel_id": str(row["id"]),
                        "email": row["email"],
                        "phone": row["phone"],
                        "first_name": row["first_name"],
                        "last_name": row["last_name"],
                        "role": row["role"],
                        "is_active": row["is_active"],
                        "created_at": row["created_at"].isoformat(),
                        "team": {
                            "id": str(row["team_id"]) if row["team_id"] else None,
                            "name": row["team_name"],
                            "coverage_area_name": row["coverage_area_name"],
                            "team_leader": {
                                "first_name": row["team_leader_first_name"],
                                "last_name": row["team_leader_last_name"]
                            } if row["team_leader_first_name"] else None
                        } if row["team_id"] else None
                    }
                    for row in rows
                ]


class OptimizedEmergencyQueries:
    """Optimized emergency request related queries"""
    
    @staticmethod
    async def get_recent_requests_with_metrics(
        firm_id: UUID,
        hours_back: int = 24,
        status_filter: Optional[str] = None,
        service_type_filter: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Optimized query to get recent emergency requests with performance metrics
        
        Args:
            firm_id: Security firm ID
            hours_back: Number of hours to look back
            status_filter: Optional status filter
            service_type_filter: Optional service type filter
            limit: Maximum number of requests to return
            
        Returns:
            Recent requests with aggregated metrics
        """
        pool = await get_db_pool()
        
        # Use composite indexes for efficient filtering
        base_query = """
            SELECT 
                pr.id,
                pr.requester_phone,
                pr.service_type,
                pr.status,
                pr.address,
                pr.created_at,
                pr.accepted_at,
                pr.arrived_at,
                pr.completed_at,
                ST_Y(pr.location) as latitude,
                ST_X(pr.location) as longitude,
                ug.name as group_name,
                ru.first_name as user_first_name,
                ru.last_name as user_last_name,
                t.name as assigned_team_name,
                sp_provider.name as service_provider_name,
                CASE 
                    WHEN pr.completed_at IS NOT NULL AND pr.accepted_at IS NOT NULL 
                    THEN EXTRACT(EPOCH FROM (pr.completed_at - pr.accepted_at)) / 60.0
                    ELSE NULL
                END as response_time_minutes
            FROM panic_requests pr
            JOIN user_groups ug ON pr.group_id = ug.id
            JOIN registered_users ru ON ug.user_id = ru.id
            JOIN stored_subscriptions ss ON ug.subscription_id = ss.id
            JOIN subscription_products sp ON ss.product_id = sp.id
            LEFT JOIN teams t ON pr.assigned_team_id = t.id
            LEFT JOIN service_providers sp_provider ON pr.assigned_service_provider_id = sp_provider.id
            WHERE sp.firm_id = $1
            AND pr.created_at >= $2
        """
        
        params = [str(firm_id), datetime.utcnow() - timedelta(hours=hours_back)]
        param_count = 2
        
        if status_filter:
            param_count += 1
            base_query += f" AND pr.status = ${param_count}"
            params.append(status_filter)
        
        if service_type_filter:
            param_count += 1
            base_query += f" AND pr.service_type = ${param_count}"
            params.append(service_type_filter)
        
        base_query += f"""
            ORDER BY pr.created_at DESC
            LIMIT ${param_count + 1}
        """
        params.append(limit)
        
        async with query_optimizer.monitor_query("get_recent_requests_with_metrics", base_query, {
            "firm_id": str(firm_id), "hours_back": hours_back
        }):
            async with pool.acquire() as conn:
                rows = await conn.fetch(base_query, *params)
                
                requests = []
                response_times = []
                status_counts = {}
                service_type_counts = {}
                
                for row in rows:
                    request_data = {
                        "request_id": str(row["id"]),
                        "requester_phone": row["requester_phone"],
                        "service_type": row["service_type"],
                        "status": row["status"],
                        "address": row["address"],
                        "location": {
                            "latitude": float(row["latitude"]),
                            "longitude": float(row["longitude"])
                        },
                        "timestamps": {
                            "created_at": row["created_at"].isoformat(),
                            "accepted_at": row["accepted_at"].isoformat() if row["accepted_at"] else None,
                            "arrived_at": row["arrived_at"].isoformat() if row["arrived_at"] else None,
                            "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None
                        },
                        "group_name": row["group_name"],
                        "user": {
                            "first_name": row["user_first_name"],
                            "last_name": row["user_last_name"]
                        },
                        "assigned_team_name": row["assigned_team_name"],
                        "service_provider_name": row["service_provider_name"],
                        "response_time_minutes": float(row["response_time_minutes"]) if row["response_time_minutes"] else None
                    }
                    
                    requests.append(request_data)
                    
                    # Collect metrics
                    if row["response_time_minutes"]:
                        response_times.append(float(row["response_time_minutes"]))
                    
                    status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1
                    service_type_counts[row["service_type"]] = service_type_counts.get(row["service_type"], 0) + 1
                
                # Calculate aggregate metrics
                metrics = {
                    "total_requests": len(requests),
                    "avg_response_time_minutes": sum(response_times) / len(response_times) if response_times else 0,
                    "status_breakdown": status_counts,
                    "service_type_breakdown": service_type_counts,
                    "completed_requests": len(response_times)
                }
                
                return {
                    "requests": requests,
                    "metrics": metrics,
                    "query_params": {
                        "firm_id": str(firm_id),
                        "hours_back": hours_back,
                        "status_filter": status_filter,
                        "service_type_filter": service_type_filter,
                        "limit": limit
                    }
                }


# Connection pool optimization utilities
class ConnectionPoolOptimizer:
    """Connection pool optimization and monitoring"""
    
    @staticmethod
    async def get_pool_stats() -> Dict[str, Any]:
        """
        Get connection pool statistics
        
        Returns:
            Pool statistics
        """
        pool = await get_db_pool()
        
        return {
            "pool_size": pool.get_size(),
            "pool_min_size": pool.get_min_size(),
            "pool_max_size": pool.get_max_size(),
            "pool_idle_size": pool.get_idle_size(),
            "pool_used_size": pool.get_size() - pool.get_idle_size(),
            "pool_utilization_percent": ((pool.get_size() - pool.get_idle_size()) / pool.get_max_size()) * 100
        }
    
    @staticmethod
    async def optimize_pool_settings() -> Dict[str, Any]:
        """
        Analyze and suggest pool optimization settings
        
        Returns:
            Optimization recommendations
        """
        stats = await ConnectionPoolOptimizer.get_pool_stats()
        recommendations = []
        
        # Check pool utilization
        if stats["pool_utilization_percent"] > 80:
            recommendations.append({
                "type": "warning",
                "message": "High pool utilization detected. Consider increasing max_size.",
                "current_max_size": stats["pool_max_size"],
                "suggested_max_size": min(stats["pool_max_size"] * 2, 50)
            })
        
        if stats["pool_utilization_percent"] < 20 and stats["pool_max_size"] > 10:
            recommendations.append({
                "type": "info",
                "message": "Low pool utilization. Consider reducing max_size to save resources.",
                "current_max_size": stats["pool_max_size"],
                "suggested_max_size": max(stats["pool_max_size"] // 2, 10)
            })
        
        return {
            "current_stats": stats,
            "recommendations": recommendations,
            "optimal_settings": {
                "min_size": max(5, stats["pool_max_size"] // 4),
                "max_size": stats["pool_max_size"],
                "command_timeout": 60,
                "server_settings": {
                    "jit": "off",
                    "shared_preload_libraries": "pg_stat_statements",
                    "track_activity_query_size": "2048"
                }
            }
        }


# Query caching utilities
class QueryCache:
    """Intelligent query result caching"""
    
    @staticmethod
    async def get_or_execute(
        cache_key: str,
        query_func,
        ttl: int = 300,
        *args,
        **kwargs
    ) -> Any:
        """
        Get result from cache or execute query and cache result
        
        Args:
            cache_key: Cache key
            query_func: Function to execute if cache miss
            ttl: Time to live in seconds
            *args: Arguments for query function
            **kwargs: Keyword arguments for query function
            
        Returns:
            Query result (from cache or fresh execution)
        """
        # Try to get from cache first
        cached_result = await cache.get(cache_key)
        if cached_result:
            logger.debug("cache_hit", cache_key=cache_key)
            return cached_result
        
        # Execute query
        logger.debug("cache_miss", cache_key=cache_key)
        result = await query_func(*args, **kwargs)
        
        # Cache the result
        await cache.set(cache_key, result, expire=ttl)
        
        return result
    
    @staticmethod
    def generate_cache_key(prefix: str, **params) -> str:
        """
        Generate a consistent cache key from parameters
        
        Args:
            prefix: Cache key prefix
            **params: Parameters to include in key
            
        Returns:
            Generated cache key
        """
        # Sort parameters for consistent key generation
        sorted_params = sorted(params.items())
        param_str = "_".join(f"{k}:{v}" for k, v in sorted_params)
        return f"{prefix}:{param_str}"