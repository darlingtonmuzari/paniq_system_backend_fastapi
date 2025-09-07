"""
Silent mode API endpoints for mobile app ringer control
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.core.exceptions import APIError, ErrorCodes
from app.services.silent_mode import (
    silent_mode_service,
    SilentModeRequest,
    SilentModeStatus,
    RingerMode,
    Platform,
    SilentModeError
)
from app.models.user import RegisteredUser
import structlog

logger = structlog.get_logger()

router = APIRouter()


class SilentModeActivationRequest(BaseModel):
    """Request to activate silent mode"""
    request_id: UUID
    platform: Platform
    duration_minutes: int = 30
    restore_mode: RingerMode = RingerMode.NORMAL


class SilentModeDeactivationRequest(BaseModel):
    """Request to deactivate silent mode"""
    request_id: Optional[UUID] = None
    restore_mode: RingerMode = RingerMode.NORMAL


class SilentModeStatusResponse(BaseModel):
    """Silent mode status response"""
    user_id: UUID
    request_id: Optional[UUID]
    is_active: bool
    activated_at: Optional[str]
    expires_at: Optional[str]
    original_mode: Optional[RingerMode]
    platform: Optional[Platform]


@router.post("/activate", response_model=SilentModeStatusResponse)
async def activate_silent_mode(
    request: SilentModeActivationRequest,
    current_user: RegisteredUser = Depends(get_current_user)
):
    """
    Activate silent mode for the current user's mobile device
    
    This endpoint is called by mobile apps to activate silent mode
    during call service emergency requests.
    """
    try:
        # Create silent mode request
        silent_request = SilentModeRequest(
            user_id=current_user.user_id,
            request_id=request.request_id,
            platform=request.platform,
            duration_minutes=request.duration_minutes,
            restore_mode=request.restore_mode
        )
        
        # Activate silent mode
        status = await silent_mode_service.activate_silent_mode(silent_request)
        
        logger.info(
            "silent_mode_activated_via_api",
            user_id=str(current_user.user_id),
            request_id=str(request.request_id),
            platform=request.platform,
            duration_minutes=request.duration_minutes
        )
        
        # Convert to response model
        return SilentModeStatusResponse(
            user_id=status.user_id,
            request_id=status.request_id,
            is_active=status.is_active,
            activated_at=status.activated_at.isoformat() if status.activated_at else None,
            expires_at=status.expires_at.isoformat() if status.expires_at else None,
            original_mode=status.original_mode,
            platform=status.platform
        )
        
    except SilentModeError as e:
        logger.error(
            "silent_mode_activation_failed_via_api",
            user_id=str(current_user.user_id),
            request_id=str(request.request_id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": ErrorCodes.SILENT_MODE_FAILED,
                "message": str(e)
            }
        )
    except Exception as e:
        logger.error(
            "silent_mode_activation_unexpected_error",
            user_id=str(current_user.user_id),
            request_id=str(request.request_id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": ErrorCodes.INTERNAL_SERVER_ERROR,
                "message": "Failed to activate silent mode"
            }
        )


@router.post("/deactivate", response_model=SilentModeStatusResponse)
async def deactivate_silent_mode(
    request: SilentModeDeactivationRequest,
    current_user: RegisteredUser = Depends(get_current_user)
):
    """
    Deactivate silent mode for the current user's mobile device
    
    This endpoint is called by mobile apps to deactivate silent mode
    and restore normal ringer settings.
    """
    try:
        # Deactivate silent mode
        status = await silent_mode_service.deactivate_silent_mode(
            user_id=current_user.user_id,
            request_id=request.request_id,
            restore_mode=request.restore_mode
        )
        
        logger.info(
            "silent_mode_deactivated_via_api",
            user_id=str(current_user.user_id),
            request_id=str(request.request_id) if request.request_id else None,
            restore_mode=request.restore_mode
        )
        
        # Convert to response model
        return SilentModeStatusResponse(
            user_id=status.user_id,
            request_id=status.request_id,
            is_active=status.is_active,
            activated_at=status.activated_at.isoformat() if status.activated_at else None,
            expires_at=status.expires_at.isoformat() if status.expires_at else None,
            original_mode=status.original_mode,
            platform=status.platform
        )
        
    except SilentModeError as e:
        logger.error(
            "silent_mode_deactivation_failed_via_api",
            user_id=str(current_user.user_id),
            request_id=str(request.request_id) if request.request_id else None,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": ErrorCodes.SILENT_MODE_FAILED,
                "message": str(e)
            }
        )
    except Exception as e:
        logger.error(
            "silent_mode_deactivation_unexpected_error",
            user_id=str(current_user.user_id),
            request_id=str(request.request_id) if request.request_id else None,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": ErrorCodes.INTERNAL_SERVER_ERROR,
                "message": "Failed to deactivate silent mode"
            }
        )


@router.get("/status", response_model=Optional[SilentModeStatusResponse])
async def get_silent_mode_status(
    current_user: RegisteredUser = Depends(get_current_user)
):
    """
    Get the current silent mode status for the user
    
    Returns the current silent mode status or None if not active.
    """
    try:
        status = await silent_mode_service.get_user_status(current_user.user_id)
        
        if not status:
            return None
        
        return SilentModeStatusResponse(
            user_id=status.user_id,
            request_id=status.request_id,
            is_active=status.is_active,
            activated_at=status.activated_at.isoformat() if status.activated_at else None,
            expires_at=status.expires_at.isoformat() if status.expires_at else None,
            original_mode=status.original_mode,
            platform=status.platform
        )
        
    except Exception as e:
        logger.error(
            "get_silent_mode_status_failed",
            user_id=str(current_user.user_id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": ErrorCodes.INTERNAL_SERVER_ERROR,
                "message": "Failed to get silent mode status"
            }
        )


@router.get("/active-sessions", response_model=List[SilentModeStatusResponse])
async def get_active_sessions(
    current_user: RegisteredUser = Depends(get_current_user)
):
    """
    Get all active silent mode sessions (admin endpoint)
    
    This endpoint is primarily for debugging and monitoring purposes.
    In production, this should be restricted to admin users only.
    """
    try:
        # Note: In a real implementation, you'd want to check if the user is an admin
        # For now, we'll allow any authenticated user to see all sessions
        sessions = await silent_mode_service.get_active_sessions()
        
        return [
            SilentModeStatusResponse(
                user_id=session.user_id,
                request_id=session.request_id,
                is_active=session.is_active,
                activated_at=session.activated_at.isoformat() if session.activated_at else None,
                expires_at=session.expires_at.isoformat() if session.expires_at else None,
                original_mode=session.original_mode,
                platform=session.platform
            )
            for session in sessions
        ]
        
    except Exception as e:
        logger.error(
            "get_active_sessions_failed",
            user_id=str(current_user.user_id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": ErrorCodes.INTERNAL_SERVER_ERROR,
                "message": "Failed to get active sessions"
            }
        )


@router.post("/cleanup-expired")
async def cleanup_expired_sessions(
    current_user: RegisteredUser = Depends(get_current_user)
):
    """
    Manually trigger cleanup of expired silent mode sessions
    
    This endpoint is primarily for maintenance purposes.
    In production, this should be restricted to admin users only.
    """
    try:
        await silent_mode_service.cleanup_expired_sessions()
        
        logger.info(
            "silent_mode_cleanup_triggered",
            user_id=str(current_user.user_id)
        )
        
        return {"message": "Expired sessions cleanup completed"}
        
    except Exception as e:
        logger.error(
            "silent_mode_cleanup_failed",
            user_id=str(current_user.user_id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": ErrorCodes.INTERNAL_SERVER_ERROR,
                "message": "Failed to cleanup expired sessions"
            }
        )