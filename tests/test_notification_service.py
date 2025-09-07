"""
Unit tests for notification service
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from datetime import datetime

from app.services.notification import (
    NotificationService,
    PushNotificationService,
    SMSNotificationService,
    EmailNotificationService,
    NotificationTemplateManager,
    NotificationRecipient,
    NotificationRequest,
    NotificationResult,
    NotificationType,
    NotificationPriority,
    NotificationTemplate,
    notification_service
)


class TestNotificationTemplateManager:
    """Test notification template management"""
    
    @pytest.fixture
    def template_manager(self):
        """Create template manager instance"""
        return NotificationTemplateManager()
    
    def test_default_templates_loaded(self, template_manager):
        """Test that default templates are loaded"""
        assert len(template_manager.templates) > 0
        assert "emergency_request_confirmed" in template_manager.templates
        assert "provider_assigned" in template_manager.templates
        assert "provider_arrived" in template_manager.templates
    
    def test_get_template(self, template_manager):
        """Test getting template by ID"""
        template = template_manager.get_template("emergency_request_confirmed")
        assert template is not None
        assert template.type == NotificationType.PUSH
        assert template.priority == NotificationPriority.HIGH
        
        # Test non-existent template
        assert template_manager.get_template("non_existent") is None
    
    def test_add_template(self, template_manager):
        """Test adding custom template"""
        custom_template = NotificationTemplate(
            id="custom_test",
            name="Custom Test Template",
            type=NotificationType.SMS,
            body="Test message: {test_var}",
            variables=["test_var"]
        )
        
        template_manager.add_template(custom_template)
        
        retrieved = template_manager.get_template("custom_test")
        assert retrieved is not None
        assert retrieved.name == "Custom Test Template"
        assert retrieved.type == NotificationType.SMS
    
    def test_render_template(self, template_manager):
        """Test template rendering with variables"""
        variables = {
            "request_id": "12345",
            "service_type": "ambulance"
        }
        
        rendered = template_manager.render_template("emergency_request_confirmed", variables)
        
        assert rendered is not None
        assert "title" in rendered
        assert "body" in rendered
        assert "12345" in rendered["body"]
        assert "ambulance" in rendered["body"]
    
    def test_render_template_missing_variable(self, template_manager):
        """Test template rendering with missing variables"""
        variables = {"request_id": "12345"}  # Missing service_type
        
        rendered = template_manager.render_template("emergency_request_confirmed", variables)
        
        # Should still return rendered content, but with original template string
        assert rendered is not None
        assert "12345" in rendered["body"]
    
    def test_render_nonexistent_template(self, template_manager):
        """Test rendering non-existent template"""
        rendered = template_manager.render_template("non_existent", {})
        assert rendered is None


class TestPushNotificationService:
    """Test push notification service"""
    
    @pytest.fixture
    def push_service(self):
        """Create push notification service"""
        return PushNotificationService()
    
    @pytest.fixture
    def recipient_with_push_token(self):
        """Create recipient with push token"""
        return NotificationRecipient(
            user_id=uuid4(),
            push_token="test_push_token_123",
            platform="android"
        )
    
    @pytest.fixture
    def recipient_without_push_token(self):
        """Create recipient without push token"""
        return NotificationRecipient(
            user_id=uuid4(),
            phone_number="+1234567890"
        )
    
    @pytest.mark.asyncio
    async def test_send_push_notification_success(self, push_service, recipient_with_push_token):
        """Test successful push notification sending"""
        result = await push_service.send_push_notification(
            recipient_with_push_token,
            "Test Title",
            "Test Body",
            {"key": "value"},
            NotificationPriority.HIGH
        )
        
        assert result.type == NotificationType.PUSH
        assert result.status == "sent"
        assert result.recipient_id == str(recipient_with_push_token.user_id)
        assert result.sent_at is not None
        assert result.external_id is not None
    
    @pytest.mark.asyncio
    async def test_send_push_notification_no_token(self, push_service, recipient_without_push_token):
        """Test push notification with no push token"""
        result = await push_service.send_push_notification(
            recipient_without_push_token,
            "Test Title",
            "Test Body"
        )
        
        assert result.type == NotificationType.PUSH
        assert result.status == "failed"
        assert "No push token available" in result.message
    
    def test_get_fcm_priority(self, push_service):
        """Test FCM priority mapping"""
        assert push_service._get_fcm_priority(NotificationPriority.LOW) == "normal"
        assert push_service._get_fcm_priority(NotificationPriority.NORMAL) == "normal"
        assert push_service._get_fcm_priority(NotificationPriority.HIGH) == "high"
        assert push_service._get_fcm_priority(NotificationPriority.URGENT) == "high"


class TestSMSNotificationService:
    """Test SMS notification service"""
    
    @pytest.fixture
    def sms_service(self):
        """Create SMS notification service"""
        return SMSNotificationService()
    
    @pytest.fixture
    def recipient_with_phone(self):
        """Create recipient with phone number"""
        return NotificationRecipient(
            user_id=uuid4(),
            phone_number="+1234567890"
        )
    
    @pytest.fixture
    def recipient_without_phone(self):
        """Create recipient without phone number"""
        return NotificationRecipient(
            user_id=uuid4(),
            email="test@example.com"
        )
    
    @pytest.mark.asyncio
    async def test_send_sms_notification_success(self, sms_service, recipient_with_phone):
        """Test successful SMS notification sending"""
        result = await sms_service.send_sms_notification(
            recipient_with_phone,
            "Test SMS message",
            NotificationPriority.HIGH
        )
        
        assert result.type == NotificationType.SMS
        assert result.status == "sent"
        assert result.recipient_id == str(recipient_with_phone.user_id)
        assert result.sent_at is not None
        assert result.external_id is not None
    
    @pytest.mark.asyncio
    async def test_send_sms_notification_no_phone(self, sms_service, recipient_without_phone):
        """Test SMS notification with no phone number"""
        result = await sms_service.send_sms_notification(
            recipient_without_phone,
            "Test SMS message"
        )
        
        assert result.type == NotificationType.SMS
        assert result.status == "failed"
        assert "No phone number available" in result.message


class TestEmailNotificationService:
    """Test email notification service"""
    
    @pytest.fixture
    def email_service(self):
        """Create email notification service"""
        return EmailNotificationService()
    
    @pytest.fixture
    def recipient_with_email(self):
        """Create recipient with email"""
        return NotificationRecipient(
            user_id=uuid4(),
            email="test@example.com"
        )
    
    @pytest.fixture
    def recipient_without_email(self):
        """Create recipient without email"""
        return NotificationRecipient(
            user_id=uuid4(),
            phone_number="+1234567890"
        )
    
    @pytest.mark.asyncio
    async def test_send_email_notification_success(self, email_service, recipient_with_email):
        """Test successful email notification sending"""
        result = await email_service.send_email_notification(
            recipient_with_email,
            "Test Subject",
            "Test email body",
            "<p>Test HTML body</p>",
            NotificationPriority.NORMAL
        )
        
        assert result.type == NotificationType.EMAIL
        assert result.status == "sent"
        assert result.recipient_id == str(recipient_with_email.user_id)
        assert result.sent_at is not None
        assert result.external_id is not None
    
    @pytest.mark.asyncio
    async def test_send_email_notification_no_email(self, email_service, recipient_without_email):
        """Test email notification with no email address"""
        result = await email_service.send_email_notification(
            recipient_without_email,
            "Test Subject",
            "Test email body"
        )
        
        assert result.type == NotificationType.EMAIL
        assert result.status == "failed"
        assert "No email address available" in result.message


class TestNotificationService:
    """Test main notification service"""
    
    @pytest.fixture
    def service(self):
        """Create notification service"""
        return NotificationService()
    
    @pytest.fixture
    def recipient(self):
        """Create test recipient"""
        return NotificationRecipient(
            user_id=uuid4(),
            phone_number="+1234567890",
            email="test@example.com",
            push_token="test_push_token",
            platform="android"
        )
    
    @pytest.mark.asyncio
    async def test_send_notification_push(self, service, recipient):
        """Test sending push notification via template"""
        request = NotificationRequest(
            template_id="emergency_request_confirmed",
            recipients=[recipient],
            variables={
                "request_id": "12345",
                "service_type": "ambulance"
            },
            priority=NotificationPriority.HIGH
        )
        
        results = await service.send_notification(request)
        
        assert len(results) == 1
        assert results[0].type == NotificationType.PUSH
        assert results[0].status == "sent"
    
    @pytest.mark.asyncio
    async def test_send_notification_sms(self, service, recipient):
        """Test sending SMS notification via template"""
        request = NotificationRequest(
            template_id="emergency_request_confirmed_sms",
            recipients=[recipient],
            variables={
                "request_id": "12345",
                "service_type": "ambulance"
            },
            priority=NotificationPriority.HIGH
        )
        
        results = await service.send_notification(request)
        
        assert len(results) == 1
        assert results[0].type == NotificationType.SMS
        assert results[0].status == "sent"
    
    @pytest.mark.asyncio
    async def test_send_notification_email(self, service, recipient):
        """Test sending email notification via template"""
        request = NotificationRequest(
            template_id="emergency_summary_email",
            recipients=[recipient],
            variables={
                "user_name": "John Doe",
                "request_id": "12345",
                "service_type": "ambulance",
                "status": "completed",
                "address": "123 Main St"
            },
            priority=NotificationPriority.NORMAL
        )
        
        results = await service.send_notification(request)
        
        assert len(results) == 1
        assert results[0].type == NotificationType.EMAIL
        assert results[0].status == "sent"
    
    @pytest.mark.asyncio
    async def test_send_notification_invalid_template(self, service, recipient):
        """Test sending notification with invalid template"""
        request = NotificationRequest(
            template_id="non_existent_template",
            recipients=[recipient],
            variables={}
        )
        
        with pytest.raises(Exception):  # Should raise NotificationError
            await service.send_notification(request)
    
    @pytest.mark.asyncio
    async def test_send_emergency_confirmation(self, service, recipient):
        """Test sending emergency confirmation notifications"""
        request_id = uuid4()
        
        results = await service.send_emergency_confirmation(
            recipient,
            request_id,
            "ambulance"
        )
        
        # Should send both push and SMS notifications
        assert len(results) == 2
        
        # Check that we have both push and SMS results
        types = [result.type for result in results]
        assert NotificationType.PUSH in types
        assert NotificationType.SMS in types
        
        # All should be successful
        for result in results:
            assert result.status == "sent"
    
    @pytest.mark.asyncio
    async def test_send_provider_assignment(self, service, recipient):
        """Test sending provider assignment notifications"""
        results = await service.send_provider_assignment(
            recipient,
            "Emergency Services Inc",
            15,
            "White ambulance"
        )
        
        # Should send both push and SMS notifications
        assert len(results) == 2
        
        # Check that we have both push and SMS results
        types = [result.type for result in results]
        assert NotificationType.PUSH in types
        assert NotificationType.SMS in types
        
        # All should be successful
        for result in results:
            assert result.status == "sent"
    
    @pytest.mark.asyncio
    async def test_send_provider_arrival(self, service, recipient):
        """Test sending provider arrival notifications"""
        results = await service.send_provider_arrival(
            recipient,
            "White ambulance",
            "ABC123"
        )
        
        # Should send both push and SMS notifications
        assert len(results) == 2
        
        # Check that we have both push and SMS results
        types = [result.type for result in results]
        assert NotificationType.PUSH in types
        assert NotificationType.SMS in types
        
        # All should be successful
        for result in results:
            assert result.status == "sent"
    
    @pytest.mark.asyncio
    async def test_send_field_agent_assignment(self, service, recipient):
        """Test sending field agent assignment notification"""
        results = await service.send_field_agent_assignment(
            recipient,
            "security",
            "123 Main St",
            "Security assistance needed"
        )
        
        # Should send push notification only
        assert len(results) == 1
        assert results[0].type == NotificationType.PUSH
        assert results[0].status == "sent"


@pytest.mark.asyncio
async def test_global_notification_service():
    """Test that global notification service instance works correctly"""
    recipient = NotificationRecipient(
        user_id=uuid4(),
        push_token="test_token",
        platform="android"
    )
    
    results = await notification_service.send_field_agent_assignment(
        recipient,
        "ambulance",
        "456 Oak Ave",
        "Medical emergency"
    )
    
    assert len(results) == 1
    assert results[0].type == NotificationType.PUSH
    assert results[0].status == "sent"


class TestNotificationModels:
    """Test notification data models"""
    
    def test_notification_recipient_creation(self):
        """Test creating notification recipient"""
        recipient = NotificationRecipient(
            user_id=uuid4(),
            phone_number="+1234567890",
            email="test@example.com",
            push_token="test_token",
            platform="android",
            preferred_language="en"
        )
        
        assert recipient.user_id is not None
        assert recipient.phone_number == "+1234567890"
        assert recipient.email == "test@example.com"
        assert recipient.push_token == "test_token"
        assert recipient.platform == "android"
        assert recipient.preferred_language == "en"
    
    def test_notification_request_creation(self):
        """Test creating notification request"""
        recipient = NotificationRecipient(user_id=uuid4())
        
        request = NotificationRequest(
            template_id="test_template",
            recipients=[recipient],
            variables={"key": "value"},
            priority=NotificationPriority.HIGH,
            metadata={"source": "test"}
        )
        
        assert request.template_id == "test_template"
        assert len(request.recipients) == 1
        assert request.variables["key"] == "value"
        assert request.priority == NotificationPriority.HIGH
        assert request.metadata["source"] == "test"
    
    def test_notification_result_creation(self):
        """Test creating notification result"""
        result = NotificationResult(
            recipient_id="test_user",
            type=NotificationType.PUSH,
            status="sent",
            message="Success",
            sent_at=datetime.utcnow(),
            external_id="ext_123"
        )
        
        assert result.recipient_id == "test_user"
        assert result.type == NotificationType.PUSH
        assert result.status == "sent"
        assert result.message == "Success"
        assert result.sent_at is not None
        assert result.external_id == "ext_123"
    
    def test_notification_template_creation(self):
        """Test creating notification template"""
        template = NotificationTemplate(
            id="test_template",
            name="Test Template",
            type=NotificationType.SMS,
            body="Hello {name}",
            variables=["name"],
            priority=NotificationPriority.NORMAL
        )
        
        assert template.id == "test_template"
        assert template.name == "Test Template"
        assert template.type == NotificationType.SMS
        assert template.body == "Hello {name}"
        assert "name" in template.variables
        assert template.priority == NotificationPriority.NORMAL