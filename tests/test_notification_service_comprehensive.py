"""
Comprehensive unit tests for notification service
"""
import pytest
from datetime import datetime
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.notification import (
    NotificationService,
    PushNotificationService,
    SMSNotificationService,
    EmailNotificationService,
    NotificationTemplateManager,
    NotificationRecipient,
    NotificationRequest,
    NotificationResult,
    NotificationTemplate,
    NotificationType,
    NotificationPriority,
    NotificationError
)


class TestNotificationRecipient:
    """Test notification recipient model"""
    
    def test_create_recipient_with_all_fields(self):
        """Test creating recipient with all fields"""
        recipient = NotificationRecipient(
            user_id=uuid4(),
            phone_number="+1234567890",
            email="test@example.com",
            push_token="fcm_token_123",
            platform="android",
            preferred_language="en"
        )
        
        assert recipient.user_id is not None
        assert recipient.phone_number == "+1234567890"
        assert recipient.email == "test@example.com"
        assert recipient.push_token == "fcm_token_123"
        assert recipient.platform == "android"
        assert recipient.preferred_language == "en"
    
    def test_create_recipient_minimal(self):
        """Test creating recipient with minimal fields"""
        recipient = NotificationRecipient(
            phone_number="+1234567890"
        )
        
        assert recipient.phone_number == "+1234567890"
        assert recipient.user_id is None
        assert recipient.email is None
        assert recipient.push_token is None
        assert recipient.preferred_language == "en"


class TestNotificationTemplate:
    """Test notification template model"""
    
    def test_create_push_template(self):
        """Test creating push notification template"""
        template = NotificationTemplate(
            id="test_push",
            name="Test Push",
            type=NotificationType.PUSH,
            title="Test Title",
            body="Test body with {variable}",
            variables=["variable"],
            priority=NotificationPriority.HIGH
        )
        
        assert template.id == "test_push"
        assert template.type == NotificationType.PUSH
        assert template.title == "Test Title"
        assert template.body == "Test body with {variable}"
        assert "variable" in template.variables
        assert template.priority == NotificationPriority.HIGH
    
    def test_create_email_template(self):
        """Test creating email notification template"""
        template = NotificationTemplate(
            id="test_email",
            name="Test Email",
            type=NotificationType.EMAIL,
            subject="Test Subject {subject_var}",
            body="Test email body with {body_var}",
            variables=["subject_var", "body_var"]
        )
        
        assert template.type == NotificationType.EMAIL
        assert template.subject == "Test Subject {subject_var}"
        assert template.body == "Test email body with {body_var}"
        assert len(template.variables) == 2


class TestPushNotificationService:
    """Test push notification service"""
    
    @pytest.fixture
    def service(self):
        return PushNotificationService()
    
    @pytest.fixture
    def recipient_with_push_token(self):
        return NotificationRecipient(
            user_id=uuid4(),
            push_token="fcm_token_123",
            platform="android"
        )
    
    @pytest.fixture
    def recipient_without_push_token(self):
        return NotificationRecipient(
            user_id=uuid4(),
            phone_number="+1234567890"
        )
    
    @pytest.mark.asyncio
    async def test_send_push_notification_success(self, service, recipient_with_push_token):
        """Test successful push notification sending"""
        result = await service.send_push_notification(
            recipient_with_push_token,
            "Test Title",
            "Test Body",
            {"key": "value"},
            NotificationPriority.HIGH
        )
        
        assert isinstance(result, NotificationResult)
        assert result.type == NotificationType.PUSH
        assert result.status == "sent"
        assert result.message == "Push notification sent successfully"
        assert result.sent_at is not None
        assert result.external_id is not None
        assert result.external_id.startswith("fcm_")
    
    @pytest.mark.asyncio
    async def test_send_push_notification_no_token(self, service, recipient_without_push_token):
        """Test push notification with no push token"""
        result = await service.send_push_notification(
            recipient_without_push_token,
            "Test Title",
            "Test Body"
        )
        
        assert result.type == NotificationType.PUSH
        assert result.status == "failed"
        assert result.message == "No push token available"
        assert result.sent_at is None
    
    @pytest.mark.asyncio
    async def test_send_push_notification_android_platform(self, service, recipient_with_push_token):
        """Test push notification with Android-specific settings"""
        recipient_with_push_token.platform = "android"
        
        result = await service.send_push_notification(
            recipient_with_push_token,
            "Emergency Alert",
            "Test emergency message",
            priority=NotificationPriority.URGENT
        )
        
        assert result.status == "sent"
        # In a real implementation, we would verify Android-specific payload
    
    @pytest.mark.asyncio
    async def test_send_push_notification_ios_platform(self, service, recipient_with_push_token):
        """Test push notification with iOS-specific settings"""
        recipient_with_push_token.platform = "ios"
        
        result = await service.send_push_notification(
            recipient_with_push_token,
            "Emergency Alert",
            "Test emergency message",
            priority=NotificationPriority.URGENT
        )
        
        assert result.status == "sent"
        # In a real implementation, we would verify iOS-specific payload
    
    def test_get_fcm_priority_high(self, service):
        """Test FCM priority mapping for high priority"""
        priority = service._get_fcm_priority(NotificationPriority.HIGH)
        assert priority == "high"
        
        priority = service._get_fcm_priority(NotificationPriority.URGENT)
        assert priority == "high"
    
    def test_get_fcm_priority_normal(self, service):
        """Test FCM priority mapping for normal priority"""
        priority = service._get_fcm_priority(NotificationPriority.NORMAL)
        assert priority == "normal"
        
        priority = service._get_fcm_priority(NotificationPriority.LOW)
        assert priority == "normal"


