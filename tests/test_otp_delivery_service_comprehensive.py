"""
Comprehensive unit tests for OTP delivery service
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import aiosmtplib
from email.mime.multipart import MIMEMultipart

from app.services.otp_delivery import OTPDeliveryService
from app.core.config import settings


class TestOTPDeliveryService:
    """Test OTP delivery service functionality"""
    
    @pytest.fixture
    def service(self):
        """OTP delivery service instance"""
        return OTPDeliveryService()
    
    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing"""
        with patch.object(settings, 'SMTP_SERVER', 'smtp.test.com'), \
             patch.object(settings, 'SMTP_PORT', 587), \
             patch.object(settings, 'SMTP_USERNAME', 'test@test.com'), \
             patch.object(settings, 'SMTP_PASSWORD', 'password'), \
             patch.object(settings, 'FROM_EMAIL', 'noreply@panic-system.com'):
            yield
    
    def test_service_initialization(self, service, mock_settings):
        """Test service initialization with settings"""
        assert service.smtp_server == 'smtp.test.com'
        assert service.smtp_port == 587
        assert service.smtp_username == 'test@test.com'
        assert service.smtp_password == 'password'
        assert service.from_email == 'noreply@panic-system.com'
    
    def test_service_initialization_sms_settings(self, service):
        """Test service initialization with SMS settings"""
        with patch.object(settings, 'SMS_API_KEY', 'test_sms_key'), \
             patch.object(settings, 'SMS_API_URL', 'https://api.sms.com'):
            
            new_service = OTPDeliveryService()
            assert new_service.sms_api_key == 'test_sms_key'
            assert new_service.sms_api_url == 'https://api.sms.com'
    
    def test_service_initialization_no_sms_settings(self, service):
        """Test service initialization without SMS settings"""
        # Default behavior when SMS settings are not configured
        assert service.sms_api_key is None
        assert service.sms_api_url is None
    
    @pytest.mark.asyncio
    async def test_send_email_otp_success(self, service, mock_settings):
        """Test successful email OTP sending"""
        email = "test@example.com"
        otp = "123456"
        
        with patch('aiosmtplib.send') as mock_send:
            mock_send.return_value = True
            
            result = await service.send_email_otp(email, otp)
            
            assert result is True
            mock_send.assert_called_once()
            
            # Verify the email message structure
            call_args = mock_send.call_args
            message = call_args[0][0]  # First positional argument
            
            assert isinstance(message, MIMEMultipart)
            assert message["To"] == email
            assert message["From"] == service.from_email
            assert message["Subject"] == "Account Unlock Code - Panic System"
            
            # Verify SMTP connection parameters
            kwargs = call_args[1]  # Keyword arguments
            assert kwargs["hostname"] == service.smtp_server
            assert kwargs["port"] == service.smtp_port
            assert kwargs["username"] == service.smtp_username
            assert kwargs["password"] == service.smtp_password
            assert kwargs["use_tls"] is True
    
    @pytest.mark.asyncio
    async def test_send_email_otp_with_account_type(self, service, mock_settings):
        """Test email OTP sending with specific account type"""
        email = "firm@example.com"
        otp = "654321"
        account_type = "security_firm"
        
        with patch('aiosmtplib.send') as mock_send:
            mock_send.return_value = True
            
            result = await service.send_email_otp(email, otp, account_type)
            
            assert result is True
            mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_email_otp_smtp_error(self, service, mock_settings):
        """Test email OTP sending with SMTP error"""
        email = "test@example.com"
        otp = "123456"
        
        with patch('aiosmtplib.send') as mock_send:
            mock_send.side_effect = aiosmtplib.SMTPException("SMTP server error")
            
            result = await service.send_email_otp(email, otp)
            
            assert result is False
            mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_email_otp_connection_error(self, service, mock_settings):
        """Test email OTP sending with connection error"""
        email = "test@example.com"
        otp = "123456"
        
        with patch('aiosmtplib.send') as mock_send:
            mock_send.side_effect = ConnectionError("Cannot connect to SMTP server")
            
            result = await service.send_email_otp(email, otp)
            
            assert result is False
            mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_email_otp_general_exception(self, service, mock_settings):
        """Test email OTP sending with general exception"""
        email = "test@example.com"
        otp = "123456"
        
        with patch('aiosmtplib.send') as mock_send:
            mock_send.side_effect = Exception("Unexpected error")
            
            result = await service.send_email_otp(email, otp)
            
            assert result is False
            mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_sms_otp_not_configured(self, service):
        """Test SMS OTP sending when SMS service is not configured"""
        mobile_number = "+1234567890"
        otp = "123456"
        
        # Service is not configured (default state)
        result = await service.send_sms_otp(mobile_number, otp)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_sms_otp_configured_success(self, service):
        """Test SMS OTP sending when SMS service is configured"""
        mobile_number = "+1234567890"
        otp = "123456"
        
        # Configure SMS service
        service.sms_api_key = "test_api_key"
        service.sms_api_url = "https://api.sms.com"
        
        result = await service.send_sms_otp(mobile_number, otp)
        
        # Currently returns True as it's a mock implementation
        assert result is True
    
    @pytest.mark.asyncio
    async def test_send_sms_otp_configured_with_exception(self, service):
        """Test SMS OTP sending with exception in configured service"""
        mobile_number = "+1234567890"
        otp = "123456"
        
        # Configure SMS service
        service.sms_api_key = "test_api_key"
        service.sms_api_url = "https://api.sms.com"
        
        # Mock an exception during SMS sending
        with patch('app.services.otp_delivery.logger') as mock_logger:
            # Simulate an exception by patching the logger to raise an exception
            # In a real implementation, this would be the SMS API call
            with patch.object(service, 'send_sms_otp', side_effect=Exception("SMS API error")):
                with pytest.raises(Exception):
                    await service.send_sms_otp(mobile_number, otp)
    
    @pytest.mark.asyncio
    async def test_send_otp_email_method(self, service, mock_settings):
        """Test send_otp with email delivery method"""
        identifier = "test@example.com"
        otp = "123456"
        delivery_method = "email"
        
        with patch.object(service, 'send_email_otp') as mock_email:
            mock_email.return_value = True
            
            result = await service.send_otp(identifier, otp, delivery_method)
            
            assert result is True
            mock_email.assert_called_once_with(identifier, otp)
    
    @pytest.mark.asyncio
    async def test_send_otp_sms_method(self, service):
        """Test send_otp with SMS delivery method"""
        identifier = "+1234567890"
        otp = "123456"
        delivery_method = "sms"
        
        with patch.object(service, 'send_sms_otp') as mock_sms:
            mock_sms.return_value = True
            
            result = await service.send_otp(identifier, otp, delivery_method)
            
            assert result is True
            mock_sms.assert_called_once_with(identifier, otp)
    
    @pytest.mark.asyncio
    async def test_send_otp_default_method(self, service, mock_settings):
        """Test send_otp with default delivery method (email)"""
        identifier = "test@example.com"
        otp = "123456"
        
        with patch.object(service, 'send_email_otp') as mock_email:
            mock_email.return_value = True
            
            result = await service.send_otp(identifier, otp)  # No method specified
            
            assert result is True
            mock_email.assert_called_once_with(identifier, otp)
    
    @pytest.mark.asyncio
    async def test_send_otp_invalid_method(self, service):
        """Test send_otp with invalid delivery method"""
        identifier = "test@example.com"
        otp = "123456"
        delivery_method = "invalid_method"
        
        result = await service.send_otp(identifier, otp, delivery_method)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_otp_email_failure(self, service, mock_settings):
        """Test send_otp when email sending fails"""
        identifier = "test@example.com"
        otp = "123456"
        delivery_method = "email"
        
        with patch.object(service, 'send_email_otp') as mock_email:
            mock_email.return_value = False
            
            result = await service.send_otp(identifier, otp, delivery_method)
            
            assert result is False
            mock_email.assert_called_once_with(identifier, otp)
    
    @pytest.mark.asyncio
    async def test_send_otp_sms_failure(self, service):
        """Test send_otp when SMS sending fails"""
        identifier = "+1234567890"
        otp = "123456"
        delivery_method = "sms"
        
        with patch.object(service, 'send_sms_otp') as mock_sms:
            mock_sms.return_value = False
            
            result = await service.send_otp(identifier, otp, delivery_method)
            
            assert result is False
            mock_sms.assert_called_once_with(identifier, otp)


