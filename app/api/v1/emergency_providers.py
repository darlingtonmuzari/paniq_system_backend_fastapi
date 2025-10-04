"""
Emergency Provider API endpoints for managing ambulances, tow trucks, etc.
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import require_emergency_provider_crud, require_emergency_provider_read
from app.services.auth import UserContext
from app.services.emergency_provider import EmergencyProviderService
from app.models.emergency_provider import ProviderType, ProviderStatus

router = APIRouter()


class ProviderCreateRequest(BaseModel):
    """Emergency provider creation request"""
    name: str = Field(..., min_length=1, max_length=255, description="Provider name")
    provider_type: Optional[ProviderType] = Field(None, description="Type of emergency provider (optional, can be derived from provider_type_id)")
    provider_type_id: str = Field(..., description="Provider type ID (foreign key)")
    license_number: Optional[str] = Field(None, max_length=100, description="License/registration number")
    contact_phone: str = Field(..., min_length=10, max_length=20, description="Contact phone number")
    contact_email: Optional[str] = Field(None, max_length=255, description="Contact email")
    
    # Address information
    street_address: str = Field(..., min_length=1, max_length=500, description="Street address")
    city: str = Field(..., min_length=1, max_length=100, description="City")
    province: str = Field(..., min_length=1, max_length=100, description="Province/State")
    country: str = Field("South Africa", min_length=1, max_length=100, description="Country")
    postal_code: str = Field(..., min_length=1, max_length=20, description="Postal/ZIP code")
    
    # Location information
    current_latitude: float = Field(..., ge=-90, le=90, description="Current location latitude")
    current_longitude: float = Field(..., ge=-180, le=180, description="Current location longitude")
    base_latitude: float = Field(..., ge=-90, le=90, description="Base location latitude")
    base_longitude: float = Field(..., ge=-180, le=180, description="Base location longitude")
    coverage_radius_km: float = Field(50.0, gt=0, le=500, description="Coverage radius in kilometers")
    
    # Additional details
    description: Optional[str] = Field(None, max_length=1000, description="Provider description")
    equipment_details: Optional[str] = Field(None, max_length=2000, description="Equipment details (JSON)")
    capacity: Optional[str] = Field(None, max_length=100, description="Capacity information")
    capabilities: Optional[List[str]] = Field(None, description="Provider capabilities (e.g., trauma_care, rescue, first_aid)")
    
    # Status (optional, defaults to AVAILABLE if not provided)
    status: Optional[ProviderStatus] = Field(None, description="Provider status (defaults to available)")


class ProviderUpdateRequest(BaseModel):
    """Emergency provider update request"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Provider name")
    provider_type_id: Optional[str] = Field(None, description="Provider type ID (foreign key)")
    contact_phone: Optional[str] = Field(None, min_length=10, max_length=20, description="Contact phone")
    contact_email: Optional[str] = Field(None, max_length=255, description="Contact email")
    
    # Address updates
    street_address: Optional[str] = Field(None, min_length=1, max_length=500, description="Street address")
    city: Optional[str] = Field(None, min_length=1, max_length=100, description="City")
    province: Optional[str] = Field(None, min_length=1, max_length=100, description="Province/State")
    country: Optional[str] = Field(None, min_length=1, max_length=100, description="Country")
    postal_code: Optional[str] = Field(None, min_length=1, max_length=20, description="Postal/ZIP code")
    
    # Location updates
    current_latitude: Optional[float] = Field(None, ge=-90, le=90, description="Current latitude")
    current_longitude: Optional[float] = Field(None, ge=-180, le=180, description="Current longitude")
    base_latitude: Optional[float] = Field(None, ge=-90, le=90, description="Base latitude")
    base_longitude: Optional[float] = Field(None, ge=-180, le=180, description="Base longitude")
    coverage_radius_km: Optional[float] = Field(None, gt=0, le=500, description="Coverage radius")
    
    # Status and details
    status: Optional[ProviderStatus] = Field(None, description="Provider status")
    description: Optional[str] = Field(None, max_length=1000, description="Description")
    equipment_details: Optional[str] = Field(None, max_length=2000, description="Equipment details")
    capacity: Optional[str] = Field(None, max_length=100, description="Capacity")
    capabilities: Optional[List[str]] = Field(None, description="Provider capabilities")
    is_active: Optional[bool] = Field(None, description="Whether provider is active")


class LocationUpdateRequest(BaseModel):
    """Provider location update request"""
    latitude: float = Field(..., ge=-90, le=90, description="Current latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Current longitude")


