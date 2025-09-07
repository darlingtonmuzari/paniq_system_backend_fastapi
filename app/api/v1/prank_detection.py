"""
Prank detection and fining API endpoints
"""
from typing import List, Optional
from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user, require_role
from app.services.prank_detection import PrankDetectionService, PrankDetectionError
from app.models.user import RegisteredUser, UserFine
from app.models.security_firm import FirmPersonnel

router = APIRouter(prefix="/prank-detection", tags=["prank-detection"])


# Request/Response models
class FinePaymentRequest(BaseModel):
    """Fine payment request"""
    payment_method: str = Field(..., description="Payment method (card, bank_transfer)")
    payment_reference: str = Field(..., description="Payment reference/transaction ID")


class PrankTrackingResponse(BaseModel):
    """Prank tracking response"""
    user_id: str
    total_prank_flags: int
    recent_prank_flags: int
    total_fines: float
    is_suspended: bool
    calculated_fine_amount: Optional[float]
    should_suspend: bool
    should_ban: bool
    days_until_ban: int


class UserFineResponse(BaseModel):
    """User fine response"""
    id: str
    user_id: str
    amount: float
    reason: str
    is_paid: bool
    paid_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class FineStatisticsResponse(BaseModel):
    """Fine statistics response"""
    total_fines: int
    paid_fines: int
    unpaid_fines: int
    total_amount: float
    paid_amount: float
    unpaid_amount: float
    payment_rate_percentage: float
    date_range: dict


@router.get("/users/{user_id}/tracking", response_model=PrankTrackingResponse)
async def get_user_prank_tracking(
    user_id: UUID,
    current_user: RegisteredUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get prank tracking information for a user
    
    Only accessible by the user themselves or admin personnel
    """
    # Check if current user is accessing their own data or is admin
    if str(current_user.user_id) != str(user_id):
        # Check if current user is admin personnel
        if not hasattr(current_user, 'role') or current_user.role not in ['office_staff', 'admin']:
            raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        service = PrankDetectionService(db)
        tracking_info = await service.track_prank_accumulation(user_id)
        return PrankTrackingResponse(**tracking_info)
    except PrankDetectionError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.post("/users/{user_id}/calculate-fine", response_model=Optional[UserFineResponse])
async def calculate_automatic_fine(
    user_id: UUID,
    current_personnel: FirmPersonnel = Depends(require_role("office_staff")),
    db: AsyncSession = Depends(get_db)
):
    """
    Calculate and create automatic fine for a user
    
    Only accessible by office staff and admins
    """
    try:
        service = PrankDetectionService(db)
        fine = await service.calculate_automatic_fine(user_id)
        
        if fine:
            return UserFineResponse(
                id=str(fine.id),
                user_id=str(fine.user_id),
                amount=float(fine.amount),
                reason=fine.reason,
                is_paid=fine.is_paid,
                paid_at=fine.paid_at,
                created_at=fine.created_at,
                updated_at=fine.updated_at
            )
        return None
    except PrankDetectionError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.post("/fines/{fine_id}/pay", response_model=UserFineResponse)
async def pay_fine(
    fine_id: UUID,
    payment_request: FinePaymentRequest,
    current_user: RegisteredUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Process fine payment
    
    Users can only pay their own fines
    """
    try:
        service = PrankDetectionService(db)
        
        # Verify the fine belongs to the current user
        user_fines = await service.get_user_fines(current_user.user_id, include_paid=False)
        fine_ids = [str(f.id) for f in user_fines]
        
        if str(fine_id) not in fine_ids:
            raise HTTPException(status_code=403, detail="Access denied - fine does not belong to user")
        
        fine = await service.process_fine_payment(
            fine_id=fine_id,
            payment_method=payment_request.payment_method,
            payment_reference=payment_request.payment_reference
        )
        
        return UserFineResponse(
            id=str(fine.id),
            user_id=str(fine.user_id),
            amount=float(fine.amount),
            reason=fine.reason,
            is_paid=fine.is_paid,
            paid_at=fine.paid_at,
            created_at=fine.created_at,
            updated_at=fine.updated_at
        )
    except PrankDetectionError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.post("/users/{user_id}/suspend")
async def suspend_user_account(
    user_id: UUID,
    current_personnel: FirmPersonnel = Depends(require_role("office_staff")),
    db: AsyncSession = Depends(get_db)
):
    """
    Suspend user account for unpaid fines
    
    Only accessible by office staff and admins
    """
    try:
        service = PrankDetectionService(db)
        suspended = await service.suspend_account_for_unpaid_fines(user_id)
        
        return {
            "user_id": str(user_id),
            "suspended": suspended,
            "message": "Account suspended for unpaid fines" if suspended else "Account was already suspended"
        }
    except PrankDetectionError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.post("/users/{user_id}/ban")
async def ban_user_permanently(
    user_id: UUID,
    reason: Optional[str] = None,
    current_personnel: FirmPersonnel = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db)
):
    """
    Create permanent ban for repeat offenders
    
    Only accessible by admins
    """
    try:
        service = PrankDetectionService(db)
        banned = await service.create_permanent_ban(user_id, reason)
        
        return {
            "user_id": str(user_id),
            "banned": banned,
            "reason": reason,
            "message": "User permanently banned" if banned else "User does not meet ban criteria"
        }
    except PrankDetectionError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.get("/users/{user_id}/fines", response_model=List[UserFineResponse])
async def get_user_fines(
    user_id: UUID,
    include_paid: bool = Query(True, description="Include paid fines"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: RegisteredUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's fines
    
    Users can only access their own fines, personnel can access any user's fines
    """
    # Check access permissions
    if str(current_user.user_id) != str(user_id):
        if not hasattr(current_user, 'role') or current_user.role not in ['office_staff', 'admin']:
            raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        service = PrankDetectionService(db)
        fines = await service.get_user_fines(user_id, include_paid, limit, offset)
        
        return [
            UserFineResponse(
                id=str(fine.id),
                user_id=str(fine.user_id),
                amount=float(fine.amount),
                reason=fine.reason,
                is_paid=fine.is_paid,
                paid_at=fine.paid_at,
                created_at=fine.created_at,
                updated_at=fine.updated_at
            )
            for fine in fines
        ]
    except PrankDetectionError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.get("/statistics", response_model=FineStatisticsResponse)
async def get_fine_statistics(
    date_from: Optional[datetime] = Query(None, description="Start date filter"),
    date_to: Optional[datetime] = Query(None, description="End date filter"),
    current_personnel: FirmPersonnel = Depends(require_role("office_staff")),
    db: AsyncSession = Depends(get_db)
):
    """
    Get fine statistics
    
    Only accessible by office staff and admins
    """
    try:
        service = PrankDetectionService(db)
        stats = await service.get_fine_statistics(date_from, date_to)
        return FineStatisticsResponse(**stats)
    except PrankDetectionError as e:
        raise HTTPException(status_code=400, detail=e.message)