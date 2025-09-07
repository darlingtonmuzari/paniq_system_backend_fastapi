"""
Database optimization API endpoints
"""
from typing import Dict, Any, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse
import structlog

from app.core.auth import get_current_user, require_role
from app.services.database_optimization import database_optimization_service
from app.core.query_optimizer import query_optimizer
from app.core.db_utils import get_pool_statistics, analyze_slow_queries
from app.models.user import RegisteredUser

logger = structlog.get_logger()

router = APIRouter(prefix="/database-optimization", tags=["Database Optimization"])


@router.get("/dashboard")
async def get_performance_dashboard(
    current_user: RegisteredUser = Depends(require_role(["admin", "system_admin"]))
) -> Dict[str, Any]:
    """
    Get comprehensive database performance dashboard
    
    Requires admin privileges
    
    Returns:
        Performance dashboard with metrics, statistics, and recommendations
    """
    try:
        dashboard = await database_optimization_service.get_performance_dashboard()
        
        logger.info(
            "performance_dashboard_accessed",
            user_id=str(current_user.user_id),
            user_email=current_user.email
        )
        
        return dashboard
        
    except Exception as e:
        logger.error(
            "failed_to_get_performance_dashboard",
            error=str(e),
            user_id=str(current_user.user_id)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate performance dashboard: {str(e)}"
        )


@router.get("/pool-statistics")
async def get_connection_pool_statistics(
    current_user: RegisteredUser = Depends(require_role(["admin", "system_admin"]))
) -> Dict[str, Any]:
    """
    Get database connection pool statistics
    
    Requires admin privileges
    
    Returns:
        Connection pool statistics and utilization metrics
    """
    try:
        stats = await get_pool_statistics()
        
        logger.info(
            "pool_statistics_accessed",
            user_id=str(current_user.user_id),
            pool_utilization=stats.get("pool_utilization_percent", 0)
        )
        
        return {
            "timestamp": database_optimization_service.__class__.__name__,
            "pool_statistics": stats,
            "status": "healthy" if stats.get("pool_utilization_percent", 0) < 80 else "warning"
        }
        
    except Exception as e:
        logger.error(
            "failed_to_get_pool_statistics",
            error=str(e),
            user_id=str(current_user.user_id)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get pool statistics: {str(e)}"
        )


@router.get("/slow-queries")
async def get_slow_queries_analysis(
    limit: int = Query(20, ge=1, le=100, description="Maximum number of slow queries to return"),
    current_user: RegisteredUser = Depends(require_role(["admin", "system_admin"]))
) -> Dict[str, Any]:
    """
    Get analysis of slow database queries
    
    Args:
        limit: Maximum number of slow queries to return (1-100)
    
    Requires admin privileges
    
    Returns:
        List of slow queries with performance metrics
    """
    try:
        slow_queries = await analyze_slow_queries()
        
        # Limit results
        limited_queries = slow_queries[:limit]
        
        logger.info(
            "slow_queries_analyzed",
            user_id=str(current_user.user_id),
            total_slow_queries=len(slow_queries),
            returned_queries=len(limited_queries)
        )
        
        return {
            "timestamp": database_optimization_service.__class__.__name__,
            "slow_queries": limited_queries,
            "total_slow_queries": len(slow_queries),
            "returned_queries": len(limited_queries),
            "analysis": {
                "avg_execution_time_ms": sum(q["mean_time_ms"] for q in limited_queries) / len(limited_queries) if limited_queries else 0,
                "total_calls": sum(q["calls"] for q in limited_queries),
                "queries_over_1s": len([q for q in limited_queries if q["mean_time_ms"] > 1000])
            }
        }
        
    except Exception as e:
        logger.error(
            "failed_to_analyze_slow_queries",
            error=str(e),
            user_id=str(current_user.user_id)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze slow queries: {str(e)}"
        )


@router.get("/query-performance")
async def get_query_performance_analysis(
    query_type: Optional[str] = Query(None, description="Filter by query type"),
    hours_back: int = Query(24, ge=1, le=168, description="Hours to analyze (1-168)"),
    current_user: RegisteredUser = Depends(require_role(["admin", "system_admin"]))
) -> Dict[str, Any]:
    """
    Get query performance analysis from monitoring data
    
    Args:
        query_type: Optional filter by query type
        hours_back: Number of hours to analyze (1-168)
    
    Requires admin privileges
    
    Returns:
        Query performance analysis and metrics
    """
    try:
        analysis = await query_optimizer.analyze_query_performance(
            query_type=query_type,
            hours_back=hours_back
        )
        
        logger.info(
            "query_performance_analyzed",
            user_id=str(current_user.user_id),
            query_type=query_type,
            hours_back=hours_back,
            total_queries=analysis.get("total_queries", 0)
        )
        
        return {
            "timestamp": database_optimization_service.__class__.__name__,
            "analysis": analysis,
            "parameters": {
                "query_type": query_type,
                "hours_back": hours_back
            }
        }
        
    except Exception as e:
        logger.error(
            "failed_to_analyze_query_performance",
            error=str(e),
            user_id=str(current_user.user_id)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze query performance: {str(e)}"
        )


@router.post("/optimize/geospatial")
async def optimize_geospatial_queries(
    background_tasks: BackgroundTasks,
    current_user: RegisteredUser = Depends(require_role(["admin", "system_admin"]))
) -> Dict[str, Any]:
    """
    Run geospatial query optimization tests
    
    Requires admin privileges
    
    Returns:
        Geospatial query optimization results
    """
    try:
        results = await database_optimization_service.optimize_geospatial_queries()
        
        logger.info(
            "geospatial_optimization_completed",
            user_id=str(current_user.user_id),
            total_tests=len(results.get("tests", [])),
            overall_rating=results.get("overall_performance", {}).get("rating", "unknown")
        )
        
        return results
        
    except Exception as e:
        logger.error(
            "failed_to_optimize_geospatial_queries",
            error=str(e),
            user_id=str(current_user.user_id)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to optimize geospatial queries: {str(e)}"
        )


@router.post("/optimize/user-queries")
async def optimize_user_queries(
    sample_user_id: Optional[UUID] = Query(None, description="Sample user ID for testing"),
    current_user: RegisteredUser = Depends(require_role(["admin", "system_admin"]))
) -> Dict[str, Any]:
    """
    Run user query optimization tests
    
    Args:
        sample_user_id: Optional user ID to use for testing
    
    Requires admin privileges
    
    Returns:
        User query optimization results
    """
    try:
        results = await database_optimization_service.optimize_user_queries(
            sample_user_id=sample_user_id
        )
        
        logger.info(
            "user_query_optimization_completed",
            user_id=str(current_user.user_id),
            sample_user_id=str(sample_user_id) if sample_user_id else None,
            total_tests=len(results.get("tests", []))
        )
        
        return results
        
    except Exception as e:
        logger.error(
            "failed_to_optimize_user_queries",
            error=str(e),
            user_id=str(current_user.user_id)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to optimize user queries: {str(e)}"
        )


@router.post("/optimize/emergency-queries")
async def optimize_emergency_queries(
    sample_firm_id: Optional[UUID] = Query(None, description="Sample firm ID for testing"),
    current_user: RegisteredUser = Depends(require_role(["admin", "system_admin"]))
) -> Dict[str, Any]:
    """
    Run emergency query optimization tests
    
    Args:
        sample_firm_id: Optional firm ID to use for testing
    
    Requires admin privileges
    
    Returns:
        Emergency query optimization results
    """
    try:
        results = await database_optimization_service.optimize_emergency_queries(
            sample_firm_id=sample_firm_id
        )
        
        logger.info(
            "emergency_query_optimization_completed",
            user_id=str(current_user.user_id),
            sample_firm_id=str(sample_firm_id) if sample_firm_id else None,
            total_tests=len(results.get("tests", []))
        )
        
        return results
        
    except Exception as e:
        logger.error(
            "failed_to_optimize_emergency_queries",
            error=str(e),
            user_id=str(current_user.user_id)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to optimize emergency queries: {str(e)}"
        )


@router.post("/optimize/comprehensive")
async def run_comprehensive_optimization(
    background_tasks: BackgroundTasks,
    current_user: RegisteredUser = Depends(require_role(["admin", "system_admin"]))
) -> Dict[str, Any]:
    """
    Run comprehensive database optimization analysis
    
    This endpoint runs all optimization tests and generates a complete report.
    The operation runs in the background and results are cached.
    
    Requires admin privileges
    
    Returns:
        Comprehensive optimization report
    """
    try:
        # Run comprehensive optimization
        report = await database_optimization_service.run_comprehensive_optimization()
        
        logger.info(
            "comprehensive_optimization_initiated",
            user_id=str(current_user.user_id),
            optimization_id=report.get("optimization_id"),
            status=report.get("status")
        )
        
        return report
        
    except Exception as e:
        logger.error(
            "failed_to_run_comprehensive_optimization",
            error=str(e),
            user_id=str(current_user.user_id)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to run comprehensive optimization: {str(e)}"
        )


