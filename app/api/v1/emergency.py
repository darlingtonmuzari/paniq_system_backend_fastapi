"""
Emergency request API endpoints
"""
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.middleware import require_mobile_attestation
from app.core.auth import UserContext
from app.services.emergency import EmergencyService, EmergencyRequestError
from app.models.emergency import PanicRequest

router = APIRouter()


class PanicRequestCreate(BaseModel):
    """Panic request creation model"""
    requester_phone: str = Field(..., description="Phone number making the request")
    group_id: UUID = Field(..., description="User group ID")
    service_type: str = Field(..., description="Type of emergency service")
    latitude: float = Field(..., ge=-90, le=90, description="Request location latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Request location longitude")
    address: str = Field(..., min_length=1, max_length=500, description="Human-readable address")
    description: Optional[str] = Field(None, max_length=1000, description="Optional request description")
    
    @validator('service_type')
    def validate_service_type(cls, v):
        valid_types = ["call", "security", "ambulance", "fire", "towing"]
        if v not in valid_types:
            raise ValueError(f"Service type must be one of: {', '.join(valid_types)}")
        return v
    
    @validator('requester_phone')
    def validate_phone(cls, v):
        # Basic phone validation - should be enhanced based on requirements
        if not v or len(v) < 10:
            raise ValueError("Phone number must be at least 10 characters")
        return v


class PanicRequestResponse(BaseModel):
    """Panic request response model"""
    id: UUID
    requester_phone: str
    group_id: UUID
    service_type: str
    latitude: float
    longitude: float
    address: str
    description: Optional[str]
    status: str
    created_at: datetime
    accepted_at: Optional[datetime]
    arrived_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True
    
    @classmethod
    def from_panic_request(cls, panic_request: PanicRequest) -> "PanicRequestResponse":
        """Create response from PanicRequest model"""
        from geoalchemy2.shape import to_shape
        
        # Extract coordinates from PostGIS point
        point = to_shape(panic_request.location)
        
        return cls(
            id=panic_request.id,
            requester_phone=panic_request.requester_phone,
            group_id=panic_request.group_id,
            service_type=panic_request.service_type,
            latitude=point.y,
            longitude=point.x,
            address=panic_request.address,
            description=panic_request.description,
            status=panic_request.status,
            created_at=panic_request.created_at,
            accepted_at=panic_request.accepted_at,
            arrived_at=panic_request.arrived_at,
            completed_at=panic_request.completed_at
        )


class RequestStatusUpdate(BaseModel):
    """Request status update model"""
    status: str = Field(..., description="New request status")
    message: Optional[str] = Field(None, max_length=500, description="Optional status message")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Optional location latitude")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Optional location longitude")


class RequestListResponse(BaseModel):
    """Request list response model"""
    requests: List[PanicRequestResponse]
    total: int
    limit: int
    offset: int


class RequestStatistics(BaseModel):
    """Request statistics model"""
    total_requests: int
    status_breakdown: dict
    service_type_breakdown: dict
    average_response_time_minutes: float
    completed_requests: int
    date_range: dict


class RequestAllocation(BaseModel):
    """Request allocation model"""
    team_id: Optional[UUID] = Field(None, description="Team ID to assign request to")
    service_provider_id: Optional[UUID] = Field(None, description="Service provider ID to assign request to")
    notes: Optional[str] = Field(None, max_length=500, description="Optional allocation notes")
    
    @validator('team_id', 'service_provider_id')
    def validate_assignment(cls, v, values):
        # Ensure exactly one assignment target is provided
        team_id = values.get('team_id')
        service_provider_id = values.get('service_provider_id')
        
        if not team_id and not service_provider_id:
            raise ValueError("Must specify either team_id or service_provider_id")
        
        if team_id and service_provider_id:
            raise ValueError("Cannot specify both team_id and service_provider_id")
        
        return v