class ProviderResponse(BaseModel):
    """Emergency provider response"""
    id: str
    firm_id: str
    name: str
    provider_type: str
    license_number: Optional[str]
    contact_phone: str
    contact_email: Optional[str]
    
    # Address fields
    street_address: Optional[str]
    city: Optional[str]
    province: Optional[str]
    country: Optional[str]
    postal_code: Optional[str]
    
    # Location
    current_latitude: float
    current_longitude: float
    base_latitude: float
    base_longitude: float
    coverage_radius_km: float
    
    # Status
    status: str
    is_active: bool
    
    # Details
    description: Optional[str]
    equipment_details: Optional[str]
    capacity: Optional[str]
    capabilities: Optional[List[str]]
    
    # Timestamps
    created_at: str
    updated_at: str
    last_location_update: str
    
    class Config:
        from_attributes = True


class ProviderListResponse(BaseModel):
    """Provider list response"""
    providers: List[ProviderResponse]
    total_count: int


class NearestProviderResponse(BaseModel):
    """Nearest provider response with distance"""
    provider: ProviderResponse
    distance_km: float
    estimated_duration_minutes: float


class NearestProvidersResponse(BaseModel):
    """Nearest providers list response"""
    providers: List[NearestProviderResponse]
    search_location: Dict[str, float]
    max_distance_km: float


class AssignmentRequest(BaseModel):
    """Provider assignment request"""
    request_id: str = Field(..., description="Emergency request ID")
    estimated_arrival_time: Optional[datetime] = Field(None, description="Estimated arrival time")


class AssignmentResponse(BaseModel):
    """Provider assignment response"""
    id: str
    provider_id: str
    request_id: str
    assigned_at: str
    estimated_arrival_time: Optional[str]
    distance_km: float
    estimated_duration_minutes: float
    status: str
    
    class Config:
        from_attributes = True


