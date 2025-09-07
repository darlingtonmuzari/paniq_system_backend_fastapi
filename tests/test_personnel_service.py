"""
Unit tests for personnel management service
"""
import pytest
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.personnel import PersonnelService
from app.models.security_firm import SecurityFirm, FirmPersonnel, Team, CoverageArea


@pytest.fixture
def mock_db():
    """Mock database session"""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def personnel_service(mock_db):
    """Personnel service with mocked database"""
    return PersonnelService(mock_db)


@pytest.fixture
def sample_firm():
    """Sample security firm"""
    return SecurityFirm(
        id=uuid4(),
        name="Test Security Firm",
        registration_number="TSF001",
        email="test@security.com",
        phone="+1234567890",
        address="123 Test St",
        verification_status="approved",
        credit_balance=100
    )


@pytest.fixture
def sample_personnel():
    """Sample firm personnel"""
    return FirmPersonnel(
        id=uuid4(),
        firm_id=uuid4(),
        email="agent@security.com",
        phone="+1234567891",
        first_name="John",
        last_name="Doe",
        role="field_agent",
        password_hash="hashed_password",
        is_active=True
    )


@pytest.fixture
def sample_team():
    """Sample team"""
    return Team(
        id=uuid4(),
        firm_id=uuid4(),
        name="Alpha Team",
        team_leader_id=uuid4(),
        coverage_area_id=uuid4(),
        is_active=True
    )


class TestPersonnelEnrollment:
    """Test personnel enrollment functionality"""
    
    @pytest.mark.asyncio
    async def test_enroll_personnel_success(self, personnel_service, mock_db, sample_firm):
        """Test successful personnel enrollment"""
        # Setup
        firm_id = sample_firm.id
        requesting_user_id = uuid4()
        
        # Mock database responses
        mock_db.get.return_value = sample_firm
        mock_execute_result = MagicMock()
        mock_execute_result.scalar_one_or_none.return_value = None  # No existing personnel
        mock_db.execute.return_value = mock_execute_result
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Execute
        result = await personnel_service.enroll_personnel(
            firm_id=firm_id,
            email="new@agent.com",
            phone="+1234567892",
            first_name="Jane",
            last_name="Smith",
            role="field_agent",
            password="password123",
            requesting_user_id=requesting_user_id
        )
        
        # Verify
        assert result is not None
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_enroll_personnel_invalid_role(self, personnel_service, mock_db, sample_firm):
        """Test personnel enrollment with invalid role"""
        # Setup
        firm_id = sample_firm.id
        requesting_user_id = uuid4()
        
        mock_db.get.return_value = sample_firm
        
        # Execute & Verify
        with pytest.raises(ValueError, match="Invalid role"):
            await personnel_service.enroll_personnel(
                firm_id=firm_id,
                email="new@agent.com",
                phone="+1234567892",
                first_name="Jane",
                last_name="Smith",
                role="invalid_role",
                password="password123",
                requesting_user_id=requesting_user_id
            )
    
    @pytest.mark.asyncio
    async def test_enroll_personnel_firm_not_found(self, personnel_service, mock_db):
        """Test personnel enrollment with non-existent firm"""
        # Setup
        firm_id = uuid4()
        requesting_user_id = uuid4()
        
        mock_db.get.return_value = None
        
        # Execute & Verify
        with pytest.raises(ValueError, match="Security firm not found"):
            await personnel_service.enroll_personnel(
                firm_id=firm_id,
                email="new@agent.com",
                phone="+1234567892",
                first_name="Jane",
                last_name="Smith",
                role="field_agent",
                password="password123",
                requesting_user_id=requesting_user_id
            )
    
    @pytest.mark.asyncio
    async def test_enroll_personnel_firm_not_approved(self, personnel_service, mock_db, sample_firm):
        """Test personnel enrollment with unapproved firm"""
        # Setup
        sample_firm.verification_status = "pending"
        firm_id = sample_firm.id
        requesting_user_id = uuid4()
        
        mock_db.get.return_value = sample_firm
        
        # Execute & Verify
        with pytest.raises(ValueError, match="Security firm must be approved"):
            await personnel_service.enroll_personnel(
                firm_id=firm_id,
                email="new@agent.com",
                phone="+1234567892",
                first_name="Jane",
                last_name="Smith",
                role="field_agent",
                password="password123",
                requesting_user_id=requesting_user_id
            )
    
    @pytest.mark.asyncio
    async def test_enroll_personnel_duplicate_email(self, personnel_service, mock_db, sample_firm, sample_personnel):
        """Test personnel enrollment with duplicate email"""
        # Setup
        firm_id = sample_firm.id
        requesting_user_id = uuid4()
        
        mock_db.get.return_value = sample_firm
        mock_execute_result = MagicMock()
        mock_execute_result.scalar_one_or_none.return_value = sample_personnel
        mock_db.execute.return_value = mock_execute_result
        
        # Execute & Verify
        with pytest.raises(ValueError, match="Personnel with this email already exists"):
            await personnel_service.enroll_personnel(
                firm_id=firm_id,
                email="agent@security.com",
                phone="+1234567892",
                first_name="Jane",
                last_name="Smith",
                role="field_agent",
                password="password123",
                requesting_user_id=requesting_user_id
            )


