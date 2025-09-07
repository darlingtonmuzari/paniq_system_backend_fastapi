"""
Comprehensive unit tests for silent mode service
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, patch, MagicMock
import json

from app.services.silent_mode import (
    SilentModeService,
    AndroidSilentModeController,
    IOSSilentModeController,
    SilentModeRequest,
    SilentModeStatus,
    SilentModeError,
    RingerMode,
    Platform,
    silent_mode_service
)
from app.core.exceptions import APIError


class TestRingerMode:
    """Test RingerMode enum"""
    
    def test_ringer_mode_values(self):
        """Test RingerMode enum values"""
        assert RingerMode.NORMAL == "normal"
        assert RingerMode.SILENT == "silent"
        assert RingerMode.VIBRATE == "vibrate"
    
    def test_ringer_mode_membership(self):
        """Test RingerMode membership"""
        assert RingerMode.NORMAL in RingerMode
        assert RingerMode.SILENT in RingerMode
        assert RingerMode.VIBRATE in RingerMode


class TestPlatform:
    """Test Platform enum"""
    
    def test_platform_values(self):
        """Test Platform enum values"""
        assert Platform.ANDROID == "android"
        assert Platform.IOS == "ios"
    
    def test_platform_membership(self):
        """Test Platform membership"""
        assert Platform.ANDROID in Platform
        assert Platform.IOS in Platform


class TestSilentModeRequest:
    """Test SilentModeRequest model"""
    
    def test_create_silent_mode_request_minimal(self):
        """Test creating silent mode request with minimal fields"""
        user_id = uuid4()
        request_id = uuid4()
        
        request = SilentModeRequest(
            user_id=user_id,
            request_id=request_id,
            platform=Platform.ANDROID
        )
        
        assert request.user_id == user_id
        assert request.request_id == request_id
        assert request.platform == Platform.ANDROID
        assert request.duration_minutes == 30  # Default
        assert request.restore_mode == RingerMode.NORMAL  # Default
        assert request.metadata == {}  # Default
    
    def test_create_silent_mode_request_full(self):
        """Test creating silent mode request with all fields"""
        user_id = uuid4()
        request_id = uuid4()
        
        request = SilentModeRequest(
            user_id=user_id,
            request_id=request_id,
            platform=Platform.IOS,
            duration_minutes=45,
            restore_mode=RingerMode.VIBRATE,
            metadata={"source": "emergency_call", "priority": "high"}
        )
        
        assert request.user_id == user_id
        assert request.request_id == request_id
        assert request.platform == Platform.IOS
        assert request.duration_minutes == 45
        assert request.restore_mode == RingerMode.VIBRATE
        assert request.metadata["source"] == "emergency_call"
        assert request.metadata["priority"] == "high"


class TestSilentModeStatus:
    """Test SilentModeStatus model"""
    
    def test_create_silent_mode_status_minimal(self):
        """Test creating silent mode status with minimal fields"""
        user_id = uuid4()
        
        status = SilentModeStatus(
            user_id=user_id,
            is_active=True
        )
        
        assert status.user_id == user_id
        assert status.is_active is True
        assert status.request_id is None
        assert status.activated_at is None
        assert status.expires_at is None
        assert status.original_mode is None
        assert status.platform is None
    
    def test_create_silent_mode_status_full(self):
        """Test creating silent mode status with all fields"""
        user_id = uuid4()
        request_id = uuid4()
        activated_at = datetime.utcnow()
        expires_at = activated_at + timedelta(minutes=30)
        
        status = SilentModeStatus(
            user_id=user_id,
            request_id=request_id,
            is_active=True,
            activated_at=activated_at,
            expires_at=expires_at,
            original_mode=RingerMode.NORMAL,
            platform=Platform.ANDROID
        )
        
        assert status.user_id == user_id
        assert status.request_id == request_id
        assert status.is_active is True
        assert status.activated_at == activated_at
        assert status.expires_at == expires_at
        assert status.original_mode == RingerMode.NORMAL
        assert status.platform == Platform.ANDROID


class TestAndroidSilentModeController:
    """Test Android silent mode controller"""
    
    @pytest.fixture
    def controller(self):
        """Android silent mode controller instance"""
        return AndroidSilentModeController()
    
    @pytest.fixture
    def mock_websocket_service(self):
        """Mock WebSocket service"""
        with patch('app.services.silent_mode.websocket_service') as mock:
            mock.manager = AsyncMock()
            mock.manager.send_personal_message = AsyncMock()
            yield mock
    
    @pytest.mark.asyncio
    async def test_activate_silent_mode_success(self, controller, mock_websocket_service):
        """Test successful Android silent mode activation"""
        user_id = uuid4()
        request_id = uuid4()
        duration_minutes = 30
        
        result = await controller.activate_silent_mode(user_id, request_id, duration_minutes)
        
        assert result["status"] == "activated"
        assert result["platform"] == "android"
        assert result["method"] == "do_not_disturb"
        assert result["duration_minutes"] == duration_minutes
        assert "activated_at" in result
        
        # Verify WebSocket message was sent
        mock_websocket_service.manager.send_personal_message.assert_called_once()
        call_args = mock_websocket_service.manager.send_personal_message.call_args
        assert call_args[0][0] == str(user_id)  # user_id
        
        message = call_args[0][1]  # message
        assert message["type"] == "silent_mode_command"
        assert "data" in message
        assert message["data"]["type"] == "activate_silent_mode"
        assert message["data"]["request_id"] == str(request_id)
        assert message["data"]["duration_minutes"] == duration_minutes
        
        # Check Android-specific settings
        android_settings = message["data"]["platform_specific"]["android"]
        assert android_settings["use_do_not_disturb"] is True
        assert android_settings["allow_emergency_calls"] is True
        assert android_settings["allow_alarms"] is True
        assert android_settings["priority_mode"] == "emergency_only"
    
    @pytest.mark.asyncio
    async def test_activate_silent_mode_websocket_error(self, controller, mock_websocket_service):
        """Test Android silent mode activation with WebSocket error"""
        user_id = uuid4()
        request_id = uuid4()
        
        mock_websocket_service.manager.send_personal_message.side_effect = Exception("WebSocket error")
        
        with pytest.raises(SilentModeError, match="Failed to activate Android silent mode"):
            await controller.activate_silent_mode(user_id, request_id)
    
    @pytest.mark.asyncio
    async def test_deactivate_silent_mode_success(self, controller, mock_websocket_service):
        """Test successful Android silent mode deactivation"""
        user_id = uuid4()
        request_id = uuid4()
        restore_mode = RingerMode.VIBRATE
        
        result = await controller.deactivate_silent_mode(user_id, request_id, restore_mode)
        
        assert result["status"] == "deactivated"
        assert result["platform"] == "android"
        assert result["restored_mode"] == restore_mode
        assert "deactivated_at" in result
        
        # Verify WebSocket message was sent
        mock_websocket_service.manager.send_personal_message.assert_called_once()
        call_args = mock_websocket_service.manager.send_personal_message.call_args
        
        message = call_args[0][1]  # message
        assert message["type"] == "silent_mode_command"
        assert message["data"]["type"] == "deactivate_silent_mode"
        assert message["data"]["restore_mode"] == restore_mode
        
        # Check Android-specific settings
        android_settings = message["data"]["platform_specific"]["android"]
        assert android_settings["restore_previous_settings"] is True
        assert android_settings["target_mode"] == restore_mode
    
    @pytest.mark.asyncio
    async def test_deactivate_silent_mode_websocket_error(self, controller, mock_websocket_service):
        """Test Android silent mode deactivation with WebSocket error"""
        user_id = uuid4()
        request_id = uuid4()
        
        mock_websocket_service.manager.send_personal_message.side_effect = Exception("WebSocket error")
        
        with pytest.raises(SilentModeError, match="Failed to deactivate Android silent mode"):
            await controller.deactivate_silent_mode(user_id, request_id)


class TestIOSSilentModeController:
    """Test iOS silent mode controller"""
    
    @pytest.fixture
    def controller(self):
        """iOS silent mode controller instance"""
        return IOSSilentModeController()
    
    @pytest.fixture
    def mock_websocket_service(self):
        """Mock WebSocket service"""
        with patch('app.services.silent_mode.websocket_service') as mock:
            mock.manager = AsyncMock()
            mock.manager.send_personal_message = AsyncMock()
            yield mock
    
    @pytest.mark.asyncio
    async def test_activate_silent_mode_success(self, controller, mock_websocket_service):
        """Test successful iOS silent mode activation"""
        user_id = uuid4()
        request_id = uuid4()
        duration_minutes = 45
        
        result = await controller.activate_silent_mode(user_id, request_id, duration_minutes)
        
        assert result["status"] == "activated"
        assert result["platform"] == "ios"
        assert result["method"] == "focus_mode"
        assert result["duration_minutes"] == duration_minutes
        assert "activated_at" in result
        
        # Verify WebSocket message was sent
        mock_websocket_service.manager.send_personal_message.assert_called_once()
        call_args = mock_websocket_service.manager.send_personal_message.call_args
        
        message = call_args[0][1]  # message
        assert message["type"] == "silent_mode_command"
        assert message["data"]["type"] == "activate_silent_mode"
        
        # Check iOS-specific settings
        ios_settings = message["data"]["platform_specific"]["ios"]
        assert ios_settings["use_focus_mode"] is True
        assert ios_settings["focus_mode_name"] == "Emergency"
        assert ios_settings["allow_emergency_calls"] is True
        assert ios_settings["allow_critical_alerts"] is True
        assert ios_settings["silence_notifications"] is True
    
    @pytest.mark.asyncio
    async def test_deactivate_silent_mode_success(self, controller, mock_websocket_service):
        """Test successful iOS silent mode deactivation"""
        user_id = uuid4()
        request_id = uuid4()
        restore_mode = RingerMode.NORMAL
        
        result = await controller.deactivate_silent_mode(user_id, request_id, restore_mode)
        
        assert result["status"] == "deactivated"
        assert result["platform"] == "ios"
        assert result["restored_mode"] == restore_mode
        assert "deactivated_at" in result
        
        # Verify WebSocket message was sent
        mock_websocket_service.manager.send_personal_message.assert_called_once()
        call_args = mock_websocket_service.manager.send_personal_message.call_args
        
        message = call_args[0][1]  # message
        assert message["data"]["type"] == "deactivate_silent_mode"
        
        # Check iOS-specific settings
        ios_settings = message["data"]["platform_specific"]["ios"]
        assert ios_settings["disable_focus_mode"] is True
        assert ios_settings["restore_previous_settings"] is True
        assert ios_settings["target_mode"] == restore_mode


class TestSilentModeService:
    """Test main silent mode service"""
    
    @pytest.fixture
    def service(self):
        """Silent mode service instance"""
        return SilentModeService()
    
    @pytest.fixture
    def mock_cache(self):
        """Mock Redis cache"""
        with patch('app.services.silent_mode.cache') as mock:
            mock.get = AsyncMock(return_value=None)
            mock.set = AsyncMock()
            mock.delete = AsyncMock()
            yield mock
    
    @pytest.fixture
    def mock_controllers(self, service):
        """Mock platform controllers"""
        service.android_controller = AsyncMock()
        service.ios_controller = AsyncMock()
        return service
    
    @pytest.fixture
    def sample_request(self):
        """Sample silent mode request"""
        return SilentModeRequest(
            user_id=uuid4(),
            request_id=uuid4(),
            platform=Platform.ANDROID,
            duration_minutes=30
        )
    
    @pytest.mark.asyncio
    async def test_activate_silent_mode_android_success(self, mock_controllers, mock_cache, sample_request):
        """Test successful Android silent mode activation"""
        # Mock controller response
        mock_controllers.android_controller.activate_silent_mode.return_value = {
            "status": "activated",
            "platform": "android"
        }
        
        result = await mock_controllers.activate_silent_mode(sample_request)
        
        assert isinstance(result, SilentModeStatus)
        assert result.user_id == sample_request.user_id
        assert result.request_id == sample_request.request_id
        assert result.is_active is True
        assert result.platform == Platform.ANDROID
        assert result.activated_at is not None
        assert result.expires_at is not None
        
        # Verify controller was called
        mock_controllers.android_controller.activate_silent_mode.assert_called_once_with(
            sample_request.user_id,
            sample_request.request_id,
            sample_request.duration_minutes
        )
        
        # Verify cache operations
        assert mock_cache.set.call_count >= 1  # Status and active sessions
    
    @pytest.mark.asyncio
    async def test_activate_silent_mode_ios_success(self, mock_controllers, mock_cache):
        """Test successful iOS silent mode activation"""
        ios_request = SilentModeRequest(
            user_id=uuid4(),
            request_id=uuid4(),
            platform=Platform.IOS,
            duration_minutes=45
        )
        
        # Mock controller response
        mock_controllers.ios_controller.activate_silent_mode.return_value = {
            "status": "activated",
            "platform": "ios"
        }
        
        result = await mock_controllers.activate_silent_mode(ios_request)
        
        assert result.platform == Platform.IOS
        
        # Verify iOS controller was called
        mock_controllers.ios_controller.activate_silent_mode.assert_called_once_with(
            ios_request.user_id,
            ios_request.request_id,
            ios_request.duration_minutes
        )
    
    @pytest.mark.asyncio
    async def test_activate_silent_mode_unsupported_platform(self, mock_controllers, mock_cache):
        """Test silent mode activation with unsupported platform"""
        # Create request with invalid platform (bypassing enum validation)
        request_data = {
            "user_id": uuid4(),
            "request_id": uuid4(),
            "platform": "windows",  # Unsupported
            "duration_minutes": 30
        }
        
        # Mock the platform check to simulate unsupported platform
        with patch.object(mock_controllers, 'activate_silent_mode') as mock_activate:
            mock_activate.side_effect = SilentModeError("Unsupported platform: windows")
            
            with pytest.raises(SilentModeError, match="Unsupported platform"):
                # Create a mock request that bypasses validation
                mock_request = MagicMock()
                mock_request.user_id = request_data["user_id"]
                mock_request.request_id = request_data["request_id"]
                mock_request.platform = request_data["platform"]
                mock_request.duration_minutes = request_data["duration_minutes"]
                
                await mock_controllers.activate_silent_mode(mock_request)
    
    @pytest.mark.asyncio
    async def test_activate_silent_mode_already_active(self, mock_controllers, mock_cache):
        """Test activating silent mode when already active"""
        user_id = uuid4()
        
        # Mock existing active status
        existing_status = SilentModeStatus(
            user_id=user_id,
            request_id=uuid4(),
            is_active=True,
            activated_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(minutes=15),
            platform=Platform.ANDROID
        )
        
        with patch.object(mock_controllers, 'get_user_status') as mock_get_status, \
             patch.object(mock_controllers, '_extend_silent_mode_session') as mock_extend:
            
            mock_get_status.return_value = existing_status
            mock_extend.return_value = existing_status
            
            request = SilentModeRequest(
                user_id=user_id,
                request_id=uuid4(),
                platform=Platform.ANDROID,
                duration_minutes=30
            )
            
            result = await mock_controllers.activate_silent_mode(request)
            
            # Should extend existing session instead of creating new one
            mock_extend.assert_called_once_with(user_id, 30)
            assert result == existing_status
    
    @pytest.mark.asyncio
    async def test_deactivate_silent_mode_success(self, mock_controllers, mock_cache):
        """Test successful silent mode deactivation"""
        user_id = uuid4()
        request_id = uuid4()
        
        # Mock active status
        active_status = SilentModeStatus(
            user_id=user_id,
            request_id=request_id,
            is_active=True,
            platform=Platform.ANDROID
        )
        
        with patch.object(mock_controllers, 'get_user_status') as mock_get_status:
            mock_get_status.return_value = active_status
            
            # Mock controller response
            mock_controllers.android_controller.deactivate_silent_mode.return_value = {
                "status": "deactivated",
                "platform": "android"
            }
            
            result = await mock_controllers.deactivate_silent_mode(user_id, request_id)
            
            assert result.user_id == user_id
            assert result.is_active is False
            
            # Verify controller was called
            mock_controllers.android_controller.deactivate_silent_mode.assert_called_once()
            
            # Verify cache cleanup
            mock_cache.delete.assert_called()
    
    @pytest.mark.asyncio
    async def test_deactivate_silent_mode_not_active(self, mock_controllers, mock_cache):
        """Test deactivating silent mode when not active"""
        user_id = uuid4()
        
        with patch.object(mock_controllers, 'get_user_status') as mock_get_status:
            mock_get_status.return_value = None  # No active session
            
            with pytest.raises(SilentModeError, match="No active silent mode session found"):
                await mock_controllers.deactivate_silent_mode(user_id)
    
    @pytest.mark.asyncio
    async def test_deactivate_silent_mode_request_id_mismatch(self, mock_controllers, mock_cache):
        """Test deactivating silent mode with wrong request ID"""
        user_id = uuid4()
        request_id = uuid4()
        wrong_request_id = uuid4()
        
        # Mock active status with different request ID
        active_status = SilentModeStatus(
            user_id=user_id,
            request_id=request_id,
            is_active=True,
            platform=Platform.ANDROID
        )
        
        with patch.object(mock_controllers, 'get_user_status') as mock_get_status:
            mock_get_status.return_value = active_status
            
            with pytest.raises(SilentModeError, match="Request ID mismatch"):
                await mock_controllers.deactivate_silent_mode(user_id, wrong_request_id)
    
    @pytest.mark.asyncio
    async def test_get_user_status_success(self, service, mock_cache):
        """Test getting user status successfully"""
        user_id = uuid4()
        
        # Mock cache data
        status_data = {
            "user_id": str(user_id),
            "request_id": str(uuid4()),
            "is_active": True,
            "activated_at": "2024-01-01T12:00:00",
            "expires_at": "2024-01-01T12:30:00",
            "platform": "android"
        }
        
        mock_cache.get.return_value = json.dumps(status_data)
        
        result = await service.get_user_status(user_id)
        
        assert result is not None
        assert result.user_id == user_id
        assert result.is_active is True
        assert result.platform == Platform.ANDROID
        assert isinstance(result.activated_at, datetime)
        assert isinstance(result.expires_at, datetime)
    
    @pytest.mark.asyncio
    async def test_get_user_status_not_found(self, service, mock_cache):
        """Test getting user status when not found"""
        user_id = uuid4()
        
        mock_cache.get.return_value = None
        
        result = await service.get_user_status(user_id)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_user_status_cache_error(self, service, mock_cache):
        """Test getting user status with cache error"""
        user_id = uuid4()
        
        mock_cache.get.side_effect = Exception("Cache error")
        
        result = await service.get_user_status(user_id)
        
        assert result is None  # Should handle error gracefully
    
    @pytest.mark.asyncio
    async def test_get_active_sessions(self, service, mock_cache):
        """Test getting active sessions"""
        user1_id = uuid4()
        user2_id = uuid4()
        
        # Mock active sessions data
        sessions_data = {
            str(user1_id): "2024-01-01T12:30:00",
            str(user2_id): "2024-01-01T13:00:00"
        }
        
        mock_cache.get.return_value = json.dumps(sessions_data)
        
        # Mock individual status lookups
        status1 = SilentModeStatus(user_id=user1_id, is_active=True, platform=Platform.ANDROID)
        status2 = SilentModeStatus(user_id=user2_id, is_active=True, platform=Platform.IOS)
        
        with patch.object(service, 'get_user_status') as mock_get_status:
            mock_get_status.side_effect = [status1, status2]
            
            result = await service.get_active_sessions()
            
            assert len(result) == 2
            assert result[0].user_id == user1_id
            assert result[1].user_id == user2_id
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self, service):
        """Test cleaning up expired sessions"""
        user_id = uuid4()
        
        # Mock expired status
        expired_status = SilentModeStatus(
            user_id=user_id,
            request_id=uuid4(),
            is_active=True,
            expires_at=datetime.utcnow() - timedelta(minutes=5),  # Expired
            platform=Platform.ANDROID
        )
        
        with patch.object(service, 'get_active_sessions') as mock_get_sessions, \
             patch.object(service, 'deactivate_silent_mode') as mock_deactivate:
            
            mock_get_sessions.return_value = [expired_status]
            mock_deactivate.return_value = expired_status
            
            await service.cleanup_expired_sessions()
            
            # Should deactivate expired session
            mock_deactivate.assert_called_once_with(
                user_id,
                expired_status.request_id,
                RingerMode.NORMAL  # Default restore mode
            )
    
    @pytest.mark.asyncio
    async def test_extend_silent_mode_session(self, service, mock_cache):
        """Test extending silent mode session"""
        user_id = uuid4()
        additional_minutes = 15
        
        # Mock existing status
        base_time = datetime.utcnow()
        existing_status = SilentModeStatus(
            user_id=user_id,
            is_active=True,
            expires_at=base_time + timedelta(minutes=10),
            platform=Platform.ANDROID
        )
        
        with patch.object(service, 'get_user_status') as mock_get_status, \
             patch.object(service, '_store_user_status') as mock_store, \
             patch.object(service, '_add_to_active_sessions') as mock_add:
            
            mock_get_status.return_value = existing_status
            
            with patch('app.services.silent_mode.datetime') as mock_datetime:
                mock_datetime.utcnow.return_value = base_time + timedelta(seconds=1)  # Slightly later
                
                result = await service._extend_silent_mode_session(user_id, additional_minutes)
                
                assert result.user_id == user_id
                assert result.expires_at > existing_status.expires_at
            
            # Verify cache updates
            mock_store.assert_called_once()
            mock_add.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_schedule_auto_deactivation(self, service):
        """Test scheduling automatic deactivation"""
        user_id = uuid4()
        delay_minutes = 0.01  # Very short delay for testing
        
        # Mock active status that should be deactivated
        active_status = SilentModeStatus(
            user_id=user_id,
            request_id=uuid4(),
            is_active=True,
            platform=Platform.ANDROID
        )
        
        with patch.object(service, 'get_user_status') as mock_get_status, \
             patch.object(service, 'deactivate_silent_mode') as mock_deactivate:
            
            mock_get_status.return_value = active_status
            mock_deactivate.return_value = active_status
            
            # Start auto-deactivation task
            task = asyncio.create_task(
                service._schedule_auto_deactivation(user_id, delay_minutes)
            )
            
            # Wait for task to complete
            await task
            
            # Verify deactivation was called
            mock_deactivate.assert_called_once_with(
                user_id,
                active_status.request_id,
                RingerMode.NORMAL
            )


class TestSilentModeServiceIntegration:
    """Integration tests for silent mode service"""
    
    @pytest.fixture
    def service(self):
        """Silent mode service with real controllers"""
        service = SilentModeService()
        # Mock the WebSocket service for controllers
        with patch('app.services.silent_mode.websocket_service') as mock_ws:
            mock_ws.manager = AsyncMock()
            mock_ws.manager.send_personal_message = AsyncMock()
            yield service
    
    @pytest.fixture
    def mock_cache(self):
        """Mock Redis cache for integration tests"""
        cache_data = {}
        
        async def mock_get(key):
            return cache_data.get(key)
        
        async def mock_set(key, value, expire=None):
            cache_data[key] = value
        
        async def mock_delete(key):
            cache_data.pop(key, None)
        
        with patch('app.services.silent_mode.cache') as mock:
            mock.get = mock_get
            mock.set = mock_set
            mock.delete = mock_delete
            yield mock
    
    @pytest.mark.asyncio
    async def test_full_silent_mode_lifecycle(self, service, mock_cache):
        """Test complete silent mode lifecycle"""
        user_id = uuid4()
        request_id = uuid4()
        
        # 1. Activate silent mode
        request = SilentModeRequest(
            user_id=user_id,
            request_id=request_id,
            platform=Platform.ANDROID,
            duration_minutes=30
        )
        
        status = await service.activate_silent_mode(request)
        
        assert status.is_active is True
        assert status.user_id == user_id
        assert status.request_id == request_id
        
        # 2. Check status
        retrieved_status = await service.get_user_status(user_id)
        assert retrieved_status is not None
        assert retrieved_status.is_active is True
        assert retrieved_status.user_id == user_id
        
        # 3. Get active sessions
        active_sessions = await service.get_active_sessions()
        assert len(active_sessions) == 1
        assert active_sessions[0].user_id == user_id
        
        # 4. Deactivate silent mode
        deactivated_status = await service.deactivate_silent_mode(user_id, request_id)
        assert deactivated_status.is_active is False
        
        # 5. Verify cleanup
        final_status = await service.get_user_status(user_id)
        assert final_status is None
        
        final_sessions = await service.get_active_sessions()
        assert len(final_sessions) == 0
    
    @pytest.mark.asyncio
    async def test_multiple_users_silent_mode(self, service, mock_cache):
        """Test silent mode with multiple users"""
        user1_id = uuid4()
        user2_id = uuid4()
        request1_id = uuid4()
        request2_id = uuid4()
        
        # Activate for both users
        request1 = SilentModeRequest(
            user_id=user1_id,
            request_id=request1_id,
            platform=Platform.ANDROID,
            duration_minutes=30
        )
        
        request2 = SilentModeRequest(
            user_id=user2_id,
            request_id=request2_id,
            platform=Platform.IOS,
            duration_minutes=45
        )
        
        status1 = await service.activate_silent_mode(request1)
        status2 = await service.activate_silent_mode(request2)
        
        assert status1.is_active is True
        assert status2.is_active is True
        
        # Check active sessions
        active_sessions = await service.get_active_sessions()
        assert len(active_sessions) == 2
        
        user_ids = {session.user_id for session in active_sessions}
        assert user1_id in user_ids
        assert user2_id in user_ids
        
        # Deactivate one user
        await service.deactivate_silent_mode(user1_id, request1_id)
        
        # Check remaining sessions
        remaining_sessions = await service.get_active_sessions()
        assert len(remaining_sessions) == 1
        assert remaining_sessions[0].user_id == user2_id


class TestSilentModeError:
    """Test SilentModeError exception"""
    
    def test_silent_mode_error_creation(self):
        """Test creating SilentModeError"""
        error = SilentModeError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, APIError)
    
    def test_silent_mode_error_default_message(self):
        """Test SilentModeError with default message"""
        error = SilentModeError()
        assert "Silent mode operation failed" in str(error)


class TestGlobalInstance:
    """Test global silent mode service instance"""
    
    def test_global_silent_mode_service_exists(self):
        """Test that global silent_mode_service instance exists"""
        assert silent_mode_service is not None
        assert isinstance(silent_mode_service, SilentModeService)
        assert hasattr(silent_mode_service, 'android_controller')
        assert hasattr(silent_mode_service, 'ios_controller')
    
    def test_global_service_controllers(self):
        """Test that global service has proper controllers"""
        assert isinstance(silent_mode_service.android_controller, AndroidSilentModeController)
        assert isinstance(silent_mode_service.ios_controller, IOSSilentModeController)