"""
Background tasks for notifications
"""
from celery import current_task
from app.core.celery import celery_app
import structlog

logger = structlog.get_logger()


@celery_app.task(bind=True)
def send_sms_task(self, phone: str, message: str):
    """Send SMS notification in background"""
    try:
        # SMS sending logic will be implemented later
        logger.info("SMS task queued", phone=phone, task_id=self.request.id)
        return {"status": "queued", "phone": phone}
    except Exception as exc:
        logger.error("SMS task failed", error=str(exc), phone=phone)
        raise self.retry(exc=exc, countdown=60, max_retries=3)


@celery_app.task(bind=True)
def send_push_notification_task(self, user_id: str, title: str, body: str, data: dict = None):
    """Send push notification in background"""
    try:
        # Push notification logic will be implemented later
        logger.info("Push notification task queued", user_id=user_id, task_id=self.request.id)
        return {"status": "queued", "user_id": user_id}
    except Exception as exc:
        logger.error("Push notification task failed", error=str(exc), user_id=user_id)
        raise self.retry(exc=exc, countdown=60, max_retries=3)