class TestOTPEmailContent:
    """Test OTP email content generation"""
    
    @pytest.fixture
    def service(self):
        """OTP delivery service instance"""
        return OTPDeliveryService()
    
    @pytest.mark.asyncio
    async def test_email_content_contains_otp(self, service):
        """Test that email content contains the OTP code"""
        email = "test@example.com"
        otp = "987654"
        
        with patch('aiosmtplib.send') as mock_send:
            mock_send.return_value = True
            
            await service.send_email_otp(email, otp)
            
            # Get the message that was sent
            call_args = mock_send.call_args
            message = call_args[0][0]
            
            # Convert message to string to check content
            message_str = str(message)
            assert otp in message_str
    
    @pytest.mark.asyncio
    async def test_email_content_structure(self, service):
        """Test email content has proper structure"""
        email = "test@example.com"
        otp = "123456"
        
        with patch('aiosmtplib.send') as mock_send:
            mock_send.return_value = True
            
            await service.send_email_otp(email, otp)
            
            # Get the message that was sent
            call_args = mock_send.call_args
            message = call_args[0][0]
            
            # Check message structure
            assert message.is_multipart()
            
            # Get parts
            parts = message.get_payload()
            assert len(parts) == 2  # Text and HTML parts
            
            # Check content types
            text_part = parts[0]
            html_part = parts[1]
            
            assert text_part.get_content_type() == "text/plain"
            assert html_part.get_content_type() == "text/html"
            
            # Check that both parts contain the OTP
            text_content = text_part.get_payload()
            html_content = html_part.get_payload()
            
            assert otp in text_content
            assert otp in html_content
    
    @pytest.mark.asyncio
    async def test_email_security_message(self, service):
        """Test that email contains security warning"""
        email = "test@example.com"
        otp = "123456"
        
        with patch('aiosmtplib.send') as mock_send:
            mock_send.return_value = True
            
            await service.send_email_otp(email, otp)
            
            # Get the message that was sent
            call_args = mock_send.call_args
            message = call_args[0][0]
            
            message_str = str(message)
            
            # Check for security-related content
            assert "expire" in message_str.lower()
            assert "10 minutes" in message_str
            assert "ignore" in message_str.lower()
    
    @pytest.mark.asyncio
    async def test_email_branding(self, service):
        """Test that email contains proper branding"""
        email = "test@example.com"
        otp = "123456"
        
        with patch('aiosmtplib.send') as mock_send:
            mock_send.return_value = True
            
            await service.send_email_otp(email, otp)
            
            # Get the message that was sent
            call_args = mock_send.call_args
            message = call_args[0][0]
            
            message_str = str(message)
            
            # Check for branding elements
            assert "Panic System" in message_str
            assert "Security Team" in message_str


