"""
Test authentication and JWT token management
"""
import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, patch, MagicMock
import jwt

from app.services.auth import (
    JWTTokenService,
    AuthService,
    PasswordService,
    UserContext,
    TokenPair,
    AuthenticationError,
    TokenExpiredError
)
from app.core.config import settings


class TestJWTTokenService:
    """Test JWT token service"""
    
    @pytest.fixture
    def service(self):
        return JWTTokenService()
    
    @pytest.fixture
    def user_data(self):
        return {
            "user_id": uuid4(),
            "user_type": "registered_user",
            "email": "test@example.com",
            "permissions": ["emergency:request", "group:manage"]
        }
    
    def test_create_access_token(self, service, user_data):
        """Test access token creation"""
        token = service.create_access_token(**user_data)
        
        assert isinstance(token, str)
        assert len(token) > 100  # JWT tokens are typically long
        
        # Decode token to verify contents
        payload = jwt.decode(
            token,
            service.secret_key,
            algorithms=[service.algorithm]
        )
        
        assert payload["sub"] == str(user_data["user_id"])
        assert payload["user_type"] == user_data["user_type"]
        assert payload["email"] == user_data["email"]
        assert payload["permissions"] == user_data["permissions"]
        assert payload["token_type"] == "access"
        assert "exp" in payload
        assert "iat" in payload
        assert "jti" in payload
    
    def test_create_refresh_token(self, service, user_data):
        """Test refresh token creation"""
        token = service.create_refresh_token(
            user_data["user_id"],
            user_data["user_type"]
        )
        
        assert isinstance(token, str)
        
        # Decode token to verify contents
        payload = jwt.decode(
            token,
            service.secret_key,
            algorithms=[service.algorithm]
        )
        
        assert payload["sub"] == str(user_data["user_id"])
        assert payload["user_type"] == user_data["user_type"]
        assert payload["token_type"] == "refresh"
        assert "exp" in payload
        assert "iat" in payload
        assert "jti" in payload
    
    def test_create_token_pair(self, service, user_data):
        """Test token pair creation"""
        token_pair = service.create_token_pair(**user_data)
        
        assert isinstance(token_pair, TokenPair)
        assert token_pair.access_token
        assert token_pair.refresh_token
        assert token_pair.token_type == "Bearer"
        assert token_pair.expires_in > 0
        
        # Verify both tokens are valid
        access_payload = jwt.decode(
            token_pair.access_token,
            service.secret_key,
            algorithms=[service.algorithm]
        )
        refresh_payload = jwt.decode(
            token_pair.refresh_token,
            service.secret_key,
            algorithms=[service.algorithm]
        )
        
        assert access_payload["token_type"] == "access"
        assert refresh_payload["token_type"] == "refresh"
    
    def test_verify_token_success(self, service, user_data):
        """Test successful token verification"""
        token = service.create_access_token(**user_data)
        
        with patch.object(service, 'is_token_blacklisted', return_value=False):
            payload = service.verify_token(token)
            
            assert payload["sub"] == str(user_data["user_id"])
            assert payload["user_type"] == user_data["user_type"]
    
    def test_verify_token_expired(self, service, user_data):
        """Test verification of expired token"""
        # Create token with past expiration
        expired_token = service.create_access_token(
            **user_data,
            expires_delta=timedelta(seconds=-1)
        )
        
        with pytest.raises(TokenExpiredError):
            service.verify_token(expired_token)
    
    def test_verify_token_invalid(self, service):
        """Test verification of invalid token"""
        invalid_token = "invalid.jwt.token"
        
        with pytest.raises(AuthenticationError):
            service.verify_token(invalid_token)
    
    @pytest.mark.asyncio
    async def test_verify_token_blacklisted(self, service, user_data):
        """Test verification of blacklisted token"""
        token = service.create_access_token(**user_data)
        
        with patch.object(service, 'is_token_blacklisted', return_value=True):
            with pytest.raises(AuthenticationError, match="revoked"):
                service.verify_token(token)
    
    @pytest.mark.asyncio
    async def test_revoke_token_success(self, service, user_data):
        """Test successful token revocation"""
        token = service.create_access_token(**user_data)
        
        with patch('app.core.redis.cache.set') as mock_cache_set:
            mock_cache_set.return_value = True
            
            result = await service.revoke_token(token)
            
            assert result is True
            mock_cache_set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_revoke_token_invalid(self, service):
        """Test revocation of invalid token"""
        invalid_token = "invalid.jwt.token"
        
        result = await service.revoke_token(invalid_token)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_is_token_blacklisted(self, service):
        """Test blacklist checking"""
        jti = "test-jti-123"
        
        with patch('app.core.redis.cache.exists') as mock_cache_exists:
            mock_cache_exists.return_value = True
            
            result = await service.is_token_blacklisted(jti)
            
            assert result is True
            mock_cache_exists.assert_called_once_with(f"blacklist:{jti}")
    
    def test_extract_user_context(self, service, user_data):
        """Test user context extraction from token"""
        token = service.create_access_token(**user_data)
        
        with patch.object(service, 'verify_token') as mock_verify:
            mock_verify.return_value = {
                "sub": str(user_data["user_id"]),
                "user_type": user_data["user_type"],
                "email": user_data["email"],
                "permissions": user_data["permissions"]
            }
            
            context = service.extract_user_context(token)
            
            assert isinstance(context, UserContext)
            assert context.user_id == user_data["user_id"]
            assert context.user_type == user_data["user_type"]
            assert context.email == user_data["email"]
            assert context.permissions == user_data["permissions"]


