"""
Emergency request processing service
"""
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import selectinload
from geoalchemy2.functions import ST_GeomFromText, ST_Within
import structlog

from app.core.redis import cache
from app.core.exceptions import APIError, ErrorCodes
from app.models.emergency import PanicRequest, RequestStatusUpdate, ServiceProvider
from app.models.user import UserGroup, GroupMobileNumber, RegisteredUser
from app.models.security_firm import SecurityFirm, CoverageArea, Team
from app.models.subscription import StoredSubscription, SubscriptionProduct
from app.services.geolocation import GeolocationService
from app.services.subscription import SubscriptionService
from app.services.websocket import websocket_service
from app.services.notification import notification_service, NotificationRecipient
from app.services.silent_mode import silent_mode_service, SilentModeRequest, Platform
from app.services.metrics import MetricsService

logger = structlog.get_logger()


class EmergencyRequestError(APIError):
    """Base emergency request error"""
    def __init__(self, message: str = "Emergency request error"):
        super().__init__(ErrorCodes.INVALID_SERVICE_TYPE, message)


class LocationNotCoveredError(EmergencyRequestError):
    """Location not covered by any security firm"""
    def __init__(self, message: str = "Location is not covered by any security firm"):
        super().__init__(ErrorCodes.LOCATION_NOT_COVERED, message)


class SubscriptionExpiredError(EmergencyRequestError):
    """Subscription expired error"""
    def __init__(self, message: str = "Subscription has expired"):
        super().__init__(ErrorCodes.SUBSCRIPTION_EXPIRED, message)


class InvalidServiceTypeError(EmergencyRequestError):
    """Invalid service type error"""
    def __init__(self, message: str = "Invalid service type"):
        super().__init__(ErrorCodes.INVALID_SERVICE_TYPE, message)


class DuplicateRequestError(EmergencyRequestError):
    """Duplicate request error"""
    def __init__(self, message: str = "Duplicate request detected"):
        super().__init__(ErrorCodes.DUPLICATE_REQUEST, message)


class UnauthorizedRequestError(EmergencyRequestError):
    """Unauthorized request error"""
    def __init__(self, message: str = "Phone number not authorized for this group"):
        super().__init__(ErrorCodes.INSUFFICIENT_PERMISSIONS, message)