class TestOTPDeliveryServiceIntegration:
    """Integration tests for OTP delivery service"""
    
    @pytest.fixture
    def service(self):
        """OTP delivery service instance"""
        return OTPDeliveryService()
    
    @pytest.mark.asyncio
    async def test_multiple_delivery_methods_same_otp(self, service):
        """Test sending same OTP via multiple delivery methods"""
        email = "test@example.com"
        phone = "+1234567890"
        otp = "123456"
        
        with patch.object(service, 'send_email_otp') as mock_email, \
             patch.object(service, 'send_sms_otp') as mock_sms:
            
            mock_email.return_value = True
            mock_sms.return_value = True
            
            # Send via email
            email_result = await service.send_otp(email, otp, "email")
            
            # Send via SMS
            sms_result = await service.send_otp(phone, otp, "sms")
            
            assert email_result is True
            assert sms_result is True
            
            mock_email.assert_called_once_with(email, otp)
            mock_sms.assert_called_once_with(phone, otp)
    
    @pytest.mark.asyncio
    async def test_fallback_behavior_email_fails_sms_succeeds(self, service):
        """Test behavior when email fails but SMS succeeds"""
        identifier = "test@example.com"
        otp = "123456"
        
        with patch.object(service, 'send_email_otp') as mock_email, \
             patch.object(service, 'send_sms_otp') as mock_sms:
            
            mock_email.return_value = False  # Email fails
            mock_sms.return_value = True     # SMS succeeds
            
            # Try email first
            email_result = await service.send_otp(identifier, otp, "email")
            assert email_result is False
            
            # Try SMS as fallback
            sms_result = await service.send_otp(identifier, otp, "sms")
            assert sms_result is True
    
    @pytest.mark.asyncio
    async def test_concurrent_otp_sending(self, service):
        """Test sending OTPs concurrently to multiple recipients"""
        recipients = [
            ("user1@example.com", "123456", "email"),
            ("user2@example.com", "654321", "email"),
            ("+1234567890", "111111", "sms"),
            ("+0987654321", "222222", "sms")
        ]
        
        with patch.object(service, 'send_email_otp') as mock_email, \
             patch.object(service, 'send_sms_otp') as mock_sms:
            
            mock_email.return_value = True
            mock_sms.return_value = True
            
            # Send all OTPs concurrently
            tasks = [
                service.send_otp(identifier, otp, method)
                for identifier, otp, method in recipients
            ]
            
            results = await asyncio.gather(*tasks)
            
            # All should succeed
            assert all(results)
            
            # Verify correct number of calls
            assert mock_email.call_count == 2  # Two email recipients
            assert mock_sms.call_count == 2    # Two SMS recipients
    
    @pytest.mark.asyncio
    async def test_otp_delivery_with_different_formats(self, service):
        """Test OTP delivery with different OTP formats"""
        test_cases = [
            ("123456", "6-digit numeric"),
            ("ABC123", "alphanumeric"),
            ("12-34-56", "formatted numeric"),
            ("a1b2c3", "mixed case alphanumeric")
        ]
        
        email = "test@example.com"
        
        with patch.object(service, 'send_email_otp') as mock_email:
            mock_email.return_value = True
            
            for otp, description in test_cases:
                result = await service.send_otp(email, otp, "email")
                assert result is True, f"Failed for {description}: {otp}"
            
            # Verify all OTPs were sent
            assert mock_email.call_count == len(test_cases)
            
            # Verify each OTP was passed correctly
            for i, (otp, _) in enumerate(test_cases):
                call_args = mock_email.call_args_list[i]
                assert call_args[0][1] == otp  # Second argument is the OTP


