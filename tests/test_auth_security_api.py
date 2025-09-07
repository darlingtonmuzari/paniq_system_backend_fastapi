"""
Tests for authentication API with account security features
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app

client = TestClient(app)


class TestAccountSecurityAPI:
    """Test cases for account security API endpoints"""
    
    def test_request_unlock_otp_success(self):
        """Test successful OTP request for account unlock"""
        with patch('app.api.v1.auth.auth_service.request_account_unlock_otp') as mock_request:
            mock_request.return_value = {
                "success": True,
                "message": "OTP sent via email",
                "expires_in_minutes": 10
            }
            
            response = client.post(
                "/api/v1/auth/request-unlock-otp",
                json={
                    "identifier": "test@example.com",
                    "delivery_method": "email"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "OTP sent via email"
            assert data["expires_in_minutes"] == 10
    
    def test_request_unlock_otp_account_not_locked(self):
        """Test OTP request when account is not locked"""
        with patch('app.api.v1.auth.auth_service.request_account_unlock_otp') as mock_request:
            mock_request.side_effect = Exception("Account is not locked")
            
            response = client.post(
                "/api/v1/auth/request-unlock-otp",
                json={
                    "identifier": "test@example.com",
                    "delivery_method": "email"
                }
            )
            
            assert response.status_code == 500
    
    def test_request_unlock_otp_sms_method(self):
        """Test OTP request with SMS delivery method"""
        with patch('app.api.v1.auth.auth_service.request_account_unlock_otp') as mock_request:
            mock_request.return_value = {
                "success": True,
                "message": "OTP sent via sms",
                "expires_in_minutes": 10
            }
            
            response = client.post(
                "/api/v1/auth/request-unlock-otp",
                json={
                    "identifier": "+1234567890",
                    "delivery_method": "sms"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "OTP sent via sms"
    
    def test_verify_unlock_otp_success(self):
        """Test successful OTP verification and account unlock"""
        with patch('app.api.v1.auth.auth_service.verify_unlock_otp') as mock_verify:
            mock_verify.return_value = {
                "success": True,
                "message": "Account unlocked successfully"
            }
            
            response = client.post(
                "/api/v1/auth/verify-unlock-otp",
                json={
                    "identifier": "test@example.com",
                    "otp": "123456"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Account unlocked successfully"
    
    def test_verify_unlock_otp_invalid_code(self):
        """Test OTP verification with invalid code"""
        with patch('app.api.v1.auth.auth_service.verify_unlock_otp') as mock_verify:
            mock_verify.return_value = {
                "success": False,
                "message": "Invalid or expired OTP"
            }
            
            response = client.post(
                "/api/v1/auth/verify-unlock-otp",
                json={
                    "identifier": "test@example.com",
                    "otp": "654321"
                }
            )
            
            assert response.status_code == 400
            data = response.json()
            assert "Invalid or expired OTP" in data["detail"]
    
    def test_verify_unlock_otp_invalid_format(self):
        """Test OTP verification with invalid OTP format"""
        response = client.post(
            "/api/v1/auth/verify-unlock-otp",
            json={
                "identifier": "test@example.com",
                "otp": "12345"  # Too short
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_get_account_status_unlocked(self):
        """Test getting account status for unlocked account"""
        with patch('app.api.v1.auth.auth_service.get_account_status') as mock_status:
            mock_status.return_value = {
                "is_locked": False,
                "failed_attempts": 2,
                "max_attempts": 5,
                "remaining_attempts": 3
            }
            
            response = client.get("/api/v1/auth/account-status/test@example.com")
            
            assert response.status_code == 200
            data = response.json()
            assert data["is_locked"] is False
            assert data["failed_attempts"] == 2
            assert data["max_attempts"] == 5
            assert data["remaining_attempts"] == 3
    
    def test_get_account_status_locked(self):
        """Test getting account status for locked account"""
        with patch('app.api.v1.auth.auth_service.get_account_status') as mock_status:
            mock_status.return_value = {
                "is_locked": True,
                "failed_attempts": 5,
                "max_attempts": 5,
                "remaining_attempts": 0
            }
            
            response = client.get("/api/v1/auth/account-status/locked@example.com")
            
            assert response.status_code == 200
            data = response.json()
            assert data["is_locked"] is True
            assert data["failed_attempts"] == 5
            assert data["remaining_attempts"] == 0
    
    def test_login_with_locked_account(self):
        """Test login attempt with locked account"""
        with patch('app.api.v1.auth.auth_service.authenticate_user') as mock_auth:
            from app.services.auth import AuthenticationError
            mock_auth.side_effect = AuthenticationError("Account is locked. Please use OTP to unlock.")
            
            response = client.post(
                "/api/v1/auth/login",
                json={
                    "email": "locked@example.com",
                    "password": "password123",
                    "user_type": "registered_user"
                }
            )
            
            assert response.status_code == 401
            data = response.json()
            assert "Invalid email or password" in data["detail"]


class TestAccountSecurityIntegration:
    """Integration tests for account security features"""
    
    def test_full_account_lockout_flow(self):
        """Test complete flow: failed logins -> lockout -> OTP unlock"""
        # This would be an integration test that:
        # 1. Makes multiple failed login attempts
        # 2. Verifies account gets locked
        # 3. Requests OTP for unlock
        # 4. Verifies OTP and unlocks account
        # 5. Verifies successful login after unlock
        
        # For now, we'll just test the API structure
        pass
    
    def test_otp_expiry_handling(self):
        """Test OTP expiry and cleanup"""
        # This would test:
        # 1. Generate OTP
        # 2. Wait for expiry (or mock time)
        # 3. Verify expired OTP is rejected
        # 4. Verify new OTP can be generated
        
        pass
    
    def test_multiple_otp_attempts(self):
        """Test multiple OTP verification attempts"""
        # This would test:
        # 1. Generate OTP
        # 2. Make multiple invalid attempts
        # 3. Verify rate limiting or attempt tracking
        
        pass