class CallServiceHandling(BaseModel):
    """Call service handling model"""
    notes: Optional[str] = Field(None, max_length=1000, description="Notes about call handling")


class RequestReassignment(BaseModel):
    """Request reassignment model"""
    new_team_id: Optional[UUID] = Field(None, description="New team ID")
    new_service_provider_id: Optional[UUID] = Field(None, description="New service provider ID")
    reason: Optional[str] = Field(None, max_length=500, description="Reason for reassignment")
    
    @validator('new_team_id', 'new_service_provider_id')
    def validate_reassignment(cls, v, values):
        new_team_id = values.get('new_team_id')
        new_service_provider_id = values.get('new_service_provider_id')
        
        if not new_team_id and not new_service_provider_id:
            raise ValueError("Must specify either new_team_id or new_service_provider_id")
        
        if new_team_id and new_service_provider_id:
            raise ValueError("Cannot specify both new_team_id and new_service_provider_id")
        
        return v


@router.post("/request", response_model=PanicRequestResponse, status_code=status.HTTP_201_CREATED)
async def submit_panic_request(
    request_data: PanicRequestCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_mobile_attestation)  # Require mobile app attestation
):
    """
    Submit a panic request for emergency services
    
    This endpoint allows mobile app users to submit emergency requests.
    The request goes through comprehensive validation including:
    - Service type validation
    - Phone number authorization (works even with locked accounts)
    - Rate limiting protection
    - Duplicate request detection
    - Subscription status validation
    - Coverage area validation
    
    **Note**: This endpoint works even if the user account is locked,
    as emergency requests should always be allowed for safety reasons.
    """
    try:
        emergency_service = EmergencyService(db)
        
        panic_request = await emergency_service.submit_panic_request(
            requester_phone=request_data.requester_phone,
            group_id=request_data.group_id,
            service_type=request_data.service_type,
            latitude=request_data.latitude,
            longitude=request_data.longitude,
            address=request_data.address,
            description=request_data.description
        )
        
        return PanicRequestResponse.from_panic_request(panic_request)
        
    except EmergencyRequestError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": e.error_code,
                "message": e.message,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred while processing the request",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/requests", response_model=RequestListResponse)
