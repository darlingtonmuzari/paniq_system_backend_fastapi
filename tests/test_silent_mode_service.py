"""
Unit tests for silent mode service
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from datetime import datetime, timedelta

from app.services.silent_mode import (
    SilentModeService,
    AndroidSilentModeController,
    IOSSilentModeController,
    SilentModeRequest,
    SilentModeStatus,
    RingerMode,
    Platform,
    SilentModeError,
    silent_mode_service
)


class TestSilentModeRequest:
    """Test SilentModeRequest model"""
    
    def test_silent_mode_request_creation(self):
        """Test creating a SilentModeRequest"""
        user_id = uuid4()
        request_id = uuid4()
        
        request = SilentModeRequest(
            user_id=user_id,
            request_id=request_id,
            platform=Platform.ANDROID,
            duration_minutes=30,
            restore_mode=RingerMode.NORMAL
        )
        
        assert request.user_id == user_id
        assert request.request_id == request_id
        assert request.platform == Platform.ANDROID
        assert request.duration_minutes == 30
        assert request.restore_mode == RingerMode.NORMAL
    
    def test_silent_mode_request_defaults(self):
        """Test SilentModeRequest with default values"""
        user_id = uuid4()
        request_id = uuid4()
        
        request = SilentModeRequest(
            user_id=user_id,
            request_id=request_id,
            platform=Platform.IOS
        )
        
        assert request.duration_minutes == 30  # Default
        assert request.restore_mode == RingerMode.NORMAL  # Default
        assert request.metadata == {}  # Default


class TestSilentModeStatus:
    """Test SilentModeStatus model"""
    
    def test_silent_mode_status_creation(self):
        """Test creating a SilentModeStatus"""
        user_id = uuid4()
        request_id = uuid4()
        now = datetime.utcnow()
        expires_at = now + timedelta(minutes=30)
        
        status = SilentModeStatus(
            user_id=user_id,
            request_id=request_id,
            is_active=True,
            activated_at=now,
            expires_at=expires_at,
            original_mode=RingerMode.NORMAL,
            platform=Platform.ANDROID
        )
        
        assert status.user_id == user_id
        assert status.request_id == request_id
        assert status.is_active is True
        assert status.activated_at == now
        assert status.expires_at == expires_at
        assert status.original_mode == RingerMode.NORMAL
        assert status.platform == Platform.ANDROID


class TestAndroidSilentModeController:
    """Test Android silent mode controller"""
    
    @pytest.fixture
    def controller(self):
        """Create Android controller instance"""
        return AndroidSilentModeController()
    
    @pytest.mark.asyncio
    async def test_activate_silent_mode(self, controller):
        """Test activating silent mode on Android"""
        user_id = uuid4()
        request_id = uuid4()
        
        with patch('app.services.silent_mode.websocket_service.manager.send_personal_message') as mock_send:
            result = await controller.activate_silent_mode(user_id, request_id, 30)
            
            assert result["status"] == "activated"
            assert result["platform"] == "android"
            assert result["method"] == "do_not_disturb"
            assert result["duration_minutes"] == 30
            assert "activated_at" in result
            
            # Verify WebSocket message was sent
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert call_args[0][0] == str(user_id)  # user_id
            
            message_data = call_args[0][1]
            assert message_data["type"] == "silent_mode_command"
            assert "data" in message_data
    
    @pytest.mark.asyncio
    async def test_deactivate_silent_mode(self, controller):
        """Test deactivating silent mode on Android"""
        user_id = uuid4()
        request_id = uuid4()
        
        with patch('app.services.silent_mode.websocket_service.manager.send_personal_message') as mock_send:
            result = await controller.deactivate_silent_mode(user_id, request_id, RingerMode.NORMAL)
            
            assert result["status"] == "deactivated"
            assert result["platform"] == "android"
            assert result["restored_mode"] == RingerMode.NORMAL
            assert "deactivated_at" in result
            
            # Verify WebSocket message was sent
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert call_args[0][0] == str(user_id)  # user_id
            
            message_data = call_args[0][1]
            assert message_data["type"] == "silent_mode_command"
            assert "data" in message_data
    
    @pytest.mark.asyncio
    async def test_activate_silent_mode_failure(self, controller):
        """Test Android silent mode activation failure"""
        user_id = uuid4()
        request_id = uuid4()
        
        with patch('app.services.silent_mode.websocket_service.manager.send_personal_message', side_effect=Exception("WebSocket error")):
            with pytest.raises(SilentModeError):
                await controller.activate_silent_mode(user_id, request_id, 30)


class TestIOSSilentModeController:
    """Test iOS silent mode controller"""
    
    @pytest.fixture
    def controller(self):
        """Create iOS controller instance"""
        return IOSSilentModeController()
    
    @pytest.mark.asyncio
    async def test_activate_silent_mode(self, controller):
        """Test activating silent mode on iOS"""
        user_id = uuid4()
        request_id = uuid4()
        
        with patch('app.services.silent_mode.websocket_service.manager.send_personal_message') as mock_send:
            result = await controller.activate_silent_mode(user_id, request_id, 30)
            
            assert result["status"] == "activated"
            assert result["platform"] == "ios"
            assert result["method"] == "focus_mode"
            assert result["duration_minutes"] == 30
            assert "activated_at" in result
            
            # Verify WebSocket message was sent
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert call_args[0][0] == str(user_id)  # user_id
            
            message_data = call_args[0][1]
            assert message_data["type"] == "silent_mode_command"
            assert "data" in message_data
    
    @pytest.mark.asyncio
    async def test_deactivate_silent_mode(self, controller):
        """Test deactivating silent mode on iOS"""
        user_id = uuid4()
        request_id = uuid4()
        
        with patch('app.services.silent_mode.websocket_service.manager.send_personal_message') as mock_send:
            result = await controller.deactivate_silent_mode(user_id, request_id, RingerMode.VIBRATE)
            
            assert result["status"] == "deactivated"
            assert result["platform"] == "ios"
            assert result["restored_mode"] == RingerMode.VIBRATE
            assert "deactivated_at" in result
            
            # Verify WebSocket message was sent
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert call_args[0][0] == str(user_id)  # user_id
            
            message_data = call_args[0][1]
            assert message_data["type"] == "silent_mode_command"
            assert "data" in message_data


class TestSilentModeService:
    """Test main silent mode service"""
    
    @pytest.fixture
    def service(self):
        """Create silent mode service instance"""
        return SilentModeService()
    
    @pytest.fixture
    def android_request(self):
        """Create Android silent mode request"""
        return SilentModeRequest(
            user_id=uuid4(),
            request_id=uuid4(),
            platform=Platform.ANDROID,
            duration_minutes=30
        )
    
    @pytest.fixture
    def ios_request(self):
        """Create iOS silent mode request"""
        return SilentModeRequest(
            user_id=uuid4(),
            request_id=uuid4(),
            platform=Platform.IOS,
            duration_minutes=45
        )
    
    @pytest.mark.asyncio
    async def test_activate_silent_mode_android(self, service, android_request):
        """Test activating silent mode for Android"""
        with patch.object(service.android_controller, 'activate_silent_mode') as mock_activate:
            with patch.object(service, '_store_user_status') as mock_store:
                with patch.object(service, '_add_to_active_sessions') as mock_add_session:
                    mock_activate.return_value = {
                        "status": "activated",
                        "platform": "android",
                        "activated_at": datetime.utcnow().isoformat()
                    }
                    
                    status = await service.activate_silent_mode(android_request)
                    
                    assert status.user_id == android_request.user_id
                    assert status.request_id == android_request.request_id
                    assert status.is_active is True
                    assert status.platform == Platform.ANDROID
                    assert status.activated_at is not None
                    assert status.expires_at is not None
                    
                    mock_activate.assert_called_once_with(
                        android_request.user_id,
                        android_request.request_id,
                        android_request.duration_minutes
                    )
                    mock_store.assert_called_once()
                    mock_add_session.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_activate_silent_mode_ios(self, service, ios_request):
        """Test activating silent mode for iOS"""
        with patch.object(service.ios_controller, 'activate_silent_mode') as mock_activate:
            with patch.object(service, '_store_user_status') as mock_store:
                with patch.object(service, '_add_to_active_sessions') as mock_add_session:
                    mock_activate.return_value = {
                        "status": "activated",
                        "platform": "ios",
                        "activated_at": datetime.utcnow().isoformat()
                    }
                    
                    status = await service.activate_silent_mode(ios_request)
                    
                    assert status.user_id == ios_request.user_id
                    assert status.request_id == ios_request.request_id
                    assert status.is_active is True
                    assert status.platform == Platform.IOS
                    assert status.activated_at is not None
                    assert status.expires_at is not None
                    
                    mock_activate.assert_called_once_with(
                        ios_request.user_id,
                        ios_request.request_id,
                        ios_request.duration_minutes
                    )
                    mock_store.assert_called_once()
                    mock_add_session.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_activate_silent_mode_already_active(self, service, android_request):
        """Test activating silent mode when already active"""
        existing_status = SilentModeStatus(
            user_id=android_request.user_id,
            request_id=uuid4(),
            is_active=True,
            activated_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(minutes=15),
            platform=Platform.ANDROID
        )
        
        with patch.object(service, 'get_user_status', return_value=existing_status):
            with patch.object(service, '_extend_silent_mode_session') as mock_extend:
                mock_extend.return_value = existing_status
                
                status = await service.activate_silent_mode(android_request)
                
                mock_extend.assert_called_once_with(
                    android_request.user_id,
                    android_request.duration_minutes
                )
                assert status == existing_status
    
    @pytest.mark.asyncio
    async def test_deactivate_silent_mode(self, service):
        """Test deactivating silent mode"""
        user_id = uuid4()
        request_id = uuid4()
        
        active_status = SilentModeStatus(
            user_id=user_id,
            request_id=request_id,
            is_active=True,
            activated_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(minutes=15),
            platform=Platform.ANDROID
        )
        
        with patch.object(service, 'get_user_status', return_value=active_status):
            with patch.object(service.android_controller, 'deactivate_silent_mode') as mock_deactivate:
                with patch.object(service, '_remove_user_status') as mock_remove:
                    with patch.object(service, '_remove_from_active_sessions') as mock_remove_session:
                        mock_deactivate.return_value = {
                            "status": "deactivated",
                            "platform": "android"
                        }
                        
                        status = await service.deactivate_silent_mode(user_id, request_id)
                        
                        assert status.is_active is False
                        mock_deactivate.assert_called_once()
                        mock_remove.assert_called_once()
                        mock_remove_session.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_deactivate_silent_mode_not_active(self, service):
        """Test deactivating silent mode when not active"""
        user_id = uuid4()
        
        with patch.object(service, 'get_user_status', return_value=None):
            with pytest.raises(SilentModeError, match="No active silent mode session found"):
                await service.deactivate_silent_mode(user_id)
    
    @pytest.mark.asyncio
    async def test_deactivate_silent_mode_request_id_mismatch(self, service):
        """Test deactivating silent mode with wrong request ID"""
        user_id = uuid4()
        request_id = uuid4()
        wrong_request_id = uuid4()
        
        active_status = SilentModeStatus(
            user_id=user_id,
            request_id=request_id,
            is_active=True,
            platform=Platform.ANDROID
        )
        
        with patch.object(service, 'get_user_status', return_value=active_status):
            with pytest.raises(SilentModeError, match="Request ID mismatch"):
                await service.deactivate_silent_mode(user_id, wrong_request_id)
    
    @pytest.mark.asyncio
    async def test_get_user_status_not_found(self, service):
        """Test getting user status when not found"""
        user_id = uuid4()
        
        with patch('app.services.silent_mode.cache.get', return_value=None):
            status = await service.get_user_status(user_id)
            assert status is None
    
    @pytest.mark.asyncio
    async def test_get_user_status_found(self, service):
        """Test getting user status when found"""
        user_id = uuid4()
        request_id = uuid4()
        
        cached_data = {
            "user_id": str(user_id),
            "request_id": str(request_id),
            "is_active": True,
            "activated_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(minutes=30)).isoformat(),
            "platform": "android"
        }
        
        import json
        with patch('app.services.silent_mode.cache.get', return_value=json.dumps(cached_data)):
            status = await service.get_user_status(user_id)
            
            assert status is not None
            assert status.user_id == user_id
            assert status.request_id == request_id
            assert status.is_active is True
            assert status.platform == Platform.ANDROID
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self, service):
        """Test cleaning up expired sessions"""
        user_id = uuid4()
        expired_status = SilentModeStatus(
            user_id=user_id,
            request_id=uuid4(),
            is_active=True,
            activated_at=datetime.utcnow() - timedelta(hours=1),
            expires_at=datetime.utcnow() - timedelta(minutes=30),  # Expired
            platform=Platform.ANDROID,
            original_mode=RingerMode.NORMAL
        )
        
        with patch.object(service, 'get_active_sessions', return_value=[expired_status]):
            with patch.object(service, 'deactivate_silent_mode') as mock_deactivate:
                await service.cleanup_expired_sessions()
                
                mock_deactivate.assert_called_once_with(
                    user_id,
                    expired_status.request_id,
                    RingerMode.NORMAL
                )
    
    @pytest.mark.asyncio
    async def test_extend_silent_mode_session(self, service):
        """Test extending silent mode session"""
        user_id = uuid4()
        
        existing_status = SilentModeStatus(
            user_id=user_id,
            request_id=uuid4(),
            is_active=True,
            activated_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(minutes=15),
            platform=Platform.ANDROID
        )
        
        with patch.object(service, 'get_user_status', return_value=existing_status):
            with patch.object(service, '_store_user_status') as mock_store:
                with patch.object(service, '_add_to_active_sessions') as mock_add_session:
                    status = await service._extend_silent_mode_session(user_id, 30)
                    
                    assert status.expires_at > existing_status.expires_at
                    mock_store.assert_called_once()
                    mock_add_session.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_unsupported_platform(self, service):
        """Test activating silent mode with unsupported platform"""
        # Create a request with an invalid platform (this would normally be caught by Pydantic)
        user_id = uuid4()
        request_id = uuid4()
        
        # Mock the request to have an invalid platform
        request = SilentModeRequest(
            user_id=user_id,
            request_id=request_id,
            platform=Platform.ANDROID  # We'll patch this
        )
        
        # Patch the platform to be invalid
        request.platform = "invalid_platform"
        
        with pytest.raises(SilentModeError, match="Unsupported platform"):
            await service.activate_silent_mode(request)


@pytest.mark.asyncio
async def test_global_silent_mode_service():
    """Test that global silent mode service instance works correctly"""
    user_id = uuid4()
    request_id = uuid4()
    
    request = SilentModeRequest(
        user_id=user_id,
        request_id=request_id,
        platform=Platform.ANDROID,
        duration_minutes=15
    )
    
    with patch.object(silent_mode_service.android_controller, 'activate_silent_mode') as mock_activate:
        with patch.object(silent_mode_service, '_store_user_status'):
            with patch.object(silent_mode_service, '_add_to_active_sessions'):
                mock_activate.return_value = {
                    "status": "activated",
                    "platform": "android",
                    "activated_at": datetime.utcnow().isoformat()
                }
                
                status = await silent_mode_service.activate_silent_mode(request)
                
                assert status.user_id == user_id
                assert status.request_id == request_id
                assert status.is_active is True
                assert status.platform == Platform.ANDROID


class TestEnumValues:
    """Test enum values"""
    
    def test_ringer_mode_values(self):
        """Test RingerMode enum values"""
        assert RingerMode.NORMAL == "normal"
        assert RingerMode.SILENT == "silent"
        assert RingerMode.VIBRATE == "vibrate"
    
    def test_platform_values(self):
        """Test Platform enum values"""
        assert Platform.ANDROID == "android"
        assert Platform.IOS == "ios"