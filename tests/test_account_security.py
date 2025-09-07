"""
Tests for account security service
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.account_security import AccountSecurityService
from app.services.otp_delivery import OTPDeliveryService


class TestAccountSecurityService:
    """Test cases for AccountSecurityService"""
    
    @pytest.fixture
    def security_service(self):
        return AccountSecurityService()
    
    @pytest.fixture
    def mock_db(self):
        return AsyncMock()
    
    @pytest.fixture
    def mock_redis(self):
        redis_mock = AsyncMock()
        redis_mock.get.return_value = None
        redis_mock.setex.return_value = True
        redis_mock.delete.return_value = True
        return redis_mock
    
    @pytest.mark.asyncio
    async def test_record_failed_login_first_attempt(self, security_service, mock_db, mock_redis):
        """Test recording first failed login attempt"""
        with patch('app.services.account_security.get_redis', return_value=mock_redis):
            result = await security_service.record_failed_login("test@example.com", mock_db)
            
            assert result["locked"] is False
            assert result["attempts"] == 1
            assert result["remaining_attempts"] == 4
            assert result["lockout_expires"] is None
            
            mock_redis.setex.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_record_failed_login_max_attempts(self, security_service, mock_db, mock_redis):
        """Test account locking after max failed attempts"""
        # Simulate 4 previous attempts
        mock_redis.get.return_value = b'4'
        
        with patch('app.services.account_security.get_redis', return_value=mock_redis):
            with patch.object(security_service, '_lock_account') as mock_lock:
                result = await security_service.record_failed_login("test@example.com", mock_db)
                
                assert result["locked"] is True
                assert result["attempts"] == 5
                assert result["remaining_attempts"] == 0
                assert result["lockout_expires"] is not None
                
                mock_lock.assert_called_once_with("test@example.com", mock_db)
    
    @pytest.mark.asyncio
    async def test_clear_failed_attempts(self, security_service, mock_redis):
        """Test clearing failed login attempts"""
        with patch('app.services.account_security.get_redis', return_value=mock_redis):
            await security_service.clear_failed_attempts("test@example.com")
            
            mock_redis.delete.assert_called_once_with("failed_login:test@example.com")
    
    @pytest.mark.asyncio
    async def test_generate_otp(self, security_service, mock_redis):
        """Test OTP generation"""
        with patch('app.services.account_security.get_redis', return_value=mock_redis):
            otp = await security_service.generate_otp("test@example.com")
            
            assert len(otp) == 6
            assert otp.isdigit()
            
            mock_redis.setex.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_verify_otp_valid(self, security_service, mock_db, mock_redis):
        """Test OTP verification with valid code"""
        mock_redis.get.return_value = b'123456'
        
        with patch('app.services.account_security.get_redis', return_value=mock_redis):
            with patch.object(security_service, '_unlock_account') as mock_unlock:
                result = await security_service.verify_otp("test@example.com", "123456", mock_db)
                
                assert result is True
                mock_unlock.assert_called_once_with("test@example.com", mock_db)
                mock_redis.delete.assert_called()
    
    @pytest.mark.asyncio
    async def test_verify_otp_invalid(self, security_service, mock_db, mock_redis):
        """Test OTP verification with invalid code"""
        mock_redis.get.return_value = b'123456'
        
        with patch('app.services.account_security.get_redis', return_value=mock_redis):
            result = await security_service.verify_otp("test@example.com", "654321", mock_db)
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_verify_otp_expired(self, security_service, mock_db, mock_redis):
        """Test OTP verification with expired code"""
        mock_redis.get.return_value = None
        
        with patch('app.services.account_security.get_redis', return_value=mock_redis):
            result = await security_service.verify_otp("test@example.com", "123456", mock_db)
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_get_failed_attempts_count(self, security_service, mock_redis):
        """Test getting failed attempts count"""
        mock_redis.get.return_value = b'3'
        
        with patch('app.services.account_security.get_redis', return_value=mock_redis):
            count = await security_service.get_failed_attempts_count("test@example.com")
            
            assert count == 3
    
    @pytest.mark.asyncio
    async def test_get_failed_attempts_count_no_attempts(self, security_service, mock_redis):
        """Test getting failed attempts count when no attempts recorded"""
        mock_redis.get.return_value = None
        
        with patch('app.services.account_security.get_redis', return_value=mock_redis):
            count = await security_service.get_failed_attempts_count("test@example.com")
            
            assert count == 0


class TestOTPDeliveryService:
    """Test cases for OTPDeliveryService"""
    
    @pytest.fixture
    def delivery_service(self):
        return OTPDeliveryService()
    
    @pytest.mark.asyncio
    async def test_send_email_otp_success(self, delivery_service):
        """Test successful email OTP delivery"""
        with patch('app.services.otp_delivery.aiosmtplib.send') as mock_send:
            mock_send.return_value = True
            
            result = await delivery_service.send_email_otp("test@example.com", "123456")
            
            assert result is True
            mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_email_otp_failure(self, delivery_service):
        """Test failed email OTP delivery"""
        with patch('app.services.otp_delivery.aiosmtplib.send') as mock_send:
            mock_send.side_effect = Exception("SMTP error")
            
            result = await delivery_service.send_email_otp("test@example.com", "123456")
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_send_sms_otp_not_configured(self, delivery_service):
        """Test SMS OTP when service not configured"""
        result = await delivery_service.send_sms_otp("+1234567890", "123456")
        
        # Should return False when SMS service not configured
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_otp_email_method(self, delivery_service):
        """Test send_otp with email method"""
        with patch.object(delivery_service, 'send_email_otp') as mock_email:
            mock_email.return_value = True
            
            result = await delivery_service.send_otp("test@example.com", "123456", "email")
            
            assert result is True
            mock_email.assert_called_once_with("test@example.com", "123456")
    
    @pytest.mark.asyncio
    async def test_send_otp_sms_method(self, delivery_service):
        """Test send_otp with SMS method"""
        with patch.object(delivery_service, 'send_sms_otp') as mock_sms:
            mock_sms.return_value = True
            
            result = await delivery_service.send_otp("+1234567890", "123456", "sms")
            
            assert result is True
            mock_sms.assert_called_once_with("+1234567890", "123456")
    
    @pytest.mark.asyncio
    async def test_send_otp_invalid_method(self, delivery_service):
        """Test send_otp with invalid method"""
        result = await delivery_service.send_otp("test@example.com", "123456", "invalid")
        
        assert result is False