class TestSMSNotificationService:
    """Test SMS notification service"""
    
    @pytest.fixture
    def service(self):
        return SMSNotificationService()
    
    @pytest.fixture
    def recipient_with_phone(self):
        return NotificationRecipient(
            user_id=uuid4(),
            phone_number="+1234567890"
        )
    
    @pytest.fixture
    def recipient_without_phone(self):
        return NotificationRecipient(
            user_id=uuid4(),
            email="test@example.com"
        )
    
    @pytest.mark.asyncio
    async def test_send_sms_notification_success(self, service, recipient_with_phone):
        """Test successful SMS notification sending"""
        result = await service.send_sms_notification(
            recipient_with_phone,
            "Test SMS message",
            NotificationPriority.HIGH
        )
        
        assert isinstance(result, NotificationResult)
        assert result.type == NotificationType.SMS
        assert result.status == "sent"
        assert result.message == "SMS notification sent successfully"
        assert result.sent_at is not None
        assert result.external_id is not None
        assert result.external_id.startswith("sms_")
    
    @pytest.mark.asyncio
    async def test_send_sms_notification_no_phone(self, service, recipient_without_phone):
        """Test SMS notification with no phone number"""
        result = await service.send_sms_notification(
            recipient_without_phone,
            "Test SMS message"
        )
        
        assert result.type == NotificationType.SMS
        assert result.status == "failed"
        assert result.message == "No phone number available"
        assert result.sent_at is None
    
    @pytest.mark.asyncio
    async def test_send_sms_notification_long_message(self, service, recipient_with_phone):
        """Test SMS notification with long message"""
        long_message = "This is a very long SMS message " * 10  # > 160 characters
        
        result = await service.send_sms_notification(
            recipient_with_phone,
            long_message,
            NotificationPriority.NORMAL
        )
        
        assert result.status == "sent"
        # In a real implementation, we might split long messages or handle differently


class TestEmailNotificationService:
    """Test email notification service"""
    
    @pytest.fixture
    def service(self):
        return EmailNotificationService()
    
    @pytest.fixture
    def recipient_with_email(self):
        return NotificationRecipient(
            user_id=uuid4(),
            email="test@example.com"
        )
    
    @pytest.fixture
    def recipient_without_email(self):
        return NotificationRecipient(
            user_id=uuid4(),
            phone_number="+1234567890"
        )
    
    @pytest.mark.asyncio
    async def test_send_email_notification_success(self, service, recipient_with_email):
        """Test successful email notification sending"""
        result = await service.send_email_notification(
            recipient_with_email,
            "Test Subject",
            "Test email body",
            "<p>Test HTML body</p>",
            NotificationPriority.NORMAL
        )
        
        assert isinstance(result, NotificationResult)
        assert result.type == NotificationType.EMAIL
        assert result.status == "sent"
        assert result.message == "Email notification sent successfully"
        assert result.sent_at is not None
        assert result.external_id is not None
        assert result.external_id.startswith("email_")
    
    @pytest.mark.asyncio
    async def test_send_email_notification_no_email(self, service, recipient_without_email):
        """Test email notification with no email address"""
        result = await service.send_email_notification(
            recipient_without_email,
            "Test Subject",
            "Test email body"
        )
        
        assert result.type == NotificationType.EMAIL
        assert result.status == "failed"
        assert result.message == "No email address available"
        assert result.sent_at is None
    
    @pytest.mark.asyncio
    async def test_send_email_notification_plain_text_only(self, service, recipient_with_email):
        """Test email notification with plain text only"""
        result = await service.send_email_notification(
            recipient_with_email,
            "Plain Text Subject",
            "Plain text email body",
            priority=NotificationPriority.LOW
        )
        
        assert result.status == "sent"


