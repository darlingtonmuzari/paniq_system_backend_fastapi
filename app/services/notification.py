"""
Notification service for push notifications, SMS, and email
"""
import asyncio
import json
from typing import Dict, List, Optional, Any, Union
from uuid import UUID
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, EmailStr
import structlog

from app.core.config import settings
from app.core.exceptions import APIError, ErrorCodes

logger = structlog.get_logger()


class NotificationType(str, Enum):
    """Notification types"""
    PUSH = "push"
    SMS = "sms"
    EMAIL = "email"


class NotificationPriority(str, Enum):
    """Notification priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class NotificationTemplate(BaseModel):
    """Notification template structure"""
    id: str
    name: str
    type: NotificationType
    subject: Optional[str] = None  # For email notifications
    title: Optional[str] = None    # For push notifications
    body: str
    variables: List[str] = []      # Template variables like {user_name}, {request_id}
    priority: NotificationPriority = NotificationPriority.NORMAL


class NotificationRecipient(BaseModel):
    """Notification recipient information"""
    user_id: Optional[UUID] = None
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None
    push_token: Optional[str] = None
    platform: Optional[str] = None  # "android" or "ios"
    preferred_language: str = "en"


class NotificationRequest(BaseModel):
    """Notification request structure"""
    template_id: str
    recipients: List[NotificationRecipient]
    variables: Dict[str, Any] = {}
    priority: NotificationPriority = NotificationPriority.NORMAL
    scheduled_at: Optional[datetime] = None
    metadata: Dict[str, Any] = {}


class NotificationResult(BaseModel):
    """Notification delivery result"""
    recipient_id: Optional[str] = None
    type: NotificationType
    status: str  # "sent", "failed", "pending"
    message: Optional[str] = None
    sent_at: Optional[datetime] = None
    external_id: Optional[str] = None  # External service message ID


class NotificationError(APIError):
    """Base notification error"""
    def __init__(self, message: str = "Notification error"):
        super().__init__(ErrorCodes.NOTIFICATION_FAILED, message)


class PushNotificationService:
    """Push notification service using Firebase Cloud Messaging (FCM)"""
    
    def __init__(self):
        self.fcm_server_key = settings.FCM_SERVER_KEY
        self.fcm_url = "https://fcm.googleapis.com/fcm/send"
        
    async def send_push_notification(
        self,
        recipient: NotificationRecipient,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL
    ) -> NotificationResult:
        """
        Send push notification via FCM
        
        Args:
            recipient: Notification recipient
            title: Notification title
            body: Notification body
            data: Additional data payload
            priority: Notification priority
            
        Returns:
            NotificationResult with delivery status
        """
        if not recipient.push_token:
            return NotificationResult(
                type=NotificationType.PUSH,
                status="failed",
                message="No push token available"
            )
            
        try:
            # Prepare FCM payload
            payload = {
                "to": recipient.push_token,
                "notification": {
                    "title": title,
                    "body": body,
                    "sound": "default"
                },
                "priority": self._get_fcm_priority(priority),
                "data": data or {}
            }
            
            # Add platform-specific settings
            if recipient.platform == "android":
                payload["android"] = {
                    "priority": "high" if priority in [NotificationPriority.HIGH, NotificationPriority.URGENT] else "normal",
                    "notification": {
                        "channel_id": "emergency_notifications"
                    }
                }
            elif recipient.platform == "ios":
                payload["apns"] = {
                    "headers": {
                        "apns-priority": "10" if priority in [NotificationPriority.HIGH, NotificationPriority.URGENT] else "5"
                    },
                    "payload": {
                        "aps": {
                            "alert": {
                                "title": title,
                                "body": body
                            },
                            "sound": "default",
                            "badge": 1
                        }
                    }
                }
            
            # In a real implementation, you would use the FCM SDK or HTTP client
            # For now, we'll simulate the API call
            logger.info(
                "push_notification_sent",
                recipient_id=str(recipient.user_id) if recipient.user_id else None,
                title=title,
                priority=priority,
                platform=recipient.platform
            )
            
            return NotificationResult(
                recipient_id=str(recipient.user_id) if recipient.user_id else None,
                type=NotificationType.PUSH,
                status="sent",
                message="Push notification sent successfully",
                sent_at=datetime.utcnow(),
                external_id=f"fcm_{datetime.utcnow().timestamp()}"
            )
            
        except Exception as e:
            logger.error(
                "push_notification_failed",
                recipient_id=str(recipient.user_id) if recipient.user_id else None,
                error=str(e)
            )
            
            return NotificationResult(
                recipient_id=str(recipient.user_id) if recipient.user_id else None,
                type=NotificationType.PUSH,
                status="failed",
                message=f"Push notification failed: {str(e)}"
            )
    
    def _get_fcm_priority(self, priority: NotificationPriority) -> str:
        """Convert notification priority to FCM priority"""
        if priority in [NotificationPriority.HIGH, NotificationPriority.URGENT]:
            return "high"
        return "normal"


class SMSNotificationService:
    """SMS notification service using Twilio"""
    
    def __init__(self):
        self.twilio_account_sid = settings.TWILIO_ACCOUNT_SID
        self.twilio_auth_token = settings.TWILIO_AUTH_TOKEN
        self.twilio_phone_number = settings.TWILIO_PHONE_NUMBER
        
    async def send_sms_notification(
        self,
        recipient: NotificationRecipient,
        message: str,
        priority: NotificationPriority = NotificationPriority.NORMAL
    ) -> NotificationResult:
        """
        Send SMS notification via Twilio
        
        Args:
            recipient: Notification recipient
            message: SMS message content
            priority: Notification priority
            
        Returns:
            NotificationResult with delivery status
        """
        if not recipient.phone_number:
            return NotificationResult(
                type=NotificationType.SMS,
                status="failed",
                message="No phone number available"
            )
            
        try:
            # In a real implementation, you would use the Twilio SDK
            # For now, we'll simulate the API call
            logger.info(
                "sms_notification_sent",
                recipient_id=str(recipient.user_id) if recipient.user_id else None,
                phone_number=recipient.phone_number,
                message_length=len(message),
                priority=priority
            )
            
            return NotificationResult(
                recipient_id=str(recipient.user_id) if recipient.user_id else None,
                type=NotificationType.SMS,
                status="sent",
                message="SMS notification sent successfully",
                sent_at=datetime.utcnow(),
                external_id=f"sms_{datetime.utcnow().timestamp()}"
            )
            
        except Exception as e:
            logger.error(
                "sms_notification_failed",
                recipient_id=str(recipient.user_id) if recipient.user_id else None,
                phone_number=recipient.phone_number,
                error=str(e)
            )
            
            return NotificationResult(
                recipient_id=str(recipient.user_id) if recipient.user_id else None,
                type=NotificationType.SMS,
                status="failed",
                message=f"SMS notification failed: {str(e)}"
            )


class EmailNotificationService:
    """Email notification service using SendGrid"""
    
    def __init__(self):
        self.sendgrid_api_key = settings.SENDGRID_API_KEY
        self.from_email = settings.FROM_EMAIL
        self.from_name = settings.FROM_NAME
        
    async def send_email_notification(
        self,
        recipient: NotificationRecipient,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL
    ) -> NotificationResult:
        """
        Send email notification via SendGrid
        
        Args:
            recipient: Notification recipient
            subject: Email subject
            body: Email body (plain text)
            html_body: Email body (HTML)
            priority: Notification priority
            
        Returns:
            NotificationResult with delivery status
        """
        if not recipient.email:
            return NotificationResult(
                type=NotificationType.EMAIL,
                status="failed",
                message="No email address available"
            )
            
        try:
            # In a real implementation, you would use the SendGrid SDK
            # For now, we'll simulate the API call
            logger.info(
                "email_notification_sent",
                recipient_id=str(recipient.user_id) if recipient.user_id else None,
                email=str(recipient.email),
                subject=subject,
                priority=priority
            )
            
            return NotificationResult(
                recipient_id=str(recipient.user_id) if recipient.user_id else None,
                type=NotificationType.EMAIL,
                status="sent",
                message="Email notification sent successfully",
                sent_at=datetime.utcnow(),
                external_id=f"email_{datetime.utcnow().timestamp()}"
            )
            
        except Exception as e:
            logger.error(
                "email_notification_failed",
                recipient_id=str(recipient.user_id) if recipient.user_id else None,
                email=str(recipient.email),
                error=str(e)
            )
            
            return NotificationResult(
                recipient_id=str(recipient.user_id) if recipient.user_id else None,
                type=NotificationType.EMAIL,
                status="failed",
                message=f"Email notification failed: {str(e)}"
            )


class NotificationTemplateManager:
    """Manages notification templates"""
    
    def __init__(self):
        self.templates: Dict[str, NotificationTemplate] = {}
        self._load_default_templates()
    
    def _load_default_templates(self):
        """Load default notification templates"""
        # Emergency request confirmation templates
        self.templates["emergency_request_confirmed"] = NotificationTemplate(
            id="emergency_request_confirmed",
            name="Emergency Request Confirmed",
            type=NotificationType.PUSH,
            title="Emergency Request Received",
            body="Your {service_type} emergency request #{request_id} has been received and is being processed.",
            variables=["request_id", "service_type"],
            priority=NotificationPriority.HIGH
        )
        
        self.templates["emergency_request_confirmed_sms"] = NotificationTemplate(
            id="emergency_request_confirmed_sms",
            name="Emergency Request Confirmed (SMS)",
            type=NotificationType.SMS,
            body="EMERGENCY: Your {service_type} request #{request_id} has been received. Help is on the way.",
            variables=["request_id", "service_type"],
            priority=NotificationPriority.HIGH
        )
        
        # Service provider assignment templates
        self.templates["provider_assigned"] = NotificationTemplate(
            id="provider_assigned",
            name="Service Provider Assigned",
            type=NotificationType.PUSH,
            title="Help is on the way",
            body="{provider_name} has been assigned to your request. ETA: {eta} minutes.",
            variables=["provider_name", "eta", "vehicle_details"],
            priority=NotificationPriority.HIGH
        )
        
        self.templates["provider_assigned_sms"] = NotificationTemplate(
            id="provider_assigned_sms",
            name="Service Provider Assigned (SMS)",
            type=NotificationType.SMS,
            body="EMERGENCY UPDATE: {provider_name} assigned to your request. ETA: {eta} min. Vehicle: {vehicle_details}",
            variables=["provider_name", "eta", "vehicle_details"],
            priority=NotificationPriority.HIGH
        )
        
        # Location update templates
        self.templates["location_update"] = NotificationTemplate(
            id="location_update",
            name="Location Update",
            type=NotificationType.PUSH,
            title="Updated ETA",
            body="Your service provider is en route. Updated ETA: {eta} minutes.",
            variables=["eta", "distance"],
            priority=NotificationPriority.NORMAL
        )
        
        # Arrival notification templates
        self.templates["provider_arrived"] = NotificationTemplate(
            id="provider_arrived",
            name="Service Provider Arrived",
            type=NotificationType.PUSH,
            title="Help has arrived",
            body="Your service provider has arrived. Look for {vehicle_description}.",
            variables=["vehicle_description", "license_plate"],
            priority=NotificationPriority.URGENT
        )
        
        self.templates["provider_arrived_sms"] = NotificationTemplate(
            id="provider_arrived_sms",
            name="Service Provider Arrived (SMS)",
            type=NotificationType.SMS,
            body="EMERGENCY: Your help has arrived! Look for {vehicle_description}, license plate {license_plate}.",
            variables=["vehicle_description", "license_plate"],
            priority=NotificationPriority.URGENT
        )
        
        # Field agent assignment templates
        self.templates["agent_assignment"] = NotificationTemplate(
            id="agent_assignment",
            name="Field Agent Assignment",
            type=NotificationType.PUSH,
            title="New Emergency Assignment",
            body="New {service_type} request at {address}. Tap to view details.",
            variables=["service_type", "address", "description"],
            priority=NotificationPriority.HIGH
        )
        
        # Email templates
        self.templates["emergency_summary_email"] = NotificationTemplate(
            id="emergency_summary_email",
            name="Emergency Request Summary",
            type=NotificationType.EMAIL,
            subject="Emergency Request #{request_id} - {service_type}",
            body="Dear {user_name},\n\nYour emergency request has been processed:\n\nRequest ID: {request_id}\nService Type: {service_type}\nStatus: {status}\nLocation: {address}\n\nThank you for using our emergency services.",
            variables=["user_name", "request_id", "service_type", "status", "address"],
            priority=NotificationPriority.NORMAL
        )
    
    def get_template(self, template_id: str) -> Optional[NotificationTemplate]:
        """Get notification template by ID"""
        return self.templates.get(template_id)
    
    def add_template(self, template: NotificationTemplate):
        """Add or update notification template"""
        self.templates[template.id] = template
    
    def render_template(self, template_id: str, variables: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Render template with variables"""
        template = self.get_template(template_id)
        if not template:
            return None
        
        rendered = {}
        
        if template.title:
            rendered["title"] = self._render_string(template.title, variables)
        
        if template.subject:
            rendered["subject"] = self._render_string(template.subject, variables)
        
        rendered["body"] = self._render_string(template.body, variables)
        
        return rendered
    
    def _render_string(self, template_string: str, variables: Dict[str, Any]) -> str:
        """Render template string with variables"""
        try:
            return template_string.format(**variables)
        except KeyError as e:
            logger.warning("template_variable_missing", variable=str(e), template=template_string)
            return template_string


