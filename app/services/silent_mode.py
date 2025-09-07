"""
Silent mode service for controlling phone ringer settings during call service requests
"""
import asyncio
from typing import Dict, Optional, Any, List
from uuid import UUID
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel
import structlog

from app.core.redis import cache
from app.core.exceptions import APIError, ErrorCodes
from app.services.websocket import websocket_service, RealtimeUpdate

logger = structlog.get_logger()


class RingerMode(str, Enum):
    """Phone ringer modes"""
    NORMAL = "normal"
    SILENT = "silent"
    VIBRATE = "vibrate"


class Platform(str, Enum):
    """Mobile platforms"""
    ANDROID = "android"
    IOS = "ios"


class SilentModeRequest(BaseModel):
    """Silent mode activation request"""
    user_id: UUID
    request_id: UUID
    platform: Platform
    duration_minutes: int = 30  # Default 30 minutes
    restore_mode: RingerMode = RingerMode.NORMAL
    metadata: Dict[str, Any] = {}


class SilentModeStatus(BaseModel):
    """Silent mode status"""
    user_id: UUID
    request_id: Optional[UUID] = None
    is_active: bool
    activated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    original_mode: Optional[RingerMode] = None
    platform: Optional[Platform] = None


class SilentModeError(APIError):
    """Silent mode operation error"""
    def __init__(self, message: str = "Silent mode operation failed"):
        super().__init__(ErrorCodes.SILENT_MODE_FAILED, message)


