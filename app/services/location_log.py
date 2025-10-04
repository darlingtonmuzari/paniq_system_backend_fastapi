"""
Location log service for tracking user location during panic requests
"""
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from geoalchemy2.functions import ST_X, ST_Y, ST_Distance
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from app.models.emergency import LocationLog, PanicRequest
from app.models.user import RegisteredUser


class LocationLogService:
    """Service for managing location logs"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_location_log(
        self,
        request_id: UUID,
        user_id: UUID,
        latitude: float,
        longitude: float,
        address: Optional[str] = None,
        accuracy: Optional[int] = None,
        source: str = "mobile"
    ) -> LocationLog:
        """
        Create a new location log entry
        
        Args:
            request_id: The panic request ID
            user_id: The user ID
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            address: Optional address string
            accuracy: GPS accuracy in meters
            source: Source of location (mobile, web, manual)
        
        Returns:
            The created LocationLog instance
        """
        # Create geometry point
        point = Point(longitude, latitude)
        
        location_log = LocationLog(
            request_id=request_id,
            user_id=user_id,
            location=from_shape(point, srid=4326),
            address=address,
            accuracy=accuracy,
            source=source
        )
        
        self.db.add(location_log)
        await self.db.commit()
        await self.db.refresh(location_log)
        
        return location_log

    async def get_location_logs_for_request(
        self,
        request_id: UUID,
        limit: int = 100
    ) -> List[LocationLog]:
        """
        Get all location logs for a specific panic request
        
        Args:
            request_id: The panic request ID
            limit: Maximum number of logs to return
        
        Returns:
            List of LocationLog instances
        """
        query = (
            select(LocationLog)
            .where(LocationLog.request_id == request_id)
            .order_by(LocationLog.created_at.desc())
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_latest_location_for_request(
        self,
        request_id: UUID
    ) -> Optional[LocationLog]:
        """
        Get the most recent location log for a panic request
        
        Args:
            request_id: The panic request ID
        
        Returns:
            The latest LocationLog or None if not found
        """
        query = (
            select(LocationLog)
            .where(LocationLog.request_id == request_id)
            .order_by(LocationLog.created_at.desc())
            .limit(1)
        )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_panic_request_location(
        self,
        request_id: UUID,
        latitude: float,
        longitude: float,
        address: Optional[str] = None
    ) -> bool:
        """
        Update the main location in the panic_requests table
        
        Args:
            request_id: The panic request ID
            latitude: New latitude
            longitude: New longitude
            address: New address
        
        Returns:
            True if update was successful, False otherwise
        """
        # Create geometry point
        point = Point(longitude, latitude)
        
        query = select(PanicRequest).where(PanicRequest.id == request_id)
        result = await self.db.execute(query)
        panic_request = result.scalar_one_or_none()
        
        if not panic_request:
            return False
        
        panic_request.location = from_shape(point, srid=4326)
        if address:
            panic_request.address = address
        
        await self.db.commit()
        return True

    def extract_coordinates(self, location_log: LocationLog) -> tuple[float, float]:
        """
        Extract latitude and longitude from a location log
        
        Args:
            location_log: LocationLog instance with geometry
        
        Returns:
            Tuple of (latitude, longitude)
        """
        from geoalchemy2.shape import to_shape
        point = to_shape(location_log.location)
        return point.y, point.x  # y is lat, x is lon

    async def get_location_distance(
        self,
        request_id: UUID,
        from_time: datetime,
        to_time: Optional[datetime] = None
    ) -> Optional[float]:
        """
        Calculate total distance traveled during a time period
        
        Args:
            request_id: The panic request ID
            from_time: Start time for calculation
            to_time: End time for calculation (defaults to now)
        
        Returns:
            Total distance in meters or None if insufficient data
        """
        to_time = to_time or datetime.utcnow()
        
        query = (
            select(LocationLog)
            .where(
                LocationLog.request_id == request_id,
                LocationLog.created_at >= from_time,
                LocationLog.created_at <= to_time
            )
            .order_by(LocationLog.created_at)
        )
        
        result = await self.db.execute(query)
        logs = result.scalars().all()
        
        if len(logs) < 2:
            return None
        
        total_distance = 0.0
        
        for i in range(1, len(logs)):
            # Calculate distance between consecutive points
            query = select(
                ST_Distance(logs[i-1].location, logs[i].location)
            )
            result = await self.db.execute(query)
            distance = result.scalar()
            total_distance += distance
        
        return total_distance