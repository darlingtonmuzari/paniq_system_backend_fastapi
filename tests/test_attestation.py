"""
Test mobile app attestation verification
"""
import pytest
import base64
import json
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.attestation import (
    AppAttestationService,
    GooglePlayIntegrityService,
    AppleAppAttestService,
    AttestationError
)


class TestGooglePlayIntegrityService:
    """Test Google Play Integrity verification"""
    
    @pytest.fixture
    def service(self):
        return GooglePlayIntegrityService()
    
    @pytest.fixture
    def mock_integrity_token(self):
        """Mock integrity token (JWT format)"""
        payload = {
            "requestDetails": {
                "requestPackageName": "com.panic.system",
                "nonce": "test_nonce_123",
                "timestampMillis": 1640995200000
            },
            "appIntegrity": {
                "appRecognitionVerdict": "PLAY_RECOGNIZED",
                "packageName": "com.panic.system",
                "certificateSha256Digest": ["abc123"],
                "versionCode": 1
            },
            "deviceIntegrity": {
                "deviceRecognitionVerdict": ["MEETS_DEVICE_INTEGRITY"]
            }
        }
        
        # Create a mock JWT token (without signature verification for testing)
        import jwt
        return jwt.encode(payload, "secret", algorithm="HS256")
    
    @pytest.mark.asyncio
    async def test_verify_integrity_token_success(self, service, mock_integrity_token):
        """Test successful integrity token verification"""
        with patch.object(service, '_decode_integrity_token') as mock_decode:
            mock_decode.return_value = {
                "requestDetails": {
                    "requestPackageName": "com.panic.system",
                    "nonce": "test_nonce"
                },
                "appIntegrity": {
                    "appRecognitionVerdict": "PLAY_RECOGNIZED"
                },
                "deviceIntegrity": {
                    "deviceRecognitionVerdict": ["MEETS_DEVICE_INTEGRITY"]
                }
            }
            
            result = await service.verify_integrity_token(mock_integrity_token, "test_nonce")
            
            assert result["verdict"] == "VALID"
            assert result["app_verdict"] == "PLAY_RECOGNIZED"
            assert "MEETS_DEVICE_INTEGRITY" in result["device_verdict"]
    
    @pytest.mark.asyncio
    async def test_verify_integrity_token_wrong_package(self, service, mock_integrity_token):
        """Test integrity token verification with wrong package name"""
        with patch.object(service, '_decode_integrity_token') as mock_decode:
            mock_decode.return_value = {
                "requestDetails": {
                    "requestPackageName": "com.wrong.package",
                    "nonce": "test_nonce"
                },
                "appIntegrity": {
                    "appRecognitionVerdict": "PLAY_RECOGNIZED"
                },
                "deviceIntegrity": {
                    "deviceRecognitionVerdict": ["MEETS_DEVICE_INTEGRITY"]
                }
            }
            
            with pytest.raises(AttestationError, match="Package name mismatch"):
                await service.verify_integrity_token(mock_integrity_token, "test_nonce")
    
    @pytest.mark.asyncio
    async def test_verify_integrity_token_unrecognized_app(self, service, mock_integrity_token):
        """Test integrity token verification with unrecognized app"""
        with patch.object(service, '_decode_integrity_token') as mock_decode:
            mock_decode.return_value = {
                "requestDetails": {
                    "requestPackageName": "com.panic.system",
                    "nonce": "test_nonce"
                },
                "appIntegrity": {
                    "appRecognitionVerdict": "UNKNOWN"
                },
                "deviceIntegrity": {
                    "deviceRecognitionVerdict": ["MEETS_DEVICE_INTEGRITY"]
                }
            }
            
            with pytest.raises(AttestationError, match="App not recognized"):
                await service.verify_integrity_token(mock_integrity_token, "test_nonce")
    
    @pytest.mark.asyncio
    async def test_verify_integrity_token_device_integrity_fail(self, service, mock_integrity_token):
        """Test integrity token verification with device integrity failure"""
        with patch.object(service, '_decode_integrity_token') as mock_decode:
            mock_decode.return_value = {
                "requestDetails": {
                    "requestPackageName": "com.panic.system",
                    "nonce": "test_nonce"
                },
                "appIntegrity": {
                    "appRecognitionVerdict": "PLAY_RECOGNIZED"
                },
                "deviceIntegrity": {
                    "deviceRecognitionVerdict": ["MEETS_VIRTUAL_INTEGRITY"]
                }
            }
            
            with pytest.raises(AttestationError, match="Device integrity check failed"):
                await service.verify_integrity_token(mock_integrity_token, "test_nonce")


