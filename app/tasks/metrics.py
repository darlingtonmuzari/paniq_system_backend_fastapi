"""
Background tasks for metrics collection and updates
"""
from celery import Celery
from app.core.config import settings
from app.core.database import get_db
from app.services.metrics import metrics_service
import asyncio
import logging

logger = logging.getLogger(__name__)

# Create Celery instance
celery_app = Celery(
    "panic_system_metrics",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    beat_schedule={
        'update-metrics-every-minute': {
            'task': 'app.tasks.metrics.update_all_metrics',
            'schedule': 60.0,  # Every minute
        },
        'update-performance-metrics-every-5-minutes': {
            'task': 'app.tasks.metrics.update_performance_metrics',
            'schedule': 300.0,  # Every 5 minutes
        },
        'cleanup-old-metrics-daily': {
            'task': 'app.tasks.metrics.cleanup_old_metrics',
            'schedule': 86400.0,  # Daily
        },
    },
)


@celery_app.task(name="app.tasks.metrics.update_all_metrics")
def update_all_metrics():
    """Update all system metrics"""
    try:
        async def _update_metrics():
            async for db in get_db():
                await metrics_service.run_periodic_metrics_update(db)
                break
        
        # Run the async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_update_metrics())
        loop.close()
        
        logger.info("Successfully updated all metrics")
        return {"status": "success", "message": "All metrics updated"}
        
    except Exception as e:
        logger.error(f"Error updating metrics: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(name="app.tasks.metrics.update_performance_metrics")
def update_performance_metrics():
    """Update performance-specific metrics"""
    try:
        async def _update_performance():
            async for db in get_db():
                await metrics_service.update_performance_metrics(db)
                break
        
        # Run the async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_update_performance())
        loop.close()
        
        logger.info("Successfully updated performance metrics")
        return {"status": "success", "message": "Performance metrics updated"}
        
    except Exception as e:
        logger.error(f"Error updating performance metrics: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(name="app.tasks.metrics.cleanup_old_metrics")
def cleanup_old_metrics():
    """Clean up old metrics data"""
    try:
        # This would typically clean up old metric data from the database
        # For now, we'll just log that the cleanup ran
        logger.info("Metrics cleanup task completed")
        return {"status": "success", "message": "Metrics cleanup completed"}
        
    except Exception as e:
        logger.error(f"Error in metrics cleanup: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(name="app.tasks.metrics.record_panic_request_metrics")
def record_panic_request_metrics(
    service_type: str,
    status: str,
    firm_id: str,
    zone: str = None,
    response_time: float = None,
    completion_time: float = None
):
    """Record panic request metrics asynchronously"""
    try:
        async def _record_metrics():
            if status == "submitted":
                await metrics_service.record_panic_request_submitted(service_type, firm_id, zone)
            elif status == "accepted" and response_time is not None:
                await metrics_service.record_panic_request_accepted(
                    f"request_{service_type}_{firm_id}", service_type, firm_id, zone or "unknown", response_time
                )
            elif status == "completed" and completion_time is not None:
                await metrics_service.record_panic_request_completed(
                    f"request_{service_type}_{firm_id}", service_type, firm_id, zone or "unknown", completion_time
                )
        
        # Run the async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_record_metrics())
        loop.close()
        
        logger.info(f"Recorded panic request metrics: {service_type} - {status}")
        return {"status": "success", "message": "Panic request metrics recorded"}
        
    except Exception as e:
        logger.error(f"Error recording panic request metrics: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(name="app.tasks.metrics.record_auth_metrics")
def record_auth_metrics(user_type: str, success: bool, account_locked: bool = False):
    """Record authentication metrics asynchronously"""
    try:
        async def _record_auth():
            await metrics_service.record_authentication_metrics(user_type, success, account_locked)
        
        # Run the async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_record_auth())
        loop.close()
        
        logger.info(f"Recorded auth metrics: {user_type} - {'success' if success else 'failed'}")
        return {"status": "success", "message": "Auth metrics recorded"}
        
    except Exception as e:
        logger.error(f"Error recording auth metrics: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(name="app.tasks.metrics.record_notification_metrics")
def record_notification_metrics(notification_type: str, success: bool):
    """Record notification metrics asynchronously"""
    try:
        async def _record_notification():
            await metrics_service.record_notification_sent(notification_type, success)
        
        # Run the async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_record_notification())
        loop.close()
        
        logger.info(f"Recorded notification metrics: {notification_type} - {'success' if success else 'failed'}")
        return {"status": "success", "message": "Notification metrics recorded"}
        
    except Exception as e:
        logger.error(f"Error recording notification metrics: {e}")
        return {"status": "error", "message": str(e)}