class TestNotificationTemplateManager:
    """Test notification template manager"""
    
    @pytest.fixture
    def manager(self):
        return NotificationTemplateManager()
    
    def test_load_default_templates(self, manager):
        """Test that default templates are loaded"""
        assert len(manager.templates) > 0
        assert "emergency_request_confirmed" in manager.templates
        assert "emergency_request_confirmed_sms" in manager.templates
        assert "provider_assigned" in manager.templates
        assert "provider_arrived" in manager.templates
        assert "agent_assignment" in manager.templates
    
    def test_get_existing_template(self, manager):
        """Test getting existing template"""
        template = manager.get_template("emergency_request_confirmed")
        
        assert template is not None
        assert template.id == "emergency_request_confirmed"
        assert template.type == NotificationType.PUSH
        assert template.priority == NotificationPriority.HIGH
    
    def test_get_nonexistent_template(self, manager):
        """Test getting non-existent template"""
        template = manager.get_template("nonexistent_template")
        assert template is None
    
    def test_add_custom_template(self, manager):
        """Test adding custom template"""
        custom_template = NotificationTemplate(
            id="custom_test",
            name="Custom Test",
            type=NotificationType.SMS,
            body="Custom message with {variable}",
            variables=["variable"]
        )
        
        manager.add_template(custom_template)
        
        retrieved = manager.get_template("custom_test")
        assert retrieved is not None
        assert retrieved.id == "custom_test"
        assert retrieved.body == "Custom message with {variable}"
    
    def test_render_template_success(self, manager):
        """Test successful template rendering"""
        variables = {
            "request_id": "12345",
            "service_type": "security"
        }
        
        rendered = manager.render_template("emergency_request_confirmed", variables)
        
        assert rendered is not None
        assert "title" in rendered
        assert "body" in rendered
        assert "12345" in rendered["body"]
        assert "security" in rendered["body"]
    
    def test_render_template_missing_variable(self, manager):
        """Test template rendering with missing variable"""
        variables = {
            "request_id": "12345"
            # Missing service_type
        }
        
        rendered = manager.render_template("emergency_request_confirmed", variables)
        
        assert rendered is not None
        # Should still return rendered content, even with missing variables
        assert "body" in rendered
    
    def test_render_template_nonexistent(self, manager):
        """Test rendering non-existent template"""
        rendered = manager.render_template("nonexistent", {"var": "value"})
        assert rendered is None
    
    def test_render_string_with_variables(self, manager):
        """Test string rendering with variables"""
        template_string = "Hello {name}, your order {order_id} is ready"
        variables = {"name": "John", "order_id": "12345"}
        
        result = manager._render_string(template_string, variables)
        
        assert result == "Hello John, your order 12345 is ready"
    
    def test_render_string_missing_variable(self, manager):
        """Test string rendering with missing variable"""
        template_string = "Hello {name}, your order {order_id} is ready"
        variables = {"name": "John"}  # Missing order_id
        
        result = manager._render_string(template_string, variables)
        
        # Should return original string when variable is missing
        assert result == template_string