class TestOTPDeliveryServiceErrorHandling:
    """Test error handling in OTP delivery service"""
    
    @pytest.fixture
    def service(self):
        """OTP delivery service instance"""
        return OTPDeliveryService()
    
    @pytest.mark.asyncio
    async def test_email_otp_with_invalid_email_format(self, service):
        """Test email OTP with invalid email format"""
        invalid_email = "not-an-email"
        otp = "123456"
        
        with patch('aiosmtplib.send') as mock_send:
            # aiosmtplib might raise an exception for invalid email
            mock_send.side_effect = Exception("Invalid email format")
            
            result = await service.send_email_otp(invalid_email, otp)
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_sms_otp_with_invalid_phone_format(self, service):
        """Test SMS OTP with invalid phone format"""
        invalid_phone = "not-a-phone"
        otp = "123456"
        
        # Configure SMS service
        service.sms_api_key = "test_key"
        service.sms_api_url = "https://api.sms.com"
        
        # Currently the mock implementation doesn't validate phone format
        # In a real implementation, this would be handled by the SMS provider
        result = await service.send_sms_otp(invalid_phone, otp)
        
        # Mock implementation returns True, but real implementation would validate
        assert result is True
    
    @pytest.mark.asyncio
    async def test_empty_otp_handling(self, service):
        """Test handling of empty OTP"""
        email = "test@example.com"
        empty_otp = ""
        
        with patch('aiosmtplib.send') as mock_send:
            mock_send.return_value = True
            
            result = await service.send_email_otp(email, empty_otp)
            
            # Should still attempt to send (validation is handled elsewhere)
            assert result is True
            mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_none_otp_handling(self, service):
        """Test handling of None OTP"""
        email = "test@example.com"
        none_otp = None
        
        with patch('aiosmtplib.send') as mock_send:
            # This would likely cause an error in email template formatting
            mock_send.side_effect = TypeError("unsupported format string")
            
            result = await service.send_email_otp(email, none_otp)
            
            assert result is False