class TestAppleAppAttestService:
    """Test Apple App Attest verification"""
    
    @pytest.fixture
    def service(self):
        return AppleAppAttestService()
    
    @pytest.fixture
    def mock_attestation_object(self):
        """Mock attestation object"""
        return base64.b64encode(b"mock_attestation_data").decode('utf-8')
    
    @pytest.fixture
    def mock_assertion(self):
        """Mock assertion"""
        return base64.b64encode(b"mock_assertion_data").decode('utf-8')
    
    @pytest.mark.asyncio
    async def test_verify_attestation_success(self, service, mock_attestation_object):
        """Test successful attestation verification"""
        with patch.object(service, '_parse_attestation_object') as mock_parse, \
             patch.object(service, '_verify_attestation_object') as mock_verify:
            
            mock_parse.return_value = {"fmt": "apple-appattest"}
            mock_verify.return_value = {"verdict": "VALID", "key_id": "test_key_123"}
            
            result = await service.verify_attestation(
                mock_attestation_object, "test_key_123", "test_challenge"
            )
            
            assert result["verdict"] == "VALID"
            assert result["key_id"] == "test_key_123"
    
    @pytest.mark.asyncio
    async def test_verify_assertion_success(self, service, mock_assertion):
        """Test successful assertion verification"""
        with patch.object(service, '_verify_assertion_data') as mock_verify:
            mock_verify.return_value = {
                "verdict": "VALID",
                "key_id": "test_key_123",
                "counter": 1
            }
            
            result = await service.verify_assertion(
                mock_assertion, "test_key_123", "test_client_data_hash"
            )
            
            assert result["verdict"] == "VALID"
            assert result["counter"] == 1
    
    @pytest.mark.asyncio
    async def test_verify_attestation_invalid_key_id(self, service, mock_attestation_object):
        """Test attestation verification with invalid key ID"""
        with patch.object(service, '_parse_attestation_object') as mock_parse:
            mock_parse.return_value = {"fmt": "apple-appattest"}
            
            with pytest.raises(AttestationError, match="Invalid key ID format"):
                await service.verify_attestation(
                    mock_attestation_object, "short", "test_challenge"
                )
    
    @pytest.mark.asyncio
    async def test_verify_attestation_invalid_challenge(self, service, mock_attestation_object):
        """Test attestation verification with invalid challenge"""
        with patch.object(service, '_parse_attestation_object') as mock_parse:
            mock_parse.return_value = {"fmt": "apple-appattest"}
            
            with pytest.raises(AttestationError, match="Invalid challenge format"):
                await service.verify_attestation(
                    mock_attestation_object, "test_key_123456", "short"
                )


class TestAppAttestationService:
    """Test main app attestation service"""
    
    @pytest.fixture
    def service(self):
        return AppAttestationService()
    
    @pytest.mark.asyncio
    async def test_verify_android_integrity_success(self, service):
        """Test successful Android integrity verification"""
        with patch.object(service.google_service, 'verify_integrity_token') as mock_verify:
            mock_verify.return_value = {"verdict": "VALID"}
            
            result = await service.verify_android_integrity("mock_token", "nonce")
            
            assert result is True
            mock_verify.assert_called_once_with("mock_token", "nonce")
    
    @pytest.mark.asyncio
    async def test_verify_android_integrity_failure(self, service):
        """Test Android integrity verification failure"""
        with patch.object(service.google_service, 'verify_integrity_token') as mock_verify:
            mock_verify.side_effect = AttestationError("Verification failed")
            
            with pytest.raises(AttestationError):
                await service.verify_android_integrity("mock_token")
    
    @pytest.mark.asyncio
    async def test_verify_ios_attestation_success(self, service):
        """Test successful iOS attestation verification"""
        with patch.object(service.apple_service, 'verify_attestation') as mock_verify:
            mock_verify.return_value = {"verdict": "VALID"}
            
            result = await service.verify_ios_attestation(
                "mock_attestation", "key_123", "challenge"
            )
            
            assert result is True
            mock_verify.assert_called_once_with("mock_attestation", "key_123", "challenge")
    
    @pytest.mark.asyncio
    async def test_verify_ios_assertion_success(self, service):
        """Test successful iOS assertion verification"""
        with patch.object(service.apple_service, 'verify_assertion') as mock_verify:
            mock_verify.return_value = {"verdict": "VALID"}
            
            result = await service.verify_ios_assertion(
                "mock_assertion", "key_123", "client_hash"
            )
            
            assert result is True
            mock_verify.assert_called_once_with("mock_assertion", "key_123", "client_hash")
    
    def test_generate_challenge(self, service):
        """Test challenge generation"""
        challenge = service.generate_challenge()
        
        assert isinstance(challenge, str)
        assert len(challenge) > 40  # Base64 encoded 32 bytes should be longer
        
        # Generate another challenge to ensure they're different
        challenge2 = service.generate_challenge()
        assert challenge != challenge2
    
    def test_create_client_data_hash(self, service):
        """Test client data hash creation"""
        request_data = {
            "endpoint": "/api/v1/emergency/request",
            "method": "POST",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
        hash1 = service.create_client_data_hash(request_data)
        hash2 = service.create_client_data_hash(request_data)
        
        # Same data should produce same hash
        assert hash1 == hash2
        
        # Different data should produce different hash
        request_data["timestamp"] = "2024-01-01T00:01:00Z"
        hash3 = service.create_client_data_hash(request_data)
        assert hash1 != hash3