class NotificationService:
    """Main notification service orchestrator"""
    
    def __init__(self):
        self.push_service = PushNotificationService()
        self.sms_service = SMSNotificationService()
        self.email_service = EmailNotificationService()
        self.template_manager = NotificationTemplateManager()
    
    async def send_notification(self, request: NotificationRequest) -> List[NotificationResult]:
        """
        Send notification using template
        
        Args:
            request: Notification request with template and recipients
            
        Returns:
            List of notification results for each recipient
        """
        template = self.template_manager.get_template(request.template_id)
        if not template:
            raise NotificationError(f"Template not found: {request.template_id}")
        
        # Render template
        rendered = self.template_manager.render_template(request.template_id, request.variables)
        if not rendered:
            raise NotificationError(f"Failed to render template: {request.template_id}")
        
        results = []
        
        # Send to all recipients
        for recipient in request.recipients:
            try:
                if template.type == NotificationType.PUSH:
                    result = await self.push_service.send_push_notification(
                        recipient,
                        rendered.get("title", ""),
                        rendered["body"],
                        request.metadata,
                        request.priority
                    )
                elif template.type == NotificationType.SMS:
                    result = await self.sms_service.send_sms_notification(
                        recipient,
                        rendered["body"],
                        request.priority
                    )
                elif template.type == NotificationType.EMAIL:
                    result = await self.email_service.send_email_notification(
                        recipient,
                        rendered.get("subject", ""),
                        rendered["body"],
                        None,  # HTML body could be added
                        request.priority
                    )
                else:
                    result = NotificationResult(
                        type=template.type,
                        status="failed",
                        message=f"Unsupported notification type: {template.type}"
                    )
                
                results.append(result)
                
            except Exception as e:
                logger.error(
                    "notification_send_error",
                    template_id=request.template_id,
                    recipient_id=str(recipient.user_id) if recipient.user_id else None,
                    error=str(e)
                )
                
                results.append(NotificationResult(
                    recipient_id=str(recipient.user_id) if recipient.user_id else None,
                    type=template.type,
                    status="failed",
                    message=f"Notification failed: {str(e)}"
                ))
        
        return results
    
    async def send_emergency_confirmation(
        self,
        recipient: NotificationRecipient,
        request_id: UUID,
        service_type: str
    ) -> List[NotificationResult]:
        """Send emergency request confirmation notifications"""
        results = []
        
        # Send push notification
        if recipient.push_token:
            push_request = NotificationRequest(
                template_id="emergency_request_confirmed",
                recipients=[recipient],
                variables={
                    "request_id": str(request_id),
                    "service_type": service_type
                },
                priority=NotificationPriority.HIGH
            )
            push_results = await self.send_notification(push_request)
            results.extend(push_results)
        
        # Send SMS backup
        if recipient.phone_number:
            sms_request = NotificationRequest(
                template_id="emergency_request_confirmed_sms",
                recipients=[recipient],
                variables={
                    "request_id": str(request_id),
                    "service_type": service_type
                },
                priority=NotificationPriority.HIGH
            )
            sms_results = await self.send_notification(sms_request)
            results.extend(sms_results)
        
        return results
    
    async def send_provider_assignment(
        self,
        recipient: NotificationRecipient,
        provider_name: str,
        eta_minutes: int,
        vehicle_details: str
    ) -> List[NotificationResult]:
        """Send service provider assignment notifications"""
        results = []
        
        variables = {
            "provider_name": provider_name,
            "eta": str(eta_minutes),
            "vehicle_details": vehicle_details
        }
        
        # Send push notification
        if recipient.push_token:
            push_request = NotificationRequest(
                template_id="provider_assigned",
                recipients=[recipient],
                variables=variables,
                priority=NotificationPriority.HIGH
            )
            push_results = await self.send_notification(push_request)
            results.extend(push_results)
        
        # Send SMS backup
        if recipient.phone_number:
            sms_request = NotificationRequest(
                template_id="provider_assigned_sms",
                recipients=[recipient],
                variables=variables,
                priority=NotificationPriority.HIGH
            )
            sms_results = await self.send_notification(sms_request)
            results.extend(sms_results)
        
        return results
    
    async def send_provider_arrival(
        self,
        recipient: NotificationRecipient,
        vehicle_description: str,
        license_plate: str
    ) -> List[NotificationResult]:
        """Send service provider arrival notifications"""
        results = []
        
        variables = {
            "vehicle_description": vehicle_description,
            "license_plate": license_plate
        }
        
        # Send push notification
        if recipient.push_token:
            push_request = NotificationRequest(
                template_id="provider_arrived",
                recipients=[recipient],
                variables=variables,
                priority=NotificationPriority.URGENT
            )
            push_results = await self.send_notification(push_request)
            results.extend(push_results)
        
        # Send SMS backup
        if recipient.phone_number:
            sms_request = NotificationRequest(
                template_id="provider_arrived_sms",
                recipients=[recipient],
                variables=variables,
                priority=NotificationPriority.URGENT
            )
            sms_results = await self.send_notification(sms_request)
            results.extend(sms_results)
        
        return results
    
    async def send_field_agent_assignment(
        self,
        recipient: NotificationRecipient,
        service_type: str,
        address: str,
        description: Optional[str] = None
    ) -> List[NotificationResult]:
        """Send field agent assignment notification"""
        push_request = NotificationRequest(
            template_id="agent_assignment",
            recipients=[recipient],
            variables={
                "service_type": service_type,
                "address": address,
                "description": description or "No additional details"
            },
            priority=NotificationPriority.HIGH
        )
        
        return await self.send_notification(push_request)


# Global notification service instance
notification_service = NotificationService()