class TestPasswordService:
    """Test password service"""
    
    def test_hash_password(self):
        """Test password hashing"""
        password = "test_password_123"
        hashed = PasswordService.hash_password(password)
        
        assert isinstance(hashed, str)
        assert hashed != password
        assert len(hashed) > 50  # Bcrypt hashes are typically long
    
    def test_verify_password_correct(self):
        """Test password verification with correct password"""
        password = "test_password_123"
        hashed = PasswordService.hash_password(password)
        
        assert PasswordService.verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password"""
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = PasswordService.hash_password(password)
        
        assert PasswordService.verify_password(wrong_password, hashed) is False
    
    def test_generate_secure_token(self):
        """Test secure token generation"""
        token1 = PasswordService.generate_secure_token()
        token2 = PasswordService.generate_secure_token()
        
        assert isinstance(token1, str)
        assert isinstance(token2, str)
        assert token1 != token2  # Should be different
        assert len(token1) > 40  # URL-safe base64 of 32 bytes
    
    def test_generate_secure_token_custom_length(self):
        """Test secure token generation with custom length"""
        token = PasswordService.generate_secure_token(length=16)
        
        # URL-safe base64 encoding of 16 bytes should be around 22-24 characters
        assert len(token) >= 20
        assert len(token) <= 25


class TestUserContext:
    """Test user context"""
    
    @pytest.fixture
    def user_context(self):
        return UserContext(
            user_id=uuid4(),
            user_type="registered_user",
            email="test@example.com",
            permissions=["emergency:request", "group:manage"]
        )
    
    @pytest.fixture
    def firm_personnel_context(self):
        return UserContext(
            user_id=uuid4(),
            user_type="firm_personnel",
            email="agent@firm.com",
            permissions=["request:view", "request:accept"],
            firm_id=uuid4(),
            role="field_agent"
        )
    
    def test_has_permission_true(self, user_context):
        """Test permission check - user has permission"""
        assert user_context.has_permission("emergency:request") is True
    
    def test_has_permission_false(self, user_context):
        """Test permission check - user doesn't have permission"""
        assert user_context.has_permission("admin:manage") is False
    
    def test_is_registered_user(self, user_context):
        """Test registered user check"""
        assert user_context.is_registered_user() is True
        assert user_context.is_firm_personnel() is False
    
    def test_is_firm_personnel(self, firm_personnel_context):
        """Test firm personnel check"""
        assert firm_personnel_context.is_firm_personnel() is True
        assert firm_personnel_context.is_registered_user() is False


class TestAuthService:
    """Test main auth service"""
    
    @pytest.fixture
    def service(self):
        return AuthService()
    
    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, service):
        """Test successful user authentication"""
        email = "test@example.com"
        password = "test_password"
        
        token_pair = await service.authenticate_user(email, password)
        
        assert isinstance(token_pair, TokenPair)
        assert token_pair.access_token
        assert token_pair.refresh_token
    
    @pytest.mark.asyncio
    async def test_refresh_token_success(self, service):
        """Test successful token refresh"""
        # Create initial token pair
        original_pair = await service.authenticate_user("test@example.com", "password")
        
        with patch.object(service.jwt_service, 'refresh_access_token') as mock_refresh:
            mock_refresh.return_value = TokenPair("new_access", "new_refresh", 3600)
            
            new_pair = await service.refresh_token(original_pair.refresh_token)
            
            assert isinstance(new_pair, TokenPair)
            mock_refresh.assert_called_once_with(original_pair.refresh_token)
    
    @pytest.mark.asyncio
    async def test_revoke_token_success(self, service):
        """Test successful token revocation"""
        token = "test.jwt.token"
        
        with patch.object(service.jwt_service, 'revoke_token') as mock_revoke:
            mock_revoke.return_value = True
            
            result = await service.revoke_token(token)
            
            assert result is True
            mock_revoke.assert_called_once_with(token)
    
    @pytest.mark.asyncio
    async def test_validate_token_success(self, service):
        """Test successful token validation"""
        token = "test.jwt.token"
        
        with patch.object(service.jwt_service, 'extract_user_context') as mock_extract:
            mock_context = UserContext(
                user_id=uuid4(),
                user_type="registered_user",
                email="test@example.com"
            )
            mock_extract.return_value = mock_context
            
            context = await service.validate_token(token)
            
            assert context == mock_context
            mock_extract.assert_called_once_with(token)
    
    def test_get_user_permissions_registered_user(self, service):
        """Test getting permissions for registered user"""
        permissions = service._get_user_permissions("registered_user")
        
        expected = ["emergency:request", "subscription:purchase", "group:manage"]
        assert permissions == expected
    
    def test_get_user_permissions_firm_personnel(self, service):
        """Test getting permissions for firm personnel"""
        permissions = service._get_user_permissions("firm_personnel")
        
        expected = ["request:view", "request:accept", "team:manage"]
        assert permissions == expected
    
    def test_get_user_permissions_unknown(self, service):
        """Test getting permissions for unknown user type"""
        permissions = service._get_user_permissions("unknown_type")
        
        assert permissions == []


class TestTokenPair:
    """Test token pair class"""
    
    def test_token_pair_creation(self):
        """Test token pair creation"""
        access_token = "access.jwt.token"
        refresh_token = "refresh.jwt.token"
        expires_in = 3600
        
        token_pair = TokenPair(access_token, refresh_token, expires_in)
        
        assert token_pair.access_token == access_token
        assert token_pair.refresh_token == refresh_token
        assert token_pair.expires_in == expires_in
        assert token_pair.token_type == "Bearer"
    
    def test_token_pair_to_dict(self):
        """Test token pair dictionary conversion"""
        token_pair = TokenPair("access_token", "refresh_token", 3600)
        
        result = token_pair.to_dict()
        
        expected = {
            "access_token": "access_token",
            "refresh_token": "refresh_token",
            "token_type": "Bearer",
            "expires_in": 3600
        }
        
        assert result == expected