class AndroidSilentModeController:
    """Android-specific silent mode controller"""
    
    async def activate_silent_mode(
        self,
        user_id: UUID,
        request_id: UUID,
        duration_minutes: int = 30
    ) -> Dict[str, Any]:
        """
        Activate silent mode on Android device
        
        Args:
            user_id: User ID
            request_id: Emergency request ID
            duration_minutes: Duration to keep silent mode active
            
        Returns:
            Dict with activation details
        """
        try:
            # Send WebSocket command to mobile app to activate silent mode
            command = {
                "type": "activate_silent_mode",
                "request_id": str(request_id),
                "duration_minutes": duration_minutes,
                "platform_specific": {
                    "android": {
                        "use_do_not_disturb": True,
                        "allow_emergency_calls": True,
                        "allow_alarms": True,
                        "priority_mode": "emergency_only"
                    }
                }
            }
            
            # Send command via WebSocket
            await websocket_service.manager.send_personal_message(
                str(user_id),
                {
                    "type": "silent_mode_command",
                    "data": command,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            logger.info(
                "android_silent_mode_activated",
                user_id=str(user_id),
                request_id=str(request_id),
                duration_minutes=duration_minutes
            )
            
            return {
                "status": "activated",
                "platform": "android",
                "method": "do_not_disturb",
                "duration_minutes": duration_minutes,
                "activated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(
                "android_silent_mode_activation_failed",
                user_id=str(user_id),
                request_id=str(request_id),
                error=str(e)
            )
            raise SilentModeError(f"Failed to activate Android silent mode: {str(e)}")
    
    async def deactivate_silent_mode(
        self,
        user_id: UUID,
        request_id: UUID,
        restore_mode: RingerMode = RingerMode.NORMAL
    ) -> Dict[str, Any]:
        """
        Deactivate silent mode on Android device
        
        Args:
            user_id: User ID
            request_id: Emergency request ID
            restore_mode: Mode to restore to
            
        Returns:
            Dict with deactivation details
        """
        try:
            # Send WebSocket command to mobile app to deactivate silent mode
            command = {
                "type": "deactivate_silent_mode",
                "request_id": str(request_id),
                "restore_mode": restore_mode,
                "platform_specific": {
                    "android": {
                        "restore_previous_settings": True,
                        "target_mode": restore_mode
                    }
                }
            }
            
            # Send command via WebSocket
            await websocket_service.manager.send_personal_message(
                str(user_id),
                {
                    "type": "silent_mode_command",
                    "data": command,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            logger.info(
                "android_silent_mode_deactivated",
                user_id=str(user_id),
                request_id=str(request_id),
                restore_mode=restore_mode
            )
            
            return {
                "status": "deactivated",
                "platform": "android",
                "restored_mode": restore_mode,
                "deactivated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(
                "android_silent_mode_deactivation_failed",
                user_id=str(user_id),
                request_id=str(request_id),
                error=str(e)
            )
            raise SilentModeError(f"Failed to deactivate Android silent mode: {str(e)}")


class IOSSilentModeController:
    """iOS-specific silent mode controller"""
    
    async def activate_silent_mode(
        self,
        user_id: UUID,
        request_id: UUID,
        duration_minutes: int = 30
    ) -> Dict[str, Any]:
        """
        Activate silent mode on iOS device
        
        Args:
            user_id: User ID
            request_id: Emergency request ID
            duration_minutes: Duration to keep silent mode active
            
        Returns:
            Dict with activation details
        """
        try:
            # Send WebSocket command to mobile app to activate silent mode
            command = {
                "type": "activate_silent_mode",
                "request_id": str(request_id),
                "duration_minutes": duration_minutes,
                "platform_specific": {
                    "ios": {
                        "use_focus_mode": True,
                        "focus_mode_name": "Emergency",
                        "allow_emergency_calls": True,
                        "allow_critical_alerts": True,
                        "silence_notifications": True
                    }
                }
            }
            
            # Send command via WebSocket
            await websocket_service.manager.send_personal_message(
                str(user_id),
                {
                    "type": "silent_mode_command",
                    "data": command,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            logger.info(
                "ios_silent_mode_activated",
                user_id=str(user_id),
                request_id=str(request_id),
                duration_minutes=duration_minutes
            )
            
            return {
                "status": "activated",
                "platform": "ios",
                "method": "focus_mode",
                "duration_minutes": duration_minutes,
                "activated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(
                "ios_silent_mode_activation_failed",
                user_id=str(user_id),
                request_id=str(request_id),
                error=str(e)
            )
            raise SilentModeError(f"Failed to activate iOS silent mode: {str(e)}")
    
    async def deactivate_silent_mode(
        self,
        user_id: UUID,
        request_id: UUID,
        restore_mode: RingerMode = RingerMode.NORMAL
    ) -> Dict[str, Any]:
        """
        Deactivate silent mode on iOS device
        
        Args:
            user_id: User ID
            request_id: Emergency request ID
            restore_mode: Mode to restore to
            
        Returns:
            Dict with deactivation details
        """
        try:
            # Send WebSocket command to mobile app to deactivate silent mode
            command = {
                "type": "deactivate_silent_mode",
                "request_id": str(request_id),
                "restore_mode": restore_mode,
                "platform_specific": {
                    "ios": {
                        "disable_focus_mode": True,
                        "restore_previous_settings": True,
                        "target_mode": restore_mode
                    }
                }
            }
            
            # Send command via WebSocket
            await websocket_service.manager.send_personal_message(
                str(user_id),
                {
                    "type": "silent_mode_command",
                    "data": command,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
            logger.info(
                "ios_silent_mode_deactivated",
                user_id=str(user_id),
                request_id=str(request_id),
                restore_mode=restore_mode
            )
            
            return {
                "status": "deactivated",
                "platform": "ios",
                "restored_mode": restore_mode,
                "deactivated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(
                "ios_silent_mode_deactivation_failed",
                user_id=str(user_id),
                request_id=str(request_id),
                error=str(e)
            )
            raise SilentModeError(f"Failed to deactivate iOS silent mode: {str(e)}")


class SilentModeService:
    """Main silent mode service"""
    
    def __init__(self):
        self.android_controller = AndroidSilentModeController()
        self.ios_controller = IOSSilentModeController()
        self.active_sessions_key = "silent_mode:active_sessions"
        self.user_status_key_prefix = "silent_mode:user:"
    
    async def activate_silent_mode(self, request: SilentModeRequest) -> SilentModeStatus:
        """
        Activate silent mode for a user
        
        Args:
            request: Silent mode activation request
            
        Returns:
            SilentModeStatus with activation details
            
        Raises:
            SilentModeError: If activation fails
        """
        # Check if user already has active silent mode
        existing_status = await self.get_user_status(request.user_id)
        if existing_status and existing_status.is_active:
            logger.warning(
                "silent_mode_already_active",
                user_id=str(request.user_id),
                existing_request_id=str(existing_status.request_id) if existing_status.request_id else None
            )
            # Extend the existing session instead of creating a new one
            return await self._extend_silent_mode_session(request.user_id, request.duration_minutes)
        
        try:
            # Activate silent mode based on platform
            if request.platform == Platform.ANDROID:
                result = await self.android_controller.activate_silent_mode(
                    request.user_id,
                    request.request_id,
                    request.duration_minutes
                )
            elif request.platform == Platform.IOS:
                result = await self.ios_controller.activate_silent_mode(
                    request.user_id,
                    request.request_id,
                    request.duration_minutes
                )
            else:
                raise SilentModeError(f"Unsupported platform: {request.platform}")
            
            # Create status record
            now = datetime.utcnow()
            expires_at = now + timedelta(minutes=request.duration_minutes)
            
            status = SilentModeStatus(
                user_id=request.user_id,
                request_id=request.request_id,
                is_active=True,
                activated_at=now,
                expires_at=expires_at,
                original_mode=request.restore_mode,
                platform=request.platform
            )
            
            # Store status in cache
            await self._store_user_status(status)
            
            # Add to active sessions for cleanup
            await self._add_to_active_sessions(request.user_id, expires_at)
            
            # Schedule automatic deactivation
            asyncio.create_task(
                self._schedule_auto_deactivation(request.user_id, request.duration_minutes)
            )
            
            logger.info(
                "silent_mode_activated",
                user_id=str(request.user_id),
                request_id=str(request.request_id),
                platform=request.platform,
                duration_minutes=request.duration_minutes
            )
            
            return status
            
        except Exception as e:
            logger.error(
                "silent_mode_activation_failed",
                user_id=str(request.user_id),
                request_id=str(request.request_id),
                error=str(e)
            )
            raise SilentModeError(f"Failed to activate silent mode: {str(e)}")
    
    async def deactivate_silent_mode(
        self,
        user_id: UUID,
        request_id: Optional[UUID] = None,
        restore_mode: RingerMode = RingerMode.NORMAL
    ) -> SilentModeStatus:
        """
        Deactivate silent mode for a user
        
        Args:
            user_id: User ID
            request_id: Optional request ID for verification
            restore_mode: Mode to restore to
            
        Returns:
            SilentModeStatus with deactivation details
            
        Raises:
            SilentModeError: If deactivation fails
        """
        # Get current status
        status = await self.get_user_status(user_id)
        if not status or not status.is_active:
            raise SilentModeError("No active silent mode session found")
        
        # Verify request ID if provided
        if request_id and status.request_id != request_id:
            raise SilentModeError("Request ID mismatch")
        
        try:
            # Deactivate silent mode based on platform
            if status.platform == Platform.ANDROID:
                result = await self.android_controller.deactivate_silent_mode(
                    user_id,
                    status.request_id,
                    restore_mode
                )
            elif status.platform == Platform.IOS:
                result = await self.ios_controller.deactivate_silent_mode(
                    user_id,
                    status.request_id,
                    restore_mode
                )
            else:
                raise SilentModeError(f"Unsupported platform: {status.platform}")
            
            # Update status
            status.is_active = False
            
            # Remove from cache
            await self._remove_user_status(user_id)
            await self._remove_from_active_sessions(user_id)
            
            logger.info(
                "silent_mode_deactivated",
                user_id=str(user_id),
                request_id=str(status.request_id) if status.request_id else None,
                platform=status.platform,
                restore_mode=restore_mode
            )
            
            return status
            
        except Exception as e:
            logger.error(
                "silent_mode_deactivation_failed",
                user_id=str(user_id),
                error=str(e)
            )
            raise SilentModeError(f"Failed to deactivate silent mode: {str(e)}")
    
    async def get_user_status(self, user_id: UUID) -> Optional[SilentModeStatus]:
        """
        Get silent mode status for a user
        
        Args:
            user_id: User ID
            
        Returns:
            SilentModeStatus or None if not found
        """
        try:
            cache_key = f"{self.user_status_key_prefix}{user_id}"
            status_data = await cache.get(cache_key)
            
            if not status_data:
                return None
            
            import json
            data = json.loads(status_data)
            
            # Parse datetime fields
            if data.get("activated_at"):
                data["activated_at"] = datetime.fromisoformat(data["activated_at"])
            if data.get("expires_at"):
                data["expires_at"] = datetime.fromisoformat(data["expires_at"])
            
            return SilentModeStatus(**data)
            
        except Exception as e:
            logger.error(
                "get_user_status_failed",
                user_id=str(user_id),
                error=str(e)
            )
            return None
    
    async def get_active_sessions(self) -> List[SilentModeStatus]:
        """
        Get all active silent mode sessions
        
        Returns:
            List of active SilentModeStatus objects
        """
        try:
            sessions_data = await cache.get(self.active_sessions_key)
            if not sessions_data:
                return []
            
            import json
            sessions = json.loads(sessions_data)
            
            active_statuses = []
            for user_id in sessions.keys():
                status = await self.get_user_status(UUID(user_id))
                if status and status.is_active:
                    active_statuses.append(status)
            
            return active_statuses
            
        except Exception as e:
            logger.error("get_active_sessions_failed", error=str(e))
            return []
    
    async def cleanup_expired_sessions(self):
        """Clean up expired silent mode sessions"""
        try:
            active_sessions = await self.get_active_sessions()
            now = datetime.utcnow()
            
            for status in active_sessions:
                if status.expires_at and status.expires_at <= now:
                    logger.info(
                        "cleaning_up_expired_session",
                        user_id=str(status.user_id),
                        expired_at=status.expires_at.isoformat()
                    )
                    
                    try:
                        await self.deactivate_silent_mode(
                            status.user_id,
                            status.request_id,
                            status.original_mode or RingerMode.NORMAL
                        )
                    except Exception as e:
                        logger.error(
                            "cleanup_session_failed",
                            user_id=str(status.user_id),
                            error=str(e)
                        )
            
        except Exception as e:
            logger.error("cleanup_expired_sessions_failed", error=str(e))
    
    async def _store_user_status(self, status: SilentModeStatus):
        """Store user status in cache"""
        cache_key = f"{self.user_status_key_prefix}{status.user_id}"
        
        # Convert to dict for JSON serialization
        data = status.model_dump()
        if data.get("activated_at"):
            data["activated_at"] = data["activated_at"].isoformat()
        if data.get("expires_at"):
            data["expires_at"] = data["expires_at"].isoformat()
        
        import json
        await cache.set(
            cache_key,
            json.dumps(data, default=str),
            expire=int((status.expires_at - datetime.utcnow()).total_seconds()) + 60  # Extra minute buffer
        )
    
    async def _remove_user_status(self, user_id: UUID):
        """Remove user status from cache"""
        cache_key = f"{self.user_status_key_prefix}{user_id}"
        await cache.delete(cache_key)
    
    async def _add_to_active_sessions(self, user_id: UUID, expires_at: datetime):
        """Add user to active sessions list"""
        try:
            sessions_data = await cache.get(self.active_sessions_key)
            if sessions_data:
                import json
                sessions = json.loads(sessions_data)
            else:
                sessions = {}
            
            sessions[str(user_id)] = expires_at.isoformat()
            
            import json
            await cache.set(
                self.active_sessions_key,
                json.dumps(sessions),
                expire=86400  # 24 hours
            )
            
        except Exception as e:
            logger.error("add_to_active_sessions_failed", user_id=str(user_id), error=str(e))
    
    async def _remove_from_active_sessions(self, user_id: UUID):
        """Remove user from active sessions list"""
        try:
            sessions_data = await cache.get(self.active_sessions_key)
            if not sessions_data:
                return
            
            import json
            sessions = json.loads(sessions_data)
            
            if str(user_id) in sessions:
                del sessions[str(user_id)]
                
                await cache.set(
                    self.active_sessions_key,
                    json.dumps(sessions),
                    expire=86400  # 24 hours
                )
            
        except Exception as e:
            logger.error("remove_from_active_sessions_failed", user_id=str(user_id), error=str(e))
    
    async def _extend_silent_mode_session(self, user_id: UUID, additional_minutes: int) -> SilentModeStatus:
        """Extend existing silent mode session"""
        status = await self.get_user_status(user_id)
        if not status:
            raise SilentModeError("No active session to extend")
        
        # Extend expiration time
        new_expires_at = datetime.utcnow() + timedelta(minutes=additional_minutes)
        status.expires_at = new_expires_at
        
        # Update cache
        await self._store_user_status(status)
        await self._add_to_active_sessions(user_id, new_expires_at)
        
        logger.info(
            "silent_mode_session_extended",
            user_id=str(user_id),
            additional_minutes=additional_minutes,
            new_expires_at=new_expires_at.isoformat()
        )
        
        return status
    
    async def _schedule_auto_deactivation(self, user_id: UUID, delay_minutes: int):
        """Schedule automatic deactivation of silent mode"""
        try:
            # Wait for the specified duration
            await asyncio.sleep(delay_minutes * 60)
            
            # Check if session is still active
            status = await self.get_user_status(user_id)
            if status and status.is_active:
                logger.info(
                    "auto_deactivating_silent_mode",
                    user_id=str(user_id),
                    delay_minutes=delay_minutes
                )
                
                await self.deactivate_silent_mode(
                    user_id,
                    status.request_id,
                    status.original_mode or RingerMode.NORMAL
                )
            
        except Exception as e:
            logger.error(
                "auto_deactivation_failed",
                user_id=str(user_id),
                error=str(e)
            )


# Global silent mode service instance
silent_mode_service = SilentModeService()