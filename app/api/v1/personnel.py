"""
Personnel and team management API endpoints
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr, validator

from app.core.database import get_db
from app.core.auth import (
    get_current_user, 
    require_firm_admin, 
    require_admin_or_super_admin,
    can_view_all_personnel
)
from app.services.auth import UserContext
from app.services.personnel import PersonnelService
from app.models.security_firm import FirmPersonnel, Team

router = APIRouter()


class PersonnelEnrollmentRequest(BaseModel):
    """Personnel enrollment request model"""
    email: EmailStr
    phone: str
    first_name: str
    last_name: str
    user_type: str
    role: str
    # Password field removed - system will automatically generate secure passwords
    
    @validator('user_type')
    def validate_user_type(cls, v):
        valid_user_types = ['office_staff', 'field_staff']
        if v not in valid_user_types:
            raise ValueError(f'User type must be one of: {", ".join(valid_user_types)}')
        return v
    
    @validator('role')
    def validate_role(cls, v):
        valid_roles = [
            'firm_staff', 'firm_supervisor', 'firm_admin',  # Office personnel
            'firm_field_leader', 'firm_field_security',     # Field personnel
            'super_admin', 'admin'                           # System administrators
        ]
        if v not in valid_roles:
            raise ValueError(f'Role must be one of: {", ".join(valid_roles)}')
        return v
    
    @validator('role')
    def validate_user_type_role_combination(cls, v, values):
        user_type = values.get('user_type')
        if user_type == 'field_staff':
            if v not in ['firm_field_leader', 'firm_field_security']:
                raise ValueError('Field staff can only be assigned firm_field_leader or firm_field_security roles')
        elif user_type == 'office_staff':
            if v not in ['firm_staff', 'firm_supervisor', 'firm_admin', 'super_admin', 'admin']:
                raise ValueError('Office staff can only be assigned firm_staff, firm_supervisor, firm_admin, super_admin, or admin roles')
        return v
    
    @validator('phone')
    def validate_phone(cls, v):
        # Basic phone validation
        cleaned = ''.join(c for c in v if c.isdigit() or c in '+()-. ')
        digits_only = ''.join(c for c in cleaned if c.isdigit())
        if len(digits_only) < 10:
            raise ValueError('Phone number must be at least 10 digits')
        return cleaned


class PersonnelResponse(BaseModel):
    """Personnel response model"""
    id: str
    firm_id: str
    email: str
    phone: str
    first_name: str
    last_name: str
    role: str
    team_id: Optional[str]
    is_active: bool
    is_locked: bool
    created_at: str
    
    class Config:
        from_attributes = True


class PersonnelEnrollmentResponse(PersonnelResponse):
    """Personnel enrollment response model with generated password"""
    generated_password: str





class PersonnelUpdateRequest(BaseModel):
    """Personnel update request model"""
    phone: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    team_id: Optional[str] = None
    
    @validator('role')
    def validate_role(cls, v):
        if v is not None:
            valid_roles = [
                'firm_staff', 'firm_supervisor', 'firm_admin',  # Office personnel
                'firm_field_leader', 'firm_field_security'      # Field personnel
            ]
            if v not in valid_roles:
                raise ValueError(f'Role must be one of: {", ".join(valid_roles)}')
        return v


class TeamCreateRequest(BaseModel):
    """Team creation request model"""
    name: str
    team_leader_id: Optional[str] = None
    coverage_area_id: Optional[str] = None
    
    @validator('name')
    def validate_name(cls, v):
        if len(v.strip()) < 2:
            raise ValueError('Team name must be at least 2 characters long')
        return v.strip()


class TeamResponse(BaseModel):
    """Team response model"""
    id: str
    firm_id: str
    name: str
    team_leader_id: Optional[str]
    coverage_area_id: Optional[str]
    is_active: bool
    created_at: str
    
    class Config:
        from_attributes = True


class TeamUpdateRequest(BaseModel):
    """Team update request model"""
    name: Optional[str] = None
    team_leader_id: Optional[str] = None
    coverage_area_id: Optional[str] = None
    is_active: Optional[bool] = None


class TeamAssignmentRequest(BaseModel):
    """Team assignment request model"""
    personnel_id: str
    team_id: str


@router.post("/firms/{firm_id}/personnel", response_model=PersonnelEnrollmentResponse)
async def enroll_personnel(
    firm_id: str,
    request: PersonnelEnrollmentRequest,
    current_user: UserContext = Depends(require_firm_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Enroll new personnel for a security firm
    
    The system automatically generates a secure password for the new personnel.
    The generated password is returned in the response for the admin to share with the personnel.
    Personnel can change their password after first login.
    """
    service = PersonnelService(db)
    
    try:
        # Password is always None - system will generate automatically
        personnel, generated_password = await service.enroll_personnel(
            firm_id=UUID(firm_id),
            email=request.email,
            phone=request.phone,
            first_name=request.first_name,
            last_name=request.last_name,
            user_type=request.user_type,
            role=request.role,
            password=None,  # Always None - service will generate
            requesting_user=current_user
        )
        
        return PersonnelEnrollmentResponse(
            id=str(personnel.id),
            firm_id=str(personnel.firm_id),
            email=personnel.email,
            phone=personnel.phone,
            first_name=personnel.first_name,
            last_name=personnel.last_name,
            role=personnel.role,
            team_id=str(personnel.team_id) if personnel.team_id else None,
            is_active=personnel.is_active,
            is_locked=personnel.is_locked,
            created_at=personnel.created_at.isoformat(),
            generated_password=generated_password  # Always include generated password
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/firms/{firm_id}/personnel", response_model=List[PersonnelResponse])
async def get_firm_personnel(
    firm_id: str,
    role_filter: Optional[str] = None,
    include_inactive: bool = False,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all personnel for a security firm
    """
    service = PersonnelService(db)
    
    try:
        personnel_list = await service.get_firm_personnel(
            firm_id=UUID(firm_id),
            requesting_user=current_user,
            role_filter=role_filter,
            include_inactive=include_inactive
        )
        
        return [
            PersonnelResponse(
                id=str(p.id),
                firm_id=str(p.firm_id),
                email=p.email,
                phone=p.phone,
                first_name=p.first_name,
                last_name=p.last_name,
                role=p.role,
                team_id=str(p.team_id) if p.team_id else None,
                is_active=p.is_active,
                is_locked=p.is_locked,
                created_at=p.created_at.isoformat()
            )
            for p in personnel_list
        ]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/personnel/{personnel_id}", response_model=PersonnelResponse)
async def update_personnel(
    personnel_id: str,
    request: PersonnelUpdateRequest,
    current_user: UserContext = Depends(require_firm_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Update personnel information (firm_admin only)
    """
    service = PersonnelService(db)
    
    try:
        # Convert team_id to UUID if provided
        updates = request.dict(exclude_unset=True)
        if 'team_id' in updates and updates['team_id']:
            updates['team_id'] = UUID(updates['team_id'])
        
        personnel = await service.update_personnel(
            personnel_id=UUID(personnel_id),
            requesting_user=current_user,
            **updates
        )
        
        return PersonnelResponse(
            id=str(personnel.id),
            firm_id=str(personnel.firm_id),
            email=personnel.email,
            phone=personnel.phone,
            first_name=personnel.first_name,
            last_name=personnel.last_name,
            role=personnel.role,
            team_id=str(personnel.team_id) if personnel.team_id else None,
            is_active=personnel.is_active,
            is_locked=personnel.is_locked,
            created_at=personnel.created_at.isoformat()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/personnel/{personnel_id}", response_model=PersonnelResponse)
async def deactivate_personnel(
    personnel_id: str,
    current_user: UserContext = Depends(require_firm_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Deactivate personnel (firm_admin only)
    """
    service = PersonnelService(db)
    
    try:
        personnel = await service.deactivate_personnel(
            personnel_id=UUID(personnel_id),
            requesting_user=current_user
        )
        
        return PersonnelResponse(
            id=str(personnel.id),
            firm_id=str(personnel.firm_id),
            email=personnel.email,
            phone=personnel.phone,
            first_name=personnel.first_name,
            last_name=personnel.last_name,
            role=personnel.role,
            team_id=str(personnel.team_id) if personnel.team_id else None,
            is_active=personnel.is_active,
            is_locked=personnel.is_locked,
            created_at=personnel.created_at.isoformat()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/personnel/{personnel_id}/lock", response_model=PersonnelResponse)
async def lock_personnel(
    personnel_id: str,
    current_user: UserContext = Depends(require_admin_or_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Lock personnel account (admin/super_admin only)
    """
    service = PersonnelService(db)
    
    try:
        personnel = await service.lock_personnel(
            personnel_id=UUID(personnel_id),
            requesting_user=current_user
        )
        
        return PersonnelResponse(
            id=str(personnel.id),
            firm_id=str(personnel.firm_id),
            email=personnel.email,
            phone=personnel.phone,
            first_name=personnel.first_name,
            last_name=personnel.last_name,
            role=personnel.role,
            team_id=str(personnel.team_id) if personnel.team_id else None,
            is_active=personnel.is_active,
            is_locked=personnel.is_locked,
            created_at=personnel.created_at.isoformat()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/personnel/{personnel_id}/unlock", response_model=PersonnelResponse)
async def unlock_personnel(
    personnel_id: str,
    current_user: UserContext = Depends(require_admin_or_super_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Unlock personnel account (admin/super_admin only)
    """
    service = PersonnelService(db)
    
    try:
        personnel = await service.unlock_personnel(
            personnel_id=UUID(personnel_id),
            requesting_user=current_user
        )
        
        return PersonnelResponse(
            id=str(personnel.id),
            firm_id=str(personnel.firm_id),
            email=personnel.email,
            phone=personnel.phone,
            first_name=personnel.first_name,
            last_name=personnel.last_name,
            role=personnel.role,
            team_id=str(personnel.team_id) if personnel.team_id else None,
            is_active=personnel.is_active,
            is_locked=personnel.is_locked,
            created_at=personnel.created_at.isoformat()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/firms/{firm_id}/teams", response_model=TeamResponse)
async def create_team(
    firm_id: str,
    request: TeamCreateRequest,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new team for a security firm
    """
    service = PersonnelService(db)
    
    try:
        team = await service.create_team(
            firm_id=UUID(firm_id),
            name=request.name,
            team_leader_id=UUID(request.team_leader_id) if request.team_leader_id else None,
            coverage_area_id=UUID(request.coverage_area_id) if request.coverage_area_id else None,
            requesting_user_id=current_user.user_id
        )
        
        return TeamResponse(
            id=str(team.id),
            firm_id=str(team.firm_id),
            name=team.name,
            team_leader_id=str(team.team_leader_id) if team.team_leader_id else None,
            coverage_area_id=str(team.coverage_area_id) if team.coverage_area_id else None,
            is_active=team.is_active,
            created_at=team.created_at.isoformat()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/firms/{firm_id}/teams", response_model=List[TeamResponse])
async def get_firm_teams(
    firm_id: str,
    include_inactive: bool = False,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all teams for a security firm
    """
    service = PersonnelService(db)
    
    try:
        teams = await service.get_firm_teams(
            firm_id=UUID(firm_id),
            requesting_user_id=current_user.user_id,
            include_inactive=include_inactive
        )
        
        return [
            TeamResponse(
                id=str(t.id),
                firm_id=str(t.firm_id),
                name=t.name,
                team_leader_id=str(t.team_leader_id) if t.team_leader_id else None,
                coverage_area_id=str(t.coverage_area_id) if t.coverage_area_id else None,
                is_active=t.is_active,
                created_at=t.created_at.isoformat()
            )
            for t in teams
        ]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/teams/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: str,
    request: TeamUpdateRequest,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update team information
    """
    service = PersonnelService(db)
    
    try:
        # Convert UUIDs if provided
        updates = request.dict(exclude_unset=True)
        if 'team_leader_id' in updates and updates['team_leader_id']:
            updates['team_leader_id'] = UUID(updates['team_leader_id'])
        if 'coverage_area_id' in updates and updates['coverage_area_id']:
            updates['coverage_area_id'] = UUID(updates['coverage_area_id'])
        
        team = await service.update_team(
            team_id=UUID(team_id),
            requesting_user_id=current_user.user_id,
            **updates
        )
        
        return TeamResponse(
            id=str(team.id),
            firm_id=str(team.firm_id),
            name=team.name,
            team_leader_id=str(team.team_leader_id) if team.team_leader_id else None,
            coverage_area_id=str(team.coverage_area_id) if team.coverage_area_id else None,
            is_active=team.is_active,
            created_at=team.created_at.isoformat()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/teams/assign", response_model=PersonnelResponse)
async def assign_personnel_to_team(
    request: TeamAssignmentRequest,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Assign personnel to a team
    """
    service = PersonnelService(db)
    
    try:
        personnel = await service.assign_personnel_to_team(
            personnel_id=UUID(request.personnel_id),
            team_id=UUID(request.team_id),
            requesting_user_id=current_user.user_id
        )
        
        return PersonnelResponse(
            id=str(personnel.id),
            firm_id=str(personnel.firm_id),
            email=personnel.email,
            phone=personnel.phone,
            first_name=personnel.first_name,
            last_name=personnel.last_name,
            role=personnel.role,
            team_id=str(personnel.team_id) if personnel.team_id else None,
            is_active=personnel.is_active,
            is_locked=personnel.is_locked,
            created_at=personnel.created_at.isoformat()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/personnel/{personnel_id}/team", response_model=PersonnelResponse)
async def remove_personnel_from_team(
    personnel_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove personnel from their current team
    """
    service = PersonnelService(db)
    
    try:
        personnel = await service.remove_personnel_from_team(
            personnel_id=UUID(personnel_id),
            requesting_user_id=current_user.user_id
        )
        
        return PersonnelResponse(
            id=str(personnel.id),
            firm_id=str(personnel.firm_id),
            email=personnel.email,
            phone=personnel.phone,
            first_name=personnel.first_name,
            last_name=personnel.last_name,
            role=personnel.role,
            team_id=str(personnel.team_id) if personnel.team_id else None,
            is_active=personnel.is_active,
            is_locked=personnel.is_locked,
            created_at=personnel.created_at.isoformat()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/teams/{team_id}/members", response_model=List[PersonnelResponse])
async def get_team_members(
    team_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all members of a team
    """
    service = PersonnelService(db)
    
    try:
        members = await service.get_team_members(
            team_id=UUID(team_id),
            requesting_user_id=current_user.user_id
        )
        
        return [
            PersonnelResponse(
                id=str(m.id),
                firm_id=str(m.firm_id),
                email=m.email,
                phone=m.phone,
                first_name=m.first_name,
                last_name=m.last_name,
                role=m.role,
                team_id=str(m.team_id) if m.team_id else None,
                is_active=m.is_active,
                is_locked=m.is_locked,
                created_at=m.created_at.isoformat()
            )
            for m in members
        ]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/personnel/{personnel_id}", response_model=PersonnelResponse)
async def get_personnel_by_id(
    personnel_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get personnel by ID
    """
    service = PersonnelService(db)
    
    try:
        personnel = await service.get_personnel_by_id(
            personnel_id=UUID(personnel_id),
            requesting_user_id=current_user.user_id
        )
        
        if not personnel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Personnel not found"
            )
        
        return PersonnelResponse(
            id=str(personnel.id),
            firm_id=str(personnel.firm_id),
            email=personnel.email,
            phone=personnel.phone,
            first_name=personnel.first_name,
            last_name=personnel.last_name,
            role=personnel.role,
            team_id=str(personnel.team_id) if personnel.team_id else None,
            is_active=personnel.is_active,
            is_locked=personnel.is_locked,
            created_at=personnel.created_at.isoformat()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/teams/{team_id}", response_model=TeamResponse)
async def get_team_by_id(
    team_id: str,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get team by ID
    """
    service = PersonnelService(db)
    
    try:
        team = await service.get_team_by_id(
            team_id=UUID(team_id),
            requesting_user_id=current_user.user_id
        )
        
        if not team:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Team not found"
            )
        
        return TeamResponse(
            id=str(team.id),
            firm_id=str(team.firm_id),
            name=team.name,
            team_leader_id=str(team.team_leader_id) if team.team_leader_id else None,
            coverage_area_id=str(team.coverage_area_id) if team.coverage_area_id else None,
            is_active=team.is_active,
            created_at=team.created_at.isoformat()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


class PersonnelWithFirmResponse(BaseModel):
    """Security firm personnel response model with firm information for admin view"""
    id: str
    firm_id: str
    firm_name: str
    email: str
    phone: str
    first_name: str
    last_name: str
    role: str  # field_agent, team_leader, office_staff, admin
    team_id: Optional[str]
    team_name: Optional[str]
    is_active: bool
    is_locked: bool
    created_at: str
    
    class Config:
        from_attributes = True


@router.get("/personnel", response_model=List[PersonnelWithFirmResponse])
async def get_all_personnel(
    role_filter: Optional[str] = None,
    firm_id_filter: Optional[str] = None,
    include_inactive: bool = False,
    limit: int = 100,
    offset: int = 0,
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get personnel with proper authorization filtering
    
    - Regular firm personnel: Can only view personnel from their own firm
    - Admin/Super Admin: Can view all personnel across all firms with filtering
    
    Query Parameters:
    - role_filter: Filter by personnel role
    - firm_id_filter: Filter by specific firm ID (admin/super_admin only)
    - include_inactive: Include inactive personnel (default: false)
    - limit: Maximum number of results (default: 100, max: 1000)
    - offset: Number of results to skip for pagination (default: 0)
    """
    service = PersonnelService(db)
    
    # Validate limit
    if limit > 1000:
        limit = 1000
    
    try:
        # Convert firm_id_filter to UUID if provided
        firm_uuid_filter = UUID(firm_id_filter) if firm_id_filter else None
        
        # Use the new authorization-aware method
        personnel_list = await service.get_personnel_with_authorization(
            requesting_user=current_user,
            firm_id_filter=firm_uuid_filter,
            role_filter=role_filter,
            include_inactive=include_inactive,
            limit=limit,
            offset=offset
        )
        
        return [
            PersonnelWithFirmResponse(
                id=str(p.id),
                firm_id=str(p.firm_id),
                firm_name=p.firm.name if p.firm else "Unknown",
                email=p.email,
                phone=p.phone,
                first_name=p.first_name,
                last_name=p.last_name,
                role=p.role,
                team_id=str(p.team_id) if p.team_id else None,
                team_name=p.team.name if p.team else None,
                is_active=p.is_active,
                is_locked=p.is_locked,
                created_at=p.created_at.isoformat()
            )
            for p in personnel_list
        ]
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )