"""
Metrics API endpoints for Prometheus scraping and monitoring
"""
from fastapi import APIRouter, Response, Depends, HTTPException
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from app.core.metrics import metrics_collector
from app.core.config import settings
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import asyncio

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/prometheus", response_class=Response)
async def get_prometheus_metrics():
    """
    Get metrics in Prometheus format for scraping
    """
    if not settings.METRICS_ENABLED:
        raise HTTPException(status_code=404, detail="Metrics disabled")
    
    metrics_data = metrics_collector.get_metrics()
    return Response(
        content=metrics_data,
        media_type="text/plain; version=0.0.4; charset=utf-8"
    )


@router.get("/health")
async def get_system_health(db: AsyncSession = Depends(get_db)):
    """
    Get system health metrics for monitoring dashboards
    """
    try:
        # Check database connectivity
        db_start = datetime.utcnow()
        await db.execute(text("SELECT 1"))
        db_latency = (datetime.utcnow() - db_start).total_seconds() * 1000
        
        # Get basic system stats
        health_data = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": {
                "status": "connected",
                "latency_ms": round(db_latency, 2)
            },
            "metrics": {
                "enabled": settings.METRICS_ENABLED
            }
        }
        
        return health_data
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "database": {
                "status": "disconnected"
            }
        }


