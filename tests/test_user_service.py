"""
Tests for UserService
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from decimal import Decimal
from uuid import UUID, uuid4

from app.services.user import UserService
from app.models.user import RegisteredUser, UserGroup, GroupMobileNumber


@pytest.fixture
def mock_db():
    """Mock database session"""
    return Mock(spec=AsyncSession)


@pytest.fixture
def user_service(mock_db):
    """UserService instance with mocked database"""
    return UserService(mock_db)


@pytest.fixture
def sample_user():
    """Sample registered user"""
    user = Mock(spec=RegisteredUser)
    user.id = uuid4()
    user.email = "john.doe@example.com"
    user.phone = "+1-555-123-4567"
    user.first_name = "John"
    user.last_name = "Doe"
    user.is_verified = False
    user.prank_flags = 0
    user.total_fines = Decimal('0.00')
    user.is_suspended = False
    user.is_locked = False
    user.failed_login_attempts = 0
    return user


@pytest.fixture
def sample_group():
    """Sample user group"""
    group = Mock(spec=UserGroup)
    group.id = uuid4()
    group.user_id = uuid4()
    group.name = "Home Security"
    group.address = "123 Main Street"
    group.latitude = 40.7128
    group.longitude = -74.0060
    group.subscription_id = None
    group.subscription_expires_at = None
    group.mobile_numbers = []
    return group


class TestUserRegistration:
    """Test user registration functionality"""
    
    @pytest.mark.asyncio
    async def test_register_user_success(self, user_service, mock_db):
        """Test successful user registration"""
        # Mock database query to return no existing user
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.add = Mock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Test data
        email = "john.doe@example.com"
        phone = "+1-555-123-4567"
        first_name = "John"
        last_name = "Doe"
        
        # Call the method
        result = await user_service.register_user(
            email=email,
            phone=phone,
            first_name=first_name,
            last_name=last_name
        )
        
        # Assertions
        mock_db.execute.assert_called_once()
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
        
        # Verify the created user has correct attributes
        added_user = mock_db.add.call_args[0][0]
        assert added_user.email == email
        assert added_user.phone == phone
        assert added_user.first_name == first_name
        assert added_user.last_name == last_name
        assert added_user.is_verified == False
        assert added_user.prank_flags == 0
        assert added_user.total_fines == Decimal('0.00')
    
    @pytest.mark.asyncio
    async def test_register_user_duplicate_email(self, user_service, mock_db):
        """Test registration with duplicate email"""
        # Mock database query to return existing user
        existing_user = Mock(spec=RegisteredUser)
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = existing_user
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Test data
        email = "john.doe@example.com"
        phone = "+1-555-123-4567"
        first_name = "John"
        last_name = "Doe"
        
        # Call the method and expect ValueError
        with pytest.raises(ValueError, match="already exists"):
            await user_service.register_user(
                email=email,
                phone=phone,
                first_name=first_name,
                last_name=last_name
            )
        
        # Verify no user was added
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_user_by_id_success(self, user_service, mock_db, sample_user):
        """Test getting user by ID"""
        # Mock database get
        mock_db.get = AsyncMock(return_value=sample_user)
        
        user_id = sample_user.id
        
        # Call the method
        result = await user_service.get_user_by_id(user_id)
        
        # Assertions
        assert result == sample_user
        mock_db.get.assert_called_once_with(RegisteredUser, user_id)
    
    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, user_service, mock_db):
        """Test getting non-existent user"""
        # Mock database get to return None
        mock_db.get = AsyncMock(return_value=None)
        
        user_id = uuid4()
        
        # Call the method and expect ValueError
        with pytest.raises(ValueError, match="not found"):
            await user_service.get_user_by_id(user_id)
    
    @pytest.mark.asyncio
    async def test_get_user_by_email(self, user_service, mock_db, sample_user):
        """Test getting user by email"""
        # Mock database query
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        email = "john.doe@example.com"
        
        # Call the method
        result = await user_service.get_user_by_email(email)
        
        # Assertions
        assert result == sample_user
        mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_user_profile(self, user_service, mock_db, sample_user):
        """Test updating user profile"""
        # Mock get_user_by_id
        user_service.get_user_by_id = AsyncMock(return_value=sample_user)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        user_id = sample_user.id
        new_first_name = "Johnny"
        new_last_name = "Smith"
        
        # Call the method
        result = await user_service.update_user_profile(
            user_id=user_id,
            first_name=new_first_name,
            last_name=new_last_name
        )
        
        # Assertions
        assert sample_user.first_name == new_first_name
        assert sample_user.last_name == new_last_name
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(sample_user)


class TestPhoneVerification:
    """Test phone verification functionality"""
    
    @pytest.mark.asyncio
    async def test_request_phone_verification_success(self, user_service, mock_db):
        """Test successful phone verification request"""
        phone = "+1-555-123-4567"
        
        # Mock OTP delivery service
        user_service.otp_delivery.send_sms_otp = AsyncMock(return_value=True)
        
        # Mock Redis cache
        with patch('app.services.user.cache') as mock_cache:
            mock_cache.set = AsyncMock()
            
            # Call the method
            result = await user_service.request_phone_verification(phone)
            
            # Assertions
            assert result["success"] == True
            assert "OTP sent" in result["message"]
            assert result["expires_in_minutes"] == 10
            mock_cache.set.assert_called_once()
            user_service.otp_delivery.send_sms_otp.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_request_phone_verification_delivery_failure(self, user_service, mock_db):
        """Test phone verification with delivery failure"""
        phone = "+1-555-123-4567"
        
        # Mock OTP delivery service to fail
        user_service.otp_delivery.send_sms_otp = AsyncMock(return_value=False)
        
        # Mock Redis cache
        with patch('app.services.user.cache') as mock_cache:
            mock_cache.set = AsyncMock()
            
            # Call the method
            result = await user_service.request_phone_verification(phone)
            
            # Assertions
            assert result["success"] == False
            assert "Failed to send" in result["message"]
    
    @pytest.mark.asyncio
    async def test_verify_phone_otp_success(self, user_service, mock_db, sample_user):
        """Test successful OTP verification"""
        phone = "+1-555-123-4567"
        otp_code = "123456"
        
        # Mock get_user_by_phone
        user_service.get_user_by_phone = AsyncMock(return_value=sample_user)
        mock_db.commit = AsyncMock()
        
        # Mock Redis cache
        with patch('app.services.user.cache') as mock_cache:
            mock_cache.get = AsyncMock(return_value=b"123456")
            mock_cache.delete = AsyncMock()
            
            # Call the method
            result = await user_service.verify_phone_otp(phone, otp_code)
            
            # Assertions
            assert result["success"] == True
            assert "verified successfully" in result["message"]
            assert sample_user.is_verified == True
            mock_db.commit.assert_called_once()
            mock_cache.delete.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_verify_phone_otp_invalid_code(self, user_service, mock_db):
        """Test OTP verification with invalid code"""
        phone = "+1-555-123-4567"
        otp_code = "999999"
        
        # Mock Redis cache
        with patch('app.services.user.cache') as mock_cache:
            mock_cache.get = AsyncMock(return_value=b"123456")  # Different OTP
            
            # Call the method
            result = await user_service.verify_phone_otp(phone, otp_code)
            
            # Assertions
            assert result["success"] == False
            assert "Invalid OTP" in result["message"]
    
    @pytest.mark.asyncio
    async def test_verify_phone_otp_expired(self, user_service, mock_db):
        """Test OTP verification with expired OTP"""
        phone = "+1-555-123-4567"
        otp_code = "123456"
        
        # Mock Redis cache to return None (expired)
        with patch('app.services.user.cache') as mock_cache:
            mock_cache.get = AsyncMock(return_value=None)
            
            # Call the method
            result = await user_service.verify_phone_otp(phone, otp_code)
            
            # Assertions
            assert result["success"] == False
            assert "expired" in result["message"]


class TestUserGroups:
    """Test user group management functionality"""
    
    @pytest.mark.asyncio
    async def test_create_user_group_success(self, user_service, mock_db, sample_user):
        """Test successful group creation"""
        # Mock get_user_by_id
        user_service.get_user_by_id = AsyncMock(return_value=sample_user)
        mock_db.add = Mock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        user_id = sample_user.id
        name = "Home Security"
        address = "123 Main Street"
        latitude = 40.7128
        longitude = -74.0060
        
        # Call the method
        result = await user_service.create_user_group(
            user_id=user_id,
            name=name,
            address=address,
            latitude=latitude,
            longitude=longitude
        )
        
        # Assertions
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
        
        # Verify the created group
        added_group = mock_db.add.call_args[0][0]
        assert added_group.user_id == user_id
        assert added_group.name == name
        assert added_group.address == address
    
    @pytest.mark.asyncio
    async def test_get_user_groups(self, user_service, mock_db, sample_user, sample_group):
        """Test getting user groups"""
        # Mock get_user_by_id
        user_service.get_user_by_id = AsyncMock(return_value=sample_user)
        
        # Mock database query
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [sample_group]
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        user_id = sample_user.id
        
        # Call the method
        result = await user_service.get_user_groups(user_id)
        
        # Assertions
        assert len(result) == 1
        assert result[0] == sample_group
        mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_user_group_by_id_success(self, user_service, mock_db, sample_group):
        """Test getting specific group by ID"""
        # Mock database query
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_group
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        user_id = sample_group.user_id
        group_id = str(sample_group.id)
        
        # Call the method
        result = await user_service.get_user_group_by_id(user_id, group_id)
        
        # Assertions
        assert result == sample_group
        mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_user_group_by_id_not_found(self, user_service, mock_db):
        """Test getting non-existent group"""
        # Mock database query to return None
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        user_id = uuid4()
        group_id = str(uuid4())
        
        # Call the method and expect ValueError
        with pytest.raises(ValueError, match="not found or not authorized"):
            await user_service.get_user_group_by_id(user_id, group_id)
    
    @pytest.mark.asyncio
    async def test_delete_user_group_success(self, user_service, mock_db, sample_group):
        """Test successful group deletion"""
        # Mock get_user_group_by_id
        user_service.get_user_group_by_id = AsyncMock(return_value=sample_group)
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()
        
        user_id = sample_group.user_id
        group_id = str(sample_group.id)
        
        # Call the method
        await user_service.delete_user_group(user_id, group_id)
        
        # Assertions
        mock_db.delete.assert_called_once_with(sample_group)
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_user_group_with_active_subscription(self, user_service, mock_db, sample_group):
        """Test deleting group with active subscription"""
        # Set up group with active subscription
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        sample_group.subscription_expires_at = now + timedelta(days=30)
        sample_group.created_at = now - timedelta(days=1)  # Created yesterday
        
        # Mock get_user_group_by_id
        user_service.get_user_group_by_id = AsyncMock(return_value=sample_group)
        
        user_id = sample_group.user_id
        group_id = str(sample_group.id)
        
        # Call the method and expect ValueError
        with pytest.raises(ValueError, match="active subscription"):
            await user_service.delete_user_group(user_id, group_id)


class TestMobileNumbers:
    """Test mobile number management functionality"""
    
    @pytest.mark.asyncio
    async def test_add_mobile_number_to_group_success(self, user_service, mock_db, sample_group):
        """Test adding mobile number to group"""
        # Mock get_user_group_by_id
        user_service.get_user_group_by_id = AsyncMock(return_value=sample_group)
        
        # Mock database query to return no existing number
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.add = Mock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        user_id = sample_group.user_id
        group_id = str(sample_group.id)
        phone_number = "+1-555-987-6543"
        user_type = "individual"
        
        # Call the method
        result = await user_service.add_mobile_number_to_group(
            user_id=user_id,
            group_id=group_id,
            phone_number=phone_number,
            user_type=user_type
        )
        
        # Assertions
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
        
        # Verify the created mobile number
        added_number = mock_db.add.call_args[0][0]
        assert added_number.group_id == group_id
        assert added_number.phone_number == phone_number
        assert added_number.user_type == user_type
        assert added_number.is_verified == False
    
    @pytest.mark.asyncio
    async def test_add_mobile_number_duplicate(self, user_service, mock_db, sample_group):
        """Test adding duplicate mobile number to group"""
        # Mock get_user_group_by_id
        user_service.get_user_group_by_id = AsyncMock(return_value=sample_group)
        
        # Mock database query to return existing number
        existing_number = Mock(spec=GroupMobileNumber)
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = existing_number
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        user_id = sample_group.user_id
        group_id = str(sample_group.id)
        phone_number = "+1-555-987-6543"
        user_type = "individual"
        
        # Call the method and expect ValueError
        with pytest.raises(ValueError, match="already exists"):
            await user_service.add_mobile_number_to_group(
                user_id=user_id,
                group_id=group_id,
                phone_number=phone_number,
                user_type=user_type
            )
    
    @pytest.mark.asyncio
    async def test_get_group_mobile_numbers(self, user_service, mock_db, sample_group):
        """Test getting mobile numbers for a group"""
        # Mock get_user_group_by_id
        user_service.get_user_group_by_id = AsyncMock(return_value=sample_group)
        
        # Mock mobile numbers
        mock_number1 = Mock(spec=GroupMobileNumber)
        mock_number2 = Mock(spec=GroupMobileNumber)
        
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_number1, mock_number2]
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        user_id = sample_group.user_id
        group_id = str(sample_group.id)
        
        # Call the method
        result = await user_service.get_group_mobile_numbers(user_id, group_id)
        
        # Assertions
        assert len(result) == 2
        assert result[0] == mock_number1
        assert result[1] == mock_number2
    
    @pytest.mark.asyncio
    async def test_remove_mobile_number_from_group_success(self, user_service, mock_db, sample_group):
        """Test removing mobile number from group"""
        # Mock get_user_group_by_id
        user_service.get_user_group_by_id = AsyncMock(return_value=sample_group)
        
        # Mock mobile number
        mock_mobile_number = Mock(spec=GroupMobileNumber)
        mock_mobile_number.group_id = sample_group.id
        mock_db.get = AsyncMock(return_value=mock_mobile_number)
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()
        
        user_id = sample_group.user_id
        group_id = str(sample_group.id)
        mobile_number_id = str(uuid4())
        
        # Call the method
        await user_service.remove_mobile_number_from_group(
            user_id=user_id,
            group_id=group_id,
            mobile_number_id=mobile_number_id
        )
        
        # Assertions
        mock_db.delete.assert_called_once_with(mock_mobile_number)
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_remove_mobile_number_not_found(self, user_service, mock_db, sample_group):
        """Test removing non-existent mobile number"""
        # Mock get_user_group_by_id
        user_service.get_user_group_by_id = AsyncMock(return_value=sample_group)
        
        # Mock database get to return None
        mock_db.get = AsyncMock(return_value=None)
        
        user_id = sample_group.user_id
        group_id = str(sample_group.id)
        mobile_number_id = str(uuid4())
        
        # Call the method and expect ValueError
        with pytest.raises(ValueError, match="not found"):
            await user_service.remove_mobile_number_from_group(
                user_id=user_id,
                group_id=group_id,
                mobile_number_id=mobile_number_id
            )


class TestUserStatistics:
    """Test user statistics functionality"""
    
    @pytest.mark.asyncio
    async def test_get_user_statistics(self, user_service, mock_db, sample_user):
        """Test getting user statistics"""
        # Mock get_user_by_id
        user_service.get_user_by_id = AsyncMock(return_value=sample_user)
        
        # Mock groups with mobile numbers
        mock_group1 = Mock()
        mock_group1.mobile_numbers = [Mock(), Mock()]  # 2 mobile numbers
        mock_group1.subscription_expires_at = None
        
        mock_group2 = Mock()
        mock_group2.mobile_numbers = [Mock()]  # 1 mobile number
        from datetime import datetime, timezone, timedelta
        mock_group2.subscription_expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        mock_group2.created_at = datetime.now(timezone.utc) - timedelta(days=1)
        
        user_service.get_user_groups = AsyncMock(return_value=[mock_group1, mock_group2])
        
        user_id = sample_user.id
        
        # Call the method
        result = await user_service.get_user_statistics(user_id)
        
        # Assertions
        assert result["total_groups"] == 2
        assert result["total_mobile_numbers"] == 3
        assert result["active_subscriptions"] == 1
        assert result["prank_flags"] == sample_user.prank_flags
        assert result["total_fines"] == float(sample_user.total_fines)
        assert result["is_suspended"] == sample_user.is_suspended
        assert result["is_verified"] == sample_user.is_verified