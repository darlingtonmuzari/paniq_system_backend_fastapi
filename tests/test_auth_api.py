"""
Test authentication API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.main import app
from app.services.auth import TokenPair, AuthenticationError, TokenExpiredError, UserContext


class TestAuthAPI:
    """Test authentication API endpoints"""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    @pytest.fixture
    def mock_token_pair(self):
        return TokenPair(
            access_token="mock.access.token",
            refresh_token="mock.refresh.token",
            expires_in=3600
        )
    
    @pytest.fixture
    def mock_user_context(self):
        return UserContext(
            user_id=uuid4(),
            user_type="registered_user",
            email="test@example.com",
            permissions=["emergency:request", "group:manage"]
        )
    
    @patch('app.services.auth.auth_service.authenticate_user')
    def test_login_success(self, mock_authenticate, client, mock_token_pair):
        """Test successful login"""
        mock_authenticate.return_value = mock_token_pair
        
        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "test_password",
            "user_type": "registered_user"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["access_token"] == "mock.access.token"
        assert data["refresh_token"] == "mock.refresh.token"
        assert data["token_type"] == "Bearer"
        assert data["expires_in"] == 3600
    
    @patch('app.services.auth.auth_service.authenticate_user')
    def test_login_invalid_credentials(self, mock_authenticate, client):
        """Test login with invalid credentials"""
        mock_authenticate.side_effect = AuthenticationError("Invalid credentials")
        
        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "wrong_password",
            "user_type": "registered_user"
        })
        
        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]
    
    def test_login_invalid_email_format(self, client):
        """Test login with invalid email format"""
        response = client.post("/api/v1/auth/login", json={
            "email": "invalid-email",
            "password": "test_password",
            "user_type": "registered_user"
        })
        
        assert response.status_code == 422  # Validation error
    
    def test_login_short_password(self, client):
        """Test login with password too short"""
        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "short",
            "user_type": "registered_user"
        })
        
        assert response.status_code == 422  # Validation error
    
    @patch('app.services.auth.auth_service.refresh_token')
    def test_refresh_token_success(self, mock_refresh, client, mock_token_pair):
        """Test successful token refresh"""
        mock_refresh.return_value = mock_token_pair
        
        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": "valid.refresh.token"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["access_token"] == "mock.access.token"
        assert data["refresh_token"] == "mock.refresh.token"
    
    @patch('app.services.auth.auth_service.refresh_token')
    def test_refresh_token_expired(self, mock_refresh, client):
        """Test refresh with expired token"""
        mock_refresh.side_effect = TokenExpiredError("Refresh token expired")
        
        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": "expired.refresh.token"
        })
        
        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()
    
    @patch('app.services.auth.auth_service.refresh_token')
    def test_refresh_token_invalid(self, mock_refresh, client):
        """Test refresh with invalid token"""
        mock_refresh.side_effect = AuthenticationError("Invalid token")
        
        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": "invalid.refresh.token"
        })
        
        assert response.status_code == 401
        assert "Invalid refresh token" in response.json()["detail"]
    
    @patch('app.services.auth.auth_service.validate_token')
    @patch('app.services.auth.auth_service.revoke_token')
    def test_revoke_token_success(self, mock_revoke, mock_validate, client, mock_user_context):
        """Test successful token revocation"""
        mock_validate.return_value = mock_user_context
        mock_revoke.return_value = True
        
        response = client.post(
            "/api/v1/auth/revoke",
            json={"token": "token.to.revoke"},
            headers={"Authorization": "Bearer valid.access.token"}
        )
        
        assert response.status_code == 200
        assert "revoked successfully" in response.json()["message"]
    
    @patch('app.services.auth.auth_service.validate_token')
    @patch('app.services.auth.auth_service.revoke_token')
    def test_revoke_token_failure(self, mock_revoke, mock_validate, client, mock_user_context):
        """Test token revocation failure"""
        mock_validate.return_value = mock_user_context
        mock_revoke.return_value = False
        
        response = client.post(
            "/api/v1/auth/revoke",
            json={"token": "token.to.revoke"},
            headers={"Authorization": "Bearer valid.access.token"}
        )
        
        assert response.status_code == 400
        assert "Failed to revoke token" in response.json()["detail"]
    
    def test_revoke_token_unauthorized(self, client):
        """Test token revocation without authentication"""
        response = client.post(
            "/api/v1/auth/revoke",
            json={"token": "token.to.revoke"}
        )
        
        assert response.status_code == 401
    
    @patch('app.services.auth.auth_service.validate_token')
    def test_logout_success(self, mock_validate, client, mock_user_context):
        """Test successful logout"""
        mock_validate.return_value = mock_user_context
        
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": "Bearer valid.access.token"}
        )
        
        assert response.status_code == 200
        assert "Logged out successfully" in response.json()["message"]
    
    def test_logout_unauthorized(self, client):
        """Test logout without authentication"""
        response = client.post("/api/v1/auth/logout")
        
        assert response.status_code == 401
    
    @patch('app.services.auth.auth_service.validate_token')
    def test_get_current_user_info(self, mock_validate, client, mock_user_context):
        """Test getting current user info"""
        mock_validate.return_value = mock_user_context
        
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer valid.access.token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["user_id"] == str(mock_user_context.user_id)
        assert data["email"] == mock_user_context.email
        assert data["user_type"] == mock_user_context.user_type
        assert data["permissions"] == mock_user_context.permissions
    
    def test_get_current_user_info_unauthorized(self, client):
        """Test getting user info without authentication"""
        response = client.get("/api/v1/auth/me")
        
        assert response.status_code == 401
    
    @patch('app.services.auth.auth_service.validate_token')
    def test_verify_token_success(self, mock_validate, client, mock_user_context):
        """Test successful token verification"""
        mock_validate.return_value = mock_user_context
        
        response = client.post(
            "/api/v1/auth/verify-token",
            headers={"Authorization": "Bearer valid.access.token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["valid"] is True
        assert data["user_id"] == str(mock_user_context.user_id)
        assert data["user_type"] == mock_user_context.user_type
    
    def test_verify_token_unauthorized(self, client):
        """Test token verification without token"""
        response = client.post("/api/v1/auth/verify-token")
        
        assert response.status_code == 401
    
    @patch('app.services.auth.auth_service.validate_token')
    def test_verify_token_expired(self, mock_validate, client):
        """Test verification of expired token"""
        mock_validate.side_effect = TokenExpiredError("Token expired")
        
        response = client.post(
            "/api/v1/auth/verify-token",
            headers={"Authorization": "Bearer expired.access.token"}
        )
        
        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()
    
    def test_login_with_platform_header(self, client):
        """Test login with platform header"""
        with patch('app.services.auth.auth_service.authenticate_user') as mock_auth:
            mock_auth.return_value = TokenPair("access", "refresh", 3600)
            
            response = client.post(
                "/api/v1/auth/login",
                json={
                    "email": "test@example.com",
                    "password": "test_password",
                    "user_type": "registered_user"
                },
                headers={"X-Platform": "android"}
            )
            
            assert response.status_code == 200
    
    def test_login_firm_personnel(self, client):
        """Test login for firm personnel"""
        with patch('app.services.auth.auth_service.authenticate_user') as mock_auth:
            mock_auth.return_value = TokenPair("access", "refresh", 3600)
            
            response = client.post("/api/v1/auth/login", json={
                "email": "agent@firm.com",
                "password": "test_password",
                "user_type": "firm_personnel"
            })
            
            assert response.status_code == 200
            mock_auth.assert_called_once_with(
                email="agent@firm.com",
                password="test_password",
                user_type="firm_personnel"
            )