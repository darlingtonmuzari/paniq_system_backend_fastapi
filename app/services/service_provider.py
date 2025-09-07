"""
Service provider location management service
"""
from typing import List, Optional, Tuple, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text, and_, or_, func
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from app.core.database import get_db
from app.models.emergency import ServiceProvider
from app.models.security_firm import SecurityFirm
from app.services.geolocation import GeolocationService


class ServiceProviderLocationService:
    """Service for managing service provider locations and availability"""
    
    def __init__(self, db: Session):
        self.db = db
        self.geolocation_service = GeolocationService(db)
    
    async def register_service_provider(
        self,
        firm_id: UUID,
        name: str,
        service_type: str,
        email: str,
        phone: str,
        address: str,
        latitude: float,
        longitude: float
    ) -> ServiceProvider:
        """
        Register a new service provider with GPS coordinates
        
        Args:
            firm_id: Security firm UUID
            name: Provider name
            service_type: Type of service (ambulance, fire, towing)
            email: Contact email
            phone: Contact phone
            address: Physical address
            latitude: GPS latitude
            longitude: GPS longitude
            
        Returns:
            ServiceProvider: Created service provider
        """
        # Validate service type
        valid_types = ["ambulance", "fire", "towing"]
        if service_type not in valid_types:
            raise ValueError(f"Invalid service type. Must be one of: {valid_types}")
        
        # Create PostGIS point from coordinates
        location_point = from_shape(Point(longitude, latitude))
        
        # Create service provider
        provider = ServiceProvider(
            firm_id=firm_id,
            name=name,
            service_type=service_type,
            email=email,
            phone=phone,
            address=address,
            location=location_point,
            is_active=True
        )
        
        self.db.add(provider)
        self.db.commit()
        self.db.refresh(provider)
        
        return provider
    
    async def update_service_provider_location(
        self,
        provider_id: UUID,
        latitude: float,
        longitude: float,
        address: Optional[str] = None
    ) -> Optional[ServiceProvider]:
        """
        Update service provider location
        
        Args:
            provider_id: Service provider UUID
            latitude: New GPS latitude
            longitude: New GPS longitude
            address: New address (optional)
            
        Returns:
            Optional[ServiceProvider]: Updated provider or None if not found
        """
        provider = self.db.query(ServiceProvider).filter(
            ServiceProvider.id == provider_id
        ).first()
        
        if not provider:
            return None
        
        # Update location
        location_point = from_shape(Point(longitude, latitude))
        provider.location = location_point
        
        if address:
            provider.address = address
        
        provider.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(provider)
        
        return provider
    
    async def find_providers_by_location(
        self,
        latitude: float,
        longitude: float,
        service_type: Optional[str] = None,
        firm_id: Optional[UUID] = None,
        max_distance_km: float = 50.0,
        limit: int = 20
    ) -> List[Tuple[ServiceProvider, float]]:
        """
        Find service providers near a location
        
        Args:
            latitude: Search center latitude
            longitude: Search center longitude
            service_type: Filter by service type (optional)
            firm_id: Filter by security firm (optional)
            max_distance_km: Maximum search distance in kilometers
            limit: Maximum number of results
            
        Returns:
            List[Tuple[ServiceProvider, float]]: List of (provider, distance_km) tuples
        """
        point = f"POINT({longitude} {latitude})"
        
        # Build query conditions
        conditions = ["sp.is_active = true"]
        params = {
            "point": point,
            "max_distance_km": max_distance_km,
            "limit": limit
        }
        
        if service_type:
            conditions.append("sp.service_type = :service_type")
            params["service_type"] = service_type
        
        if firm_id:
            conditions.append("sp.firm_id = :firm_id")
            params["firm_id"] = str(firm_id)
        
        where_clause = " AND ".join(conditions)
        
        query = text(f"""
            SELECT sp.*, 
                   ST_Distance(
                       sp.location::geography,
                       ST_GeomFromText(:point, 4326)::geography
                   ) / 1000.0 as distance_km
            FROM service_providers sp
            WHERE {where_clause}
            AND ST_Distance(
                sp.location::geography,
                ST_GeomFromText(:point, 4326)::geography
            ) / 1000.0 <= :max_distance_km
            ORDER BY distance_km ASC
            LIMIT :limit
        """)
        
        result = self.db.execute(query, params).fetchall()
        
        providers_with_distance = []
        for row in result:
            provider = self.db.query(ServiceProvider).filter(
                ServiceProvider.id == row.id
            ).first()
            if provider:
                providers_with_distance.append((provider, float(row.distance_km)))
        
        return providers_with_distance
    
    async def find_providers_in_coverage_area(
        self,
        coverage_area_id: UUID,
        service_type: Optional[str] = None
    ) -> List[ServiceProvider]:
        """
        Find service providers within a specific coverage area
        
        Args:
            coverage_area_id: Coverage area UUID
            service_type: Filter by service type (optional)
            
        Returns:
            List[ServiceProvider]: List of providers in coverage area
        """
        conditions = ["sp.is_active = true"]
        params = {"coverage_area_id": str(coverage_area_id)}
        
        if service_type:
            conditions.append("sp.service_type = :service_type")
            params["service_type"] = service_type
        
        where_clause = " AND ".join(conditions)
        
        query = text(f"""
            SELECT sp.*
            FROM service_providers sp
            JOIN coverage_areas ca ON ca.id = :coverage_area_id
            WHERE {where_clause}
            AND ST_Contains(ca.boundary, sp.location)
            ORDER BY sp.name
        """)
        
        result = self.db.execute(query, params).fetchall()
        
        providers = []
        for row in result:
            provider = self.db.query(ServiceProvider).filter(
                ServiceProvider.id == row.id
            ).first()
            if provider:
                providers.append(provider)
        
        return providers
    
    async def rank_providers_by_distance(
        self,
        providers: List[ServiceProvider],
        latitude: float,
        longitude: float
    ) -> List[Tuple[ServiceProvider, float]]:
        """
        Rank service providers by distance from a location
        
        Args:
            providers: List of service providers to rank
            latitude: Reference point latitude
            longitude: Reference point longitude
            
        Returns:
            List[Tuple[ServiceProvider, float]]: Ranked list of (provider, distance_km)
        """
        providers_with_distance = []
        
        for provider in providers:
            # Extract coordinates from provider location
            from geoalchemy2.shape import to_shape
            point_shape = to_shape(provider.location)
            provider_lat = point_shape.y
            provider_lon = point_shape.x
            
            # Calculate distance
            distance = await self.geolocation_service.calculate_distance_km(
                latitude, longitude, provider_lat, provider_lon
            )
            
            providers_with_distance.append((provider, distance))
        
        # Sort by distance
        providers_with_distance.sort(key=lambda x: x[1])
        
        return providers_with_distance
    
    async def get_provider_availability_status(
        self,
        provider_id: UUID,
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get service provider availability status based on recent activity
        
        Args:
            provider_id: Service provider UUID
            time_window_hours: Hours to look back for activity
            
        Returns:
            Dict[str, Any]: Availability status information
        """
        provider = self.db.query(ServiceProvider).filter(
            ServiceProvider.id == provider_id
        ).first()
        
        if not provider:
            return {"available": False, "reason": "Provider not found"}
        
        if not provider.is_active:
            return {"available": False, "reason": "Provider inactive"}
        
        # Check recent request assignments
        cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
        
        query = text("""
            SELECT COUNT(*) as active_requests,
                   COUNT(CASE WHEN pr.status IN ('pending', 'accepted') THEN 1 END) as pending_requests,
                   MAX(pr.created_at) as last_request_time
            FROM panic_requests pr
            WHERE pr.assigned_service_provider_id = :provider_id
            AND pr.created_at >= :cutoff_time
        """)
        
        result = self.db.execute(query, {
            "provider_id": str(provider_id),
            "cutoff_time": cutoff_time
        }).fetchone()
        
        active_requests = result.active_requests if result else 0
        pending_requests = result.pending_requests if result else 0
        last_request_time = result.last_request_time if result else None
        
        # Determine availability based on workload
        if pending_requests >= 3:  # Configurable threshold
            availability_status = "busy"
            available = False
        elif pending_requests >= 1:
            availability_status = "limited"
            available = True
        else:
            availability_status = "available"
            available = True
        
        return {
            "available": available,
            "status": availability_status,
            "active_requests": active_requests,
            "pending_requests": pending_requests,
            "last_request_time": last_request_time,
            "provider_name": provider.name,
            "service_type": provider.service_type
        }
    
    async def update_provider_availability(
        self,
        provider_id: UUID,
        is_active: bool
    ) -> Optional[ServiceProvider]:
        """
        Update service provider availability status
        
        Args:
            provider_id: Service provider UUID
            is_active: New availability status
            
        Returns:
            Optional[ServiceProvider]: Updated provider or None if not found
        """
        provider = self.db.query(ServiceProvider).filter(
            ServiceProvider.id == provider_id
        ).first()
        
        if not provider:
            return None
        
        provider.is_active = is_active
        provider.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(provider)
        
        return provider
    
    async def get_providers_by_firm(
        self,
        firm_id: UUID,
        service_type: Optional[str] = None,
        active_only: bool = True
    ) -> List[ServiceProvider]:
        """
        Get all service providers for a security firm
        
        Args:
            firm_id: Security firm UUID
            service_type: Filter by service type (optional)
            active_only: Only return active providers
            
        Returns:
            List[ServiceProvider]: List of providers
        """
        query = self.db.query(ServiceProvider).filter(
            ServiceProvider.firm_id == firm_id
        )
        
        if service_type:
            query = query.filter(ServiceProvider.service_type == service_type)
        
        if active_only:
            query = query.filter(ServiceProvider.is_active == True)
        
        return query.order_by(ServiceProvider.name).all()
    
    async def get_provider_statistics(
        self,
        provider_id: UUID,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get service provider performance statistics
        
        Args:
            provider_id: Service provider UUID
            days: Number of days to analyze
            
        Returns:
            Dict[str, Any]: Provider statistics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        query = text("""
            SELECT 
                COUNT(*) as total_requests,
                COUNT(CASE WHEN pr.status = 'completed' THEN 1 END) as completed_requests,
                COUNT(CASE WHEN pr.status = 'cancelled' THEN 1 END) as cancelled_requests,
                AVG(CASE 
                    WHEN pr.arrived_at IS NOT NULL AND pr.accepted_at IS NOT NULL 
                    THEN EXTRACT(EPOCH FROM (pr.arrived_at - pr.accepted_at)) / 60.0 
                END) as avg_response_time_minutes,
                AVG(CASE 
                    WHEN rf.performance_rating IS NOT NULL 
                    THEN rf.performance_rating 
                END) as avg_rating
            FROM panic_requests pr
            LEFT JOIN request_feedback rf ON pr.id = rf.request_id
            WHERE pr.assigned_service_provider_id = :provider_id
            AND pr.created_at >= :cutoff_date
        """)
        
        result = self.db.execute(query, {
            "provider_id": str(provider_id),
            "cutoff_date": cutoff_date
        }).fetchone()
        
        if not result:
            return {
                "total_requests": 0,
                "completed_requests": 0,
                "cancelled_requests": 0,
                "completion_rate": 0.0,
                "avg_response_time_minutes": None,
                "avg_rating": None
            }
        
        total_requests = result.total_requests or 0
        completed_requests = result.completed_requests or 0
        completion_rate = (completed_requests / total_requests * 100) if total_requests > 0 else 0.0
        
        return {
            "total_requests": total_requests,
            "completed_requests": completed_requests,
            "cancelled_requests": result.cancelled_requests or 0,
            "completion_rate": round(completion_rate, 2),
            "avg_response_time_minutes": round(result.avg_response_time_minutes, 2) if result.avg_response_time_minutes else None,
            "avg_rating": round(result.avg_rating, 2) if result.avg_rating else None
        }
    
    async def find_optimal_provider(
        self,
        latitude: float,
        longitude: float,
        service_type: str,
        firm_id: UUID,
        max_distance_km: float = 30.0
    ) -> Optional[Tuple[ServiceProvider, float, Dict[str, Any]]]:
        """
        Find the optimal service provider considering distance and availability
        
        Args:
            latitude: Request location latitude
            longitude: Request location longitude
            service_type: Required service type
            firm_id: Security firm UUID
            max_distance_km: Maximum search distance
            
        Returns:
            Optional[Tuple[ServiceProvider, float, Dict]]: (provider, distance, availability_info)
        """
        # Find nearby providers
        nearby_providers = await self.find_providers_by_location(
            latitude, longitude, service_type, firm_id, max_distance_km
        )
        
        if not nearby_providers:
            return None
        
        # Score providers based on distance and availability
        best_provider = None
        best_score = float('inf')
        best_distance = 0
        best_availability = {}
        
        for provider, distance in nearby_providers:
            availability = await self.get_provider_availability_status(provider.id)
            
            if not availability["available"]:
                continue
            
            # Calculate score (lower is better)
            # Distance weight: 1.0, Pending requests weight: 5.0 (km equivalent)
            score = distance + (availability["pending_requests"] * 5.0)
            
            if score < best_score:
                best_score = score
                best_provider = provider
                best_distance = distance
                best_availability = availability
        
        if best_provider:
            return best_provider, best_distance, best_availability
        
        return None


def get_service_provider_service(db: Session = None) -> ServiceProviderLocationService:
    """
    Factory function to get ServiceProviderLocationService instance
    
    Args:
        db: Database session (optional, will create new if not provided)
        
    Returns:
        ServiceProviderLocationService: Service instance
    """
    if db is None:
        db = next(get_db())
    
    return ServiceProviderLocationService(db)