class TestNotificationService:
    """Test main notification service"""
    
    @pytest.fixture
    def service(self):
        return NotificationService()
    
    @pytest.fixture
    def recipient(self):
        return NotificationRecipient(
            user_id=uuid4(),
            phone_number="+1234567890",
            email="test@example.com",
            push_token="fcm_token_123",
            platform="android"
        )
    
    @pytest.mark.asyncio
    async def test_send_notification_push_success(self, service, recipient):
        """Test sending push notification via main service"""
        request = NotificationRequest(
            template_id="emergency_request_confirmed",
            recipients=[recipient],
            variables={
                "request_id": "12345",
                "service_type": "security"
            },
            priority=NotificationPriority.HIGH
        )
        
        with patch.object(service.push_service, 'send_push_notification') as mock_push:
            mock_push.return_value = NotificationResult(
                type=NotificationType.PUSH,
                status="sent",
                message="Success"
            )
            
            results = await service.send_notification(request)
            
            assert len(results) == 1
            assert results[0].status == "sent"
            mock_push.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_notification_sms_success(self, service, recipient):
        """Test sending SMS notification via main service"""
        request = NotificationRequest(
            template_id="emergency_request_confirmed_sms",
            recipients=[recipient],
            variables={
                "request_id": "12345",
                "service_type": "security"
            },
            priority=NotificationPriority.HIGH
        )
        
        with patch.object(service.sms_service, 'send_sms_notification') as mock_sms:
            mock_sms.return_value = NotificationResult(
                type=NotificationType.SMS,
                status="sent",
                message="Success"
            )
            
            results = await service.send_notification(request)
            
            assert len(results) == 1
            assert results[0].status == "sent"
            mock_sms.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_notification_email_success(self, service, recipient):
        """Test sending email notification via main service"""
        request = NotificationRequest(
            template_id="emergency_summary_email",
            recipients=[recipient],
            variables={
                "user_name": "John Doe",
                "request_id": "12345",
                "service_type": "security",
                "status": "completed",
                "address": "123 Main St"
            }
        )
        
        with patch.object(service.email_service, 'send_email_notification') as mock_email:
            mock_email.return_value = NotificationResult(
                type=NotificationType.EMAIL,
                status="sent",
                message="Success"
            )
            
            results = await service.send_notification(request)
            
            assert len(results) == 1
            assert results[0].status == "sent"
            mock_email.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_notification_template_not_found(self, service, recipient):
        """Test sending notification with non-existent template"""
        request = NotificationRequest(
            template_id="nonexistent_template",
            recipients=[recipient],
            variables={}
        )
        
        with pytest.raises(NotificationError, match="Template not found"):
            await service.send_notification(request)
    
    @pytest.mark.asyncio
    async def test_send_notification_multiple_recipients(self, service):
        """Test sending notification to multiple recipients"""
        recipients = [
            NotificationRecipient(user_id=uuid4(), push_token="token1", platform="android"),
            NotificationRecipient(user_id=uuid4(), push_token="token2", platform="ios")
        ]
        
        request = NotificationRequest(
            template_id="emergency_request_confirmed",
            recipients=recipients,
            variables={
                "request_id": "12345",
                "service_type": "security"
            }
        )
        
        with patch.object(service.push_service, 'send_push_notification') as mock_push:
            mock_push.return_value = NotificationResult(
                type=NotificationType.PUSH,
                status="sent",
                message="Success"
            )
            
            results = await service.send_notification(request)
            
            assert len(results) == 2
            assert all(result.status == "sent" for result in results)
            assert mock_push.call_count == 2
    
    @pytest.mark.asyncio
    async def test_send_emergency_confirmation(self, service, recipient):
        """Test sending emergency confirmation notifications"""
        request_id = uuid4()
        service_type = "security"
        
        with patch.object(service, 'send_notification') as mock_send:
            mock_send.return_value = [
                NotificationResult(type=NotificationType.PUSH, status="sent", message="Success")
            ]
            
            results = await service.send_emergency_confirmation(recipient, request_id, service_type)
            
            assert len(results) == 2  # Results from both push and SMS calls
            assert mock_send.call_count == 2  # Push and SMS
            
            # Verify the calls were made with correct templates
            call_args = mock_send.call_args_list
            assert call_args[0][0][0].template_id == "emergency_request_confirmed"
            assert call_args[1][0][0].template_id == "emergency_request_confirmed_sms"
    
    @pytest.mark.asyncio
    async def test_send_provider_assignment(self, service, recipient):
        """Test sending provider assignment notifications"""
        provider_name = "ABC Security"
        eta_minutes = 15
        vehicle_details = "White SUV - License ABC123"
        
        with patch.object(service, 'send_notification') as mock_send:
            mock_send.return_value = [
                NotificationResult(type=NotificationType.PUSH, status="sent", message="Success")
            ]
            
            results = await service.send_provider_assignment(
                recipient, provider_name, eta_minutes, vehicle_details
            )
            
            assert len(results) == 2  # Push and SMS
            assert mock_send.call_count == 2
    
    @pytest.mark.asyncio
    async def test_send_provider_arrival(self, service, recipient):
        """Test sending provider arrival notifications"""
        vehicle_description = "White SUV"
        license_plate = "ABC123"
        
        with patch.object(service, 'send_notification') as mock_send:
            mock_send.return_value = [
                NotificationResult(type=NotificationType.PUSH, status="sent", message="Success")
            ]
            
            results = await service.send_provider_arrival(
                recipient, vehicle_description, license_plate
            )
            
            assert len(results) == 2  # Push and SMS
            assert mock_send.call_count == 2
    
    @pytest.mark.asyncio
    async def test_send_field_agent_assignment(self, service, recipient):
        """Test sending field agent assignment notification"""
        service_type = "security"
        address = "123 Main St"
        description = "Suspicious activity reported"
        
        with patch.object(service, 'send_notification') as mock_send:
            mock_send.return_value = [
                NotificationResult(type=NotificationType.PUSH, status="sent", message="Success")
            ]
            
            results = await service.send_field_agent_assignment(
                recipient, service_type, address, description
            )
            
            assert len(results) == 1
            assert mock_send.call_count == 1
            
            # Verify correct template and variables
            call_args = mock_send.call_args_list[0][0][0]
            assert call_args.template_id == "agent_assignment"
            assert call_args.variables["service_type"] == service_type
            assert call_args.variables["address"] == address
            assert call_args.variables["description"] == description
    
    @pytest.mark.asyncio
    async def test_send_field_agent_assignment_no_description(self, service, recipient):
        """Test sending field agent assignment without description"""
        service_type = "security"
        address = "123 Main St"
        
        with patch.object(service, 'send_notification') as mock_send:
            mock_send.return_value = [
                NotificationResult(type=NotificationType.PUSH, status="sent", message="Success")
            ]
            
            results = await service.send_field_agent_assignment(
                recipient, service_type, address
            )
            
            assert len(results) == 1
            
            # Verify default description is used
            call_args = mock_send.call_args_list[0][0][0]
            assert call_args.variables["description"] == "No additional details"