class EmergencyService:
    """Service for managing emergency requests"""
    
    VALID_SERVICE_TYPES = ["call", "security", "ambulance", "fire", "towing"]
    RATE_LIMIT_WINDOW_MINUTES = 5
    MAX_REQUESTS_PER_WINDOW = 3
    DUPLICATE_REQUEST_WINDOW_MINUTES = 10
    
    def __init__(self, db: AsyncSession):
        self.db = db
        # Note: GeolocationService and SubscriptionService will be initialized with the same db session
        # but they may need to be adapted for async operations
        self.geolocation_service = GeolocationService(db)
        self.subscription_service = SubscriptionService(db)
        self.metrics_service = MetricsService()
    
    async def submit_panic_request(
        self,
        requester_phone: str,
        group_id: UUID,
        service_type: str,
        latitude: float,
        longitude: float,
        address: str,
        description: Optional[str] = None
    ) -> PanicRequest:
        """
        Submit a panic request with comprehensive validation
        
        Args:
            requester_phone: Phone number making the request
            group_id: User group ID
            service_type: Type of emergency service
            latitude: Request location latitude
            longitude: Request location longitude
            address: Human-readable address
            description: Optional request description
            
        Returns:
            Created panic request
            
        Raises:
            Various emergency request errors based on validation failures
        """
        logger.info(
            "panic_request_submission_started",
            requester_phone=requester_phone,
            group_id=str(group_id),
            service_type=service_type,
            latitude=latitude,
            longitude=longitude
        )
        
        # 1. Validate service type
        if service_type not in self.VALID_SERVICE_TYPES:
            raise InvalidServiceTypeError(
                f"Invalid service type. Must be one of: {', '.join(self.VALID_SERVICE_TYPES)}"
            )
        
        # 2. Validate request authorization (works even with locked accounts)
        user_id = await self._validate_panic_request_authorization(requester_phone, group_id)
        
        # 3. Check for rate limiting
        await self._check_rate_limiting(requester_phone)
        
        # 4. Check for duplicate requests
        await self._check_duplicate_requests(requester_phone, service_type, latitude, longitude)
        
        # 5. Validate subscription status
        group = await self._validate_subscription_status(group_id)
        
        # 6. Validate coverage area
        firm_id = await self._validate_coverage_area(group, latitude, longitude)
        
        # 7. Create panic request
        panic_request = PanicRequest(
            user_id=user_id,
            group_id=group_id,
            requester_phone=requester_phone,
            service_type=service_type,
            location=ST_GeomFromText(f"POINT({longitude} {latitude})", 4326),
            address=address,
            description=description,
            status="pending"
        )
        
        self.db.add(panic_request)
        await self.db.flush()  # Get the request ID
        
        # 8. Create initial status update
        status_update = RequestStatusUpdate(
            request_id=panic_request.id,
            status="pending",
            message="Emergency request received and validated"
        )
        self.db.add(status_update)
        
        # 9. Update rate limiting cache
        await self._update_rate_limiting_cache(requester_phone)
        
        await self.db.commit()
        await self.db.refresh(panic_request)
        
        # Record initial submission event for metrics
        await self.metrics_service.record_request_lifecycle_event(
            panic_request.id, "submitted", panic_request.created_at
        )
        
        # Send real-time confirmation to requester
        await websocket_service.send_request_confirmation(
            panic_request.id,
            group.user_id,  # Assuming group has user_id
            {
                "request_id": str(panic_request.id),
                "service_type": service_type,
                "status": "pending",
                "address": address
            }
        )
        
        # Send notification confirmation
        # Create notification recipient from requester phone
        notification_recipient = NotificationRecipient(
            phone_number=requester_phone,
            # Note: In a real implementation, you would look up user details
            # to get push token, email, etc. from the database
        )
        
        await notification_service.send_emergency_confirmation(
            notification_recipient,
            panic_request.id,
            service_type
        )
        
        # Activate silent mode for call service requests
        if service_type == "call":
            try:
                # Note: In a real implementation, you would determine the platform
                # from the user's device information stored in the database
                platform = Platform.ANDROID  # Default, should be determined from user data
                
                silent_mode_request = SilentModeRequest(
                    user_id=group.user_id,  # Assuming group has user_id
                    request_id=panic_request.id,
                    platform=platform,
                    duration_minutes=30  # 30 minutes for call requests
                )
                
                await silent_mode_service.activate_silent_mode(silent_mode_request)
                
                logger.info(
                    "silent_mode_activated_for_call_request",
                    request_id=str(panic_request.id),
                    user_id=str(group.user_id)
                )
                
            except Exception as e:
                # Don't fail the emergency request if silent mode fails
                logger.error(
                    "silent_mode_activation_failed_for_call_request",
                    request_id=str(panic_request.id),
                    error=str(e)
                )
        
        logger.info(
            "panic_request_submitted_successfully",
            request_id=str(panic_request.id),
            requester_phone=requester_phone,
            service_type=service_type,
            firm_id=str(firm_id)
        )
        
        return panic_request
    
    async def _validate_panic_request_authorization(
        self,
        requester_phone: str,
        group_id: UUID
    ) -> UUID:
        """
        Validate that the phone number is authorized to make requests for this group
        This works even if the account is locked
        
        Args:
            requester_phone: Phone number making the request
            group_id: User group ID
            
        Returns:
            UUID of the authorized user
            
        Raises:
            UnauthorizedRequestError: If phone number is not authorized
        """
        # First check if phone number belongs to any registered user and is a member of the group
        from app.models.user import UserGroupMembership
        
        result = await self.db.execute(
            select(RegisteredUser.id, UserGroup.id).
            select_from(RegisteredUser).
            join(UserGroupMembership, RegisteredUser.id == UserGroupMembership.user_id).
            join(UserGroup, UserGroupMembership.group_id == UserGroup.id).
            where(
                and_(
                    RegisteredUser.phone == requester_phone,
                    UserGroup.id == group_id,
                    RegisteredUser.is_verified == True
                )
            )
        )
        
        user_group = result.first()
        if not user_group:
            # Fallback: Check if phone number belongs to the group (legacy method)
            result = await self.db.execute(
                select(GroupMobileNumber).where(
                    and_(
                        GroupMobileNumber.group_id == group_id,
                        GroupMobileNumber.phone_number == requester_phone,
                        GroupMobileNumber.is_verified == True
                    )
                )
            )
            
            group_member = result.scalar_one_or_none()
            if not group_member:
                raise UnauthorizedRequestError(
                    "Phone number is not authorized to make requests for this group"
                )
            
            # Find the user by phone number if group mobile number exists
            result = await self.db.execute(
                select(RegisteredUser.id).where(RegisteredUser.phone == requester_phone)
            )
            user = result.scalar_one_or_none()
            if not user:
                raise UnauthorizedRequestError(
                    "Phone number not associated with any registered user"
                )
            
            return user
        
        return user_group[0]
    
    async def _check_rate_limiting(self, requester_phone: str) -> bool:
        """
        Check if the requester is within rate limits
        
        Args:
            requester_phone: Phone number to check
            
        Returns:
            True if within limits
            
        Raises:
            EmergencyRequestError: If rate limit exceeded
        """
        cache_key = f"rate_limit:emergency:{requester_phone}"
        current_count = await cache.get(cache_key)
        
        if current_count and int(current_count) >= self.MAX_REQUESTS_PER_WINDOW:
            raise EmergencyRequestError(
                f"Rate limit exceeded. Maximum {self.MAX_REQUESTS_PER_WINDOW} requests "
                f"per {self.RATE_LIMIT_WINDOW_MINUTES} minutes allowed"
            )
        
        return True
    
    async def _check_duplicate_requests(
        self,
        requester_phone: str,
        service_type: str,
        latitude: float,
        longitude: float
    ) -> bool:
        """
        Check for duplicate requests within the time window
        
        Args:
            requester_phone: Phone number making the request
            service_type: Type of service requested
            latitude: Request latitude
            longitude: Request longitude
            
        Returns:
            True if no duplicates found
            
        Raises:
            DuplicateRequestError: If duplicate request detected
        """
        # Check for recent requests from same phone with same service type
        cutoff_time = datetime.utcnow() - timedelta(minutes=self.DUPLICATE_REQUEST_WINDOW_MINUTES)
        
        result = await self.db.execute(
            select(PanicRequest).where(
                and_(
                    PanicRequest.requester_phone == requester_phone,
                    PanicRequest.service_type == service_type,
                    PanicRequest.created_at >= cutoff_time,
                    PanicRequest.status.in_(["pending", "assigned", "accepted", "en_route"])
                )
            )
        )
        
        existing_requests = result.scalars().all()
        
        # Check if any existing request is for a similar location (within 100m)
        for existing_request in existing_requests:
            # Extract coordinates from existing request
            from geoalchemy2.shape import to_shape
            existing_point = to_shape(existing_request.location)
            existing_lat = existing_point.y
            existing_lon = existing_point.x
            
            # Calculate distance using geolocation service
            distance_km = await self.geolocation_service.calculate_distance_km(
                latitude, longitude, existing_lat, existing_lon
            )
            
            # If within 100 meters (0.1 km), consider it a duplicate
            if distance_km <= 0.1:
                raise DuplicateRequestError(
                    f"Similar request already exists (Request ID: {existing_request.id})"
                )
        
        return True
    
    async def _validate_subscription_status(self, group_id: UUID) -> UserGroup:
        """
        Validate that the group has an active subscription
        
        Args:
            group_id: User group ID
            
        Returns:
            UserGroup object
            
        Raises:
            SubscriptionExpiredError: If subscription is expired or invalid
        """
        # Get group with subscription details
        result = await self.db.execute(
            select(UserGroup).where(UserGroup.id == group_id)
        )
        
        group = result.scalar_one_or_none()
        if not group:
            raise EmergencyRequestError("User group not found")
        
        # Check subscription status
        subscription_status = await self.subscription_service.validate_subscription_status(str(group_id))
        
        if not subscription_status["is_active"]:
            raise SubscriptionExpiredError(
                "Group subscription has expired or is not active"
            )
        
        return group
    
    async def _validate_coverage_area(
        self,
        group: UserGroup,
        latitude: float,
        longitude: float
    ) -> UUID:
        """
        Validate that the request location is within a security firm's coverage area
        
        Args:
            group: User group object
            latitude: Request latitude
            longitude: Request longitude
            
        Returns:
            Security firm ID that covers the location
            
        Raises:
            LocationNotCoveredError: If location is not covered
        """
        # Get the subscription product to find the firm
        if not group.subscription_id:
            raise SubscriptionExpiredError("Group has no active subscription")
        
        result = await self.db.execute(
            select(StoredSubscription).options(
                selectinload(StoredSubscription.product).selectinload(SubscriptionProduct.firm)
            ).where(StoredSubscription.id == group.subscription_id)
        )
        
        stored_subscription = result.scalar_one_or_none()
        if not stored_subscription or not stored_subscription.product:
            raise SubscriptionExpiredError("Invalid subscription")
        
        firm = stored_subscription.product.firm
        if not firm:
            raise EmergencyRequestError("Security firm not found")
        
        # Validate location is within firm's coverage area
        is_covered = await self.geolocation_service.validate_location_in_coverage(
            latitude, longitude, firm.id
        )
        
        if not is_covered:
            # Get alternative firms for better error message
            alternative_firms = await self.subscription_service.get_alternative_firms_for_location(
                latitude, longitude
            )
            
            error_message = "Location is outside the security firm's coverage area"
            if alternative_firms:
                firm_names = [f["firm_name"] for f in alternative_firms[:3]]
                error_message += f". Alternative firms available: {', '.join(firm_names)}"
            
            raise LocationNotCoveredError(error_message)
        
        return firm.id
    
    async def _update_rate_limiting_cache(self, requester_phone: str) -> None:
        """
        Update rate limiting cache for the requester
        
        Args:
            requester_phone: Phone number to update
        """
        cache_key = f"rate_limit:emergency:{requester_phone}"
        current_count = await cache.get(cache_key)
        
        if current_count:
            new_count = int(current_count) + 1
        else:
            new_count = 1
        
        # Set with expiration time
        await cache.set(
            cache_key,
            str(new_count),
            expire=self.RATE_LIMIT_WINDOW_MINUTES * 60
        )
    
    async def get_request_by_id(self, request_id: UUID) -> Optional[PanicRequest]:
        """
        Get panic request by ID with all related data
        
        Args:
            request_id: Panic request ID
            
        Returns:
            PanicRequest object or None
        """
        result = await self.db.execute(
            select(PanicRequest).options(
                selectinload(PanicRequest.user),
                selectinload(PanicRequest.group),
                selectinload(PanicRequest.assigned_team),
                selectinload(PanicRequest.assigned_service_provider),
                selectinload(PanicRequest.status_updates),
                selectinload(PanicRequest.feedback)
            ).where(PanicRequest.id == request_id)
        )
        
        return result.scalar_one_or_none()
    
    async def get_user_requests(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
        status_filter: Optional[str] = None
    ) -> List[PanicRequest]:
        """
        Get panic requests for a user's groups
        
        Args:
            user_id: User ID
            limit: Maximum number of requests to return
            offset: Number of requests to skip
            status_filter: Optional status filter
            
        Returns:
            List of panic requests
        """
        # Build query - get requests from groups that the user is a member of
        from app.models.user import UserGroupMembership
        
        query = select(PanicRequest).options(
            selectinload(PanicRequest.user),
            selectinload(PanicRequest.group),
            selectinload(PanicRequest.assigned_team),
            selectinload(PanicRequest.status_updates)
        ).join(UserGroup).join(
            UserGroupMembership, UserGroup.id == UserGroupMembership.group_id
        ).where(UserGroupMembership.user_id == user_id)
        
        if status_filter:
            query = query.where(PanicRequest.status == status_filter)
        
        query = query.order_by(desc(PanicRequest.created_at)).limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_group_requests(
        self,
        group_id: UUID,
        limit: int = 50,
        offset: int = 0
    ) -> List[PanicRequest]:
        """
        Get panic requests for a specific group
        
        Args:
            group_id: Group ID
            limit: Maximum number of requests to return
            offset: Number of requests to skip
            
        Returns:
            List of panic requests
        """
        result = await self.db.execute(
            select(PanicRequest).options(
                selectinload(PanicRequest.user),
                selectinload(PanicRequest.group),
                selectinload(PanicRequest.status_updates),
                selectinload(PanicRequest.assigned_team),
                selectinload(PanicRequest.assigned_service_provider)
            ).where(PanicRequest.group_id == group_id)
            .order_by(desc(PanicRequest.created_at))
            .limit(limit)
            .offset(offset)
        )
        
        return result.scalars().all()
    
    async def update_request_status(
        self,
        request_id: UUID,
        new_status: str,
        message: Optional[str] = None,
        updated_by_id: Optional[UUID] = None,
        location: Optional[Tuple[float, float]] = None
    ) -> bool:
        """
        Update panic request status with tracking
        
        Args:
            request_id: Panic request ID
            new_status: New status value
            message: Optional status message
            updated_by_id: ID of person updating status
            location: Optional location coordinates (lat, lon)
            
        Returns:
            True if updated successfully
        """
        # Get existing request
        panic_request = await self.get_request_by_id(request_id)
        if not panic_request:
            raise EmergencyRequestError("Panic request not found")
        
        # Update request status
        panic_request.status = new_status
        
        # Set timestamps based on status
        now = datetime.utcnow()
        if new_status == "accepted" and not panic_request.accepted_at:
            panic_request.accepted_at = now
        elif new_status == "arrived" and not panic_request.arrived_at:
            panic_request.arrived_at = now
        elif new_status == "completed" and not panic_request.completed_at:
            panic_request.completed_at = now
        
        # Create status update record
        location_geom = None
        if location:
            lat, lon = location
            location_geom = ST_GeomFromText(f"POINT({lon} {lat})", 4326)
        
        status_update = RequestStatusUpdate(
            request_id=request_id,
            status=new_status,
            message=message,
            location=location_geom,
            updated_by_id=updated_by_id
        )
        
        self.db.add(status_update)
        await self.db.commit()
        
        # Record metrics for lifecycle events based on status
        if new_status == "accepted":
            # We would need firm_id and zone info for this, but they're not available in this context
            # For now, we'll skip detailed metrics for status updates
            pass
        elif new_status == "completed":
            # We would need firm_id, zone, and timing info for this
            # For now, we'll skip detailed metrics for status updates  
            pass
        # Note: Consider implementing a simpler metrics method for status updates
        
        # Send real-time status update to all subscribers
        additional_data = {}
        if location:
            additional_data["location"] = {"latitude": location[0], "longitude": location[1]}
        if updated_by_id:
            additional_data["updated_by"] = str(updated_by_id)
            
        await websocket_service.send_request_status_update(
            request_id,
            new_status,
            additional_data
        )
        
        logger.info(
            "panic_request_status_updated",
            request_id=str(request_id),
            old_status=panic_request.status,
            new_status=new_status,
            updated_by=str(updated_by_id) if updated_by_id else None
        )
        
        return True
    
    async def get_request_statistics(
        self,
        firm_id: Optional[UUID] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get emergency request statistics
        
        Args:
            firm_id: Optional firm ID filter
            date_from: Optional start date filter
            date_to: Optional end date filter
            
        Returns:
            Dictionary with request statistics
        """
        # Build base query
        query = select(PanicRequest)
        
        if firm_id:
            # Join with subscription data to filter by firm
            query = query.join(UserGroup).join(
                StoredSubscription, UserGroup.subscription_id == StoredSubscription.id
            ).join(SubscriptionProduct).where(SubscriptionProduct.firm_id == firm_id)
        
        if date_from:
            query = query.where(PanicRequest.created_at >= date_from)
        
        if date_to:
            query = query.where(PanicRequest.created_at <= date_to)
        
        result = await self.db.execute(query)
        requests = result.scalars().all()
        
        # Calculate statistics
        total_requests = len(requests)
        status_counts = {}
        service_type_counts = {}
        
        for request in requests:
            # Count by status
            status_counts[request.status] = status_counts.get(request.status, 0) + 1
            
            # Count by service type
            service_type_counts[request.service_type] = service_type_counts.get(request.service_type, 0) + 1
        
        # Calculate response times for completed requests
        response_times = []
        for request in requests:
            if request.completed_at and request.accepted_at:
                response_time = (request.completed_at - request.accepted_at).total_seconds() / 60  # minutes
                response_times.append(response_time)
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        return {
            "total_requests": total_requests,
            "status_breakdown": status_counts,
            "service_type_breakdown": service_type_counts,
            "average_response_time_minutes": round(avg_response_time, 2),
            "completed_requests": len(response_times),
            "date_range": {
                "from": date_from.isoformat() if date_from else None,
                "to": date_to.isoformat() if date_to else None
            }
        }
    
    # Request Allocation and Assignment Methods
    
    async def get_pending_requests_for_firm(
        self,
        firm_id: UUID,
        limit: int = 50,
        offset: int = 0
    ) -> List[PanicRequest]:
        """
        Get pending panic requests for a security firm
        
        Args:
            firm_id: Security firm ID
            limit: Maximum number of requests to return
            offset: Number of requests to skip
            
        Returns:
            List of pending panic requests
        """
        # Query for pending requests that belong to groups with subscriptions from this firm
        result = await self.db.execute(
            select(PanicRequest).options(
                selectinload(PanicRequest.user),
                selectinload(PanicRequest.group),
                selectinload(PanicRequest.status_updates)
            ).join(UserGroup).join(
                StoredSubscription, UserGroup.subscription_id == StoredSubscription.id
            ).join(SubscriptionProduct).where(
                and_(
                    SubscriptionProduct.firm_id == firm_id,
                    PanicRequest.status == "pending"
                )
            ).order_by(PanicRequest.created_at).limit(limit).offset(offset)
        )
        
        return result.scalars().all()
    
    async def allocate_request_to_team(
        self,
        request_id: UUID,
        team_id: UUID,
        allocated_by_id: UUID
    ) -> bool:
        """
        Allocate a panic request to a team
        
        Args:
            request_id: Panic request ID
            team_id: Team ID to assign the request to
            allocated_by_id: ID of office staff member allocating the request
            
        Returns:
            True if successfully allocated
            
        Raises:
            EmergencyRequestError: If request cannot be allocated
        """
        # Get the panic request
        panic_request = await self.get_request_by_id(request_id)
        if not panic_request:
            raise EmergencyRequestError("Panic request not found")
        
        if panic_request.status != "pending":
            raise EmergencyRequestError("Request is not in pending status")
        
        # Verify team exists and belongs to the correct firm
        from app.models.security_firm import Team
        result = await self.db.execute(
            select(Team).where(Team.id == team_id)
        )
        team = result.scalar_one_or_none()
        
        if not team:
            raise EmergencyRequestError("Team not found")
        
        if not team.is_active:
            raise EmergencyRequestError("Team is not active")
        
        # For call service type, don't assign to field agents
        if panic_request.service_type == "call":
            raise EmergencyRequestError("Call service requests should not be assigned to field teams")
        
        # Update request assignment
        panic_request.assigned_team_id = team_id
        panic_request.status = "assigned"
        
        # Create status update
        status_update = RequestStatusUpdate(
            request_id=request_id,
            status="assigned",
            message=f"Request assigned to team {team.name}",
            updated_by_id=allocated_by_id
        )
        
        self.db.add(status_update)
        await self.db.commit()
        
        # Send real-time status update to all subscribers
        await websocket_service.send_request_status_update(
            request_id,
            "assigned",
            {
                "team_id": str(team_id),
                "team_name": team.name,
                "assigned_by": str(allocated_by_id)
            }
        )
        
        # Notify team members about the new assignment
        # Get team members and notify them
        from app.models.security_firm import FirmPersonnel
        result = await self.db.execute(
            select(FirmPersonnel).where(
                and_(
                    FirmPersonnel.team_id == team_id,
                    FirmPersonnel.is_active == True
                )
            )
        )
        team_members = result.scalars().all()
        
        for member in team_members:
            await websocket_service.notify_field_agent_assignment(
                member.id,
                {
                    "request_id": str(request_id),
                    "service_type": panic_request.service_type,
                    "address": panic_request.address,
                    "description": panic_request.description,
                    "requester_phone": panic_request.requester_phone
                }
            )
        
        logger.info(
            "panic_request_allocated_to_team",
            request_id=str(request_id),
            team_id=str(team_id),
            allocated_by=str(allocated_by_id)
        )
        
        return True
    
    async def allocate_request_to_service_provider(
        self,
        request_id: UUID,
        service_provider_id: UUID,
        allocated_by_id: UUID
    ) -> bool:
        """
        Allocate a panic request to an external service provider
        
        Args:
            request_id: Panic request ID
            service_provider_id: Service provider ID
            allocated_by_id: ID of office staff member allocating the request
            
        Returns:
            True if successfully allocated
            
        Raises:
            EmergencyRequestError: If request cannot be allocated
        """
        # Get the panic request
        panic_request = await self.get_request_by_id(request_id)
        if not panic_request:
            raise EmergencyRequestError("Panic request not found")
        
        if panic_request.status != "pending":
            raise EmergencyRequestError("Request is not in pending status")
        
        # Verify service provider exists and is active
        result = await self.db.execute(
            select(ServiceProvider).where(ServiceProvider.id == service_provider_id)
        )
        service_provider = result.scalar_one_or_none()
        
        if not service_provider:
            raise EmergencyRequestError("Service provider not found")
        
        if not service_provider.is_active:
            raise EmergencyRequestError("Service provider is not active")
        
        # Verify service type matches
        if panic_request.service_type != service_provider.service_type:
            raise EmergencyRequestError(
                f"Service type mismatch: request is for {panic_request.service_type}, "
                f"provider offers {service_provider.service_type}"
            )
        
        # Update request assignment
        panic_request.assigned_service_provider_id = service_provider_id
        panic_request.status = "assigned"
        
        # Create status update
        status_update = RequestStatusUpdate(
            request_id=request_id,
            status="assigned",
            message=f"Request assigned to {service_provider.name}",
            updated_by_id=allocated_by_id
        )
        
        self.db.add(status_update)
        await self.db.commit()
        
        # Send real-time provider assignment notification
        estimated_arrival_time = 15  # Default ETA, should be calculated based on location
        await websocket_service.send_provider_assignment(
            request_id,
            {
                "provider_id": str(service_provider_id),
                "provider_name": service_provider.name,
                "provider_phone": service_provider.phone,
                "service_type": service_provider.service_type
            },
            estimated_arrival_time=estimated_arrival_time
        )
        
        # Send notification to requester about provider assignment
        requester_recipient = NotificationRecipient(
            phone_number=panic_request.requester_phone
        )
        
        await notification_service.send_provider_assignment(
            requester_recipient,
            service_provider.name,
            estimated_arrival_time,
            f"{service_provider.service_type} vehicle"
        )
        
        # Notify the service provider about the new assignment
        provider_recipient = NotificationRecipient(
            user_id=service_provider_id,
            # Note: In a real implementation, you would look up provider contact details
        )
        
        await notification_service.send_field_agent_assignment(
            provider_recipient,
            panic_request.service_type,
            panic_request.address,
            panic_request.description
        )
        
        await websocket_service.notify_field_agent_assignment(
            service_provider_id,
            {
                "request_id": str(request_id),
                "service_type": panic_request.service_type,
                "address": panic_request.address,
                "description": panic_request.description,
                "requester_phone": panic_request.requester_phone,
                "location": {
                    "latitude": panic_request.location.x if panic_request.location else None,
                    "longitude": panic_request.location.y if panic_request.location else None
                }
            }
        )
        
        logger.info(
            "panic_request_allocated_to_service_provider",
            request_id=str(request_id),
            service_provider_id=str(service_provider_id),
            allocated_by=str(allocated_by_id)
        )
        
        return True
    
    async def handle_call_service_request(
        self,
        request_id: UUID,
        handled_by_id: UUID,
        notes: Optional[str] = None
    ) -> bool:
        """
        Handle a call service request directly by office staff
        
        Args:
            request_id: Panic request ID
            handled_by_id: ID of office staff handling the call
            notes: Optional notes about the call handling
            
        Returns:
            True if successfully handled
            
        Raises:
            EmergencyRequestError: If request cannot be handled
        """
        # Get the panic request
        panic_request = await self.get_request_by_id(request_id)
        if not panic_request:
            raise EmergencyRequestError("Panic request not found")
        
        if panic_request.service_type != "call":
            raise EmergencyRequestError("This method is only for call service requests")
        
        if panic_request.status not in ["pending", "assigned"]:
            raise EmergencyRequestError("Request is not in a state that can be handled")
        
        # Update request status to handled
        panic_request.status = "handled"
        panic_request.accepted_at = datetime.utcnow()
        
        # Create status update
        message = "Call service handled by office staff"
        if notes:
            message += f": {notes}"
        
        status_update = RequestStatusUpdate(
            request_id=request_id,
            status="handled",
            message=message,
            updated_by_id=handled_by_id
        )
        
        self.db.add(status_update)
        await self.db.commit()
        
        # Deactivate silent mode for call requests
        try:
            # Get the user ID from the group
            group = panic_request.group
            if group and group.user_id:
                await silent_mode_service.deactivate_silent_mode(
                    group.user_id,
                    request_id
                )
                
                logger.info(
                    "silent_mode_deactivated_for_handled_call",
                    request_id=str(request_id),
                    user_id=str(group.user_id)
                )
                
        except Exception as e:
            # Don't fail the request handling if silent mode deactivation fails
            logger.error(
                "silent_mode_deactivation_failed_for_handled_call",
                request_id=str(request_id),
                error=str(e)
            )
        
        logger.info(
            "call_service_request_handled",
            request_id=str(request_id),
            handled_by=str(handled_by_id)
        )
        
        return True
    
    async def get_team_assigned_requests(
        self,
        team_id: UUID,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[PanicRequest]:
        """
        Get panic requests assigned to a specific team
        
        Args:
            team_id: Team ID
            status_filter: Optional status filter
            limit: Maximum number of requests to return
            offset: Number of requests to skip
            
        Returns:
            List of assigned panic requests
        """
        query = select(PanicRequest).options(
            selectinload(PanicRequest.user),
            selectinload(PanicRequest.group),
            selectinload(PanicRequest.status_updates)
        ).where(PanicRequest.assigned_team_id == team_id)
        
        if status_filter:
            query = query.where(PanicRequest.status == status_filter)
        
        query = query.order_by(desc(PanicRequest.created_at)).limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_service_provider_assigned_requests(
        self,
        service_provider_id: UUID,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[PanicRequest]:
        """
        Get panic requests assigned to a specific service provider
        
        Args:
            service_provider_id: Service provider ID
            status_filter: Optional status filter
            limit: Maximum number of requests to return
            offset: Number of requests to skip
            
        Returns:
            List of assigned panic requests
        """
        query = select(PanicRequest).options(
            selectinload(PanicRequest.group),
            selectinload(PanicRequest.status_updates)
        ).where(PanicRequest.assigned_service_provider_id == service_provider_id)
        
        if status_filter:
            query = query.where(PanicRequest.status == status_filter)
        
        query = query.order_by(desc(PanicRequest.created_at)).limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def reassign_request(
        self,
        request_id: UUID,
        new_team_id: Optional[UUID] = None,
        new_service_provider_id: Optional[UUID] = None,
        reassigned_by_id: UUID = None,
        reason: Optional[str] = None
    ) -> bool:
        """
        Reassign a panic request to a different team or service provider
        
        Args:
            request_id: Panic request ID
            new_team_id: New team ID (mutually exclusive with service_provider_id)
            new_service_provider_id: New service provider ID
            reassigned_by_id: ID of person reassigning the request
            reason: Reason for reassignment
            
        Returns:
            True if successfully reassigned
            
        Raises:
            EmergencyRequestError: If request cannot be reassigned
        """
        if not new_team_id and not new_service_provider_id:
            raise EmergencyRequestError("Must specify either team or service provider for reassignment")
        
        if new_team_id and new_service_provider_id:
            raise EmergencyRequestError("Cannot assign to both team and service provider")
        
        # Get the panic request
        panic_request = await self.get_request_by_id(request_id)
        if not panic_request:
            raise EmergencyRequestError("Panic request not found")
        
        if panic_request.status not in ["assigned", "accepted"]:
            raise EmergencyRequestError("Request cannot be reassigned in current status")
        
        # Clear existing assignments
        panic_request.assigned_team_id = None
        panic_request.assigned_service_provider_id = None
        
        # Set new assignment
        if new_team_id:
            # Verify team exists
            from app.models.security_firm import Team
            result = await self.db.execute(
                select(Team).where(Team.id == new_team_id)
            )
            team = result.scalar_one_or_none()
            if not team or not team.is_active:
                raise EmergencyRequestError("Invalid or inactive team")
            
            panic_request.assigned_team_id = new_team_id
            assignment_target = f"team {team.name}"
        
        if new_service_provider_id:
            # Verify service provider exists
            result = await self.db.execute(
                select(ServiceProvider).where(ServiceProvider.id == new_service_provider_id)
            )
            service_provider = result.scalar_one_or_none()
            if not service_provider or not service_provider.is_active:
                raise EmergencyRequestError("Invalid or inactive service provider")
            
            panic_request.assigned_service_provider_id = new_service_provider_id
            assignment_target = service_provider.name
        
        # Update status back to assigned
        panic_request.status = "assigned"
        
        # Create status update
        message = f"Request reassigned to {assignment_target}"
        if reason:
            message += f" - Reason: {reason}"
        
        status_update = RequestStatusUpdate(
            request_id=request_id,
            status="assigned",
            message=message,
            updated_by_id=reassigned_by_id
        )
        
        self.db.add(status_update)
        await self.db.commit()
        
        logger.info(
            "panic_request_reassigned",
            request_id=str(request_id),
            new_team_id=str(new_team_id) if new_team_id else None,
            new_service_provider_id=str(new_service_provider_id) if new_service_provider_id else None,
            reassigned_by=str(reassigned_by_id)
        )
        
        return True
    
    # Field Agent Request Handling Methods
    
    async def get_agent_assigned_requests(
        self,
        agent_id: UUID,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[PanicRequest]:
        """
        Get panic requests accessible to a specific firm personnel
        
        - Field agents and team leaders: see requests assigned to their team
        - Firm supervisors and firm users without team: see all requests for their firm
        - Other roles without team: no access
        
        Args:
            agent_id: Firm personnel ID
            status_filter: Optional status filter
            limit: Maximum number of requests to return
            offset: Number of requests to skip
            
        Returns:
            List of accessible panic requests
        """
        # Get agent's team first
        from app.models.security_firm import FirmPersonnel
        try:
            result = await self.db.execute(
                select(FirmPersonnel).where(FirmPersonnel.id == agent_id)
            )
            agent = result.scalar_one_or_none()
            
            if not agent:
                logger.warning(f"Agent not found: {agent_id}")
                return []
                
            logger.info(f"Found agent: {agent.email}, role: {agent.role}, team: {agent.team_id}, firm: {agent.firm_id}")
        except Exception as e:
            logger.error(f"Error fetching agent {agent_id}: {str(e)}")
            raise
        
        # Build query based on user role and team assignment
        query = select(PanicRequest).options(
            selectinload(PanicRequest.user),
            selectinload(PanicRequest.group),
            selectinload(PanicRequest.status_updates)
        )
        
        if agent.team_id:
            # Field agents and team leaders: see only their team's requests
            query = query.where(PanicRequest.assigned_team_id == agent.team_id)
        elif agent.role in ["firm_supervisor", "firm_user", "firm_admin"]:
            # Firm supervisors and users without team: see all requests for their firm
            # First check if there are any teams for their firm
            from app.models.security_firm import Team
            logger.info(f"Looking for teams for firm {agent.firm_id}")
            try:
                team_result = await self.db.execute(
                    select(Team.id).where(Team.firm_id == agent.firm_id)
                )
                team_ids = team_result.scalars().all()
                logger.info(f"Found {len(team_ids)} teams for firm {agent.firm_id}")
                
                if team_ids:
                    # If there are teams for this firm, show requests assigned to any of those teams
                    query = query.where(PanicRequest.assigned_team_id.in_(team_ids))
                else:
                    # If no teams exist for this firm yet, return empty list
                    logger.info(f"No teams found for firm {agent.firm_id}, returning empty list")
                    return []
            except Exception as e:
                logger.error(f"Error checking teams for firm {agent.firm_id}: {str(e)}")
                raise
        else:
            # Other roles without team assignment: no access
            return []
        
        if status_filter:
            query = query.where(PanicRequest.status == status_filter)
        
        query = query.order_by(desc(PanicRequest.created_at)).limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def accept_request(
        self,
        request_id: UUID,
        agent_id: UUID,
        estimated_arrival_minutes: Optional[int] = None
    ) -> bool:
        """
        Accept a panic request as a field agent
        
        Args:
            request_id: Panic request ID
            agent_id: Field agent ID accepting the request
            estimated_arrival_minutes: Estimated time to arrival
            
        Returns:
            True if successfully accepted
            
        Raises:
            EmergencyRequestError: If request cannot be accepted
        """
        # Get the panic request
        panic_request = await self.get_request_by_id(request_id)
        if not panic_request:
            raise EmergencyRequestError("Panic request not found")
        
        if panic_request.status != "assigned":
            raise EmergencyRequestError("Request is not in assigned status")
        
        # Verify agent is part of the assigned team
        from app.models.security_firm import FirmPersonnel
        result = await self.db.execute(
            select(FirmPersonnel).where(FirmPersonnel.id == agent_id)
        )
        agent = result.scalar_one_or_none()
        
        if not agent:
            raise EmergencyRequestError("Field agent not found")
        
        if str(agent.team_id) != str(panic_request.assigned_team_id):
            raise EmergencyRequestError("Agent is not part of the assigned team")
        
        # Update request status
        panic_request.status = "accepted"
        panic_request.accepted_at = datetime.utcnow()
        
        # Create status update
        message = f"Request accepted by field agent {agent.first_name} {agent.last_name}"
        if estimated_arrival_minutes:
            message += f" (ETA: {estimated_arrival_minutes} minutes)"
        
        status_update = RequestStatusUpdate(
            request_id=request_id,
            status="accepted",
            message=message,
            updated_by_id=agent_id
        )
        
        self.db.add(status_update)
        await self.db.commit()
        
        logger.info(
            "panic_request_accepted_by_agent",
            request_id=str(request_id),
            agent_id=str(agent_id),
            eta_minutes=estimated_arrival_minutes
        )
        
        return True
    
    async def reject_request(
        self,
        request_id: UUID,
        agent_id: UUID,
        reason: Optional[str] = None
    ) -> bool:
        """
        Reject a panic request as a field agent
        
        Args:
            request_id: Panic request ID
            agent_id: Field agent ID rejecting the request
            reason: Optional reason for rejection
            
        Returns:
            True if successfully rejected
            
        Raises:
            EmergencyRequestError: If request cannot be rejected
        """
        # Get the panic request
        panic_request = await self.get_request_by_id(request_id)
        if not panic_request:
            raise EmergencyRequestError("Panic request not found")
        
        if panic_request.status != "assigned":
            raise EmergencyRequestError("Request is not in assigned status")
        
        # Verify agent is part of the assigned team
        from app.models.security_firm import FirmPersonnel
        result = await self.db.execute(
            select(FirmPersonnel).where(FirmPersonnel.id == agent_id)
        )
        agent = result.scalar_one_or_none()
        
        if not agent:
            raise EmergencyRequestError("Field agent not found")
        
        if str(agent.team_id) != str(panic_request.assigned_team_id):
            raise EmergencyRequestError("Agent is not part of the assigned team")
        
        # Update request status back to pending for reassignment
        panic_request.status = "pending"
        panic_request.assigned_team_id = None
        
        # Create status update
        message = f"Request rejected by field agent {agent.first_name} {agent.last_name}"
        if reason:
            message += f" - Reason: {reason}"
        
        status_update = RequestStatusUpdate(
            request_id=request_id,
            status="pending",
            message=message,
            updated_by_id=agent_id
        )
        
        self.db.add(status_update)
        await self.db.commit()
        
        logger.info(
            "panic_request_rejected_by_agent",
            request_id=str(request_id),
            agent_id=str(agent_id),
            reason=reason
        )
        
        return True
    
    async def update_agent_location(
        self,
        request_id: UUID,
        agent_id: UUID,
        latitude: float,
        longitude: float,
        status_message: Optional[str] = None
    ) -> bool:
        """
        Update field agent location during service
        
        Args:
            request_id: Panic request ID
            agent_id: Field agent ID
            latitude: Current latitude
            longitude: Current longitude
            status_message: Optional status message
            
        Returns:
            True if successfully updated
            
        Raises:
            EmergencyRequestError: If location cannot be updated
        """
        # Get the panic request
        panic_request = await self.get_request_by_id(request_id)
        if not panic_request:
            raise EmergencyRequestError("Panic request not found")
        
        if panic_request.status not in ["accepted", "en_route"]:
            raise EmergencyRequestError("Request is not in a trackable status")
        
        # Verify agent is part of the assigned team
        from app.models.security_firm import FirmPersonnel
        result = await self.db.execute(
            select(FirmPersonnel).where(FirmPersonnel.id == agent_id)
        )
        agent = result.scalar_one_or_none()
        
        if not agent:
            raise EmergencyRequestError("Field agent not found")
        
        if str(agent.team_id) != str(panic_request.assigned_team_id):
            raise EmergencyRequestError("Agent is not part of the assigned team")
        
        # Update status to en_route if not already
        if panic_request.status == "accepted":
            panic_request.status = "en_route"
        
        # Create location update
        location_geom = ST_GeomFromText(f"POINT({longitude} {latitude})", 4326)
        
        message = status_message or "Agent location updated"
        
        status_update = RequestStatusUpdate(
            request_id=request_id,
            status=panic_request.status,
            message=message,
            location=location_geom,
            updated_by_id=agent_id
        )
        
        self.db.add(status_update)
        await self.db.commit()
        
        logger.info(
            "agent_location_updated",
            request_id=str(request_id),
            agent_id=str(agent_id),
            latitude=latitude,
            longitude=longitude
        )
        
        return True
    
    async def mark_arrived(
        self,
        request_id: UUID,
        agent_id: UUID,
        arrival_notes: Optional[str] = None
    ) -> bool:
        """
        Mark that field agent has arrived at the location
        
        Args:
            request_id: Panic request ID
            agent_id: Field agent ID
            arrival_notes: Optional notes about arrival
            
        Returns:
            True if successfully marked as arrived
            
        Raises:
            EmergencyRequestError: If arrival cannot be marked
        """
        # Get the panic request
        panic_request = await self.get_request_by_id(request_id)
        if not panic_request:
            raise EmergencyRequestError("Panic request not found")
        
        if panic_request.status not in ["accepted", "en_route"]:
            raise EmergencyRequestError("Request is not in a status that can be marked as arrived")
        
        # Verify agent is part of the assigned team
        from app.models.security_firm import FirmPersonnel
        result = await self.db.execute(
            select(FirmPersonnel).where(FirmPersonnel.id == agent_id)
        )
        agent = result.scalar_one_or_none()
        
        if not agent:
            raise EmergencyRequestError("Field agent not found")
        
        if str(agent.team_id) != str(panic_request.assigned_team_id):
            raise EmergencyRequestError("Agent is not part of the assigned team")
        
        # Update request status
        panic_request.status = "arrived"
        panic_request.arrived_at = datetime.utcnow()
        
        # Create status update
        message = f"Field agent {agent.first_name} {agent.last_name} has arrived at location"
        if arrival_notes:
            message += f" - Notes: {arrival_notes}"
        
        status_update = RequestStatusUpdate(
            request_id=request_id,
            status="arrived",
            message=message,
            updated_by_id=agent_id
        )
        
        self.db.add(status_update)
        await self.db.commit()
        
        logger.info(
            "agent_arrived_at_location",
            request_id=str(request_id),
            agent_id=str(agent_id)
        )
        
        return True
    
    async def complete_request_with_feedback(
        self,
        request_id: UUID,
        agent_id: UUID,
        is_prank: bool = False,
        performance_rating: Optional[int] = None,
        completion_notes: Optional[str] = None
    ) -> bool:
        """
        Complete a panic request with feedback
        
        Args:
            request_id: Panic request ID
            agent_id: Field agent ID completing the request
            is_prank: Whether the request was a prank
            performance_rating: Performance rating (1-5)
            completion_notes: Notes about the completion
            
        Returns:
            True if successfully completed
            
        Raises:
            EmergencyRequestError: If request cannot be completed
        """
        # Get the panic request
        panic_request = await self.get_request_by_id(request_id)
        if not panic_request:
            raise EmergencyRequestError("Panic request not found")
        
        if panic_request.status not in ["arrived", "en_route", "accepted"]:
            raise EmergencyRequestError("Request is not in a status that can be completed")
        
        # Verify agent is part of the assigned team
        from app.models.security_firm import FirmPersonnel
        result = await self.db.execute(
            select(FirmPersonnel).where(FirmPersonnel.id == agent_id)
        )
        agent = result.scalar_one_or_none()
        
        if not agent:
            raise EmergencyRequestError("Field agent not found")
        
        if str(agent.team_id) != str(panic_request.assigned_team_id):
            raise EmergencyRequestError("Agent is not part of the assigned team")
        
        # Validate performance rating
        if performance_rating is not None and (performance_rating < 1 or performance_rating > 5):
            raise EmergencyRequestError("Performance rating must be between 1 and 5")
        
        # Update request status
        panic_request.status = "completed"
        panic_request.completed_at = datetime.utcnow()
        
        # Create feedback record
        from app.models.emergency import RequestFeedback
        feedback = RequestFeedback(
            request_id=request_id,
            team_member_id=agent_id,
            is_prank=is_prank,
            performance_rating=performance_rating,
            comments=completion_notes
        )
        
        self.db.add(feedback)
        
        # Create status update
        message = f"Request completed by field agent {agent.first_name} {agent.last_name}"
        if is_prank:
            message += " (flagged as prank)"
        if performance_rating:
            message += f" (rating: {performance_rating}/5)"
        
        status_update = RequestStatusUpdate(
            request_id=request_id,
            status="completed",
            message=message,
            updated_by_id=agent_id
        )
        
        self.db.add(status_update)
        
        # If flagged as prank, update user's prank count
        if is_prank:
            await self._handle_prank_flag(panic_request.group_id)
        
        await self.db.commit()
        
        logger.info(
            "panic_request_completed_by_agent",
            request_id=str(request_id),
            agent_id=str(agent_id),
            is_prank=is_prank,
            performance_rating=performance_rating
        )
        
        return True
    
    async def _handle_prank_flag(self, group_id: UUID) -> None:
        """
        Handle prank flag by updating group owner's prank count
        
        Args:
            group_id: User group ID
        """
        # Get the group owner (user with role 'owner' in memberships)
        from app.models.user import UserGroupMembership
        
        result = await self.db.execute(
            select(RegisteredUser).join(
                UserGroupMembership, RegisteredUser.id == UserGroupMembership.user_id
            ).where(
                and_(
                    UserGroupMembership.group_id == group_id,
                    UserGroupMembership.role == 'owner'
                )
            )
        )
        
        owner = result.scalar_one_or_none()
        if owner:
            # Increment prank flags
            owner.prank_flags += 1
            
            logger.info(
                "user_prank_flag_incremented",
                user_id=str(owner.id),
                total_prank_flags=owner.prank_flags
            )
    
    async def get_agent_active_requests(
        self,
        agent_id: UUID
    ) -> List[PanicRequest]:
        """
        Get active requests for a field agent
        
        Args:
            agent_id: Field agent ID
            
        Returns:
            List of active panic requests
        """
        return await self.get_agent_assigned_requests(
            agent_id=agent_id,
            status_filter=None  # Get all statuses, filter in query
        )
    
    async def get_request_location_updates(
        self,
        request_id: UUID,
        limit: int = 50
    ) -> List[RequestStatusUpdate]:
        """
        Get location updates for a panic request
        
        Args:
            request_id: Panic request ID
            limit: Maximum number of updates to return
            
        Returns:
            List of status updates with location data
        """
        result = await self.db.execute(
            select(RequestStatusUpdate).where(
                and_(
                    RequestStatusUpdate.request_id == request_id,
                    RequestStatusUpdate.location.isnot(None)
                )
            ).order_by(desc(RequestStatusUpdate.created_at)).limit(limit)
        )
        
        return result.scalars().all()
    
    async def find_nearest_team(
        self,
        latitude: float,
        longitude: float,
        firm_id: Optional[UUID] = None
    ) -> Tuple[Optional[Team], Optional[float]]:
        """
        Find the nearest team to a given location based on distance to coverage area centroid
        
        Args:
            latitude: Request location latitude
            longitude: Request location longitude  
            firm_id: Optional firm ID to filter teams
            
        Returns:
            Tuple of (nearest_team, distance_km) or (None, None) if no teams found
        """
        try:
            # Create a point from the request location
            request_point = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)
            
            # Query to find the nearest team based on coverage area centroid
            query = select(
                Team,
                # Calculate distance in kilometers between request point and coverage area centroid
                func.ST_Distance(
                    func.ST_Transform(request_point, 3857),
                    func.ST_Transform(func.ST_Centroid(CoverageArea.boundary), 3857)
                ).label('distance_m')
            ).join(
                CoverageArea, Team.coverage_area_id == CoverageArea.id
            ).where(
                and_(
                    Team.is_active == True,
                    CoverageArea.is_active == True
                )
            )
            
            # Filter by firm if specified
            if firm_id:
                query = query.where(Team.firm_id == firm_id)
            
            # Order by distance and get the nearest
            query = query.order_by('distance_m').limit(1)
            
            result = await self.db.execute(query)
            row = result.first()
            
            if row:
                team, distance_m = row
                distance_km = distance_m / 1000.0  # Convert meters to kilometers
                logger.info(f"Found nearest team: {team.name} at {distance_km:.2f}km distance")
                return team, distance_km
            else:
                logger.warning(f"No teams found for location ({latitude}, {longitude})")
                return None, None
                
        except Exception as e:
            logger.error(f"Error finding nearest team: {e}")
            raise EmergencyRequestError(f"Failed to find nearest team: {str(e)}")
    
    async def assign_request_to_nearest_team(
        self,
        request_id: UUID,
        assigner_id: UUID,
        max_distance_km: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Assign a panic request to the nearest available team
        
        Args:
            request_id: Panic request ID
            assigner_id: ID of the user making the assignment
            max_distance_km: Maximum distance in km to consider teams (optional)
            
        Returns:
            Dict with assignment details including team info and distance
            
        Raises:
            EmergencyRequestError: If assignment fails
        """
        # Get the panic request
        panic_request = await self.get_request_by_id(request_id)
        if not panic_request:
            raise EmergencyRequestError("Panic request not found")
        
        # Check if already assigned
        if panic_request.assigned_team_id:
            # Get current team info for comparison
            current_team_result = await self.db.execute(
                select(Team).where(Team.id == panic_request.assigned_team_id)
            )
            current_team = current_team_result.scalar_one_or_none()
            raise EmergencyRequestError(
                f"Request is already assigned to team: {current_team.name if current_team else 'Unknown'}"
            )
        
        # Extract coordinates from the geometry
        from geoalchemy2.functions import ST_X, ST_Y
        location_result = await self.db.execute(
            select(ST_X(PanicRequest.location), ST_Y(PanicRequest.location))
            .where(PanicRequest.id == request_id)
        )
        coordinates = location_result.first()
        if not coordinates:
            raise EmergencyRequestError("Could not extract location coordinates from panic request")
        
        longitude, latitude = coordinates
        
        # Find the nearest team
        nearest_team, distance_km = await self.find_nearest_team(
            latitude=latitude,
            longitude=longitude,
            firm_id=None  # Search all firms for now, can be restricted later
        )
        
        if not nearest_team:
            raise EmergencyRequestError("No available teams found for this location")
        
        # Check distance limit if specified
        if max_distance_km and distance_km > max_distance_km:
            raise EmergencyRequestError(
                f"Nearest team is {distance_km:.2f}km away, which exceeds the maximum distance of {max_distance_km}km"
            )
        
        # Assign the request to the nearest team
        panic_request.assigned_team_id = nearest_team.id
        panic_request.status = "assigned"
        panic_request.updated_at = datetime.utcnow()
        
        # Create a status update record
        from app.models.emergency import RequestStatusUpdate
        status_update = RequestStatusUpdate(
            id=uuid4(),
            request_id=request_id,
            status="assigned",
            updated_by=assigner_id,
            message=f"Auto-assigned to nearest team: {nearest_team.name} ({distance_km:.2f}km away)",
            created_at=datetime.utcnow()
        )
        
        self.db.add(status_update)
        await self.db.commit()
        
        # Log the assignment
        logger.info(f"Assigned request {request_id} to team {nearest_team.name} at {distance_km:.2f}km distance")
        
        return {
            "request_id": str(request_id),
            "assigned_team": {
                "id": str(nearest_team.id),
                "name": nearest_team.name,
                "firm_id": str(nearest_team.firm_id)
            },
            "distance_km": round(distance_km, 2),
            "status": "assigned",
            "message": f"Request successfully assigned to {nearest_team.name}"
        }