@router.post("/", response_model=ProviderResponse)
async def create_provider(
    request: ProviderCreateRequest,
    current_user: UserContext = Depends(require_emergency_provider_crud),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new emergency provider
    
    Creates an emergency provider (ambulance, tow truck, etc.) for the firm.
    Only firm administrators can create providers for their firm.
    """
    try:
        service = EmergencyProviderService(db)
        
        provider = await service.create_provider(
            firm_id=current_user.firm_id,
            name=request.name,
            provider_type=request.provider_type,
            provider_type_id=UUID(request.provider_type_id),
            contact_phone=request.contact_phone,
            street_address=request.street_address,
            city=request.city,
            province=request.province,
            country=request.country,
            postal_code=request.postal_code,
            current_latitude=request.current_latitude,
            current_longitude=request.current_longitude,
            base_latitude=request.base_latitude,
            base_longitude=request.base_longitude,
            coverage_radius_km=request.coverage_radius_km,
            license_number=request.license_number,
            contact_email=request.contact_email,
            description=request.description,
            equipment_details=request.equipment_details,
            capacity=request.capacity,
            capabilities=request.capabilities,
            status=request.status
        )
        
        return ProviderResponse(
            id=str(provider.id),
            firm_id=str(provider.firm_id),
            name=provider.name,
            provider_type=provider.provider_type.value,
            license_number=provider.license_number,
            contact_phone=provider.contact_phone,
            contact_email=provider.contact_email,
            street_address=provider.street_address,
            city=provider.city,
            province=provider.province,
            country=provider.country,
            postal_code=provider.postal_code,
            current_latitude=provider.current_latitude,
            current_longitude=provider.current_longitude,
            base_latitude=provider.base_latitude,
            base_longitude=provider.base_longitude,
            coverage_radius_km=provider.coverage_radius_km,
            status=provider.status.value,
            is_active=provider.is_active,
            description=provider.description,
            equipment_details=provider.equipment_details,
            capacity=provider.capacity,
            capabilities=provider.capabilities,
            created_at=provider.created_at.isoformat(),
            updated_at=provider.updated_at.isoformat(),
            last_location_update=provider.last_location_update.isoformat()
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create emergency provider"
        )


@router.get("/", response_model=ProviderListResponse)
async def get_firm_providers(
    provider_type: Optional[ProviderType] = Query(None, description="Filter by provider type"),
    provider_status: Optional[ProviderStatus] = Query(None, description="Filter by status"),
    include_inactive: bool = Query(False, description="Include inactive providers"),
    current_user: UserContext = Depends(require_emergency_provider_read),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all emergency providers for the firm
    
    Returns a list of emergency providers registered by the current firm.
    Can be filtered by type, status, and active status.
    """
    try:
        service = EmergencyProviderService(db)
        
        providers = await service.get_firm_providers(
            firm_id=current_user.firm_id,
            provider_type=provider_type,
            status=provider_status,
            include_inactive=include_inactive
        )
        
        provider_responses = []
        for provider in providers:
            # Handle both old array-based capabilities and new relationship-based capabilities
            capabilities = []
            if hasattr(provider, 'capabilities') and provider.capabilities:
                # Old array-based capabilities (fallback)
                capabilities = provider.capabilities
            elif hasattr(provider, 'provider_capabilities') and provider.provider_capabilities:
                # New relationship-based capabilities
                capabilities = [pc.capability.code for pc in provider.provider_capabilities if pc.capability]
            
            provider_responses.append(ProviderResponse(
                id=str(provider.id),
                firm_id=str(provider.firm_id),
                name=provider.name,
                provider_type=provider.provider_type.value,
                license_number=provider.license_number,
                contact_phone=provider.contact_phone,
                contact_email=provider.contact_email,
                street_address=provider.street_address,
                city=provider.city,
                province=provider.province,
                country=provider.country,
                postal_code=provider.postal_code,
                current_latitude=provider.current_latitude,
                current_longitude=provider.current_longitude,
                base_latitude=provider.base_latitude,
                base_longitude=provider.base_longitude,
                coverage_radius_km=provider.coverage_radius_km,
                status=provider.status.value,
                is_active=provider.is_active,
                description=provider.description,
                equipment_details=provider.equipment_details,
                capacity=provider.capacity,
                capabilities=capabilities,
                created_at=provider.created_at.isoformat(),
                updated_at=provider.updated_at.isoformat(),
                last_location_update=provider.last_location_update.isoformat()
            ))
        
        return ProviderListResponse(
            providers=provider_responses,
            total_count=len(provider_responses)
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()  # Print detailed error to logs
        print(f"Emergency providers error: {e}")  # Also print simplified error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve emergency providers: {str(e)}"
        )


@router.get("/{provider_id}", response_model=ProviderResponse)
async def get_provider(
    provider_id: str,
    current_user: UserContext = Depends(require_emergency_provider_read),
    db: AsyncSession = Depends(get_db)
):
    """
    Get emergency provider by ID
    
    Returns detailed information about a specific emergency provider.
    Only accessible by the firm that owns the provider.
    """
    try:
        service = EmergencyProviderService(db)
        provider = await service.get_provider_by_id(UUID(provider_id))
        
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Emergency provider not found"
            )
        
        # Ensure firm admin can only view their own firm's providers
        if provider.firm_id != current_user.firm_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view providers from your own firm"
            )
        
        return ProviderResponse(
            id=str(provider.id),
            firm_id=str(provider.firm_id),
            name=provider.name,
            provider_type=provider.provider_type.value,
            license_number=provider.license_number,
            contact_phone=provider.contact_phone,
            contact_email=provider.contact_email,
            street_address=provider.street_address,
            city=provider.city,
            province=provider.province,
            country=provider.country,
            postal_code=provider.postal_code,
            current_latitude=provider.current_latitude,
            current_longitude=provider.current_longitude,
            base_latitude=provider.base_latitude,
            base_longitude=provider.base_longitude,
            coverage_radius_km=provider.coverage_radius_km,
            status=provider.status.value,
            is_active=provider.is_active,
            description=provider.description,
            equipment_details=provider.equipment_details,
            capacity=provider.capacity,
            capabilities=provider.capabilities,
            created_at=provider.created_at.isoformat(),
            updated_at=provider.updated_at.isoformat(),
            last_location_update=provider.last_location_update.isoformat()
        )
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid provider ID"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve emergency provider"
        )