class TestPersonnelManagement:
    """Test personnel management functionality"""
    
    @pytest.mark.asyncio
    async def test_get_firm_personnel(self, personnel_service, mock_db):
        """Test getting firm personnel"""
        # Setup
        firm_id = uuid4()
        requesting_user_id = uuid4()
        personnel_list = [
            FirmPersonnel(
                id=uuid4(),
                firm_id=firm_id,
                email=f"agent{i}@security.com",
                phone=f"+123456789{i}",
                first_name=f"Agent{i}",
                last_name="Doe",
                role="field_agent",
                password_hash="hashed_password",
                is_active=True
            )
            for i in range(3)
        ]
        
        mock_execute_result = MagicMock()
        mock_scalars_result = MagicMock()
        mock_scalars_result.all.return_value = personnel_list
        mock_execute_result.scalars.return_value = mock_scalars_result
        mock_db.execute.return_value = mock_execute_result
        
        # Execute
        result = await personnel_service.get_firm_personnel(
            firm_id=firm_id,
            requesting_user_id=requesting_user_id
        )
        
        # Verify
        assert len(result) == 3
        mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_personnel(self, personnel_service, mock_db, sample_personnel):
        """Test updating personnel information"""
        # Setup
        personnel_id = sample_personnel.id
        requesting_user_id = uuid4()
        
        mock_db.get.return_value = sample_personnel
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Execute
        result = await personnel_service.update_personnel(
            personnel_id=personnel_id,
            requesting_user_id=requesting_user_id,
            phone="+9876543210",
            role="team_leader"
        )
        
        # Verify
        assert result.phone == "+9876543210"
        assert result.role == "team_leader"
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_deactivate_personnel(self, personnel_service, mock_db, sample_personnel):
        """Test deactivating personnel"""
        # Setup
        personnel_id = sample_personnel.id
        requesting_user_id = uuid4()
        
        mock_db.get.return_value = sample_personnel
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Execute
        result = await personnel_service.deactivate_personnel(
            personnel_id=personnel_id,
            requesting_user_id=requesting_user_id
        )
        
        # Verify
        assert result.is_active is False
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()


