"""
Test main application setup
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "panic-system-platform"}


def test_api_root():
    """Test API root endpoint"""
    response = client.get("/api/v1/")
    assert response.status_code == 200
    assert response.json() == {"message": "Panic System Platform API v1"}