@router.put("/{provider_id}", response_model=ProviderResponse)
async def update_provider(
    provider_id: str,
    request: ProviderUpdateRequest,
    current_user: UserContext = Depends(require_emergency_provider_crud),
    db: AsyncSession = Depends(get_db)
):
    """
    Update emergency provider
    
    Updates the specified emergency provider with new information.
    Only non-null fields in the request will be updated.
    """
    try:
        service = EmergencyProviderService(db)
        
        # Check if provider exists and belongs to firm
        existing_provider = await service.get_provider_by_id(UUID(provider_id))
        if not existing_provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Emergency provider not found"
            )
        
        if existing_provider.firm_id != current_user.firm_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update providers from your own firm"
            )
        
        provider = await service.update_provider(
            provider_id=UUID(provider_id),
            name=request.name,
            provider_type_id=UUID(request.provider_type_id) if request.provider_type_id else None,
            contact_phone=request.contact_phone,
            contact_email=request.contact_email,
            street_address=request.street_address,
            city=request.city,
            province=request.province,
            country=request.country,
            postal_code=request.postal_code,
            current_latitude=request.current_latitude,
            current_longitude=request.current_longitude,
            base_latitude=request.base_latitude,
            base_longitude=request.base_longitude,
            coverage_radius_km=request.coverage_radius_km,
            status=request.status,
            description=request.description,
            equipment_details=request.equipment_details,
            capacity=request.capacity,
            capabilities=request.capabilities,
            is_active=request.is_active
        )
        
        return ProviderResponse(
            id=str(provider.id),
            firm_id=str(provider.firm_id),
            name=provider.name,
            provider_type=provider.provider_type.value,
            license_number=provider.license_number,
            contact_phone=provider.contact_phone,
            contact_email=provider.contact_email,
            street_address=provider.street_address,
            city=provider.city,
            province=provider.province,
            country=provider.country,
            postal_code=provider.postal_code,
            current_latitude=provider.current_latitude,
            current_longitude=provider.current_longitude,
            base_latitude=provider.base_latitude,
            base_longitude=provider.base_longitude,
            coverage_radius_km=provider.coverage_radius_km,
            status=provider.status.value,
            is_active=provider.is_active,
            description=provider.description,
            equipment_details=provider.equipment_details,
            capacity=provider.capacity,
            capabilities=provider.capabilities,
            created_at=provider.created_at.isoformat(),
            updated_at=provider.updated_at.isoformat(),
            last_location_update=provider.last_location_update.isoformat()
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update emergency provider"
        )


@router.patch("/{provider_id}/location", response_model=ProviderResponse)
async def update_provider_location(
    provider_id: str,
    request: LocationUpdateRequest,
    current_user: UserContext = Depends(require_emergency_provider_crud),
    db: AsyncSession = Depends(get_db)
):
    """
    Update provider's current location
    
    Updates only the current location of the provider. This is typically
    used for real-time location tracking of mobile providers.
    """
    try:
        service = EmergencyProviderService(db)
        
        # Check if provider exists and belongs to firm
        existing_provider = await service.get_provider_by_id(UUID(provider_id))
        if not existing_provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Emergency provider not found"
            )
        
        if existing_provider.firm_id != current_user.firm_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update providers from your own firm"
            )
        
        provider = await service.update_provider_location(
            provider_id=UUID(provider_id),
            latitude=request.latitude,
            longitude=request.longitude
        )
        
        return ProviderResponse(
            id=str(provider.id),
            firm_id=str(provider.firm_id),
            name=provider.name,
            provider_type=provider.provider_type.value,
            license_number=provider.license_number,
            contact_phone=provider.contact_phone,
            contact_email=provider.contact_email,
            street_address=provider.street_address,
            city=provider.city,
            province=provider.province,
            country=provider.country,
            postal_code=provider.postal_code,
            current_latitude=provider.current_latitude,
            current_longitude=provider.current_longitude,
            base_latitude=provider.base_latitude,
            base_longitude=provider.base_longitude,
            coverage_radius_km=provider.coverage_radius_km,
            status=provider.status.value,
            is_active=provider.is_active,
            description=provider.description,
            equipment_details=provider.equipment_details,
            capacity=provider.capacity,
            capabilities=provider.capabilities,
            created_at=provider.created_at.isoformat(),
            updated_at=provider.updated_at.isoformat(),
            last_location_update=provider.last_location_update.isoformat()
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update provider location"
        )


