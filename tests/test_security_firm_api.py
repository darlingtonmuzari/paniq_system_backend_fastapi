"""
Tests for security firm registration API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import Mock, patch, AsyncMock
import json

from app.main import app
from app.models.security_firm import SecurityFirm, CoverageArea
from app.services.security_firm import SecurityFirmService


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


@pytest.fixture
def mock_db():
    """Mock database session"""
    return Mock(spec=AsyncSession)


@pytest.fixture
def sample_firm_data():
    """Sample security firm registration data"""
    return {
        "name": "Elite Security Services",
        "registration_number": "ESS-2024-001",
        "email": "contact@elitesecurity.com",
        "phone": "+1-555-012-3456",
        "address": "123 Security Street, Safety City, SC 12345"
    }


@pytest.fixture
def sample_coverage_area():
    """Sample coverage area data"""
    return {
        "name": "Downtown District",
        "boundary_coordinates": [
            [-74.0059, 40.7128],  # NYC coordinates as example
            [-74.0059, 40.7228],
            [-73.9959, 40.7228],
            [-73.9959, 40.7128],
            [-74.0059, 40.7128]   # Close the polygon
        ]
    }


class TestSecurityFirmRegistration:
    """Test security firm registration endpoints"""
    
    def test_register_security_firm_success(self, client, sample_firm_data):
        """Test successful security firm registration"""
        with patch('app.api.v1.security_firms.SecurityFirmService') as mock_service_class:
            # Mock the service
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock the register_firm method
            mock_firm = Mock()
            mock_firm.id = "123e4567-e89b-12d3-a456-426614174000"
            mock_firm.name = sample_firm_data["name"]
            mock_firm.registration_number = sample_firm_data["registration_number"]
            mock_firm.email = sample_firm_data["email"]
            mock_firm.phone = sample_firm_data["phone"]
            mock_firm.address = sample_firm_data["address"]
            mock_firm.verification_status = "pending"
            mock_firm.credit_balance = 0
            mock_firm.is_locked = False
            mock_firm.created_at = "2024-01-01T00:00:00"
            
            mock_service.register_firm = AsyncMock(return_value=mock_firm)
            
            # Make request
            response = client.post("/api/v1/security-firms/register", json=sample_firm_data)
            
            # Assertions
            if response.status_code != 200:
                print(f"Response: {response.json()}")
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == sample_firm_data["name"]
            assert data["registration_number"] == sample_firm_data["registration_number"]
            assert data["email"] == sample_firm_data["email"]
            assert data["verification_status"] == "pending"
            
            # Verify service was called correctly
            mock_service.register_firm.assert_called_once_with(
                name=sample_firm_data["name"],
                registration_number=sample_firm_data["registration_number"],
                email=sample_firm_data["email"],
                phone=sample_firm_data["phone"],
                address=sample_firm_data["address"]
            )
    
    def test_register_security_firm_duplicate_registration(self, client, sample_firm_data):
        """Test registration with duplicate registration number"""
        with patch('app.api.v1.security_firms.SecurityFirmService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock service to raise ValueError for duplicate
            mock_service.register_firm = AsyncMock(
                side_effect=ValueError("Security firm with this registration number or email already exists")
            )
            
            response = client.post("/api/v1/security-firms/register", json=sample_firm_data)
            
            assert response.status_code == 400
            assert "already exists" in response.json()["message"]
    
    def test_register_security_firm_invalid_data(self, client):
        """Test registration with invalid data"""
        invalid_data = {
            "name": "A",  # Too short
            "registration_number": "AB",  # Too short
            "email": "invalid-email",  # Invalid email
            "phone": "123",  # Too short
            "address": ""  # Empty
        }
        
        response = client.post("/api/v1/security-firms/register", json=invalid_data)
        assert response.status_code == 422  # Validation error
    
    def test_register_security_firm_missing_fields(self, client):
        """Test registration with missing required fields"""
        incomplete_data = {
            "name": "Test Security"
            # Missing other required fields
        }
        
        response = client.post("/api/v1/security-firms/register", json=incomplete_data)
        assert response.status_code == 422


class TestSecurityFirmVerification:
    """Test security firm verification endpoints"""
    
    @patch('app.core.auth.require_admin')
    def test_get_pending_firms_success(self, mock_auth, client):
        """Test getting pending firms for admin review"""
        # Mock authentication
        mock_user = Mock()
        mock_user.user_type = "admin"
        mock_auth.return_value = mock_user
        
        with patch('app.api.v1.security_firms.SecurityFirmService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock pending firms
            mock_firm = Mock()
            mock_firm.id = "123e4567-e89b-12d3-a456-426614174000"
            mock_firm.name = "Test Security"
            mock_firm.verification_status = "pending"
            mock_firm.created_at = "2024-01-01T00:00:00"
            
            mock_service.get_pending_firms = AsyncMock(return_value=[mock_firm])
            
            response = client.get("/api/v1/security-firms/pending")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["verification_status"] == "pending"
    
    @patch('app.core.auth.require_admin')
    def test_verify_security_firm_approve(self, mock_auth, client):
        """Test approving a security firm"""
        mock_user = Mock()
        mock_user.user_type = "admin"
        mock_auth.return_value = mock_user
        
        firm_id = "123e4567-e89b-12d3-a456-426614174000"
        verification_data = {
            "verification_status": "approved"
        }
        
        with patch('app.api.v1.security_firms.SecurityFirmService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            mock_firm = Mock()
            mock_firm.id = firm_id
            mock_firm.verification_status = "approved"
            mock_firm.created_at = "2024-01-01T00:00:00"
            
            mock_service.verify_firm = AsyncMock(return_value=mock_firm)
            
            response = client.put(
                f"/api/v1/security-firms/{firm_id}/verify",
                json=verification_data
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["verification_status"] == "approved"
            
            mock_service.verify_firm.assert_called_once_with(
                firm_id=firm_id,
                verification_status="approved",
                rejection_reason=None
            )
    
    @patch('app.core.auth.require_admin')
    def test_verify_security_firm_reject(self, mock_auth, client):
        """Test rejecting a security firm"""
        mock_user = Mock()
        mock_user.user_type = "admin"
        mock_auth.return_value = mock_user
        
        firm_id = "123e4567-e89b-12d3-a456-426614174000"
        verification_data = {
            "verification_status": "rejected",
            "rejection_reason": "Incomplete documentation"
        }
        
        with patch('app.api.v1.security_firms.SecurityFirmService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            mock_firm = Mock()
            mock_firm.id = firm_id
            mock_firm.verification_status = "rejected"
            
            mock_service.verify_firm = AsyncMock(return_value=mock_firm)
            
            response = client.put(
                f"/api/v1/security-firms/{firm_id}/verify",
                json=verification_data
            )
            
            assert response.status_code == 200
            mock_service.verify_firm.assert_called_once_with(
                firm_id=firm_id,
                verification_status="rejected",
                rejection_reason="Incomplete documentation"
            )


class TestCoverageAreas:
    """Test coverage area management endpoints"""
    
    @patch('app.core.auth.get_current_user')
    def test_create_coverage_area_success(self, mock_auth, client, sample_coverage_area):
        """Test successful coverage area creation"""
        mock_user = Mock()
        mock_user.id = "user123"
        mock_auth.return_value = mock_user
        
        firm_id = "123e4567-e89b-12d3-a456-426614174000"
        
        with patch('app.api.v1.security_firms.SecurityFirmService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock coverage area
            mock_coverage_area = Mock()
            mock_coverage_area.id = "area123"
            mock_coverage_area.name = sample_coverage_area["name"]
            mock_coverage_area.created_at = "2024-01-01T00:00:00"
            
            # Mock the geometry conversion
            with patch('geoalchemy2.shape.to_shape') as mock_to_shape:
                mock_polygon = Mock()
                mock_polygon.exterior.coords = sample_coverage_area["boundary_coordinates"]
                mock_to_shape.return_value = mock_polygon
                
                mock_coverage_area.boundary = Mock()  # Mock geometry object
                
                mock_service.create_coverage_area = AsyncMock(return_value=mock_coverage_area)
                
                response = client.post(
                    f"/api/v1/security-firms/{firm_id}/coverage-areas",
                    json=sample_coverage_area
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["name"] == sample_coverage_area["name"]
                assert data["boundary_coordinates"] == sample_coverage_area["boundary_coordinates"]
    
    @patch('app.core.auth.get_current_user')
    def test_create_coverage_area_invalid_polygon(self, mock_auth, client):
        """Test coverage area creation with invalid polygon"""
        mock_user = Mock()
        mock_user.id = "user123"
        mock_auth.return_value = mock_user
        
        firm_id = "123e4567-e89b-12d3-a456-426614174000"
        invalid_area = {
            "name": "Invalid Area",
            "boundary_coordinates": [
                [-74.0059, 40.7128],  # Only 2 points - invalid polygon
                [-74.0059, 40.7228]
            ]
        }
        
        response = client.post(
            f"/api/v1/security-firms/{firm_id}/coverage-areas",
            json=invalid_area
        )
        
        assert response.status_code == 422  # Validation error
    
    @patch('app.core.auth.get_current_user')
    def test_get_coverage_areas_success(self, mock_auth, client):
        """Test getting coverage areas for a firm"""
        mock_user = Mock()
        mock_user.id = "user123"
        mock_auth.return_value = mock_user
        
        firm_id = "123e4567-e89b-12d3-a456-426614174000"
        
        with patch('app.api.v1.security_firms.SecurityFirmService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            # Mock coverage areas
            mock_area = Mock()
            mock_area.id = "area123"
            mock_area.name = "Test Area"
            mock_area.created_at = "2024-01-01T00:00:00"
            
            with patch('geoalchemy2.shape.to_shape') as mock_to_shape:
                mock_polygon = Mock()
                mock_polygon.exterior.coords = [[-74.0059, 40.7128], [-74.0059, 40.7228]]
                mock_to_shape.return_value = mock_polygon
                
                mock_area.boundary = Mock()
                
                mock_service.get_coverage_areas = AsyncMock(return_value=[mock_area])
                
                response = client.get(f"/api/v1/security-firms/{firm_id}/coverage-areas")
                
                assert response.status_code == 200
                data = response.json()
                assert len(data) == 1
                assert data[0]["name"] == "Test Area"


class TestDocumentUpload:
    """Test document upload functionality"""
    
    @patch('app.core.auth.get_current_user')
    def test_upload_document_success(self, mock_auth, client):
        """Test successful document upload"""
        mock_user = Mock()
        mock_user.id = "user123"
        mock_auth.return_value = mock_user
        
        firm_id = "123e4567-e89b-12d3-a456-426614174000"
        
        with patch('app.api.v1.security_firms.SecurityFirmService') as mock_service_class:
            mock_service = Mock()
            mock_service_class.return_value = mock_service
            
            mock_service.upload_verification_document = AsyncMock(
                return_value="uploads/security_firms/test_document.pdf"
            )
            
            # Create a mock file
            test_file = ("test_document.pdf", b"fake pdf content", "application/pdf")
            
            response = client.post(
                f"/api/v1/security-firms/{firm_id}/documents",
                files={"file": test_file}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "document_url" in data
            assert "successfully" in data["message"]
    
    @patch('app.core.auth.get_current_user')
    def test_upload_document_invalid_type(self, mock_auth, client):
        """Test document upload with invalid file type"""
        mock_user = Mock()
        mock_user.id = "user123"
        mock_auth.return_value = mock_user
        
        firm_id = "123e4567-e89b-12d3-a456-426614174000"
        
        # Create a mock file with invalid type
        test_file = ("test_document.txt", b"fake text content", "text/plain")
        
        response = client.post(
            f"/api/v1/security-firms/{firm_id}/documents",
            files={"file": test_file}
        )
        
        assert response.status_code == 400
        assert "Only PDF, JPEG, and PNG files are allowed" in response.json()["detail"]