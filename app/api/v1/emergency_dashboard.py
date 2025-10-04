"""
Emergency Dashboard API endpoints for supervisors and office staff
No mobile attestation required - designed for web dashboard access
"""
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc

from app.core.database import get_db
from app.core.auth import get_current_user, UserContext
from app.services.emergency import EmergencyService, EmergencyRequestError
from app.models.emergency import PanicRequest
from app.api.v1.emergency import (
    PanicRequestResponse,
    RequestListResponse,
    RequestStatusUpdate,
    RequestAllocation,
    CallServiceHandling,
    RequestReassignment
)
import structlog

logger = structlog.get_logger()

router = APIRouter()


class EmergencyDashboardSummary(BaseModel):
    """Dashboard summary model"""
    total_requests: int
    pending_requests: int
    active_requests: int
    completed_requests: int
    urgent_requests: int
    recent_requests: List[PanicRequestResponse]


class ResponseAction(BaseModel):
    """Response action model for dashboard"""
    action: str = Field(..., description="Action type: acknowledge, assign, escalate, complete")
    message: Optional[str] = Field(None, description="Response message")
    team_id: Optional[UUID] = Field(None, description="Team ID for assignment")
    service_provider_id: Optional[UUID] = Field(None, description="Service provider ID for assignment")
    priority: Optional[str] = Field(None, description="Priority level: low, medium, high, urgent")
    notes: Optional[str] = Field(None, description="Additional notes")


class BulkAction(BaseModel):
    """Bulk action model"""
    request_ids: List[UUID] = Field(..., description="List of request IDs")
    action: str = Field(..., description="Action to perform")
    team_id: Optional[UUID] = Field(None, description="Team ID for bulk assignment")
    message: Optional[str] = Field(None, description="Bulk action message")