class TestNotificationResult:
    """Test notification result model"""
    
    def test_create_successful_result(self):
        """Test creating successful notification result"""
        result = NotificationResult(
            recipient_id="user_123",
            type=NotificationType.PUSH,
            status="sent",
            message="Notification sent successfully",
            sent_at=datetime.utcnow(),
            external_id="fcm_12345"
        )
        
        assert result.recipient_id == "user_123"
        assert result.type == NotificationType.PUSH
        assert result.status == "sent"
        assert result.message == "Notification sent successfully"
        assert result.sent_at is not None
        assert result.external_id == "fcm_12345"
    
    def test_create_failed_result(self):
        """Test creating failed notification result"""
        result = NotificationResult(
            type=NotificationType.SMS,
            status="failed",
            message="Phone number not available"
        )
        
        assert result.type == NotificationType.SMS
        assert result.status == "failed"
        assert result.message == "Phone number not available"
        assert result.sent_at is None
        assert result.external_id is None


class TestNotificationRequest:
    """Test notification request model"""
    
    def test_create_notification_request(self):
        """Test creating notification request"""
        recipients = [
            NotificationRecipient(user_id=uuid4(), push_token="token1"),
            NotificationRecipient(user_id=uuid4(), phone_number="+1234567890")
        ]
        
        request = NotificationRequest(
            template_id="test_template",
            recipients=recipients,
            variables={"var1": "value1", "var2": "value2"},
            priority=NotificationPriority.HIGH,
            metadata={"source": "emergency_system"}
        )
        
        assert request.template_id == "test_template"
        assert len(request.recipients) == 2
        assert request.variables["var1"] == "value1"
        assert request.priority == NotificationPriority.HIGH
        assert request.metadata["source"] == "emergency_system"
    
    def test_create_notification_request_minimal(self):
        """Test creating notification request with minimal fields"""
        recipient = NotificationRecipient(phone_number="+1234567890")
        
        request = NotificationRequest(
            template_id="test_template",
            recipients=[recipient]
        )
        
        assert request.template_id == "test_template"
        assert len(request.recipients) == 1
        assert request.variables == {}
        assert request.priority == NotificationPriority.NORMAL
        assert request.scheduled_at is None
        assert request.metadata == {}