"""
Geolocation validation and spatial services
"""
from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from geoalchemy2 import functions as geo_func
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import Point
import math

from app.core.database import get_db
from app.models.security_firm import CoverageArea, SecurityFirm
from app.models.emergency import ServiceProvider
from app.models.user import UserGroup


class GeolocationService:
    """Service for geospatial operations and coverage validation"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def validate_location_in_coverage(
        self, 
        latitude: float, 
        longitude: float, 
        firm_id: UUID
    ) -> bool:
        """
        Validate if a location point is within any coverage area of a security firm
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            firm_id: Security firm UUID
            
        Returns:
            bool: True if location is within coverage, False otherwise
        """
        # Create point geometry from coordinates
        point = f"POINT({longitude} {latitude})"
        
        # Query to check if point is within any coverage area of the firm
        query = text("""
            SELECT COUNT(*) > 0 as is_covered
            FROM coverage_areas ca
            WHERE ca.firm_id = :firm_id
            AND ST_Contains(ca.boundary, ST_GeomFromText(:point, 4326))
        """)
        
        result = self.db.execute(query, {
            "firm_id": str(firm_id),
            "point": point
        }).fetchone()
        
        return bool(result.is_covered) if result else False
    
    async def find_covering_firms(
        self, 
        latitude: float, 
        longitude: float
    ) -> List[SecurityFirm]:
        """
        Find all security firms that cover a specific location
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            
        Returns:
            List[SecurityFirm]: List of security firms covering the location
        """
        point = f"POINT({longitude} {latitude})"
        
        query = text("""
            SELECT DISTINCT sf.*
            FROM security_firms sf
            JOIN coverage_areas ca ON sf.id = ca.firm_id
            WHERE ST_Contains(ca.boundary, ST_GeomFromText(:point, 4326))
            AND sf.verification_status = 'approved'
        """)
        
        result = self.db.execute(query, {"point": point}).fetchall()
        
        # Convert to SecurityFirm objects
        firms = []
        for row in result:
            firm = self.db.query(SecurityFirm).filter(SecurityFirm.id == row.id).first()
            if firm:
                firms.append(firm)
        
        return firms
    
    async def calculate_distance_km(
        self, 
        lat1: float, 
        lon1: float, 
        lat2: float, 
        lon2: float
    ) -> float:
        """
        Calculate distance between two points using PostGIS
        
        Args:
            lat1, lon1: First point coordinates
            lat2, lon2: Second point coordinates
            
        Returns:
            float: Distance in kilometers
        """
        query = text("""
            SELECT ST_Distance(
                ST_GeomFromText(:point1, 4326)::geography,
                ST_GeomFromText(:point2, 4326)::geography
            ) / 1000.0 as distance_km
        """)
        
        result = self.db.execute(query, {
            "point1": f"POINT({lon1} {lat1})",
            "point2": f"POINT({lon2} {lat2})"
        }).fetchone()
        
        return float(result.distance_km) if result else 0.0
    
    async def calculate_haversine_distance(
        self, 
        lat1: float, 
        lon1: float, 
        lat2: float, 
        lon2: float
    ) -> float:
        """
        Calculate distance using Haversine formula (fallback method)
        
        Args:
            lat1, lon1: First point coordinates
            lat2, lon2: Second point coordinates
            
        Returns:
            float: Distance in kilometers
        """
        # Convert latitude and longitude from degrees to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Radius of earth in kilometers
        r = 6371
        
        return c * r
    
    async def find_nearest_service_providers(
        self, 
        latitude: float, 
        longitude: float, 
        service_type: str,
        firm_id: UUID,
        max_distance_km: float = 50.0,
        limit: int = 10
    ) -> List[Tuple[ServiceProvider, float]]:
        """
        Find nearest service providers of a specific type within distance limit
        
        Args:
            latitude: Request location latitude
            longitude: Request location longitude
            service_type: Type of service (ambulance, fire, towing)
            firm_id: Security firm UUID
            max_distance_km: Maximum search distance in kilometers
            limit: Maximum number of providers to return
            
        Returns:
            List[Tuple[ServiceProvider, float]]: List of (provider, distance_km) tuples
        """
        point = f"POINT({longitude} {latitude})"
        
        query = text("""
            SELECT sp.*, 
                   ST_Distance(
                       sp.location::geography,
                       ST_GeomFromText(:point, 4326)::geography
                   ) / 1000.0 as distance_km
            FROM service_providers sp
            WHERE sp.firm_id = :firm_id
            AND sp.service_type = :service_type
            AND sp.is_active = true
            AND ST_Distance(
                sp.location::geography,
                ST_GeomFromText(:point, 4326)::geography
            ) / 1000.0 <= :max_distance_km
            ORDER BY distance_km ASC
            LIMIT :limit
        """)
        
        result = self.db.execute(query, {
            "point": point,
            "firm_id": str(firm_id),
            "service_type": service_type,
            "max_distance_km": max_distance_km,
            "limit": limit
        }).fetchall()
        
        providers_with_distance = []
        for row in result:
            provider = self.db.query(ServiceProvider).filter(
                ServiceProvider.id == row.id
            ).first()
            if provider:
                providers_with_distance.append((provider, float(row.distance_km)))
        
        return providers_with_distance
    
    async def validate_group_location_coverage(
        self, 
        group_id: UUID
    ) -> Tuple[bool, Optional[List[SecurityFirm]]]:
        """
        Validate if a user group's location is covered by any security firm
        
        Args:
            group_id: User group UUID
            
        Returns:
            Tuple[bool, Optional[List[SecurityFirm]]]: (is_covered, covering_firms)
        """
        group = self.db.query(UserGroup).filter(UserGroup.id == group_id).first()
        if not group:
            return False, None
        
        # Extract coordinates from PostGIS point
        point_shape = to_shape(group.location)
        latitude = point_shape.y
        longitude = point_shape.x
        
        covering_firms = await self.find_covering_firms(latitude, longitude)
        
        return len(covering_firms) > 0, covering_firms
    
    async def get_coverage_area_center(self, coverage_area_id: UUID) -> Optional[Tuple[float, float]]:
        """
        Get the center point of a coverage area
        
        Args:
            coverage_area_id: Coverage area UUID
            
        Returns:
            Optional[Tuple[float, float]]: (latitude, longitude) or None
        """
        query = text("""
            SELECT ST_Y(ST_Centroid(boundary)) as latitude,
                   ST_X(ST_Centroid(boundary)) as longitude
            FROM coverage_areas
            WHERE id = :coverage_area_id
        """)
        
        result = self.db.execute(query, {
            "coverage_area_id": str(coverage_area_id)
        }).fetchone()
        
        if result:
            return float(result.latitude), float(result.longitude)
        
        return None
    
    async def get_coverage_area_bounds(
        self, 
        coverage_area_id: UUID
    ) -> Optional[Tuple[float, float, float, float]]:
        """
        Get the bounding box of a coverage area
        
        Args:
            coverage_area_id: Coverage area UUID
            
        Returns:
            Optional[Tuple[float, float, float, float]]: (min_lat, min_lon, max_lat, max_lon)
        """
        query = text("""
            SELECT ST_YMin(boundary) as min_lat,
                   ST_XMin(boundary) as min_lon,
                   ST_YMax(boundary) as max_lat,
                   ST_XMax(boundary) as max_lon
            FROM coverage_areas
            WHERE id = :coverage_area_id
        """)
        
        result = self.db.execute(query, {
            "coverage_area_id": str(coverage_area_id)
        }).fetchone()
        
        if result:
            return (
                float(result.min_lat),
                float(result.min_lon),
                float(result.max_lat),
                float(result.max_lon)
            )
        
        return None
    
    async def is_location_within_distance(
        self, 
        lat1: float, 
        lon1: float, 
        lat2: float, 
        lon2: float, 
        max_distance_km: float
    ) -> bool:
        """
        Check if two locations are within a specified distance
        
        Args:
            lat1, lon1: First location coordinates
            lat2, lon2: Second location coordinates
            max_distance_km: Maximum distance in kilometers
            
        Returns:
            bool: True if locations are within distance, False otherwise
        """
        distance = await self.calculate_distance_km(lat1, lon1, lat2, lon2)
        return distance <= max_distance_km


def get_geolocation_service(db: Session = None) -> GeolocationService:
    """
    Factory function to get GeolocationService instance
    
    Args:
        db: Database session (optional, will create new if not provided)
        
    Returns:
        GeolocationService: Service instance
    """
    if db is None:
        db = next(get_db())
    
    return GeolocationService(db)