@router.get("/optimization-report/{optimization_id}")
async def get_optimization_report(
    optimization_id: str,
    current_user: RegisteredUser = Depends(require_role(["admin", "system_admin"]))
) -> Dict[str, Any]:
    """
    Get cached optimization report by ID
    
    Args:
        optimization_id: Optimization report ID
    
    Requires admin privileges
    
    Returns:
        Cached optimization report
    """
    try:
        from app.core.redis import cache
        
        report = await cache.get(f"optimization_report:{optimization_id}")
        
        if not report:
            raise HTTPException(
                status_code=404,
                detail=f"Optimization report {optimization_id} not found or expired"
            )
        
        logger.info(
            "optimization_report_retrieved",
            user_id=str(current_user.user_id),
            optimization_id=optimization_id
        )
        
        return report
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "failed_to_get_optimization_report",
            error=str(e),
            user_id=str(current_user.user_id),
            optimization_id=optimization_id
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get optimization report: {str(e)}"
        )


@router.get("/explain-plan")
async def get_query_explain_plan(
    query: str = Query(..., description="SQL query to analyze"),
    current_user: RegisteredUser = Depends(require_role(["admin", "system_admin"]))
) -> Dict[str, Any]:
    """
    Get EXPLAIN ANALYZE plan for a SQL query
    
    Args:
        query: SQL query to analyze
    
    Requires admin privileges
    
    Returns:
        Query execution plan and analysis
    """
    try:
        # Basic validation to prevent dangerous queries
        query_lower = query.lower().strip()
        
        # Only allow SELECT queries for safety
        if not query_lower.startswith('select'):
            raise HTTPException(
                status_code=400,
                detail="Only SELECT queries are allowed for explain plan analysis"
            )
        
        # Prevent potentially dangerous operations
        dangerous_keywords = ['drop', 'delete', 'update', 'insert', 'create', 'alter', 'truncate']
        if any(keyword in query_lower for keyword in dangerous_keywords):
            raise HTTPException(
                status_code=400,
                detail="Query contains potentially dangerous operations"
            )
        
        explain_plan = await query_optimizer.get_query_explain_plan(query)
        
        logger.info(
            "explain_plan_generated",
            user_id=str(current_user.user_id),
            query_length=len(query)
        )
        
        return {
            "timestamp": database_optimization_service.__class__.__name__,
            "query": query,
            "explain_plan": explain_plan,
            "recommendations": [
                "Review the execution plan for sequential scans on large tables",
                "Consider adding indexes for columns used in WHERE clauses",
                "Check for expensive operations like nested loops on large datasets",
                "Verify that spatial indexes are being used for geospatial queries"
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "failed_to_generate_explain_plan",
            error=str(e),
            user_id=str(current_user.user_id)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate explain plan: {str(e)}"
        )


@router.get("/health")
async def get_database_health(
    current_user: RegisteredUser = Depends(require_role(["admin", "system_admin"]))
) -> Dict[str, Any]:
    """
    Get database health status
    
    Requires admin privileges
    
    Returns:
        Database health metrics and status
    """
    try:
        from app.core.db_utils import check_db_connection
        
        # Check database connection
        db_connected = await check_db_connection()
        
        # Get pool statistics
        pool_stats = await get_pool_statistics()
        
        # Determine overall health
        health_status = "healthy"
        issues = []
        
        if not db_connected:
            health_status = "critical"
            issues.append("Database connection failed")
        
        if pool_stats.get("pool_utilization_percent", 0) > 90:
            health_status = "warning" if health_status == "healthy" else health_status
            issues.append("High connection pool utilization")
        
        # Get recent query performance
        query_analysis = await query_optimizer.analyze_query_performance(hours_back=1)
        
        if query_analysis.get("slow_queries_count", 0) > 5:
            health_status = "warning" if health_status == "healthy" else health_status
            issues.append("High number of slow queries in the last hour")
        
        health_data = {
            "timestamp": database_optimization_service.__class__.__name__,
            "status": health_status,
            "database_connected": db_connected,
            "pool_statistics": pool_stats,
            "recent_query_performance": {
                "total_queries": query_analysis.get("total_queries", 0),
                "avg_execution_time_ms": query_analysis.get("avg_execution_time_ms", 0),
                "slow_queries_count": query_analysis.get("slow_queries_count", 0)
            },
            "issues": issues,
            "recommendations": []
        }
        
        # Add recommendations based on issues
        if "High connection pool utilization" in issues:
            health_data["recommendations"].append(
                "Consider increasing DATABASE_POOL_SIZE or optimizing query patterns"
            )
        
        if "High number of slow queries" in issues:
            health_data["recommendations"].append(
                "Review slow queries and consider adding database indexes"
            )
        
        logger.info(
            "database_health_checked",
            user_id=str(current_user.user_id),
            health_status=health_status,
            issues_count=len(issues)
        )
        
        return health_data
        
    except Exception as e:
        logger.error(
            "failed_to_check_database_health",
            error=str(e),
            user_id=str(current_user.user_id)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check database health: {str(e)}"
        )