@router.get("/business")
async def get_business_metrics(
    db: AsyncSession = Depends(get_db),
    hours: int = 24
):
    """
    Get business metrics for the last N hours
    """
    try:
        since = datetime.utcnow() - timedelta(hours=hours)
        
        # Get panic request metrics
        panic_requests_query = text("""
            SELECT 
                service_type,
                status,
                COUNT(*) as count,
                AVG(EXTRACT(EPOCH FROM (accepted_at - created_at))) as avg_response_time,
                AVG(EXTRACT(EPOCH FROM (completed_at - created_at))) as avg_completion_time
            FROM panic_requests 
            WHERE created_at >= :since
            GROUP BY service_type, status
        """)
        
        panic_results = await db.execute(panic_requests_query, {"since": since})
        panic_metrics = []
        
        for row in panic_results:
            panic_metrics.append({
                "service_type": row.service_type,
                "status": row.status,
                "count": row.count,
                "avg_response_time_seconds": row.avg_response_time,
                "avg_completion_time_seconds": row.avg_completion_time
            })
        
        # Get subscription metrics
        subscription_query = text("""
            SELECT 
                COUNT(*) as active_subscriptions,
                COUNT(DISTINCT user_id) as unique_users
            FROM user_groups 
            WHERE subscription_expires_at > NOW()
        """)
        
        subscription_result = await db.execute(subscription_query)
        subscription_row = subscription_result.fetchone()
        
        # Get prank detection metrics
        prank_query = text("""
            SELECT 
                COUNT(*) as total_prank_flags,
                COUNT(DISTINCT pr.group_id) as users_with_pranks
            FROM request_feedback rf
            JOIN panic_requests pr ON rf.request_id = pr.id
            WHERE rf.is_prank = true AND rf.created_at >= :since
        """)
        
        prank_result = await db.execute(prank_query, {"since": since})
        prank_row = prank_result.fetchone()
        
        return {
            "period_hours": hours,
            "timestamp": datetime.utcnow().isoformat(),
            "panic_requests": panic_metrics,
            "subscriptions": {
                "active_subscriptions": subscription_row.active_subscriptions if subscription_row else 0,
                "unique_users": subscription_row.unique_users if subscription_row else 0
            },
            "prank_detection": {
                "total_flags": prank_row.total_prank_flags if prank_row else 0,
                "users_with_pranks": prank_row.users_with_pranks if prank_row else 0
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching business metrics: {str(e)}")


@router.get("/performance")
async def get_performance_metrics(
    db: AsyncSession = Depends(get_db),
    firm_id: Optional[str] = None,
    hours: int = 24
):
    """
    Get performance metrics by zone and service type
    """
    try:
        since = datetime.utcnow() - timedelta(hours=hours)
        
        # Build query with optional firm filter
        where_clause = "WHERE pr.created_at >= :since"
        params = {"since": since}
        
        if firm_id:
            where_clause += " AND ug.subscription_id IN (SELECT id FROM subscription_products WHERE firm_id = :firm_id)"
            params["firm_id"] = firm_id
        
        performance_query = text(f"""
            SELECT 
                ca.name as zone_name,
                pr.service_type,
                COUNT(*) as total_requests,
                AVG(EXTRACT(EPOCH FROM (pr.accepted_at - pr.created_at))) as avg_response_time,
                AVG(EXTRACT(EPOCH FROM (pr.completed_at - pr.created_at))) as avg_completion_time,
                COUNT(CASE WHEN pr.status = 'completed' THEN 1 END) as completed_requests,
                COUNT(CASE WHEN rf.is_prank = true THEN 1 END) as prank_requests
            FROM panic_requests pr
            JOIN user_groups ug ON pr.group_id = ug.id
            JOIN subscription_products sp ON ug.subscription_id = sp.id
            JOIN coverage_areas ca ON ST_Contains(ca.boundary, pr.location)
            LEFT JOIN request_feedback rf ON pr.id = rf.request_id
            {where_clause}
            GROUP BY ca.name, pr.service_type
            ORDER BY ca.name, pr.service_type
        """)
        
        results = await db.execute(performance_query, params)
        performance_metrics = []
        
        for row in results:
            completion_rate = (row.completed_requests / row.total_requests * 100) if row.total_requests > 0 else 0
            prank_rate = (row.prank_requests / row.total_requests * 100) if row.total_requests > 0 else 0
            
            performance_metrics.append({
                "zone_name": row.zone_name,
                "service_type": row.service_type,
                "total_requests": row.total_requests,
                "avg_response_time_seconds": row.avg_response_time,
                "avg_completion_time_seconds": row.avg_completion_time,
                "completion_rate_percent": round(completion_rate, 2),
                "prank_rate_percent": round(prank_rate, 2)
            })
        
        return {
            "period_hours": hours,
            "firm_id": firm_id,
            "timestamp": datetime.utcnow().isoformat(),
            "performance_by_zone": performance_metrics
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching performance metrics: {str(e)}")


@router.get("/alerts")
async def get_active_alerts(db: AsyncSession = Depends(get_db)):
    """
    Get active alerts based on performance thresholds
    """
    try:
        alerts = []
        
        # Check for zones with poor response times
        slow_zones_query = text("""
            SELECT 
                ca.name as zone_name,
                pr.service_type,
                AVG(EXTRACT(EPOCH FROM (pr.accepted_at - pr.created_at))) as avg_response_time,
                COUNT(*) as request_count
            FROM panic_requests pr
            JOIN user_groups ug ON pr.group_id = ug.id
            JOIN coverage_areas ca ON ST_Contains(ca.boundary, pr.location)
            WHERE pr.created_at >= NOW() - INTERVAL '1 hour'
            AND pr.accepted_at IS NOT NULL
            GROUP BY ca.name, pr.service_type
            HAVING AVG(EXTRACT(EPOCH FROM (pr.accepted_at - pr.created_at))) > :threshold
            AND COUNT(*) >= 3
        """)
        
        slow_results = await db.execute(slow_zones_query, {
            "threshold": settings.RESPONSE_TIME_ALERT_THRESHOLD_SECONDS
        })
        
        for row in slow_results:
            alerts.append({
                "type": "slow_response_time",
                "severity": "warning",
                "zone": row.zone_name,
                "service_type": row.service_type,
                "avg_response_time": round(row.avg_response_time, 2),
                "threshold": settings.RESPONSE_TIME_ALERT_THRESHOLD_SECONDS,
                "request_count": row.request_count,
                "message": f"Zone {row.zone_name} has slow {row.service_type} response times"
            })
        
        # Check for high prank rates
        prank_rate_query = text("""
            SELECT 
                ca.name as zone_name,
                COUNT(*) as total_requests,
                COUNT(CASE WHEN rf.is_prank = true THEN 1 END) as prank_requests
            FROM panic_requests pr
            JOIN user_groups ug ON pr.group_id = ug.id
            JOIN coverage_areas ca ON ST_Contains(ca.boundary, pr.location)
            LEFT JOIN request_feedback rf ON pr.id = rf.request_id
            WHERE pr.created_at >= NOW() - INTERVAL '24 hours'
            GROUP BY ca.name
            HAVING COUNT(*) >= 10
            AND (COUNT(CASE WHEN rf.is_prank = true THEN 1 END)::float / COUNT(*) * 100) > 20
        """)
        
        prank_results = await db.execute(prank_rate_query)
        
        for row in prank_results:
            prank_rate = (row.prank_requests / row.total_requests * 100) if row.total_requests > 0 else 0
            alerts.append({
                "type": "high_prank_rate",
                "severity": "warning",
                "zone": row.zone_name,
                "prank_rate_percent": round(prank_rate, 2),
                "total_requests": row.total_requests,
                "prank_requests": row.prank_requests,
                "message": f"Zone {row.zone_name} has high prank request rate: {prank_rate:.1f}%"
            })
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "alert_count": len(alerts),
            "alerts": alerts
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching alerts: {str(e)}")


@router.post("/update-cache-metrics")
async def update_cache_metrics():
    """
    Update cache hit rate metrics (called by cache service)
    """
    try:
        # This would typically be called by the cache service
        # For now, we'll simulate some cache metrics
        
        # Update Redis cache metrics
        metrics_collector.update_cache_hit_rate("redis", 85.5)
        
        # Update application cache metrics
        metrics_collector.update_cache_hit_rate("application", 92.3)
        
        return {
            "status": "success",
            "message": "Cache metrics updated",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating cache metrics: {str(e)}")