async def get_user_requests(
    limit: int = 50,
    offset: int = 0,
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: UserContext = Depends(get_current_user),
    _: dict = Depends(require_mobile_attestation)
):
    """
    Get panic requests for the current user's groups
    
    Returns a paginated list of panic requests associated with
    the authenticated user's groups.
    """
    try:
        emergency_service = EmergencyService(db)
        
        requests = await emergency_service.get_user_requests(
            user_id=current_user.user_id,
            limit=limit,
            offset=offset,
            status_filter=status_filter
        )
        
        # Convert to response models
        request_responses = [
            PanicRequestResponse.from_panic_request(req) for req in requests
        ]
        
        return RequestListResponse(
            requests=request_responses,
            total=len(request_responses),  # This should be actual total from DB
            limit=limit,
            offset=offset
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "Failed to retrieve requests",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/requests/{request_id}", response_model=PanicRequestResponse)
async def get_panic_request(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: UserContext = Depends(get_current_user),
    _: dict = Depends(require_mobile_attestation)
):
    """
    Get a specific panic request by ID
    
    Returns detailed information about a panic request.
    Users can only access requests from their own groups.
    """
    try:
        emergency_service = EmergencyService(db)
        
        panic_request = await emergency_service.get_request_by_id(request_id)
        
        if not panic_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "REQUEST_NOT_FOUND",
                    "message": "Panic request not found",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        # Verify user has access to this request
        if str(panic_request.group.user_id) != str(current_user.user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "ACCESS_DENIED",
                    "message": "You don't have access to this request",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        return PanicRequestResponse.from_panic_request(panic_request)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "Failed to retrieve request",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/groups/{group_id}/requests", response_model=RequestListResponse)
async def get_group_requests(
    group_id: UUID,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: UserContext = Depends(get_current_user),
    _: dict = Depends(require_mobile_attestation)
):
    """
    Get panic requests for a specific group
    
    Returns panic requests for a specific user group.
    Users can only access requests from their own groups.
    """
    try:
        # Verify user owns the group
        from app.models.user import UserGroup
        from sqlalchemy import select
        
        result = await db.execute(
            select(UserGroup).where(UserGroup.id == group_id)
        )
        group = result.scalar_one_or_none()
        
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "GROUP_NOT_FOUND",
                    "message": "User group not found",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        if str(group.user_id) != str(current_user.user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "ACCESS_DENIED",
                    "message": "You don't have access to this group",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        emergency_service = EmergencyService(db)
        
        requests = await emergency_service.get_group_requests(
            group_id=group_id,
            limit=limit,
            offset=offset
        )
        
        # Convert to response models
        request_responses = [
            PanicRequestResponse.from_panic_request(req) for req in requests
        ]
        
        return RequestListResponse(
            requests=request_responses,
            total=len(request_responses),
            limit=limit,
            offset=offset
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "Failed to retrieve group requests",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.put("/requests/{request_id}/status", response_model=dict)
async def update_request_status(
    request_id: UUID,
    status_update: RequestStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserContext = Depends(get_current_user),
    _: dict = Depends(require_mobile_attestation)
):
    """
    Update panic request status
    
    Allows authorized users (field agents, team leaders) to update
    the status of panic requests with optional location tracking.
    """
    try:
        emergency_service = EmergencyService(db)
        
        # Prepare location tuple if provided
        location = None
        if status_update.latitude is not None and status_update.longitude is not None:
            location = (status_update.latitude, status_update.longitude)
        
        success = await emergency_service.update_request_status(
            request_id=request_id,
            new_status=status_update.status,
            message=status_update.message,
            updated_by_id=current_user.user_id,
            location=location
        )
        
        if success:
            return {
                "success": True,
                "message": "Request status updated successfully",
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "UPDATE_FAILED",
                    "message": "Failed to update request status",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
    except EmergencyRequestError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": e.error_code,
                "message": e.message,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "Failed to update request status",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/statistics", response_model=RequestStatistics)
async def get_request_statistics(
    firm_id: Optional[UUID] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    current_user: UserContext = Depends(get_current_user)
):
    """
    Get emergency request statistics
    
    Returns statistical information about emergency requests.
    Firm personnel can filter by their firm, admins can see all.
    """
    try:
        # Authorization check
        if firm_id and current_user.is_firm_personnel():
            # Firm personnel can only see their own firm's statistics
            if str(current_user.firm_id) != str(firm_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "error_code": "ACCESS_DENIED",
                        "message": "You can only view statistics for your own firm",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
        elif current_user.is_firm_personnel() and not firm_id:
            # Default to user's firm if they're firm personnel
            firm_id = current_user.firm_id
        
        emergency_service = EmergencyService(db)
        
        statistics = await emergency_service.get_request_statistics(
            firm_id=firm_id,
            date_from=date_from,
            date_to=date_to
        )
        
        return RequestStatistics(**statistics)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "Failed to retrieve statistics",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


# Request Allocation Endpoints (for office staff)

@router.get("/firm/{firm_id}/pending", response_model=RequestListResponse)
async def get_pending_requests_for_firm(
    firm_id: UUID,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: UserContext = Depends(get_current_user)
):
    """
    Get pending panic requests for a security firm
    
    This endpoint allows office staff to view pending requests
    that need to be allocated to teams or service providers.
    """
    try:
        # Authorization check - only firm personnel can access their firm's requests
        if not current_user.is_firm_personnel():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "ACCESS_DENIED",
                    "message": "Only firm personnel can access this endpoint",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        if str(current_user.firm_id) != str(firm_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "ACCESS_DENIED",
                    "message": "You can only access requests for your own firm",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        emergency_service = EmergencyService(db)
        
        requests = await emergency_service.get_pending_requests_for_firm(
            firm_id=firm_id,
            limit=limit,
            offset=offset
        )
        
        # Convert to response models
        request_responses = [
            PanicRequestResponse.from_panic_request(req) for req in requests
        ]
        
        return RequestListResponse(
            requests=request_responses,
            total=len(request_responses),
            limit=limit,
            offset=offset
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "Failed to retrieve pending requests",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.post("/requests/{request_id}/allocate", response_model=dict)
async def allocate_request(
    request_id: UUID,
    allocation: RequestAllocation,
    db: AsyncSession = Depends(get_db),
    current_user: UserContext = Depends(get_current_user)
):
    """
    Allocate a panic request to a team or service provider
    
    This endpoint allows office staff to assign pending requests
    to appropriate teams or external service providers.
    """
    try:
        # Authorization check - only firm personnel with appropriate role
        if not current_user.is_firm_personnel():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "ACCESS_DENIED",
                    "message": "Only firm personnel can allocate requests",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        # Check if user has office staff role
        if current_user.role not in ["office_staff", "team_leader"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "INSUFFICIENT_PERMISSIONS",
                    "message": "Only office staff and team leaders can allocate requests",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        emergency_service = EmergencyService(db)
        
        success = False
        if allocation.team_id:
            success = await emergency_service.allocate_request_to_team(
                request_id=request_id,
                team_id=allocation.team_id,
                allocated_by_id=current_user.user_id
            )
        elif allocation.service_provider_id:
            success = await emergency_service.allocate_request_to_service_provider(
                request_id=request_id,
                service_provider_id=allocation.service_provider_id,
                allocated_by_id=current_user.user_id
            )
        
        if success:
            return {
                "success": True,
                "message": "Request allocated successfully",
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "ALLOCATION_FAILED",
                    "message": "Failed to allocate request",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
    except EmergencyRequestError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": e.error_code,
                "message": e.message,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "Failed to allocate request",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.post("/requests/{request_id}/handle-call", response_model=dict)
async def handle_call_service(
    request_id: UUID,
    call_handling: CallServiceHandling,
    db: AsyncSession = Depends(get_db),
    current_user: UserContext = Depends(get_current_user)
):
    """
    Handle a call service request directly
    
    This endpoint allows office staff to handle call service requests
    without assigning them to field agents.
    """
    try:
        # Authorization check
        if not current_user.is_firm_personnel():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "ACCESS_DENIED",
                    "message": "Only firm personnel can handle call requests",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        if current_user.role != "office_staff":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "INSUFFICIENT_PERMISSIONS",
                    "message": "Only office staff can handle call requests",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        emergency_service = EmergencyService(db)
        
        success = await emergency_service.handle_call_service_request(
            request_id=request_id,
            handled_by_id=current_user.user_id,
            notes=call_handling.notes
        )
        
        if success:
            return {
                "success": True,
                "message": "Call service request handled successfully",
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "HANDLING_FAILED",
                    "message": "Failed to handle call service request",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
    except EmergencyRequestError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": e.error_code,
                "message": e.message,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "Failed to handle call service request",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/teams/{team_id}/requests", response_model=RequestListResponse)
async def get_team_requests(
    team_id: UUID,
    status_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: UserContext = Depends(get_current_user)
):
    """
    Get panic requests assigned to a specific team
    
    This endpoint allows team leaders and office staff to view
    requests assigned to a particular team.
    """
    try:
        # Authorization check
        if not current_user.is_firm_personnel():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "ACCESS_DENIED",
                    "message": "Only firm personnel can access team requests",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        emergency_service = EmergencyService(db)
        
        requests = await emergency_service.get_team_assigned_requests(
            team_id=team_id,
            status_filter=status_filter,
            limit=limit,
            offset=offset
        )
        
        # Convert to response models
        request_responses = [
            PanicRequestResponse.from_panic_request(req) for req in requests
        ]
        
        return RequestListResponse(
            requests=request_responses,
            total=len(request_responses),
            limit=limit,
            offset=offset
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "Failed to retrieve team requests",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.post("/requests/{request_id}/reassign", response_model=dict)
async def reassign_request(
    request_id: UUID,
    reassignment: RequestReassignment,
    db: AsyncSession = Depends(get_db),
    current_user: UserContext = Depends(get_current_user)
):
    """
    Reassign a panic request to a different team or service provider
    
    This endpoint allows office staff and team leaders to reassign
    requests when needed.
    """
    try:
        # Authorization check
        if not current_user.is_firm_personnel():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "ACCESS_DENIED",
                    "message": "Only firm personnel can reassign requests",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        if current_user.role not in ["office_staff", "team_leader"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "INSUFFICIENT_PERMISSIONS",
                    "message": "Only office staff and team leaders can reassign requests",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        emergency_service = EmergencyService(db)
        
        success = await emergency_service.reassign_request(
            request_id=request_id,
            new_team_id=reassignment.new_team_id,
            new_service_provider_id=reassignment.new_service_provider_id,
            reassigned_by_id=current_user.user_id,
            reason=reassignment.reason
        )
        
        if success:
            return {
                "success": True,
                "message": "Request reassigned successfully",
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "REASSIGNMENT_FAILED",
                    "message": "Failed to reassign request",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
    except EmergencyRequestError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": e.error_code,
                "message": e.message,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "Failed to reassign request",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


# Field Agent Endpoints

class RequestAcceptance(BaseModel):
    """Request acceptance model"""
    estimated_arrival_minutes: Optional[int] = Field(None, ge=1, le=180, description="Estimated arrival time in minutes")


class RequestRejection(BaseModel):
    """Request rejection model"""
    reason: Optional[str] = Field(None, max_length=500, description="Reason for rejection")


class LocationUpdate(BaseModel):
    """Location update model"""
    latitude: float = Field(..., ge=-90, le=90, description="Current latitude")
    longitude: float = Field(..., ge=-180, le=180, description="Current longitude")
    status_message: Optional[str] = Field(None, max_length=200, description="Optional status message")


class ArrivalNotification(BaseModel):
    """Arrival notification model"""
    arrival_notes: Optional[str] = Field(None, max_length=500, description="Notes about arrival")


class RequestCompletion(BaseModel):
    """Request completion model"""
    is_prank: bool = Field(False, description="Whether the request was a prank")
    performance_rating: Optional[int] = Field(None, ge=1, le=5, description="Performance rating (1-5)")
    completion_notes: Optional[str] = Field(None, max_length=1000, description="Notes about completion")


@router.get("/agent/requests", response_model=RequestListResponse)
async def get_agent_requests(
    status_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: UserContext = Depends(get_current_user),
    _: dict = Depends(require_mobile_attestation)
):
    """
    Get panic requests assigned to the current field agent
    
    This endpoint allows field agents to view requests assigned
    to their team that they can accept and handle.
    """
    try:
        # Authorization check - only field agents
        if not current_user.is_firm_personnel():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "ACCESS_DENIED",
                    "message": "Only firm personnel can access this endpoint",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        if current_user.role not in ["field_agent", "team_leader"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "INSUFFICIENT_PERMISSIONS",
                    "message": "Only field agents and team leaders can access agent requests",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        emergency_service = EmergencyService(db)
        
        requests = await emergency_service.get_agent_assigned_requests(
            agent_id=current_user.user_id,
            status_filter=status_filter,
            limit=limit,
            offset=offset
        )
        
        # Convert to response models
        request_responses = [
            PanicRequestResponse.from_panic_request(req) for req in requests
        ]
        
        return RequestListResponse(
            requests=request_responses,
            total=len(request_responses),
            limit=limit,
            offset=offset
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "Failed to retrieve agent requests",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.post("/agent/requests/{request_id}/accept", response_model=dict)
async def accept_request(
    request_id: UUID,
    acceptance: RequestAcceptance,
    db: AsyncSession = Depends(get_db),
    current_user: UserContext = Depends(get_current_user),
    _: dict = Depends(require_mobile_attestation)
):
    """
    Accept a panic request as a field agent
    
    This endpoint allows field agents to accept requests assigned
    to their team and provide an estimated arrival time.
    """
    try:
        # Authorization check
        if not current_user.is_firm_personnel():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "ACCESS_DENIED",
                    "message": "Only firm personnel can accept requests",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        if current_user.role not in ["field_agent", "team_leader"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "INSUFFICIENT_PERMISSIONS",
                    "message": "Only field agents and team leaders can accept requests",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        emergency_service = EmergencyService(db)
        
        success = await emergency_service.accept_request(
            request_id=request_id,
            agent_id=current_user.user_id,
            estimated_arrival_minutes=acceptance.estimated_arrival_minutes
        )
        
        if success:
            return {
                "success": True,
                "message": "Request accepted successfully",
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "ACCEPTANCE_FAILED",
                    "message": "Failed to accept request",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
    except EmergencyRequestError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": e.error_code,
                "message": e.message,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "Failed to accept request",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.post("/agent/requests/{request_id}/reject", response_model=dict)
async def reject_request(
    request_id: UUID,
    rejection: RequestRejection,
    db: AsyncSession = Depends(get_db),
    current_user: UserContext = Depends(get_current_user),
    _: dict = Depends(require_mobile_attestation)
):
    """
    Reject a panic request as a field agent
    
    This endpoint allows field agents to reject requests assigned
    to their team with an optional reason.
    """
    try:
        # Authorization check
        if not current_user.is_firm_personnel():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "ACCESS_DENIED",
                    "message": "Only firm personnel can reject requests",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        if current_user.role not in ["field_agent", "team_leader"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "INSUFFICIENT_PERMISSIONS",
                    "message": "Only field agents and team leaders can reject requests",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        emergency_service = EmergencyService(db)
        
        success = await emergency_service.reject_request(
            request_id=request_id,
            agent_id=current_user.user_id,
            reason=rejection.reason
        )
        
        if success:
            return {
                "success": True,
                "message": "Request rejected successfully",
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "REJECTION_FAILED",
                    "message": "Failed to reject request",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
    except EmergencyRequestError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": e.error_code,
                "message": e.message,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "Failed to reject request",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.post("/agent/requests/{request_id}/complete", response_model=dict)
async def complete_request(
    request_id: UUID,
    completion: RequestCompletion,
    db: AsyncSession = Depends(get_db),
    current_user: UserContext = Depends(get_current_user),
    _: dict = Depends(require_mobile_attestation)
):
    """
    Complete a panic request with feedback
    
    This endpoint allows field agents to mark requests as completed
    and provide feedback including prank flags and performance ratings.
    """
    try:
        # Authorization check
        if not current_user.is_firm_personnel():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "ACCESS_DENIED",
                    "message": "Only firm personnel can complete requests",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        if current_user.role not in ["field_agent", "team_leader"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "INSUFFICIENT_PERMISSIONS",
                    "message": "Only field agents and team leaders can complete requests",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        emergency_service = EmergencyService(db)
        
        success = await emergency_service.complete_request_with_feedback(
            request_id=request_id,
            agent_id=current_user.user_id,
            is_prank=completion.is_prank,
            performance_rating=completion.performance_rating,
            completion_notes=completion.completion_notes
        )
        
        if success:
            return {
                "success": True,
                "message": "Request completed successfully",
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "COMPLETION_FAILED",
                    "message": "Failed to complete request",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
    except EmergencyRequestError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": e.error_code,
                "message": e.message,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "Failed to complete request",
                "timestamp": datetime.utcnow().isoformat()
            }
        )