@router.get("/summary", response_model=EmergencyDashboardSummary)
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_db),
    current_user: UserContext = Depends(get_current_user)
):
    """
    Get emergency dashboard summary for supervisors and office staff
    
    Returns overview statistics and recent requests without requiring mobile attestation.
    **Roles allowed:** firm_admin, firm_supervisor, firm_staff, firm_user, team_leader, admin
    """
    try:
        # Authorization check
        if not current_user.is_firm_personnel() and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "ACCESS_DENIED",
                    "message": "Only firm personnel and administrators can access dashboard summary",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        allowed_roles = ["firm_admin", "firm_supervisor", "firm_staff", "firm_user", "team_leader", "admin"]
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "INSUFFICIENT_PERMISSIONS",
                    "message": f"Role '{current_user.role}' not authorized for dashboard access",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        emergency_service = EmergencyService(db)
        
        # Get summary statistics using existing methods
        if current_user.role == "admin":
            # Admin - simplified for now
            total_requests = 0
            pending_requests = 0
            active_requests = 0
            completed_requests = 0
            urgent_requests = 0
            recent_requests_data = []
        else:
            # Firm personnel see only their firm's requests
            firm_id = current_user.firm_id
            
            # Get pending requests for the firm using existing method
            pending_requests_data = await emergency_service.get_pending_requests_for_firm(
                firm_id=firm_id, 
                limit=100, 
                offset=0
            )
            pending_requests = len(pending_requests_data)
            
            # For now, set basic counts (can be enhanced later)
            total_requests = pending_requests  # Simplified
            active_requests = 0  # Would need additional implementation
            completed_requests = 0  # Would need additional implementation
            urgent_requests = 0  # Would need additional implementation
            
            # Use first 10 pending requests as recent requests
            recent_requests_data = pending_requests_data[:10]
        
        # Convert to response models
        recent_requests = [
            PanicRequestResponse.from_panic_request(req) for req in recent_requests_data
        ]
        
        return EmergencyDashboardSummary(
            total_requests=total_requests,
            pending_requests=pending_requests,
            active_requests=active_requests,
            completed_requests=completed_requests,
            urgent_requests=urgent_requests,
            recent_requests=recent_requests
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in get_dashboard_summary", error=str(e), exception_type=type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "Failed to retrieve dashboard summary",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/requests", response_model=RequestListResponse)
async def get_emergency_requests(
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    service_type_filter: Optional[str] = Query(None, description="Filter by service type"),
    priority_filter: Optional[str] = Query(None, description="Filter by priority"),
    date_from: Optional[datetime] = Query(None, description="Filter from date"),
    date_to: Optional[datetime] = Query(None, description="Filter to date"),
    search: Optional[str] = Query(None, description="Search in requester info"),
    limit: int = Query(50, description="Number of requests to return", le=100),
    offset: int = Query(0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db),
    current_user: UserContext = Depends(get_current_user)
):
    """
    Get emergency requests for dashboard with advanced filtering
    
    **Roles allowed:** firm_admin, firm_supervisor, firm_staff, firm_user, team_leader, admin
    """
    try:
        # Authorization check
        if not current_user.is_firm_personnel() and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "ACCESS_DENIED",
                    "message": "Only firm personnel and administrators can access emergency requests",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        allowed_roles = ["firm_admin", "firm_supervisor", "firm_staff", "firm_user", "team_leader", "admin"]
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "INSUFFICIENT_PERMISSIONS",
                    "message": f"Role '{current_user.role}' not authorized for dashboard access",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        emergency_service = EmergencyService(db)
        
        # Get requests based on user role using existing methods
        if current_user.role == "admin":
            # Admin - simplified for now, return empty list
            requests = []
        else:
            # Get pending requests for the firm using existing method
            # Note: This is simplified and doesn't implement all filters yet
            requests = await emergency_service.get_pending_requests_for_firm(
                firm_id=current_user.firm_id,
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
        logger.error("Error in get_emergency_requests", error=str(e), exception_type=type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "Failed to retrieve emergency requests",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/requests/{request_id}", response_model=PanicRequestResponse)
async def get_request_details(
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: UserContext = Depends(get_current_user)
):
    """
    Get detailed emergency request information
    
    **Roles allowed:** firm_admin, firm_supervisor, firm_staff, firm_user, team_leader, admin
    """
    try:
        # Authorization check
        if not current_user.is_firm_personnel() and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "ACCESS_DENIED",
                    "message": "Only firm personnel and administrators can access request details",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        allowed_roles = ["firm_admin", "firm_supervisor", "firm_staff", "firm_user", "team_leader", "admin"]
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "INSUFFICIENT_PERMISSIONS",
                    "message": f"Role '{current_user.role}' not authorized for dashboard access",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        emergency_service = EmergencyService(db)
        
        panic_request = await emergency_service.get_request_by_id(request_id)
        
        if not panic_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "REQUEST_NOT_FOUND",
                    "message": "Emergency request not found",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        # Additional authorization: firm personnel can only see their firm's requests
        if current_user.role != "admin" and current_user.is_firm_personnel():
            # Verify request belongs to user's firm (implementation depends on your data model)
            # This is a placeholder - implement based on your request-firm relationship
            pass
        
        return PanicRequestResponse.from_panic_request(panic_request)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in get_request_details", error=str(e), exception_type=type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "Failed to retrieve request details",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.post("/requests/{request_id}/respond", response_model=dict)
async def respond_to_emergency_request(
    request_id: UUID,
    response: ResponseAction,
    db: AsyncSession = Depends(get_db),
    current_user: UserContext = Depends(get_current_user)
):
    """
    Respond to an emergency request with various actions
    
    Available actions:
    - acknowledge: Acknowledge receipt of the request
    - assign: Assign to a team or service provider
    - escalate: Escalate priority level
    - complete: Mark as completed (for office staff handling call services)
    
    **Roles allowed:** firm_admin, firm_supervisor, firm_staff, firm_user, team_leader
    """
    try:
        # Authorization check
        if not current_user.is_firm_personnel():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "ACCESS_DENIED",
                    "message": "Only firm personnel can respond to emergency requests",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        allowed_roles = ["firm_admin", "firm_supervisor", "firm_staff", "firm_user", "team_leader"]
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "INSUFFICIENT_PERMISSIONS",
                    "message": f"Role '{current_user.role}' cannot respond to emergency requests",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        emergency_service = EmergencyService(db)
        
        # Get the request first to verify it exists
        panic_request = await emergency_service.get_request_by_id(request_id)
        if not panic_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": "REQUEST_NOT_FOUND",
                    "message": "Emergency request not found",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        success = False
        action_message = ""
        
        if response.action == "acknowledge":
            success = await emergency_service.update_request_status(
                request_id=request_id,
                new_status="acknowledged",
                message=response.message or "Request acknowledged by office staff",
                updated_by_id=current_user.user_id
            )
            action_message = "Request acknowledged successfully"
            
        elif response.action == "assign":
            if response.team_id:
                success = await emergency_service.allocate_request_to_team(
                    request_id=request_id,
                    team_id=response.team_id,
                    allocated_by_id=current_user.user_id
                )
                action_message = "Request assigned to team successfully"
            elif response.service_provider_id:
                success = await emergency_service.allocate_request_to_service_provider(
                    request_id=request_id,
                    service_provider_id=response.service_provider_id,
                    allocated_by_id=current_user.user_id
                )
                action_message = "Request assigned to service provider successfully"
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error_code": "INVALID_ASSIGNMENT",
                        "message": "Must specify team_id or service_provider_id for assignment",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
                
        elif response.action == "escalate":
            # Update priority and status
            success = await emergency_service.update_request_status(
                request_id=request_id,
                new_status="escalated",
                message=f"Request escalated to {response.priority or 'high'} priority",
                updated_by_id=current_user.user_id
            )
            action_message = "Request escalated successfully"
            
        elif response.action == "complete":
            # For call services that can be completed by office staff
            success = await emergency_service.handle_call_service_request(
                request_id=request_id,
                handled_by_id=current_user.user_id,
                notes=response.notes
            )
            action_message = "Request completed successfully"
            
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "INVALID_ACTION",
                    "message": f"Unknown action: {response.action}",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        if success:
            return {
                "success": True,
                "message": action_message,
                "action": response.action,
                "request_id": str(request_id),
                "handled_by": {
                    "user_id": str(current_user.user_id),
                    "role": current_user.role
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "ACTION_FAILED",
                    "message": f"Failed to {response.action} request",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in respond_to_emergency_request", error=str(e), exception_type=type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "Failed to respond to emergency request",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.put("/requests/{request_id}/status", response_model=dict)
async def update_emergency_request_status(
    request_id: UUID,
    status_update: RequestStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserContext = Depends(get_current_user)
):
    """
    Update emergency request status
    
    **Roles allowed:** firm_admin, firm_supervisor, firm_staff, firm_user, team_leader
    """
    try:
        # Authorization check
        if not current_user.is_firm_personnel():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "ACCESS_DENIED",
                    "message": "Only firm personnel can update request status",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        allowed_roles = ["firm_admin", "firm_supervisor", "firm_staff", "firm_user", "team_leader"]
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "INSUFFICIENT_PERMISSIONS",
                    "message": f"Role '{current_user.role}' cannot update request status",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
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
                "updated_by": {
                    "user_id": str(current_user.user_id),
                    "role": current_user.role
                },
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in update_emergency_request_status", error=str(e), exception_type=type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "Failed to update request status",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.post("/requests/bulk-action", response_model=dict)
async def perform_bulk_action(
    bulk_action: BulkAction,
    db: AsyncSession = Depends(get_db),
    current_user: UserContext = Depends(get_current_user)
):
    """
    Perform bulk actions on multiple emergency requests
    
    Available actions:
    - acknowledge: Acknowledge multiple requests
    - assign: Assign multiple requests to the same team
    - escalate: Escalate multiple requests
    
    **Roles allowed:** firm_admin, firm_supervisor, firm_user, team_leader
    """
    try:
        # Authorization check
        if not current_user.is_firm_personnel():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "ACCESS_DENIED",
                    "message": "Only firm personnel can perform bulk actions",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        allowed_roles = ["firm_admin", "firm_supervisor", "firm_user", "team_leader"]
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "INSUFFICIENT_PERMISSIONS",
                    "message": f"Role '{current_user.role}' cannot perform bulk actions",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        emergency_service = EmergencyService(db)
        
        successful_count = 0
        failed_count = 0
        errors = []
        
        for request_id in bulk_action.request_ids:
            try:
                if bulk_action.action == "acknowledge":
                    success = await emergency_service.update_request_status(
                        request_id=request_id,
                        new_status="acknowledged",
                        message=bulk_action.message or "Bulk acknowledgment by office staff",
                        updated_by_id=current_user.user_id
                    )
                elif bulk_action.action == "assign" and bulk_action.team_id:
                    success = await emergency_service.allocate_request_to_team(
                        request_id=request_id,
                        team_id=bulk_action.team_id,
                        allocated_by_id=current_user.user_id
                    )
                elif bulk_action.action == "escalate":
                    success = await emergency_service.update_request_status(
                        request_id=request_id,
                        new_status="escalated",
                        message="Bulk escalation",
                        updated_by_id=current_user.user_id
                    )
                else:
                    success = False
                
                if success:
                    successful_count += 1
                else:
                    failed_count += 1
                    errors.append(f"Request {request_id}: Action failed")
                    
            except Exception as e:
                failed_count += 1
                errors.append(f"Request {request_id}: {str(e)}")
        
        return {
            "success": True,
            "message": f"Bulk action completed: {successful_count} successful, {failed_count} failed",
            "action": bulk_action.action,
            "successful_count": successful_count,
            "failed_count": failed_count,
            "errors": errors if errors else None,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in perform_bulk_action", error=str(e), exception_type=type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "Failed to perform bulk action",
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/pending", response_model=RequestListResponse)
async def get_pending_requests(
    limit: int = Query(50, description="Number of requests to return", le=100),
    offset: int = Query(0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db),
    current_user: UserContext = Depends(get_current_user)
):
    """
    Get all pending emergency requests that need immediate attention
    
    **Roles allowed:** firm_admin, firm_supervisor, firm_staff, firm_user, team_leader, admin
    """
    try:
        # Authorization check
        if not current_user.is_firm_personnel() and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "ACCESS_DENIED",
                    "message": "Only firm personnel and administrators can access pending requests",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        allowed_roles = ["firm_admin", "firm_supervisor", "firm_staff", "firm_user", "team_leader", "admin"]
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "INSUFFICIENT_PERMISSIONS",
                    "message": f"Role '{current_user.role}' not authorized for pending requests access",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        emergency_service = EmergencyService(db)
        
        # Get pending requests based on user role
        if current_user.role == "admin":
            # Admin - simplified for now, return empty list
            requests = []
        else:
            requests = await emergency_service.get_pending_requests_for_firm(
                firm_id=current_user.firm_id,
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
        logger.error("Error in get_pending_requests", error=str(e), exception_type=type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "Failed to retrieve pending requests",
                "timestamp": datetime.utcnow().isoformat()
            }
        )