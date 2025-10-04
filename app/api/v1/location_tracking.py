"""
Location tracking API endpoints
"""
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import RegisteredUser
from app.services.location_log import LocationLogService


router = APIRouter()


class LocationUpdateRequest(BaseModel):
    """Request model for location updates"""
    request_id: UUID
    latitude: float = Field(..., ge=-90, le=90, description="Latitude coordinate")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude coordinate")
    address: Optional[str] = None
    accuracy: Optional[int] = Field(None, ge=0, description="GPS accuracy in meters")
    source: str = Field("mobile", description="Source of location update")
    update_panic_request: bool = Field(True, description="Whether to update the main panic request location")


class LocationLogResponse(BaseModel):
    """Response model for location log"""
    id: UUID
    request_id: UUID
    user_id: UUID
    latitude: float
    longitude: float
    address: Optional[str]
    accuracy: Optional[int]
    source: str
    created_at: datetime
    updated_at: datetime


class LocationLogsResponse(BaseModel):
    """Response model for multiple location logs"""
    logs: List[LocationLogResponse]
    total_count: int


@router.post("/update", response_model=LocationLogResponse)
async def update_location(
    location_data: LocationUpdateRequest,
    current_user: RegisteredUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update user location during a panic request
    
    This endpoint:
    1. Creates a new location log entry
    2. Optionally updates the main panic request location
    3. Can be called multiple times during an active request
    """
    service = LocationLogService(db)
    
    try:
        # Create location log entry
        location_log = await service.create_location_log(
            request_id=location_data.request_id,
            user_id=current_user.id,
            latitude=location_data.latitude,
            longitude=location_data.longitude,
            address=location_data.address,
            accuracy=location_data.accuracy,
            source=location_data.source
        )
        
        # Update panic request location if requested
        if location_data.update_panic_request:
            await service.update_panic_request_location(
                request_id=location_data.request_id,
                latitude=location_data.latitude,
                longitude=location_data.longitude,
                address=location_data.address
            )
        
        # Extract coordinates for response
        lat, lon = service.extract_coordinates(location_log)
        
        return LocationLogResponse(
            id=location_log.id,
            request_id=location_log.request_id,
            user_id=location_log.user_id,
            latitude=lat,
            longitude=lon,
            address=location_log.address,
            accuracy=location_log.accuracy,
            source=location_log.source,
            created_at=location_log.created_at,
            updated_at=location_log.updated_at
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update location: {str(e)}"
        )


@router.get("/request/{request_id}", response_model=LocationLogsResponse)
async def get_request_location_history(
    request_id: UUID,
    limit: int = 100,
    current_user: RegisteredUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get location history for a specific panic request
    """
    service = LocationLogService(db)
    
    try:
        location_logs = await service.get_location_logs_for_request(
            request_id=request_id,
            limit=limit
        )
        
        # Convert to response format
        log_responses = []
        for log in location_logs:
            lat, lon = service.extract_coordinates(log)
            log_responses.append(LocationLogResponse(
                id=log.id,
                request_id=log.request_id,
                user_id=log.user_id,
                latitude=lat,
                longitude=lon,
                address=log.address,
                accuracy=log.accuracy,
                source=log.source,
                created_at=log.created_at,
                updated_at=log.updated_at
            ))
        
        return LocationLogsResponse(
            logs=log_responses,
            total_count=len(log_responses)
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get location history: {str(e)}"
        )


@router.get("/request/{request_id}/latest", response_model=LocationLogResponse)
async def get_latest_location(
    request_id: UUID,
    current_user: RegisteredUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the most recent location for a panic request
    """
    service = LocationLogService(db)
    
    try:
        location_log = await service.get_latest_location_for_request(request_id)
        
        if not location_log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No location found for this request"
            )
        
        lat, lon = service.extract_coordinates(location_log)
        
        return LocationLogResponse(
            id=location_log.id,
            request_id=location_log.request_id,
            user_id=location_log.user_id,
            latitude=lat,
            longitude=lon,
            address=location_log.address,
            accuracy=location_log.accuracy,
            source=location_log.source,
            created_at=location_log.created_at,
            updated_at=location_log.updated_at
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get latest location: {str(e)}"
        )


class LocationDistanceResponse(BaseModel):
    """Response model for location distance calculation"""
    request_id: UUID
    distance_meters: Optional[float]
    from_time: datetime
    to_time: datetime


@router.get("/request/{request_id}/distance", response_model=LocationDistanceResponse)
async def get_location_distance(
    request_id: UUID,
    from_time: datetime,
    to_time: Optional[datetime] = None,
    current_user: RegisteredUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Calculate total distance traveled during a panic request
    """
    service = LocationLogService(db)
    
    try:
        if to_time is None:
            to_time = datetime.utcnow()
        
        distance = await service.get_location_distance(
            request_id=request_id,
            from_time=from_time,
            to_time=to_time
        )
        
        return LocationDistanceResponse(
            request_id=request_id,
            distance_meters=distance,
            from_time=from_time,
            to_time=to_time
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate distance: {str(e)}"
        )