"""
Test middleware functionality
"""
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.core.middleware import MobileAttestationMiddleware, RequestLoggingMiddleware
from app.services.attestation import AttestationError


class TestMobileAttestationMiddleware:
    """Test mobile attestation middleware"""
    
    @pytest.fixture
    def app(self):
        """Create test FastAPI app with middleware"""
        app = FastAPI()
        app.add_middleware(MobileAttestationMiddleware)
        
        @app.get("/api/v1/mobile/test")
        async def mobile_endpoint():
            return {"message": "success"}
        
        @app.get("/api/v1/public/test")
        async def public_endpoint():
            return {"message": "public"}
        
        @app.get("/health")
        async def health_endpoint():
            return {"status": "healthy"}
        
        return app
    
    @pytest.fixture
    def client(self, app):
        return TestClient(app)
    
    def test_public_endpoint_no_attestation_required(self, client):
        """Test that public endpoints don't require attestation"""
        response = client.get("/api/v1/public/test")
        assert response.status_code == 200
        assert response.json() == {"message": "public"}
    
    def test_health_endpoint_exempt(self, client):
        """Test that health endpoint is exempt from attestation"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}
    
    def test_mobile_endpoint_requires_attestation(self, client):
        """Test that mobile endpoints require attestation"""
        response = client.get("/api/v1/mobile/test")
        assert response.status_code == 401
        assert "attestation" in response.json()["message"].lower()
    
    def test_mobile_endpoint_missing_platform_header(self, client):
        """Test mobile endpoint with missing platform header"""
        response = client.get("/api/v1/mobile/test")
        assert response.status_code == 401
        assert "platform" in response.json()["message"].lower()
    
    @patch('app.services.attestation.attestation_service.verify_android_integrity')
    def test_android_attestation_success(self, mock_verify, client):
        """Test successful Android attestation"""
        mock_verify.return_value = True
        
        headers = {
            "X-Platform": "android",
            "X-Integrity-Token": "mock_integrity_token"
        }
        
        response = client.get("/api/v1/mobile/test", headers=headers)
        assert response.status_code == 200
        assert response.json() == {"message": "success"}
    
    @patch('app.services.attestation.attestation_service.verify_android_integrity')
    def test_android_attestation_failure(self, mock_verify, client):
        """Test Android attestation failure"""
        mock_verify.side_effect = AttestationError("Verification failed")
        
        headers = {
            "X-Platform": "android",
            "X-Integrity-Token": "invalid_token"
        }
        
        response = client.get("/api/v1/mobile/test", headers=headers)
        assert response.status_code == 401
        assert "attestation" in response.json()["message"].lower()
    
    def test_android_missing_integrity_token(self, client):
        """Test Android request with missing integrity token"""
        headers = {"X-Platform": "android"}
        
        response = client.get("/api/v1/mobile/test", headers=headers)
        assert response.status_code == 401
        assert "integrity token" in response.json()["details"]["reason"].lower()
    
    @patch('app.services.attestation.attestation_service.verify_ios_attestation')
    def test_ios_attestation_success(self, mock_verify, client):
        """Test successful iOS attestation"""
        mock_verify.return_value = True
        
        headers = {
            "X-Platform": "ios",
            "X-Attestation-Object": "mock_attestation_object",
            "X-Key-ID": "mock_key_id",
            "X-Challenge": "mock_challenge"
        }
        
        response = client.get("/api/v1/mobile/test", headers=headers)
        assert response.status_code == 200
        assert response.json() == {"message": "success"}
    
    @patch('app.services.attestation.attestation_service.verify_ios_assertion')
    def test_ios_assertion_success(self, mock_verify, client):
        """Test successful iOS assertion"""
        mock_verify.return_value = True
        
        headers = {
            "X-Platform": "ios",
            "X-Assertion": "mock_assertion",
            "X-Key-ID": "mock_key_id",
            "X-Client-Data-Hash": "mock_hash"
        }
        
        response = client.get("/api/v1/mobile/test", headers=headers)
        assert response.status_code == 200
        assert response.json() == {"message": "success"}
    
    def test_ios_missing_attestation_data(self, client):
        """Test iOS request with missing attestation data"""
        headers = {"X-Platform": "ios"}
        
        response = client.get("/api/v1/mobile/test", headers=headers)
        assert response.status_code == 401
        assert "attestation data" in response.json()["details"]["reason"].lower()


class TestRequestLoggingMiddleware:
    """Test request logging middleware"""
    
    @pytest.fixture
    def app(self):
        """Create test FastAPI app with logging middleware"""
        app = FastAPI()
        app.add_middleware(RequestLoggingMiddleware)
        
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        
        @app.get("/error")
        async def error_endpoint():
            raise Exception("Test error")
        
        return app
    
    @pytest.fixture
    def client(self, app):
        return TestClient(app)
    
    def test_request_logging_success(self, client):
        """Test successful request logging"""
        response = client.get("/test")
        
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
        assert "X-Process-Time" in response.headers
        
        # Verify request ID is a valid UUID format
        request_id = response.headers["X-Request-ID"]
        assert len(request_id) == 36  # UUID length with hyphens
        assert request_id.count("-") == 4  # UUID has 4 hyphens
    
    def test_request_logging_error(self, client):
        """Test request logging with error"""
        with pytest.raises(Exception):
            client.get("/error")
    
    def test_process_time_header(self, client):
        """Test that process time header is added"""
        response = client.get("/test")
        
        process_time = float(response.headers["X-Process-Time"])
        assert process_time >= 0
        assert process_time < 1.0  # Should be very fast for simple endpoint