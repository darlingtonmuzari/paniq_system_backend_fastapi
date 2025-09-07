"""
Personnel and team management service for security firms
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
import structlog

from app.models.security_firm import SecurityFirm, FirmPersonnel, Team, CoverageArea
from app.services.auth import pwd_context, UserContext
from app.services.otp_delivery import OTPDeliveryService
from app.core.exceptions import APIError, ErrorCodes
from app.core.auth import (
    generate_secure_password, 
    can_manage_personnel, 
    can_view_all_personnel,
    can_lock_unlock_personnel,
    get_personnel_filter_for_user
)

logger = structlog.get_logger()


class PersonnelService:
    """Service for managing security firm personnel and teams"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.email_service = OTPDeliveryService()
    
    async def enroll_personnel(
        self,
        firm_id: UUID,
        email: str,
        phone: str,
        first_name: str,
        last_name: str,
        user_type: str,
        role: str,
        password: Optional[str],
        requesting_user: UserContext
    ) -> tuple[FirmPersonnel, Optional[str]]:
        """
        Enroll new personnel for a security firm
        
        Args:
            firm_id: Security firm ID
            email: Personnel email
            phone: Personnel phone number
            first_name: Personnel first name
            last_name: Personnel last name
            user_type: Personnel user type (office_staff, field_staff)
            role: Personnel role (firm_staff, firm_supervisor, firm_admin, firm_field_leader, firm_field_security)
            password: Personnel password
            requesting_user_id: ID of user making the request
            
        Returns:
            Created FirmPersonnel object and generated password (if any)
            
        Raises:
            ValueError: If validation fails
        """
        # Validate user_type
        valid_user_types = ['office_staff', 'field_staff']
        if user_type not in valid_user_types:
            raise ValueError(f"Invalid user type. Must be one of: {', '.join(valid_user_types)}")
        
        # Validate role
        valid_roles = [
            'firm_staff', 'firm_supervisor', 'firm_admin',  # Office personnel
            'firm_field_leader', 'firm_field_security'      # Field personnel
        ]
        if role not in valid_roles:
            raise ValueError(f"Invalid role. Must be one of: {', '.join(valid_roles)}")
        
        # Validate user_type and role combination
        if user_type == 'field_staff':
            if role not in ['firm_field_leader', 'firm_field_security']:
                raise ValueError('Field staff can only be assigned firm_field_leader or firm_field_security roles')
        elif user_type == 'office_staff':
            if role not in ['firm_staff', 'firm_supervisor', 'firm_admin']:
                raise ValueError('Office staff can only be assigned firm_staff, firm_supervisor, or firm_admin roles')
        
        # Verify firm exists and is approved
        firm = await self.db.get(SecurityFirm, firm_id)
        if not firm:
            raise ValueError("Security firm not found")
        
        if firm.verification_status != "approved":
            raise ValueError("Security firm must be approved to enroll personnel")
        
        # Authorization check - only firm_admin can enroll personnel
        if not can_manage_personnel(requesting_user, firm_id):
            raise ValueError("Only firm administrators can enroll personnel")
        
        # Check if email already exists
        existing_personnel = await self.db.execute(
            select(FirmPersonnel).where(FirmPersonnel.email == email)
        )
        if existing_personnel.scalar_one_or_none():
            raise ValueError("Personnel with this email already exists")
        
        # Generate password if not provided
        generated_password = None
        if password is None:
            password = generate_secure_password()
            generated_password = password  # Store for return
            logger.info(
                "password_generated_for_personnel",
                email=email,
                firm_id=str(firm_id)
            )
        
        # Hash password
        hashed_password = pwd_context.hash(password)
        
        # Create personnel record
        personnel = FirmPersonnel(
            firm_id=firm_id,
            email=email,
            phone=phone,
            first_name=first_name,
            last_name=last_name,
            role=role,
            password_hash=hashed_password,
            is_active=True
        )
        
        self.db.add(personnel)
        await self.db.commit()
        await self.db.refresh(personnel)
        
        # Send credentials email if password was generated
        if generated_password:
            try:
                email_sent = await self.email_service.send_personnel_credentials_email(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    password=generated_password,
                    firm_name=firm.name,
                    role=role
                )
                
                if email_sent:
                    logger.info(
                        "personnel_credentials_email_sent",
                        personnel_id=str(personnel.id),
                        email=email,
                        firm_id=str(firm_id)
                    )
                else:
                    logger.warning(
                        "personnel_credentials_email_failed",
                        personnel_id=str(personnel.id),
                        email=email,
                        firm_id=str(firm_id)
                    )
            except Exception as e:
                logger.error(
                    "personnel_credentials_email_error",
                    personnel_id=str(personnel.id),
                    email=email,
                    firm_id=str(firm_id),
                    error=str(e)
                )
        
        logger.info(
            "personnel_enrolled",
            personnel_id=str(personnel.id),
            firm_id=str(firm_id),
            role=role,
            enrolled_by=str(requesting_user.user_id),
            password_generated=generated_password is not None
        )
        
        return personnel, generated_password
    
    async def get_firm_personnel(
        self,
        firm_id: UUID,
        requesting_user: UserContext,
        role_filter: Optional[str] = None,
        include_inactive: bool = False
    ) -> List[FirmPersonnel]:
        """
        Get all personnel for a security firm
        
        Args:
            firm_id: Security firm ID
            requesting_user: User making the request
            role_filter: Optional role filter
            include_inactive: Whether to include inactive personnel
            
        Returns:
            List of FirmPersonnel objects
        """
        # Authorization check
        if not can_view_all_personnel(requesting_user):
            # Regular users can only view their own firm's personnel
            if not requesting_user.firm_id or requesting_user.firm_id != firm_id:
                raise ValueError("Access denied: You can only view personnel from your own firm")
        
        query = select(FirmPersonnel).where(FirmPersonnel.firm_id == firm_id)
        
        if role_filter:
            query = query.where(FirmPersonnel.role == role_filter)
        
        if not include_inactive:
            query = query.where(FirmPersonnel.is_active == True)
        
        # Load team relationships
        query = query.options(selectinload(FirmPersonnel.team))
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def update_personnel(
        self,
        personnel_id: UUID,
        requesting_user: UserContext,
        **updates
    ) -> FirmPersonnel:
        """
        Update personnel information (firm_admin only)
        
        Args:
            personnel_id: Personnel ID to update
            requesting_user: User making the request
            **updates: Fields to update
            
        Returns:
            Updated FirmPersonnel object
        """
        personnel = await self.db.get(FirmPersonnel, personnel_id)
        if not personnel:
            raise ValueError("Personnel not found")
        
        # Authorization check - only firm_admin can update personnel
        if not can_manage_personnel(requesting_user, personnel.firm_id):
            raise ValueError("Only firm administrators can update personnel")
        
        # Update allowed fields
        allowed_fields = ['phone', 'first_name', 'last_name', 'role', 'is_active', 'team_id']
        for field, value in updates.items():
            if field in allowed_fields and hasattr(personnel, field):
                setattr(personnel, field, value)
        
        await self.db.commit()
        await self.db.refresh(personnel)
        
        logger.info(
            "personnel_updated",
            personnel_id=str(personnel_id),
            updated_by=str(requesting_user.user_id),
            updates=updates
        )
        
        return personnel
    
    async def deactivate_personnel(
        self,
        personnel_id: UUID,
        requesting_user: UserContext
    ) -> FirmPersonnel:
        """
        Deactivate personnel (firm_admin only)
        
        Args:
            personnel_id: Personnel ID to deactivate
            requesting_user: User making the request
            
        Returns:
            Deactivated FirmPersonnel object
        """
        personnel = await self.db.get(FirmPersonnel, personnel_id)
        if not personnel:
            raise ValueError("Personnel not found")
        
        # Authorization check - only firm_admin can deactivate personnel
        if not can_manage_personnel(requesting_user, personnel.firm_id):
            raise ValueError("Only firm administrators can deactivate personnel")
        
        personnel.is_active = False
        await self.db.commit()
        await self.db.refresh(personnel)
        
        logger.info(
            "personnel_deactivated",
            personnel_id=str(personnel_id),
            deactivated_by=str(requesting_user.user_id)
        )
        
        return personnel
    
    async def create_team(
        self,
        firm_id: UUID,
        name: str,
        team_leader_id: Optional[UUID],
        coverage_area_id: Optional[UUID],
        requesting_user_id: UUID
    ) -> Team:
        """
        Create a new team for a security firm
        
        Args:
            firm_id: Security firm ID
            name: Team name
            team_leader_id: Optional team leader personnel ID
            coverage_area_id: Optional coverage area ID
            requesting_user_id: ID of user making the request
            
        Returns:
            Created Team object
        """
        # Verify firm exists
        firm = await self.db.get(SecurityFirm, firm_id)
        if not firm:
            raise ValueError("Security firm not found")
        
        # TODO: Add authorization check
        
        # Validate team leader if provided
        if team_leader_id:
            team_leader = await self.db.get(FirmPersonnel, team_leader_id)
            if not team_leader or team_leader.firm_id != firm_id:
                raise ValueError("Invalid team leader")
            
            if team_leader.role not in ['team_leader', 'office_staff']:
                raise ValueError("Team leader must have team_leader or office_staff role")
        
        # Validate coverage area if provided
        if coverage_area_id:
            coverage_area = await self.db.get(CoverageArea, coverage_area_id)
            if not coverage_area or coverage_area.firm_id != firm_id:
                raise ValueError("Invalid coverage area")
        
        # Create team
        team = Team(
            firm_id=firm_id,
            name=name,
            team_leader_id=team_leader_id,
            coverage_area_id=coverage_area_id,
            is_active=True
        )
        
        self.db.add(team)
        await self.db.commit()
        await self.db.refresh(team)
        
        logger.info(
            "team_created",
            team_id=str(team.id),
            firm_id=str(firm_id),
            team_leader_id=str(team_leader_id) if team_leader_id else None,
            created_by=str(requesting_user_id)
        )
        
        return team
    
    async def get_firm_teams(
        self,
        firm_id: UUID,
        requesting_user_id: UUID,
        include_inactive: bool = False
    ) -> List[Team]:
        """
        Get all teams for a security firm
        
        Args:
            firm_id: Security firm ID
            requesting_user_id: ID of user making the request
            include_inactive: Whether to include inactive teams
            
        Returns:
            List of Team objects
        """
        # TODO: Add authorization check
        
        query = select(Team).where(Team.firm_id == firm_id)
        
        if not include_inactive:
            query = query.where(Team.is_active == True)
        
        # Load relationships
        query = query.options(
            selectinload(Team.team_leader),
            selectinload(Team.coverage_area),
            selectinload(Team.members)
        )
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def update_team(
        self,
        team_id: UUID,
        requesting_user_id: UUID,
        **updates
    ) -> Team:
        """
        Update team information
        
        Args:
            team_id: Team ID to update
            requesting_user_id: ID of user making the request
            **updates: Fields to update
            
        Returns:
            Updated Team object
        """
        team = await self.db.get(Team, team_id)
        if not team:
            raise ValueError("Team not found")
        
        # TODO: Add authorization check
        
        # Validate team leader if being updated
        if 'team_leader_id' in updates and updates['team_leader_id']:
            team_leader = await self.db.get(FirmPersonnel, updates['team_leader_id'])
            if not team_leader or team_leader.firm_id != team.firm_id:
                raise ValueError("Invalid team leader")
            
            if team_leader.role not in ['team_leader', 'office_staff']:
                raise ValueError("Team leader must have team_leader or office_staff role")
        
        # Validate coverage area if being updated
        if 'coverage_area_id' in updates and updates['coverage_area_id']:
            coverage_area = await self.db.get(CoverageArea, updates['coverage_area_id'])
            if not coverage_area or coverage_area.firm_id != team.firm_id:
                raise ValueError("Invalid coverage area")
        
        # Update allowed fields
        allowed_fields = ['name', 'team_leader_id', 'coverage_area_id', 'is_active']
        for field, value in updates.items():
            if field in allowed_fields and hasattr(team, field):
                setattr(team, field, value)
        
        await self.db.commit()
        await self.db.refresh(team)
        
        logger.info(
            "team_updated",
            team_id=str(team_id),
            updated_by=str(requesting_user_id),
            updates=updates
        )
        
        return team
    
    async def assign_personnel_to_team(
        self,
        personnel_id: UUID,
        team_id: UUID,
        requesting_user_id: UUID
    ) -> FirmPersonnel:
        """
        Assign personnel to a team
        
        Args:
            personnel_id: Personnel ID to assign
            team_id: Team ID to assign to
            requesting_user_id: ID of user making the request
            
        Returns:
            Updated FirmPersonnel object
        """
        personnel = await self.db.get(FirmPersonnel, personnel_id)
        if not personnel:
            raise ValueError("Personnel not found")
        
        team = await self.db.get(Team, team_id)
        if not team:
            raise ValueError("Team not found")
        
        # Verify personnel and team belong to same firm
        if personnel.firm_id != team.firm_id:
            raise ValueError("Personnel and team must belong to the same firm")
        
        # TODO: Add authorization check
        
        personnel.team_id = team_id
        await self.db.commit()
        await self.db.refresh(personnel)
        
        logger.info(
            "personnel_assigned_to_team",
            personnel_id=str(personnel_id),
            team_id=str(team_id),
            assigned_by=str(requesting_user_id)
        )
        
        return personnel
    
    async def remove_personnel_from_team(
        self,
        personnel_id: UUID,
        requesting_user_id: UUID
    ) -> FirmPersonnel:
        """
        Remove personnel from their current team
        
        Args:
            personnel_id: Personnel ID to remove from team
            requesting_user_id: ID of user making the request
            
        Returns:
            Updated FirmPersonnel object
        """
        personnel = await self.db.get(FirmPersonnel, personnel_id)
        if not personnel:
            raise ValueError("Personnel not found")
        
        # TODO: Add authorization check
        
        old_team_id = personnel.team_id
        personnel.team_id = None
        await self.db.commit()
        await self.db.refresh(personnel)
        
        logger.info(
            "personnel_removed_from_team",
            personnel_id=str(personnel_id),
            old_team_id=str(old_team_id) if old_team_id else None,
            removed_by=str(requesting_user_id)
        )
        
        return personnel
    
    async def get_team_members(
        self,
        team_id: UUID,
        requesting_user_id: UUID
    ) -> List[FirmPersonnel]:
        """
        Get all members of a team
        
        Args:
            team_id: Team ID
            requesting_user_id: ID of user making the request
            
        Returns:
            List of FirmPersonnel objects
        """
        team = await self.db.get(Team, team_id)
        if not team:
            raise ValueError("Team not found")
        
        # TODO: Add authorization check
        
        result = await self.db.execute(
            select(FirmPersonnel).where(
                and_(
                    FirmPersonnel.team_id == team_id,
                    FirmPersonnel.is_active == True
                )
            )
        )
        return result.scalars().all()
    
    async def get_personnel_by_id(
        self,
        personnel_id: UUID,
        requesting_user_id: UUID
    ) -> Optional[FirmPersonnel]:
        """
        Get personnel by ID with authorization check
        
        Args:
            personnel_id: Personnel ID
            requesting_user_id: ID of user making the request
            
        Returns:
            FirmPersonnel object or None
        """
        personnel = await self.db.get(FirmPersonnel, personnel_id)
        if not personnel:
            return None
        
        # TODO: Add authorization check
        
        return personnel
    
    async def get_team_by_id(
        self,
        team_id: UUID,
        requesting_user_id: UUID
    ) -> Optional[Team]:
        """
        Get team by ID with authorization check
        
        Args:
            team_id: Team ID
            requesting_user_id: ID of user making the request
            
        Returns:
            Team object or None
        """
        team = await self.db.get(Team, team_id)
        if not team:
            return None
        
        # TODO: Add authorization check
        
        # Load relationships
        await self.db.refresh(team, ['team_leader', 'coverage_area', 'members'])
        
        return team
    
    async def get_all_personnel(
        self,
        requesting_user_id: UUID,
        role_filter: Optional[str] = None,
        firm_id_filter: Optional[UUID] = None,
        include_inactive: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[FirmPersonnel]:
        """
        Get all firm personnel across all security firms (admin only)
        
        This method only returns security firm personnel, not mobile users or other user types.
        
        Args:
            requesting_user_id: ID of user making the request (must be admin)
            role_filter: Optional role filter (field_agent, team_leader, office_staff, admin)
            firm_id_filter: Optional firm ID filter
            include_inactive: Whether to include inactive personnel
            limit: Maximum number of results to return
            offset: Number of results to skip
            
        Returns:
            List of FirmPersonnel objects (security firm personnel only)
        """
        # Note: Authorization check should be done at the API level (require_admin)
        
        # Query only FirmPersonnel table - excludes mobile users and other user types
        query = select(FirmPersonnel)
        
        # Validate and apply role filter (only firm personnel roles)
        if role_filter:
            valid_roles = ['field_agent', 'team_leader', 'office_staff', 'admin']
            if role_filter not in valid_roles:
                raise ValueError(f"Invalid role filter. Must be one of: {', '.join(valid_roles)}")
            query = query.where(FirmPersonnel.role == role_filter)
        
        if firm_id_filter:
            query = query.where(FirmPersonnel.firm_id == firm_id_filter)
        
        if not include_inactive:
            query = query.where(FirmPersonnel.is_active == True)
        
        # Load relationships for firm and team information
        query = query.options(
            selectinload(FirmPersonnel.team),
            selectinload(FirmPersonnel.firm)
        )
        
        # Add pagination
        query = query.offset(offset).limit(limit)
        
        result = await self.db.execute(query)
        personnel_list = result.scalars().all()
        
        logger.info(
            "firm_personnel_retrieved",
            count=len(personnel_list),
            requested_by=str(requesting_user_id),
            filters={
                "role": role_filter,
                "firm_id": str(firm_id_filter) if firm_id_filter else None,
                "include_inactive": include_inactive
            }
        )
        
        return personnel_list
    
    async def get_personnel_with_authorization(
        self,
        requesting_user: UserContext,
        firm_id_filter: Optional[UUID] = None,
        role_filter: Optional[str] = None,
        include_inactive: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[FirmPersonnel]:
        """
        Get personnel with proper authorization filtering
        
        Args:
            requesting_user: User making the request
            firm_id_filter: Optional firm ID filter
            role_filter: Optional role filter
            include_inactive: Whether to include inactive personnel
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of FirmPersonnel objects based on user permissions
        """
        # Get filter based on user permissions
        user_filter = get_personnel_filter_for_user(requesting_user)
        
        if user_filter["firm_id_filter"] == "NO_ACCESS":
            return []
        
        # Build query
        query = select(FirmPersonnel)
        
        # Apply firm filter based on permissions
        if user_filter["firm_id_filter"] is not None:
            # User can only see their firm's personnel
            query = query.where(FirmPersonnel.firm_id == user_filter["firm_id_filter"])
        elif firm_id_filter is not None:
            # Admin/super_admin with specific firm filter
            query = query.where(FirmPersonnel.firm_id == firm_id_filter)
        
        # Apply additional filters
        if role_filter:
            query = query.where(FirmPersonnel.role == role_filter)
        
        if not include_inactive:
            query = query.where(FirmPersonnel.is_active == True)
        
        # Load relationships
        query = query.options(
            selectinload(FirmPersonnel.team),
            selectinload(FirmPersonnel.firm)
        )
        
        # Add pagination
        query = query.offset(offset).limit(limit)
        
        result = await self.db.execute(query)
        personnel_list = result.scalars().all()
        
        logger.info(
            "personnel_retrieved_with_authorization",
            count=len(personnel_list),
            requested_by=str(requesting_user.user_id),
            user_role=requesting_user.role,
            can_view_all=can_view_all_personnel(requesting_user),
            filters={
                "firm_id": str(firm_id_filter) if firm_id_filter else None,
                "role": role_filter,
                "include_inactive": include_inactive
            }
        )
        
        return personnel_list
    
    async def lock_personnel(
        self,
        personnel_id: UUID,
        requesting_user: UserContext
    ) -> FirmPersonnel:
        """
        Lock personnel account (admin/super_admin only)
        
        Args:
            personnel_id: Personnel ID to lock
            requesting_user: User making the request
            
        Returns:
            Updated FirmPersonnel object
            
        Raises:
            ValueError: If authorization fails or personnel not found
        """
        # Authorization check - only admin/super_admin can lock personnel
        if not can_lock_unlock_personnel(requesting_user):
            raise ValueError("Only administrators can lock personnel accounts")
        
        personnel = await self.db.get(FirmPersonnel, personnel_id)
        if not personnel:
            raise ValueError("Personnel not found")
        
        personnel.is_locked = True
        await self.db.commit()
        await self.db.refresh(personnel)
        
        logger.info(
            "personnel_locked",
            personnel_id=str(personnel_id),
            locked_by=str(requesting_user.user_id),
            personnel_email=personnel.email
        )
        
        return personnel
    
    async def unlock_personnel(
        self,
        personnel_id: UUID,
        requesting_user: UserContext
    ) -> FirmPersonnel:
        """
        Unlock personnel account (admin/super_admin only)
        
        Args:
            personnel_id: Personnel ID to unlock
            requesting_user: User making the request
            
        Returns:
            Updated FirmPersonnel object
            
        Raises:
            ValueError: If authorization fails or personnel not found
        """
        # Authorization check - only admin/super_admin can unlock personnel
        if not can_lock_unlock_personnel(requesting_user):
            raise ValueError("Only administrators can unlock personnel accounts")
        
        personnel = await self.db.get(FirmPersonnel, personnel_id)
        if not personnel:
            raise ValueError("Personnel not found")
        
        personnel.is_locked = False
        await self.db.commit()
        await self.db.refresh(personnel)
        
        logger.info(
            "personnel_unlocked",
            personnel_id=str(personnel_id),
            unlocked_by=str(requesting_user.user_id),
            personnel_email=personnel.email
        )
        
        return personnel
    
    async def lock_personnel(
        self,
        personnel_id: UUID,
        requesting_user: UserContext
    ) -> FirmPersonnel:
        """
        Lock personnel account (admin/super_admin only)
        
        Args:
            personnel_id: Personnel ID to lock
            requesting_user: User making the request
            
        Returns:
            Updated FirmPersonnel object
        """
        # Authorization check - only admin/super_admin can lock
        if not can_lock_unlock_personnel(requesting_user):
            raise ValueError("Only administrators can lock personnel accounts")
        
        personnel = await self.db.get(FirmPersonnel, personnel_id)
        if not personnel:
            raise ValueError("Personnel not found")
        
        from sqlalchemy import func
        personnel.is_locked = True
        personnel.locked_at = func.now()
        await self.db.commit()
        await self.db.refresh(personnel)
        
        logger.info(
            "personnel_locked",
            personnel_id=str(personnel_id),
            locked_by=str(requesting_user.user_id),
            locked_by_role=requesting_user.role
        )
        
        return personnel
    
    async def unlock_personnel(
        self,
        personnel_id: UUID,
        requesting_user: UserContext
    ) -> FirmPersonnel:
        """
        Unlock personnel account (admin/super_admin only)
        
        Args:
            personnel_id: Personnel ID to unlock
            requesting_user: User making the request
            
        Returns:
            Updated FirmPersonnel object
        """
        # Authorization check - only admin/super_admin can unlock
        if not can_lock_unlock_personnel(requesting_user):
            raise ValueError("Only administrators can unlock personnel accounts")
        
        personnel = await self.db.get(FirmPersonnel, personnel_id)
        if not personnel:
            raise ValueError("Personnel not found")
        
        personnel.is_locked = False
        personnel.locked_at = None
        personnel.failed_login_attempts = 0  # Reset failed attempts
        await self.db.commit()
        await self.db.refresh(personnel)
        
        logger.info(
            "personnel_unlocked",
            personnel_id=str(personnel_id),
            unlocked_by=str(requesting_user.user_id),
            unlocked_by_role=requesting_user.role
        )
        
        return personnel