"""
Business metrics tracking service
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, func
from app.core.metrics import metrics_collector
from app.core.database import get_db
from app.models.emergency import PanicRequest
from app.models.user import UserGroup
from app.models.subscription import SubscriptionProduct
import asyncio
import logging

logger = logging.getLogger(__name__)


class MetricsService:
    """Service for collecting and updating business metrics"""
    
    def __init__(self):
        self.metrics_collector = metrics_collector
    
    async def record_panic_request_submitted(
        self,
        service_type: str,
        firm_id: str,
        zone: Optional[str] = None
    ):
        """Record a panic request submission"""
        self.metrics_collector.record_panic_request(
            service_type=service_type,
            status="submitted",
            firm_id=firm_id
        )
        logger.info(f"Recorded panic request submission: {service_type} for firm {firm_id}")
    
    async def record_panic_request_accepted(
        self,
        request_id: str,
        service_type: str,
        firm_id: str,
        zone: str,
        response_time_seconds: float
    ):
        """Record a panic request acceptance with response time"""
        self.metrics_collector.record_panic_request(
            service_type=service_type,
            status="accepted",
            firm_id=firm_id
        )
        
        self.metrics_collector.record_panic_response_time(
            service_type=service_type,
            zone=zone,
            response_time=response_time_seconds
        )
        
        logger.info(f"Recorded panic request acceptance: {request_id} in {response_time_seconds}s")
    
    async def record_panic_request_completed(
        self,
        request_id: str,
        service_type: str,
        firm_id: str,
        zone: str,
        completion_time_seconds: float
    ):
        """Record a panic request completion with total time"""
        self.metrics_collector.record_panic_request(
            service_type=service_type,
            status="completed",
            firm_id=firm_id
        )
        
        self.metrics_collector.record_panic_completion_time(
            service_type=service_type,
            zone=zone,
            completion_time=completion_time_seconds
        )
        
        logger.info(f"Recorded panic request completion: {request_id} in {completion_time_seconds}s")
    
    async def record_authentication_metrics(
        self,
        user_type: str,
        success: bool,
        account_locked: bool = False
    ):
        """Record authentication attempt metrics"""
        status = "success" if success else "failed"
        self.metrics_collector.record_auth_attempt(status, user_type)
        
        if not success:
            self.metrics_collector.record_failed_login(user_type)
        
        if account_locked:
            self.metrics_collector.record_account_lockout(user_type)
        
        logger.info(f"Recorded auth attempt: {user_type} - {status}")
    
    async def record_subscription_purchase(self, product_id: str, firm_id: str):
        """Record subscription purchase"""
        self.metrics_collector.record_subscription_purchase(product_id, firm_id)
        logger.info(f"Recorded subscription purchase: {product_id} for firm {firm_id}")
    
    async def record_credit_transaction(self, transaction_type: str, firm_id: str):
        """Record credit transaction"""
        self.metrics_collector.record_credit_transaction(transaction_type, firm_id)
        logger.info(f"Recorded credit transaction: {transaction_type} for firm {firm_id}")
    
    async def record_prank_detection(self, user_id: str, firm_id: str, fine_amount: Optional[float] = None):
        """Record prank detection and fine if applicable"""
        self.metrics_collector.record_prank_flag(user_id, firm_id)
        
        if fine_amount:
            self.metrics_collector.record_user_fine(user_id, str(fine_amount))
        
        logger.info(f"Recorded prank detection: user {user_id}, firm {firm_id}")
    
    async def record_notification_sent(self, notification_type: str, success: bool):
        """Record notification delivery"""
        status = "success" if success else "failed"
        self.metrics_collector.record_notification_sent(notification_type, status)
        logger.info(f"Recorded notification: {notification_type} - {status}")
    
    async def update_websocket_connections(self, connection_type: str, count: int):
        """Update WebSocket connection count"""
        self.metrics_collector.update_websocket_connections(connection_type, count)
    
    async def update_system_health_metrics(self, db: AsyncSession):
        """Update system health metrics"""
        try:
            # Update database connection metrics (simplified)
            # In a real implementation, you'd get actual connection pool stats
            self.metrics_collector.update_database_connections(20)  # Example value
            
            # Update Redis connection metrics (simplified)
            self.metrics_collector.update_redis_connections(10)  # Example value
            
            logger.debug("Updated system health metrics")
            
        except Exception as e:
            logger.error(f"Error updating system health metrics: {e}")
    
    async def update_performance_metrics(self, db: AsyncSession):
        """Update zone and firm performance metrics"""
        try:
            # Calculate zone performance metrics
            zone_performance_query = text("""
                SELECT 
                    ca.id as zone_id,
                    ca.name as zone_name,
                    pr.service_type,
                    AVG(EXTRACT(EPOCH FROM (pr.accepted_at - pr.created_at))) as avg_response_time
                FROM panic_requests pr
                JOIN user_groups ug ON pr.group_id = ug.id
                JOIN coverage_areas ca ON ST_Contains(ca.boundary, pr.location)
                WHERE pr.created_at >= NOW() - INTERVAL '1 hour'
                AND pr.accepted_at IS NOT NULL
                GROUP BY ca.id, ca.name, pr.service_type
            """)
            
            zone_results = await db.execute(zone_performance_query)
            
            for row in zone_results:
                self.metrics_collector.update_zone_performance(
                    zone_id=str(row.zone_id),
                    service_type=row.service_type,
                    avg_response_time=row.avg_response_time or 0
                )
            
            # Calculate firm performance metrics
            firm_performance_query = text("""
                SELECT 
                    sp.firm_id,
                    pr.service_type,
                    AVG(EXTRACT(EPOCH FROM (pr.accepted_at - pr.created_at))) as avg_response_time
                FROM panic_requests pr
                JOIN user_groups ug ON pr.group_id = ug.id
                JOIN subscription_products sp ON ug.subscription_id = sp.id
                WHERE pr.created_at >= NOW() - INTERVAL '1 hour'
                AND pr.accepted_at IS NOT NULL
                GROUP BY sp.firm_id, pr.service_type
            """)
            
            firm_results = await db.execute(firm_performance_query)
            
            for row in firm_results:
                self.metrics_collector.update_firm_performance(
                    firm_id=str(row.firm_id),
                    service_type=row.service_type,
                    avg_response_time=row.avg_response_time or 0
                )
            
            logger.debug("Updated performance metrics")
            
        except Exception as e:
            logger.error(f"Error updating performance metrics: {e}")
    
    async def update_subscription_metrics(self, db: AsyncSession):
        """Update active subscription counts per firm"""
        try:
            subscription_query = text("""
                SELECT 
                    sp.firm_id,
                    COUNT(*) as active_count
                FROM user_groups ug
                JOIN subscription_products sp ON ug.subscription_id = sp.id
                WHERE ug.subscription_expires_at > NOW()
                GROUP BY sp.firm_id
            """)
            
            results = await db.execute(subscription_query)
            
            for row in results:
                self.metrics_collector.update_active_subscriptions(
                    firm_id=str(row.firm_id),
                    count=row.active_count
                )
            
            logger.debug("Updated subscription metrics")
            
        except Exception as e:
            logger.error(f"Error updating subscription metrics: {e}")
    
    async def run_periodic_metrics_update(self, db: AsyncSession):
        """Run periodic update of all metrics"""
        try:
            await asyncio.gather(
                self.update_system_health_metrics(db),
                self.update_performance_metrics(db),
                self.update_subscription_metrics(db)
            )
            logger.info("Completed periodic metrics update")
            
        except Exception as e:
            logger.error(f"Error in periodic metrics update: {e}")


# Global metrics service instance
metrics_service = MetricsService()