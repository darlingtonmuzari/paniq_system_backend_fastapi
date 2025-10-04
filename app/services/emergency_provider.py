"""
Emergency Provider service for managing ambulances, tow trucks, etc.
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, text, exists
from sqlalchemy.orm import selectinload
import math

from app.models.emergency_provider import EmergencyProvider, ProviderAssignment, ProviderType, ProviderStatus, EmergencyProviderType
from app.models.capability import ProviderCapability
from app.models.emergency import PanicRequest
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmergencyProviderService:
    """Service for managing emergency providers"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_provider(
        self,
        firm_id: UUID,
        name: str,
        provider_type: Optional[ProviderType],
        provider_type_id: UUID,
        contact_phone: str,
        street_address: str,
        city: str,
        province: str,
        postal_code: str,
        current_latitude: float,
        current_longitude: float,
        base_latitude: float,
        base_longitude: float,
        coverage_radius_km: float = 50.0,
        license_number: Optional[str] = None,
        contact_email: Optional[str] = None,
        country: str = "South Africa",
        description: Optional[str] = None,
        equipment_details: Optional[str] = None,
        capacity: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        status: Optional[ProviderStatus] = None
    ) -> EmergencyProvider:
        """Create a new emergency provider"""
        
        # Validate provider type exists and is active
        provider_type_query = select(EmergencyProviderType).where(
            EmergencyProviderType.id == provider_type_id
        )
        result = await self.db.execute(provider_type_query)
        provider_type_obj = result.scalar_one_or_none()
        
        if not provider_type_obj:
            raise ValueError(f"Provider type with ID {provider_type_id} not found")
        
        if not provider_type_obj.is_active:
            raise ValueError(f"Provider type '{provider_type_obj.name}' is not active")
        
        # If provider_type is not provided, derive it from the provider_type_obj code
        if not provider_type:
            try:
                provider_type = ProviderType(provider_type_obj.code)
            except ValueError:
                # If the code doesn't match any enum value, default to the first part of the code
                provider_type = ProviderType.AMBULANCE  # Default fallback
        
        provider = EmergencyProvider(
            firm_id=firm_id,
            name=name,
            provider_type=provider_type,
            provider_type_id=provider_type_id,
            license_number=license_number,
            contact_phone=contact_phone,
            contact_email=contact_email,
            street_address=street_address,
            city=city,
            province=province,
            country=country,
            postal_code=postal_code,
            current_latitude=current_latitude,
            current_longitude=current_longitude,
            base_latitude=base_latitude,
            base_longitude=base_longitude,
            coverage_radius_km=coverage_radius_km,
            description=description,
            equipment_details=equipment_details,
            capacity=capacity,
            capabilities=capabilities,
            status=status or ProviderStatus.AVAILABLE
        )
        
        self.db.add(provider)
        await self.db.commit()
        await self.db.refresh(provider)
        
        logger.info(
            "emergency_provider_created",
            provider_id=str(provider.id),
            firm_id=str(firm_id),
            provider_type=provider_type.value if provider_type else "unknown",
            name=name
        )
        
        return provider

    async def get_firm_providers(
        self,
        firm_id: UUID,
        provider_type: Optional[ProviderType] = None,
        status: Optional[ProviderStatus] = None,
        include_inactive: bool = False
    ) -> List[EmergencyProvider]:
        """Get all providers for a firm"""
        
        query = select(EmergencyProvider).options(
            selectinload(EmergencyProvider.provider_capabilities).selectinload(ProviderCapability.capability)
        ).where(EmergencyProvider.firm_id == firm_id)
        
        if not include_inactive:
            query = query.where(EmergencyProvider.is_active == True)
            
        if provider_type:
            query = query.where(EmergencyProvider.provider_type == provider_type)
            
        if status:
            query = query.where(EmergencyProvider.status == status)
            
        query = query.order_by(EmergencyProvider.name)
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_provider_by_id(self, provider_id: UUID) -> Optional[EmergencyProvider]:
        """Get provider by ID"""
        
        query = select(EmergencyProvider).where(EmergencyProvider.id == provider_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_provider(
        self,
        provider_id: UUID,
        name: Optional[str] = None,
        provider_type_id: Optional[UUID] = None,
        contact_phone: Optional[str] = None,
        contact_email: Optional[str] = None,
        street_address: Optional[str] = None,
        city: Optional[str] = None,
        province: Optional[str] = None,
        country: Optional[str] = None,
        postal_code: Optional[str] = None,
        current_latitude: Optional[float] = None,
        current_longitude: Optional[float] = None,
        base_latitude: Optional[float] = None,
        base_longitude: Optional[float] = None,
        coverage_radius_km: Optional[float] = None,
        status: Optional[ProviderStatus] = None,
        description: Optional[str] = None,
        equipment_details: Optional[str] = None,
        capacity: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        is_active: Optional[bool] = None
    ) -> Optional[EmergencyProvider]:
        """Update provider details"""
        
        provider = await self.get_provider_by_id(provider_id)
        if not provider:
            return None
            
        if name is not None:
            provider.name = name
        if provider_type_id is not None:
            # Validate that the new provider type exists and is active
            provider_type_obj = await self.validate_provider_type(provider_type_id)
            provider.provider_type_id = provider_type_id
            # Update the enum type as well based on the provider type code
            try:
                provider.provider_type = ProviderType(provider_type_obj.code)
            except ValueError:
                # If code doesn't match enum, keep the original or default
                pass
        if contact_phone is not None:
            provider.contact_phone = contact_phone
        if contact_email is not None:
            provider.contact_email = contact_email
        if street_address is not None:
            provider.street_address = street_address
        if city is not None:
            provider.city = city
        if province is not None:
            provider.province = province
        if country is not None:
            provider.country = country
        if postal_code is not None:
            provider.postal_code = postal_code
        if current_latitude is not None:
            provider.current_latitude = current_latitude
            provider.last_location_update = datetime.utcnow()
        if current_longitude is not None:
            provider.current_longitude = current_longitude
            provider.last_location_update = datetime.utcnow()
        if base_latitude is not None:
            provider.base_latitude = base_latitude
        if base_longitude is not None:
            provider.base_longitude = base_longitude
        if coverage_radius_km is not None:
            provider.coverage_radius_km = coverage_radius_km
        if status is not None:
            provider.status = status
        if description is not None:
            provider.description = description
        if equipment_details is not None:
            provider.equipment_details = equipment_details
        if capacity is not None:
            provider.capacity = capacity
        if capabilities is not None:
            provider.capabilities = capabilities
        if is_active is not None:
            provider.is_active = is_active
            
        await self.db.commit()
        await self.db.refresh(provider)
        
        logger.info(
            "emergency_provider_updated",
            provider_id=str(provider_id),
            updated_fields=[k for k, v in locals().items() if k not in ['self', 'provider_id', 'provider'] and v is not None]
        )
        
        return provider

    async def update_provider_location(
        self,
        provider_id: UUID,
        latitude: float,
        longitude: float
    ) -> Optional[EmergencyProvider]:
        """Update provider's current location"""
        
        provider = await self.get_provider_by_id(provider_id)
        if not provider:
            return None
            
        provider.current_latitude = latitude
        provider.current_longitude = longitude
        provider.last_location_update = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(provider)
        
        return provider

    async def delete_provider(self, provider_id: UUID) -> bool:
        """Delete a provider (soft delete by setting inactive)"""
        
        provider = await self.get_provider_by_id(provider_id)
        if not provider:
            return False
            
        # Check if provider has active assignments
        active_assignments = await self.db.execute(
            select(ProviderAssignment).where(
                and_(
                    ProviderAssignment.provider_id == provider_id,
                    ProviderAssignment.status.in_(["assigned", "en_route", "arrived"])
                )
            )
        )
        
        if active_assignments.scalars().first():
            raise ValueError("Cannot delete provider with active assignments")
            
        provider.is_active = False
        await self.db.commit()
        
        logger.info(
            "emergency_provider_deleted",
            provider_id=str(provider_id)
        )
        
        return True

    def calculate_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        """Calculate distance between two points using Haversine formula"""
        
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

    async def find_nearest_providers(
        self,
        latitude: float,
        longitude: float,
        provider_type: ProviderType,
        max_distance_km: float = 100.0,
        limit: int = 10,
        firm_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Find nearest available providers to a location"""
        
        # Build base query
        query = select(EmergencyProvider).where(
            and_(
                EmergencyProvider.provider_type == provider_type,
                EmergencyProvider.status == ProviderStatus.AVAILABLE,
                EmergencyProvider.is_active == True
            )
        )
        
        # Filter by firm if specified
        if firm_id:
            query = query.where(EmergencyProvider.firm_id == firm_id)
        
        result = await self.db.execute(query)
        providers = result.scalars().all()
        
        # Calculate distances and filter by max distance
        provider_distances = []
        for provider in providers:
            distance = self.calculate_distance(
                latitude, longitude,
                provider.current_latitude, provider.current_longitude
            )
            
            if distance <= max_distance_km and distance <= provider.coverage_radius_km:
                provider_distances.append({
                    "provider": provider,
                    "distance_km": distance,
                    "estimated_duration_minutes": self.estimate_travel_time(distance)
                })
        
        # Sort by distance and limit results
        provider_distances.sort(key=lambda x: x["distance_km"])
        return provider_distances[:limit]

    def estimate_travel_time(self, distance_km: float) -> float:
        """Estimate travel time based on distance (simple calculation)"""
        # Assume average speed of 60 km/h in urban areas, 80 km/h for longer distances
        if distance_km <= 10:
            avg_speed = 40  # km/h for city driving
        elif distance_km <= 50:
            avg_speed = 60  # km/h for suburban
        else:
            avg_speed = 80  # km/h for highway
            
        return (distance_km / avg_speed) * 60  # Convert to minutes

    async def assign_provider_to_request(
        self,
        provider_id: UUID,
        request_id: UUID,
        estimated_arrival_time: Optional[datetime] = None
    ) -> ProviderAssignment:
        """Assign a provider to an emergency request"""
        
        # Get provider and request
        provider = await self.get_provider_by_id(provider_id)
        if not provider:
            raise ValueError("Provider not found")
            
        if provider.status != ProviderStatus.AVAILABLE:
            raise ValueError("Provider is not available")
        
        # Get request location for distance calculation
        request_query = select(PanicRequest).where(PanicRequest.id == request_id)
        request_result = await self.db.execute(request_query)
        request = request_result.scalar_one_or_none()
        
        if not request:
            raise ValueError("Request not found")
        
        # Calculate distance (assuming request.location is a PostGIS point)
        # For now, we'll need to extract lat/lon from the geometry
        # This would typically be done with PostGIS functions
        distance_km = 0.0  # Placeholder - would calculate from PostGIS geometry
        estimated_duration = self.estimate_travel_time(distance_km)
        
        # Create assignment
        assignment = ProviderAssignment(
            provider_id=provider_id,
            request_id=request_id,
            distance_km=distance_km,
            estimated_duration_minutes=estimated_duration,
            estimated_arrival_time=estimated_arrival_time,
            status="assigned"
        )
        
        # Update provider status
        provider.status = ProviderStatus.BUSY
        
        self.db.add(assignment)
        await self.db.commit()
        await self.db.refresh(assignment)
        
        logger.info(
            "provider_assigned_to_request",
            provider_id=str(provider_id),
            request_id=str(request_id),
            distance_km=distance_km
        )
        
        return assignment

    async def get_provider_assignments(
        self,
        provider_id: UUID,
        status: Optional[str] = None
    ) -> List[ProviderAssignment]:
        """Get assignments for a provider"""
        
        query = select(ProviderAssignment).where(ProviderAssignment.provider_id == provider_id)
        
        if status:
            query = query.where(ProviderAssignment.status == status)
            
        query = query.order_by(ProviderAssignment.assigned_at.desc())
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_assignment_status(
        self,
        assignment_id: UUID,
        status: str,
        notes: Optional[str] = None,
        actual_arrival_time: Optional[datetime] = None,
        completion_time: Optional[datetime] = None
    ) -> Optional[ProviderAssignment]:
        """Update assignment status"""
        
        query = select(ProviderAssignment).where(ProviderAssignment.id == assignment_id)
        result = await self.db.execute(query)
        assignment = result.scalar_one_or_none()
        
        if not assignment:
            return None
            
        assignment.status = status
        if notes:
            assignment.notes = notes
        if actual_arrival_time:
            assignment.actual_arrival_time = actual_arrival_time
        if completion_time:
            assignment.completion_time = completion_time
            
        # Update provider status if assignment is completed or cancelled
        if status in ["completed", "cancelled"]:
            provider = await self.get_provider_by_id(assignment.provider_id)
            if provider:
                provider.status = ProviderStatus.AVAILABLE
        
        await self.db.commit()
        await self.db.refresh(assignment)
        
        return assignment
    
    async def delete_unused_providers(self) -> int:
        """
        Delete emergency providers that haven't been used in any emergency requests
        
        Returns:
            int: Number of providers deleted
        """
        try:
            # Find providers that are not referenced in any provider assignments
            unused_providers_query = select(EmergencyProvider).where(
                ~exists().where(
                    ProviderAssignment.provider_id == EmergencyProvider.id
                )
            )
            
            result = await self.db.execute(unused_providers_query)
            unused_providers = result.scalars().all()
            
            deleted_count = 0
            for provider in unused_providers:
                await self.db.delete(provider)
                deleted_count += 1
            
            await self.db.commit()
            
            logger.info(
                "unused_providers_cleanup_completed",
                deleted_count=deleted_count
            )
            
            return deleted_count
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting unused providers: {str(e)}", exc_info=True)
            raise
    
    async def validate_provider_type(self, provider_type_id: UUID) -> EmergencyProviderType:
        """Validate that provider type exists and is active"""
        
        try:
            query = select(EmergencyProviderType).where(
                EmergencyProviderType.id == provider_type_id
            )
            result = await self.db.execute(query)
            provider_type = result.scalar_one_or_none()
            
            if not provider_type:
                raise ValueError(f"Provider type with ID {provider_type_id} not found")
            
            if not provider_type.is_active:
                raise ValueError(f"Provider type '{provider_type.name}' is not active")
            
            return provider_type
            
        except Exception as e:
            logger.error(f"Error validating provider type: {str(e)}", exc_info=True)
            raise