"""
Tests for SecurityFirmService
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from geoalchemy2.shape import from_shape
from shapely.geometry import Polygon

from app.services.security_firm import SecurityFirmService
from app.models.security_firm import SecurityFirm, CoverageArea


@pytest.fixture
def mock_db():
    """Mock database session"""
    return Mock(spec=AsyncSession)


@pytest.fixture
def security_firm_service(mock_db):
    """SecurityFirmService instance with mocked database"""
    return SecurityFirmService(mock_db)


@pytest.fixture
def sample_firm():
    """Sample security firm"""
    firm = Mock(spec=SecurityFirm)
    firm.id = "123e4567-e89b-12d3-a456-426614174000"
    firm.name = "Elite Security Services"
    firm.registration_number = "ESS-2024-001"
    firm.email = "contact@elitesecurity.com"
    firm.phone = "+1-555-0123"
    firm.address = "123 Security Street, Safety City, SC 12345"
    firm.verification_status = "pending"
    firm.credit_balance = 0
    return firm


class TestSecurityFirmRegistration:
    """Test security firm registration functionality"""
    
    @pytest.mark.asyncio
    async def test_register_firm_success(self, security_firm_service, mock_db):
        """Test successful firm registration"""
        # Mock database query to return no existing firm
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.add = Mock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Test data
        name = "Elite Security Services"
        registration_number = "ESS-2024-001"
        email = "contact@elitesecurity.com"
        phone = "+1-555-0123"
        address = "123 Security Street, Safety City, SC 12345"
        
        # Call the method
        result = await security_firm_service.register_firm(
            name=name,
            registration_number=registration_number,
            email=email,
            phone=phone,
            address=address
        )
        
        # Assertions
        mock_db.execute.assert_called_once()
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
        
        # Verify the created firm has correct attributes
        added_firm = mock_db.add.call_args[0][0]
        assert added_firm.name == name
        assert added_firm.registration_number == registration_number
        assert added_firm.email == email
        assert added_firm.phone == phone
        assert added_firm.address == address
        assert added_firm.verification_status == "pending"
        assert added_firm.credit_balance == 0
    
    @pytest.mark.asyncio
    async def test_register_firm_duplicate_registration_number(self, security_firm_service, mock_db):
        """Test registration with duplicate registration number"""
        # Mock database query to return existing firm
        existing_firm = Mock(spec=SecurityFirm)
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = existing_firm
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Test data
        name = "Elite Security Services"
        registration_number = "ESS-2024-001"
        email = "contact@elitesecurity.com"
        phone = "+1-555-0123"
        address = "123 Security Street, Safety City, SC 12345"
        
        # Call the method and expect ValueError
        with pytest.raises(ValueError, match="already exists"):
            await security_firm_service.register_firm(
                name=name,
                registration_number=registration_number,
                email=email,
                phone=phone,
                address=address
            )
        
        # Verify no firm was added
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_pending_firms(self, security_firm_service, mock_db):
        """Test getting pending firms"""
        # Mock database query
        mock_firm1 = Mock(spec=SecurityFirm)
        mock_firm1.verification_status = "pending"
        mock_firm2 = Mock(spec=SecurityFirm)
        mock_firm2.verification_status = "pending"
        
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_firm1, mock_firm2]
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Call the method
        result = await security_firm_service.get_pending_firms()
        
        # Assertions
        assert len(result) == 2
        assert all(firm.verification_status == "pending" for firm in result)
        mock_db.execute.assert_called_once()


class TestSecurityFirmVerification:
    """Test security firm verification functionality"""
    
    @pytest.mark.asyncio
    async def test_verify_firm_approve(self, security_firm_service, mock_db, sample_firm):
        """Test approving a security firm"""
        # Mock database get
        sample_firm.verification_status = "pending"
        mock_db.get = AsyncMock(return_value=sample_firm)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        firm_id = "123e4567-e89b-12d3-a456-426614174000"
        
        # Call the method
        result = await security_firm_service.verify_firm(
            firm_id=firm_id,
            verification_status="approved"
        )
        
        # Assertions
        assert sample_firm.verification_status == "approved"
        mock_db.get.assert_called_once_with(SecurityFirm, firm_id)
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(sample_firm)
    
    @pytest.mark.asyncio
    async def test_verify_firm_reject(self, security_firm_service, mock_db, sample_firm):
        """Test rejecting a security firm"""
        # Mock database get
        sample_firm.verification_status = "pending"
        mock_db.get = AsyncMock(return_value=sample_firm)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        firm_id = "123e4567-e89b-12d3-a456-426614174000"
        
        # Call the method
        result = await security_firm_service.verify_firm(
            firm_id=firm_id,
            verification_status="rejected",
            rejection_reason="Incomplete documentation"
        )
        
        # Assertions
        assert sample_firm.verification_status == "rejected"
        mock_db.get.assert_called_once_with(SecurityFirm, firm_id)
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_verify_firm_not_found(self, security_firm_service, mock_db):
        """Test verifying non-existent firm"""
        # Mock database get to return None
        mock_db.get = AsyncMock(return_value=None)
        
        firm_id = "nonexistent-id"
        
        # Call the method and expect ValueError
        with pytest.raises(ValueError, match="not found"):
            await security_firm_service.verify_firm(
                firm_id=firm_id,
                verification_status="approved"
            )
    
    @pytest.mark.asyncio
    async def test_verify_firm_already_processed(self, security_firm_service, mock_db, sample_firm):
        """Test verifying already processed firm"""
        # Mock database get
        sample_firm.verification_status = "approved"  # Already processed
        mock_db.get = AsyncMock(return_value=sample_firm)
        
        firm_id = "123e4567-e89b-12d3-a456-426614174000"
        
        # Call the method and expect ValueError
        with pytest.raises(ValueError, match="already been processed"):
            await security_firm_service.verify_firm(
                firm_id=firm_id,
                verification_status="approved"
            )


class TestCoverageAreaManagement:
    """Test coverage area management functionality"""
    
    @pytest.mark.asyncio
    async def test_create_coverage_area_success(self, security_firm_service, mock_db, sample_firm):
        """Test successful coverage area creation"""
        # Mock approved firm
        sample_firm.verification_status = "approved"
        mock_db.get = AsyncMock(return_value=sample_firm)
        mock_db.add = Mock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        firm_id = "123e4567-e89b-12d3-a456-426614174000"
        user_id = "user123"
        name = "Downtown District"
        boundary_coordinates = [
            [-74.0059, 40.7128],
            [-74.0059, 40.7228],
            [-73.9959, 40.7228],
            [-73.9959, 40.7128],
            [-74.0059, 40.7128]
        ]
        
        # Call the method
        result = await security_firm_service.create_coverage_area(
            firm_id=firm_id,
            name=name,
            boundary_coordinates=boundary_coordinates,
            user_id=user_id
        )
        
        # Assertions
        mock_db.get.assert_called_once_with(SecurityFirm, firm_id)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
        
        # Verify the created coverage area
        added_area = mock_db.add.call_args[0][0]
        assert added_area.firm_id == firm_id
        assert added_area.name == name
    
    @pytest.mark.asyncio
    async def test_create_coverage_area_firm_not_found(self, security_firm_service, mock_db):
        """Test coverage area creation with non-existent firm"""
        # Mock database get to return None
        mock_db.get = AsyncMock(return_value=None)
        
        firm_id = "nonexistent-id"
        user_id = "user123"
        name = "Test Area"
        boundary_coordinates = [[-74.0059, 40.7128], [-74.0059, 40.7228], [-73.9959, 40.7228]]
        
        # Call the method and expect ValueError
        with pytest.raises(ValueError, match="not found"):
            await security_firm_service.create_coverage_area(
                firm_id=firm_id,
                name=name,
                boundary_coordinates=boundary_coordinates,
                user_id=user_id
            )
    
    @pytest.mark.asyncio
    async def test_create_coverage_area_firm_not_approved(self, security_firm_service, mock_db, sample_firm):
        """Test coverage area creation with unapproved firm"""
        # Mock pending firm
        sample_firm.verification_status = "pending"
        mock_db.get = AsyncMock(return_value=sample_firm)
        
        firm_id = "123e4567-e89b-12d3-a456-426614174000"
        user_id = "user123"
        name = "Test Area"
        boundary_coordinates = [[-74.0059, 40.7128], [-74.0059, 40.7228], [-73.9959, 40.7228]]
        
        # Call the method and expect ValueError
        with pytest.raises(ValueError, match="must be approved"):
            await security_firm_service.create_coverage_area(
                firm_id=firm_id,
                name=name,
                boundary_coordinates=boundary_coordinates,
                user_id=user_id
            )
    
    @pytest.mark.asyncio
    async def test_create_coverage_area_invalid_polygon(self, security_firm_service, mock_db, sample_firm):
        """Test coverage area creation with invalid polygon"""
        # Mock approved firm
        sample_firm.verification_status = "approved"
        mock_db.get = AsyncMock(return_value=sample_firm)
        
        firm_id = "123e4567-e89b-12d3-a456-426614174000"
        user_id = "user123"
        name = "Test Area"
        boundary_coordinates = [[-74.0059, 40.7128]]  # Invalid - only one point
        
        # Call the method and expect ValueError
        with pytest.raises(ValueError, match="Invalid polygon"):
            await security_firm_service.create_coverage_area(
                firm_id=firm_id,
                name=name,
                boundary_coordinates=boundary_coordinates,
                user_id=user_id
            )
    
    @pytest.mark.asyncio
    async def test_get_coverage_areas(self, security_firm_service, mock_db, sample_firm):
        """Test getting coverage areas for a firm"""
        # Mock firm
        mock_db.get = AsyncMock(return_value=sample_firm)
        
        # Mock coverage areas
        mock_area1 = Mock(spec=CoverageArea)
        mock_area1.firm_id = sample_firm.id
        mock_area2 = Mock(spec=CoverageArea)
        mock_area2.firm_id = sample_firm.id
        
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_area1, mock_area2]
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        firm_id = "123e4567-e89b-12d3-a456-426614174000"
        user_id = "user123"
        
        # Call the method
        result = await security_firm_service.get_coverage_areas(firm_id, user_id)
        
        # Assertions
        assert len(result) == 2
        mock_db.get.assert_called_once_with(SecurityFirm, firm_id)
        mock_db.execute.assert_called_once()


class TestCreditManagement:
    """Test credit management functionality"""
    
    @pytest.mark.asyncio
    async def test_update_credit_balance_add_credits(self, security_firm_service, mock_db, sample_firm):
        """Test adding credits to firm balance"""
        # Mock firm with initial balance
        sample_firm.credit_balance = 100
        mock_db.get = AsyncMock(return_value=sample_firm)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        firm_id = "123e4567-e89b-12d3-a456-426614174000"
        credit_amount = 50
        
        # Call the method
        result = await security_firm_service.update_credit_balance(firm_id, credit_amount)
        
        # Assertions
        assert sample_firm.credit_balance == 150
        mock_db.get.assert_called_once_with(SecurityFirm, firm_id)
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_credit_balance_deduct_credits(self, security_firm_service, mock_db, sample_firm):
        """Test deducting credits from firm balance"""
        # Mock firm with sufficient balance
        sample_firm.credit_balance = 100
        mock_db.get = AsyncMock(return_value=sample_firm)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        firm_id = "123e4567-e89b-12d3-a456-426614174000"
        credit_amount = -30
        
        # Call the method
        result = await security_firm_service.update_credit_balance(firm_id, credit_amount)
        
        # Assertions
        assert sample_firm.credit_balance == 70
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_credit_balance_insufficient_credits(self, security_firm_service, mock_db, sample_firm):
        """Test deducting more credits than available"""
        # Mock firm with insufficient balance
        sample_firm.credit_balance = 10
        mock_db.get = AsyncMock(return_value=sample_firm)
        
        firm_id = "123e4567-e89b-12d3-a456-426614174000"
        credit_amount = -50  # More than available
        
        # Call the method and expect ValueError
        with pytest.raises(ValueError, match="Insufficient credits"):
            await security_firm_service.update_credit_balance(firm_id, credit_amount)
    
    @pytest.mark.asyncio
    async def test_update_credit_balance_firm_not_found(self, security_firm_service, mock_db):
        """Test updating credits for non-existent firm"""
        # Mock database get to return None
        mock_db.get = AsyncMock(return_value=None)
        
        firm_id = "nonexistent-id"
        credit_amount = 50
        
        # Call the method and expect ValueError
        with pytest.raises(ValueError, match="not found"):
            await security_firm_service.update_credit_balance(firm_id, credit_amount)


class TestDocumentUpload:
    """Test document upload functionality"""
    
    @pytest.mark.asyncio
    async def test_upload_verification_document_success(self, security_firm_service, mock_db, sample_firm):
        """Test successful document upload"""
        # Mock firm
        mock_db.get = AsyncMock(return_value=sample_firm)
        
        # Mock file
        mock_file = Mock()
        mock_file.filename = "test_document.pdf"
        mock_file.read = AsyncMock(return_value=b"fake pdf content")
        
        firm_id = "123e4567-e89b-12d3-a456-426614174000"
        user_id = "user123"
        
        # Mock file operations
        with patch('os.makedirs') as mock_makedirs, \
             patch('builtins.open', create=True) as mock_open, \
             patch('uuid.uuid4') as mock_uuid:
            
            mock_uuid.return_value = "unique-id"
            mock_file_handle = Mock()
            mock_open.return_value.__enter__.return_value = mock_file_handle
            
            # Call the method
            result = await security_firm_service.upload_verification_document(
                firm_id=firm_id,
                file=mock_file,
                user_id=user_id
            )
            
            # Assertions
            assert "uploads/security_firms" in result
            assert "unique-id.pdf" in result
            mock_makedirs.assert_called_once()
            mock_file_handle.write.assert_called_once_with(b"fake pdf content")
    
    @pytest.mark.asyncio
    async def test_upload_verification_document_firm_not_found(self, security_firm_service, mock_db):
        """Test document upload for non-existent firm"""
        # Mock database get to return None
        mock_db.get = AsyncMock(return_value=None)
        
        mock_file = Mock()
        firm_id = "nonexistent-id"
        user_id = "user123"
        
        # Call the method and expect ValueError
        with pytest.raises(ValueError, match="not found"):
            await security_firm_service.upload_verification_document(
                firm_id=firm_id,
                file=mock_file,
                user_id=user_id
            )