class TestTeamManagement:
    """Test team management functionality"""
    
    @pytest.mark.asyncio
    async def test_create_team_success(self, personnel_service, mock_db, sample_firm):
        """Test successful team creation"""
        # Setup
        firm_id = sample_firm.id
        requesting_user_id = uuid4()
        
        mock_db.get.return_value = sample_firm
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Execute
        result = await personnel_service.create_team(
            firm_id=firm_id,
            name="Bravo Team",
            team_leader_id=None,
            coverage_area_id=None,
            requesting_user_id=requesting_user_id
        )
        
        # Verify
        assert result is not None
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_team_with_leader(self, personnel_service, mock_db, sample_firm, sample_personnel):
        """Test team creation with team leader"""
        # Setup
        firm_id = sample_firm.id
        team_leader = sample_personnel
        team_leader.role = "team_leader"
        team_leader.firm_id = firm_id
        requesting_user_id = uuid4()
        
        # Mock database calls
        def mock_get(model_class, id_value):
            if model_class == SecurityFirm:
                return sample_firm
            elif model_class == FirmPersonnel:
                return team_leader
            return None
        
        mock_db.get.side_effect = mock_get
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Execute
        result = await personnel_service.create_team(
            firm_id=firm_id,
            name="Charlie Team",
            team_leader_id=team_leader.id,
            coverage_area_id=None,
            requesting_user_id=requesting_user_id
        )
        
        # Verify
        assert result is not None
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_team_invalid_leader_role(self, personnel_service, mock_db, sample_firm, sample_personnel):
        """Test team creation with invalid team leader role"""
        # Setup
        firm_id = sample_firm.id
        team_leader = sample_personnel
        team_leader.role = "field_agent"  # Invalid for team leader
        team_leader.firm_id = firm_id
        requesting_user_id = uuid4()
        
        def mock_get(model_class, id_value):
            if model_class == SecurityFirm:
                return sample_firm
            elif model_class == FirmPersonnel:
                return team_leader
            return None
        
        mock_db.get.side_effect = mock_get
        
        # Execute & Verify
        with pytest.raises(ValueError, match="Team leader must have team_leader or office_staff role"):
            await personnel_service.create_team(
                firm_id=firm_id,
                name="Delta Team",
                team_leader_id=team_leader.id,
                coverage_area_id=None,
                requesting_user_id=requesting_user_id
            )
    
    @pytest.mark.asyncio
    async def test_get_firm_teams(self, personnel_service, mock_db):
        """Test getting firm teams"""
        # Setup
        firm_id = uuid4()
        requesting_user_id = uuid4()
        teams_list = [
            Team(
                id=uuid4(),
                firm_id=firm_id,
                name=f"Team {i}",
                team_leader_id=None,
                coverage_area_id=None,
                is_active=True
            )
            for i in range(2)
        ]
        
        mock_execute_result = MagicMock()
        mock_scalars_result = MagicMock()
        mock_scalars_result.all.return_value = teams_list
        mock_execute_result.scalars.return_value = mock_scalars_result
        mock_db.execute.return_value = mock_execute_result
        
        # Execute
        result = await personnel_service.get_firm_teams(
            firm_id=firm_id,
            requesting_user_id=requesting_user_id
        )
        
        # Verify
        assert len(result) == 2
        mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_assign_personnel_to_team(self, personnel_service, mock_db, sample_personnel, sample_team):
        """Test assigning personnel to team"""
        # Setup
        personnel_id = sample_personnel.id
        team_id = sample_team.id
        sample_personnel.firm_id = sample_team.firm_id  # Same firm
        requesting_user_id = uuid4()
        
        def mock_get(model_class, id_value):
            if model_class == FirmPersonnel:
                return sample_personnel
            elif model_class == Team:
                return sample_team
            return None
        
        mock_db.get.side_effect = mock_get
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Execute
        result = await personnel_service.assign_personnel_to_team(
            personnel_id=personnel_id,
            team_id=team_id,
            requesting_user_id=requesting_user_id
        )
        
        # Verify
        assert result.team_id == team_id
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_assign_personnel_different_firms(self, personnel_service, mock_db, sample_personnel, sample_team):
        """Test assigning personnel to team from different firms"""
        # Setup
        personnel_id = sample_personnel.id
        team_id = sample_team.id
        sample_personnel.firm_id = uuid4()  # Different firm
        sample_team.firm_id = uuid4()
        requesting_user_id = uuid4()
        
        def mock_get(model_class, id_value):
            if model_class == FirmPersonnel:
                return sample_personnel
            elif model_class == Team:
                return sample_team
            return None
        
        mock_db.get.side_effect = mock_get
        
        # Execute & Verify
        with pytest.raises(ValueError, match="Personnel and team must belong to the same firm"):
            await personnel_service.assign_personnel_to_team(
                personnel_id=personnel_id,
                team_id=team_id,
                requesting_user_id=requesting_user_id
            )
    
    @pytest.mark.asyncio
    async def test_remove_personnel_from_team(self, personnel_service, mock_db, sample_personnel):
        """Test removing personnel from team"""
        # Setup
        personnel_id = sample_personnel.id
        sample_personnel.team_id = uuid4()  # Currently assigned to a team
        requesting_user_id = uuid4()
        
        mock_db.get.return_value = sample_personnel
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Execute
        result = await personnel_service.remove_personnel_from_team(
            personnel_id=personnel_id,
            requesting_user_id=requesting_user_id
        )
        
        # Verify
        assert result.team_id is None
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_team_members(self, personnel_service, mock_db, sample_team):
        """Test getting team members"""
        # Setup
        team_id = sample_team.id
        requesting_user_id = uuid4()
        members_list = [
            FirmPersonnel(
                id=uuid4(),
                firm_id=sample_team.firm_id,
                email=f"agent{i}@security.com",
                phone=f"+123456789{i}",
                first_name=f"Agent{i}",
                last_name="Doe",
                role="field_agent",
                password_hash="hashed_password",
                is_active=True,
                team_id=team_id
            )
            for i in range(3)
        ]
        
        mock_db.get.return_value = sample_team
        mock_execute_result = MagicMock()
        mock_scalars_result = MagicMock()
        mock_scalars_result.all.return_value = members_list
        mock_execute_result.scalars.return_value = mock_scalars_result
        mock_db.execute.return_value = mock_execute_result
        
        # Execute
        result = await personnel_service.get_team_members(
            team_id=team_id,
            requesting_user_id=requesting_user_id
        )
        
        # Verify
        assert len(result) == 3
        mock_db.execute.assert_called_once()


