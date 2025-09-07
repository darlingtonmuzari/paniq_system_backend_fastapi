"""
Database optimization service for monitoring and improving query performance
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from uuid import UUID
import asyncio
import structlog

from app.core.query_optimizer import (
    query_optimizer, 
    OptimizedGeospatialQueries,
    OptimizedUserQueries,
    OptimizedEmergencyQueries,
    ConnectionPoolOptimizer,
    QueryCache
)
from app.core.db_utils import (
    get_pool_statistics,
    analyze_slow_queries,
    optimize_database_settings,
    execute_optimized_query
)
from app.core.redis import cache

logger = structlog.get_logger()


class DatabaseOptimizationService:
    """Service for database performance optimization and monitoring"""
    
    def __init__(self):
        self.optimization_cache_ttl = 300  # 5 minutes
        self.performance_monitoring_enabled = True
    
    async def get_performance_dashboard(self) -> Dict[str, Any]:
        """
        Get comprehensive database performance dashboard
        
        Returns:
            Performance dashboard data
        """
        try:
            # Get pool statistics
            pool_stats = await get_pool_statistics()
            
            # Get query performance analysis
            query_analysis = await query_optimizer.analyze_query_performance(hours_back=24)
            
            # Get slow queries
            slow_queries = await analyze_slow_queries()
            
            # Get database optimization suggestions
            db_optimization = await optimize_database_settings()
            
            # Get connection pool optimization
            pool_optimization = await ConnectionPoolOptimizer.optimize_pool_settings()
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "pool_statistics": pool_stats,
                "query_performance": query_analysis,
                "slow_queries": slow_queries[:10],  # Top 10 slow queries
                "database_optimization": db_optimization,
                "pool_optimization": pool_optimization,
                "cache_statistics": await self._get_cache_statistics(),
                "recommendations": await self._generate_optimization_recommendations(
                    pool_stats, query_analysis, slow_queries
                )
            }
            
        except Exception as e:
            logger.error("failed_to_generate_performance_dashboard", error=str(e))
            return {"error": str(e)}
    
    async def optimize_geospatial_queries(self) -> Dict[str, Any]:
        """
        Test and optimize geospatial query performance
        
        Returns:
            Geospatial optimization results
        """
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "tests": []
        }
        
        try:
            # Test coverage area queries
            test_locations = [
                (40.7128, -74.0060),  # New York
                (34.0522, -118.2437),  # Los Angeles
                (41.8781, -87.6298),   # Chicago
            ]
            
            for lat, lon in test_locations:
                start_time = asyncio.get_event_loop().time()
                
                coverage_results = await OptimizedGeospatialQueries.find_coverage_for_location(
                    lat, lon
                )
                
                execution_time = (asyncio.get_event_loop().time() - start_time) * 1000
                
                results["tests"].append({
                    "test_type": "coverage_lookup",
                    "location": {"latitude": lat, "longitude": lon},
                    "execution_time_ms": execution_time,
                    "results_count": len(coverage_results),
                    "performance_rating": "excellent" if execution_time < 50 else 
                                        "good" if execution_time < 100 else 
                                        "needs_optimization"
                })
            
            # Test service provider queries
            if test_locations:
                lat, lon = test_locations[0]
                
                for service_type in ["ambulance", "fire", "towing"]:
                    start_time = asyncio.get_event_loop().time()
                    
                    # Note: This would need a valid firm_id in a real scenario
                    # For testing, we'll simulate the query structure
                    test_query = """
                        SELECT COUNT(*) FROM service_providers sp
                        WHERE sp.service_type = $1
                        AND sp.is_active = true
                        AND ST_DWithin(
                            sp.location::geography,
                            ST_GeomFromText($2, 4326)::geography,
                            50000
                        )
                    """
                    
                    result = await execute_optimized_query(
                        test_query,
                        service_type,
                        f"POINT({lon} {lat})",
                        query_name=f"test_service_provider_{service_type}"
                    )
                    
                    execution_time = (asyncio.get_event_loop().time() - start_time) * 1000
                    
                    results["tests"].append({
                        "test_type": "service_provider_lookup",
                        "service_type": service_type,
                        "location": {"latitude": lat, "longitude": lon},
                        "execution_time_ms": execution_time,
                        "results_count": result[0]["count"] if result else 0,
                        "performance_rating": "excellent" if execution_time < 100 else 
                                            "good" if execution_time < 200 else 
                                            "needs_optimization"
                    })
            
            # Calculate overall performance score
            avg_time = sum(t["execution_time_ms"] for t in results["tests"]) / len(results["tests"])
            results["overall_performance"] = {
                "average_execution_time_ms": avg_time,
                "rating": "excellent" if avg_time < 75 else 
                         "good" if avg_time < 150 else 
                         "needs_optimization",
                "total_tests": len(results["tests"])
            }
            
        except Exception as e:
            logger.error("failed_to_optimize_geospatial_queries", error=str(e))
            results["error"] = str(e)
        
        return results
    
    async def optimize_user_queries(self, sample_user_id: Optional[UUID] = None) -> Dict[str, Any]:
        """
        Test and optimize user-related query performance
        
        Args:
            sample_user_id: Optional user ID for testing
            
        Returns:
            User query optimization results
        """
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "tests": []
        }
        
        try:
            # Test user subscription queries
            if sample_user_id:
                start_time = asyncio.get_event_loop().time()
                
                subscriptions = await OptimizedUserQueries.get_user_active_subscriptions_with_groups(
                    sample_user_id
                )
                
                execution_time = (asyncio.get_event_loop().time() - start_time) * 1000
                
                results["tests"].append({
                    "test_type": "user_subscriptions",
                    "user_id": str(sample_user_id),
                    "execution_time_ms": execution_time,
                    "results_count": len(subscriptions),
                    "performance_rating": "excellent" if execution_time < 100 else 
                                        "good" if execution_time < 200 else 
                                        "needs_optimization"
                })
            
            # Test general user query patterns
            test_queries = [
                {
                    "name": "active_users_count",
                    "query": "SELECT COUNT(*) FROM registered_users WHERE is_suspended = false",
                    "expected_time_ms": 50
                },
                {
                    "name": "recent_registrations",
                    "query": "SELECT COUNT(*) FROM registered_users WHERE created_at >= NOW() - INTERVAL '7 days'",
                    "expected_time_ms": 100
                },
                {
                    "name": "subscription_expiry_check",
                    "query": "SELECT COUNT(*) FROM user_groups WHERE subscription_expires_at <= NOW() + INTERVAL '7 days'",
                    "expected_time_ms": 75
                }
            ]
            
            for test in test_queries:
                start_time = asyncio.get_event_loop().time()
                
                result = await execute_optimized_query(
                    test["query"],
                    query_name=test["name"]
                )
                
                execution_time = (asyncio.get_event_loop().time() - start_time) * 1000
                
                results["tests"].append({
                    "test_type": test["name"],
                    "execution_time_ms": execution_time,
                    "expected_time_ms": test["expected_time_ms"],
                    "performance_rating": "excellent" if execution_time < test["expected_time_ms"] else 
                                        "good" if execution_time < test["expected_time_ms"] * 1.5 else 
                                        "needs_optimization",
                    "results_count": result[0]["count"] if result else 0
                })
            
        except Exception as e:
            logger.error("failed_to_optimize_user_queries", error=str(e))
            results["error"] = str(e)
        
        return results
    
    async def optimize_emergency_queries(self, sample_firm_id: Optional[UUID] = None) -> Dict[str, Any]:
        """
        Test and optimize emergency request query performance
        
        Args:
            sample_firm_id: Optional firm ID for testing
            
        Returns:
            Emergency query optimization results
        """
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "tests": []
        }
        
        try:
            # Test emergency request queries
            if sample_firm_id:
                start_time = asyncio.get_event_loop().time()
                
                recent_requests = await OptimizedEmergencyQueries.get_recent_requests_with_metrics(
                    sample_firm_id,
                    hours_back=24,
                    limit=50
                )
                
                execution_time = (asyncio.get_event_loop().time() - start_time) * 1000
                
                results["tests"].append({
                    "test_type": "recent_requests_with_metrics",
                    "firm_id": str(sample_firm_id),
                    "execution_time_ms": execution_time,
                    "results_count": len(recent_requests.get("requests", [])),
                    "performance_rating": "excellent" if execution_time < 200 else 
                                        "good" if execution_time < 400 else 
                                        "needs_optimization"
                })
            
            # Test general emergency query patterns
            test_queries = [
                {
                    "name": "pending_requests_count",
                    "query": "SELECT COUNT(*) FROM panic_requests WHERE status = 'pending'",
                    "expected_time_ms": 25
                },
                {
                    "name": "recent_requests_by_service",
                    "query": """
                        SELECT service_type, COUNT(*) 
                        FROM panic_requests 
                        WHERE created_at >= NOW() - INTERVAL '24 hours'
                        GROUP BY service_type
                    """,
                    "expected_time_ms": 100
                },
                {
                    "name": "response_time_analysis",
                    "query": """
                        SELECT AVG(EXTRACT(EPOCH FROM (completed_at - accepted_at)) / 60.0) as avg_response_minutes
                        FROM panic_requests 
                        WHERE completed_at IS NOT NULL AND accepted_at IS NOT NULL
                        AND created_at >= NOW() - INTERVAL '7 days'
                    """,
                    "expected_time_ms": 150
                }
            ]
            
            for test in test_queries:
                start_time = asyncio.get_event_loop().time()
                
                result = await execute_optimized_query(
                    test["query"],
                    query_name=test["name"]
                )
                
                execution_time = (asyncio.get_event_loop().time() - start_time) * 1000
                
                results["tests"].append({
                    "test_type": test["name"],
                    "execution_time_ms": execution_time,
                    "expected_time_ms": test["expected_time_ms"],
                    "performance_rating": "excellent" if execution_time < test["expected_time_ms"] else 
                                        "good" if execution_time < test["expected_time_ms"] * 1.5 else 
                                        "needs_optimization",
                    "has_results": len(result) > 0 if result else False
                })
            
        except Exception as e:
            logger.error("failed_to_optimize_emergency_queries", error=str(e))
            results["error"] = str(e)
        
        return results
    
    async def run_comprehensive_optimization(self) -> Dict[str, Any]:
        """
        Run comprehensive database optimization analysis
        
        Returns:
            Complete optimization report
        """
        logger.info("starting_comprehensive_database_optimization")
        
        optimization_report = {
            "timestamp": datetime.utcnow().isoformat(),
            "optimization_id": f"opt_{int(datetime.utcnow().timestamp())}",
            "status": "running"
        }
        
        try:
            # Run all optimization tests
            tasks = [
                self.get_performance_dashboard(),
                self.optimize_geospatial_queries(),
                self.optimize_user_queries(),
                self.optimize_emergency_queries()
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            optimization_report.update({
                "status": "completed",
                "performance_dashboard": results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])},
                "geospatial_optimization": results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])},
                "user_optimization": results[2] if not isinstance(results[2], Exception) else {"error": str(results[2])},
                "emergency_optimization": results[3] if not isinstance(results[3], Exception) else {"error": str(results[3])},
                "summary": await self._generate_optimization_summary(results)
            })
            
            # Cache the report
            await cache.set(
                f"optimization_report:{optimization_report['optimization_id']}",
                optimization_report,
                expire=3600  # 1 hour
            )
            
            logger.info(
                "comprehensive_optimization_completed",
                optimization_id=optimization_report["optimization_id"],
                duration_seconds=(datetime.utcnow().timestamp() - 
                                int(optimization_report["optimization_id"].split("_")[1]))
            )
            
        except Exception as e:
            logger.error("comprehensive_optimization_failed", error=str(e))
            optimization_report.update({
                "status": "failed",
                "error": str(e)
            })
        
        return optimization_report
    
    async def _get_cache_statistics(self) -> Dict[str, Any]:
        """Get Redis cache statistics"""
        try:
            # Get basic cache info
            info = await cache.redis.info()
            
            return {
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "used_memory_peak_human": info.get("used_memory_peak_human", "0B"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate_percent": (
                    (info.get("keyspace_hits", 0) / 
                     max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1)) * 100
                ),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "instantaneous_ops_per_sec": info.get("instantaneous_ops_per_sec", 0)
            }
            
        except Exception as e:
            logger.error("failed_to_get_cache_statistics", error=str(e))
            return {"error": str(e)}
    
    async def _generate_optimization_recommendations(
        self,
        pool_stats: Dict[str, Any],
        query_analysis: Dict[str, Any],
        slow_queries: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate optimization recommendations based on analysis"""
        recommendations = []
        
        # Pool utilization recommendations
        if pool_stats.get("pool_utilization_percent", 0) > 80:
            recommendations.append({
                "category": "connection_pool",
                "priority": "high",
                "issue": "High connection pool utilization",
                "recommendation": "Consider increasing DATABASE_POOL_SIZE or optimizing query patterns",
                "current_value": f"{pool_stats['pool_utilization_percent']:.1f}%",
                "target_value": "< 70%"
            })
        
        # Query performance recommendations
        if query_analysis.get("slow_queries_count", 0) > 10:
            recommendations.append({
                "category": "query_performance",
                "priority": "medium",
                "issue": "High number of slow queries detected",
                "recommendation": "Review and optimize slow queries, consider adding indexes",
                "current_value": str(query_analysis["slow_queries_count"]),
                "target_value": "< 5"
            })
        
        # Average execution time recommendations
        avg_time = query_analysis.get("avg_execution_time_ms", 0)
        if avg_time > 200:
            recommendations.append({
                "category": "query_performance",
                "priority": "high",
                "issue": "High average query execution time",
                "recommendation": "Optimize frequently used queries and add appropriate indexes",
                "current_value": f"{avg_time:.1f}ms",
                "target_value": "< 100ms"
            })
        
        # Slow query specific recommendations
        if slow_queries:
            for query in slow_queries[:3]:  # Top 3 slow queries
                if query["mean_time_ms"] > 500:
                    recommendations.append({
                        "category": "slow_query",
                        "priority": "high",
                        "issue": f"Very slow query detected: {query['query'][:50]}...",
                        "recommendation": "Analyze query execution plan and add missing indexes",
                        "current_value": f"{query['mean_time_ms']:.1f}ms average",
                        "target_value": "< 100ms"
                    })
        
        return recommendations
    
    async def _generate_optimization_summary(self, results: List[Any]) -> Dict[str, Any]:
        """Generate optimization summary from results"""
        summary = {
            "overall_status": "healthy",
            "critical_issues": 0,
            "warnings": 0,
            "optimizations_applied": 0,
            "performance_score": 100
        }
        
        try:
            # Analyze results and calculate summary metrics
            for result in results:
                if isinstance(result, Exception):
                    summary["critical_issues"] += 1
                    summary["performance_score"] -= 20
                    continue
                
                if isinstance(result, dict):
                    # Check for errors in results
                    if "error" in result:
                        summary["critical_issues"] += 1
                        summary["performance_score"] -= 15
                    
                    # Check for performance issues
                    if "tests" in result:
                        for test in result["tests"]:
                            rating = test.get("performance_rating", "good")
                            if rating == "needs_optimization":
                                summary["warnings"] += 1
                                summary["performance_score"] -= 5
                            elif rating == "excellent":
                                summary["optimizations_applied"] += 1
            
            # Determine overall status
            if summary["critical_issues"] > 0:
                summary["overall_status"] = "critical"
            elif summary["warnings"] > 3:
                summary["overall_status"] = "warning"
            elif summary["performance_score"] < 70:
                summary["overall_status"] = "needs_attention"
            
            # Ensure performance score doesn't go below 0
            summary["performance_score"] = max(0, summary["performance_score"])
            
        except Exception as e:
            logger.error("failed_to_generate_optimization_summary", error=str(e))
            summary.update({
                "overall_status": "error",
                "error": str(e)
            })
        
        return summary


# Global service instance
database_optimization_service = DatabaseOptimizationService()