@router.delete("/{provider_id}")
async def delete_provider(
    provider_id: str,
    current_user: UserContext = Depends(require_emergency_provider_crud),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete emergency provider
    
    Deactivates the specified emergency provider. Providers with active
    assignments cannot be deleted.
    """
    try:
        service = EmergencyProviderService(db)
        
        # Check if provider exists and belongs to firm
        existing_provider = await service.get_provider_by_id(UUID(provider_id))
        if not existing_provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Emergency provider not found"
            )
        
        if existing_provider.firm_id != current_user.firm_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete providers from your own firm"
            )
        
        success = await service.delete_provider(UUID(provider_id))
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to delete provider"
            )
        
        return {"message": "Emergency provider deleted successfully"}
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete emergency provider"
        )


@router.get("/search/nearest", response_model=NearestProvidersResponse)
async def find_nearest_providers(
    latitude: float = Query(..., ge=-90, le=90, description="Search location latitude"),
    longitude: float = Query(..., ge=-180, le=180, description="Search location longitude"),
    provider_type: ProviderType = Query(..., description="Type of provider to search for"),
    max_distance_km: float = Query(100.0, gt=0, le=500, description="Maximum search distance"),
    limit: int = Query(10, gt=0, le=50, description="Maximum number of results"),
    current_user: UserContext = Depends(require_emergency_provider_read),
    db: AsyncSession = Depends(get_db)
):
    """
    Find nearest available providers
    
    Searches for the nearest available emergency providers of the specified type
    within the maximum distance. Results are sorted by distance.
    """
    try:
        service = EmergencyProviderService(db)
        
        # Search for nearest providers within the firm
        provider_distances = await service.find_nearest_providers(
            latitude=latitude,
            longitude=longitude,
            provider_type=provider_type,
            max_distance_km=max_distance_km,
            limit=limit,
            firm_id=current_user.firm_id
        )
        
        # Convert to response format
        nearest_providers = []
        for item in provider_distances:
            provider = item["provider"]
            nearest_providers.append(NearestProviderResponse(
                provider=ProviderResponse(
                    id=str(provider.id),
                    firm_id=str(provider.firm_id),
                    name=provider.name,
                    provider_type=provider.provider_type.value,
                    license_number=provider.license_number,
                    contact_phone=provider.contact_phone,
                    contact_email=provider.contact_email,
                    current_latitude=provider.current_latitude,
                    current_longitude=provider.current_longitude,
                    base_latitude=provider.base_latitude,
                    base_longitude=provider.base_longitude,
                    coverage_radius_km=provider.coverage_radius_km,
                    status=provider.status.value,
                    is_active=provider.is_active,
                    description=provider.description,
                    equipment_details=provider.equipment_details,
                    capacity=provider.capacity,
                    created_at=provider.created_at.isoformat(),
                    updated_at=provider.updated_at.isoformat(),
                    last_location_update=provider.last_location_update.isoformat()
                ),
                distance_km=item["distance_km"],
                estimated_duration_minutes=item["estimated_duration_minutes"]
            ))
        
        return NearestProvidersResponse(
            providers=nearest_providers,
            search_location={"latitude": latitude, "longitude": longitude},
            max_distance_km=max_distance_km
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search for nearest providers"
        )


@router.post("/{provider_id}/assign", response_model=AssignmentResponse)
async def assign_provider_to_request(
    provider_id: str,
    request: AssignmentRequest,
    current_user: UserContext = Depends(require_emergency_provider_crud),
    db: AsyncSession = Depends(get_db)
):
    """
    Assign provider to emergency request
    
    Assigns the specified provider to an emergency request. The provider
    must be available and belong to the current firm.
    """
    try:
        service = EmergencyProviderService(db)
        
        # Check if provider exists and belongs to firm
        existing_provider = await service.get_provider_by_id(UUID(provider_id))
        if not existing_provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Emergency provider not found"
            )
        
        if existing_provider.firm_id != current_user.firm_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only assign providers from your own firm"
            )
        
        assignment = await service.assign_provider_to_request(
            provider_id=UUID(provider_id),
            request_id=UUID(request.request_id),
            estimated_arrival_time=request.estimated_arrival_time
        )
        
        return AssignmentResponse(
            id=str(assignment.id),
            provider_id=str(assignment.provider_id),
            request_id=str(assignment.request_id),
            assigned_at=assignment.assigned_at.isoformat(),
            estimated_arrival_time=assignment.estimated_arrival_time.isoformat() if assignment.estimated_arrival_time else None,
            distance_km=assignment.distance_km,
            estimated_duration_minutes=assignment.estimated_duration_minutes,
            status=assignment.status
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to assign provider to request"
        )


@router.delete("/cleanup/unused")
async def delete_unused_providers(
    current_user: UserContext = Depends(require_emergency_provider_crud),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete emergency providers that haven't been used in any emergency requests
    
    Only accessible by firm_user, firm_supervisor, and firm_admin
    """
    try:
        service = EmergencyProviderService(db)
        deleted_count = await service.delete_unused_providers()
        
        return {
            "message": f"Successfully deleted {deleted_count} unused emergency providers",
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete unused providers"
        )