class TestPersonnelRetrieval:
    """Test personnel and team retrieval functionality"""
    
    @pytest.mark.asyncio
    async def test_get_personnel_by_id(self, personnel_service, mock_db, sample_personnel):
        """Test getting personnel by ID"""
        # Setup
        personnel_id = sample_personnel.id
        requesting_user_id = uuid4()
        
        mock_db.get.return_value = sample_personnel
        
        # Execute
        result = await personnel_service.get_personnel_by_id(
            personnel_id=personnel_id,
            requesting_user_id=requesting_user_id
        )
        
        # Verify
        assert result == sample_personnel
        mock_db.get.assert_called_once_with(FirmPersonnel, personnel_id)
    
    @pytest.mark.asyncio
    async def test_get_personnel_by_id_not_found(self, personnel_service, mock_db):
        """Test getting personnel by ID when not found"""
        # Setup
        personnel_id = uuid4()
        requesting_user_id = uuid4()
        
        mock_db.get.return_value = None
        
        # Execute
        result = await personnel_service.get_personnel_by_id(
            personnel_id=personnel_id,
            requesting_user_id=requesting_user_id
        )
        
        # Verify
        assert result is None
        mock_db.get.assert_called_once_with(FirmPersonnel, personnel_id)
    
    @pytest.mark.asyncio
    async def test_get_team_by_id(self, personnel_service, mock_db, sample_team):
        """Test getting team by ID"""
        # Setup
        team_id = sample_team.id
        requesting_user_id = uuid4()
        
        mock_db.get.return_value = sample_team
        mock_db.refresh = AsyncMock()
        
        # Execute
        result = await personnel_service.get_team_by_id(
            team_id=team_id,
            requesting_user_id=requesting_user_id
        )
        
        # Verify
        assert result == sample_team
        mock_db.get.assert_called_once_with(Team, team_id)
        mock_db.refresh.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_team_by_id_not_found(self, personnel_service, mock_db):
        """Test getting team by ID when not found"""
        # Setup
        team_id = uuid4()
        requesting_user_id = uuid4()
        
        mock_db.get.return_value = None
        
        # Execute
        result = await personnel_service.get_team_by_id(
            team_id=team_id,
            requesting_user_id=requesting_user_id
        )
        
        # Verify
        assert result is None
        mock_db.get.assert_called_once_with(Team, team_id)