"""
Unit tests for personnel management API endpoints
"""
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import status

from app.main import app
from app.services.personnel import PersonnelService
from app.models.security_firm import FirmPersonnel, Team
from app.services.auth import UserContext


@pytest.fixture
def client():
    """Test client"""
    return TestClient(app)


@pytest.fixture
def mock_user_context():
    """Mock user context"""
    return UserContext(
        user_id=uuid4(),
        user_type="firm_personnel",
        email="test@security.com",
        permissions=["team:manage", "personnel:manage"],
        firm_id=uuid4(),
        role="office_staff"
    )


@pytest.fixture
def sample_personnel_data():
    """Sample personnel data"""
    return {
        "email": "agent@security.com",
        "phone": "+1234567890",
        "first_name": "John",
        "last_name": "Doe",
        "role": "field_agent",
        "password": "password123"
    }


@pytest.fixture
def sample_team_data():
    """Sample team data"""
    return {
        "name": "Alpha Team",
        "team_leader_id": None,
        "coverage_area_id": None
    }


class TestPersonnelEnrollmentAPI:
    """Test personnel enrollment API endpoints"""
    
    @patch('app.core.auth.get_current_user')
    @patch('app.services.personnel.PersonnelService.enroll_personnel')
    def test_enroll_personnel_success(self, mock_enroll, mock_auth, client, mock_user_context, sample_personnel_data):
        """Test successful personnel enrollment"""
        # Setup
        firm_id = str(uuid4())
        personnel_id = uuid4()
        
        mock_auth.return_value = mock_user_context
        mock_personnel = FirmPersonnel(
            id=personnel_id,
            firm_id=uuid4(),
            email=sample_personnel_data["email"],
            phone=sample_personnel_data["phone"],
            first_name=sample_personnel_data["first_name"],
            last_name=sample_personnel_data["last_name"],
            role=sample_personnel_data["role"],
            password_hash="hashed_password",
            is_active=True,
            is_locked=False
        )
        mock_personnel.created_at = "2024-01-01T00:00:00"
        mock_enroll.return_value = mock_personnel
        
        # Execute
        response = client.post(
            f"/api/v1/personnel/firms/{firm_id}/personnel",
            json=sample_personnel_data,
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Verify
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == sample_personnel_data["email"]
        assert data["role"] == sample_personnel_data["role"]
        assert data["is_active"] is True
        mock_enroll.assert_called_once()
    
    @patch('app.core.auth.get_current_user')
    def test_enroll_personnel_invalid_role(self, mock_auth, client, mock_user_context):
        """Test personnel enrollment with invalid role"""
        # Setup
        firm_id = str(uuid4())
        mock_auth.return_value = mock_user_context
        
        invalid_data = {
            "email": "agent@security.com",
            "phone": "+1234567890",
            "first_name": "John",
            "last_name": "Doe",
            "role": "invalid_role",
            "password": "password123"
        }
        
        # Execute
        response = client.post(
            f"/api/v1/personnel/firms/{firm_id}/personnel",
            json=invalid_data,
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Verify
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @patch('app.core.auth.get_current_user')
    def test_enroll_personnel_weak_password(self, mock_auth, client, mock_user_context):
        """Test personnel enrollment with weak password"""
        # Setup
        firm_id = str(uuid4())
        mock_auth.return_value = mock_user_context
        
        weak_password_data = {
            "email": "agent@security.com",
            "phone": "+1234567890",
            "first_name": "John",
            "last_name": "Doe",
            "role": "field_agent",
            "password": "123"  # Too short
        }
        
        # Execute
        response = client.post(
            f"/api/v1/personnel/firms/{firm_id}/personnel",
            json=weak_password_data,
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Verify
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @patch('app.core.auth.get_current_user')
    @patch('app.services.personnel.PersonnelService.enroll_personnel')
    def test_enroll_personnel_service_error(self, mock_enroll, mock_auth, client, mock_user_context, sample_personnel_data):
        """Test personnel enrollment with service error"""
        # Setup
        firm_id = str(uuid4())
        mock_auth.return_value = mock_user_context
        mock_enroll.side_effect = ValueError("Security firm not found")
        
        # Execute
        response = client.post(
            f"/api/v1/personnel/firms/{firm_id}/personnel",
            json=sample_personnel_data,
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Verify
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Security firm not found" in response.json()["detail"]


class TestPersonnelManagementAPI:
    """Test personnel management API endpoints"""
    
    @patch('app.core.auth.get_current_user')
    @patch('app.services.personnel.PersonnelService.get_firm_personnel')
    def test_get_firm_personnel(self, mock_get_personnel, mock_auth, client, mock_user_context):
        """Test getting firm personnel"""
        # Setup
        firm_id = str(uuid4())
        mock_auth.return_value = mock_user_context
        
        mock_personnel_list = [
            FirmPersonnel(
                id=uuid4(),
                firm_id=uuid4(),
                email=f"agent{i}@security.com",
                phone=f"+123456789{i}",
                first_name=f"Agent{i}",
                last_name="Doe",
                role="field_agent",
                password_hash="hashed_password",
                is_active=True,
                is_locked=False
            )
            for i in range(3)
        ]
        
        for personnel in mock_personnel_list:
            personnel.created_at = "2024-01-01T00:00:00"
            personnel.team_id = None
        
        mock_get_personnel.return_value = mock_personnel_list
        
        # Execute
        response = client.get(
            f"/api/v1/personnel/firms/{firm_id}/personnel",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Verify
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 3
        assert all(p["role"] == "field_agent" for p in data)
        mock_get_personnel.assert_called_once()
    
    @patch('app.core.auth.get_current_user')
    @patch('app.services.personnel.PersonnelService.get_firm_personnel')
    def test_get_firm_personnel_with_filters(self, mock_get_personnel, mock_auth, client, mock_user_context):
        """Test getting firm personnel with role filter"""
        # Setup
        firm_id = str(uuid4())
        mock_auth.return_value = mock_user_context
        mock_get_personnel.return_value = []
        
        # Execute
        response = client.get(
            f"/api/v1/personnel/firms/{firm_id}/personnel?role_filter=team_leader&include_inactive=true",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Verify
        assert response.status_code == status.HTTP_200_OK
        mock_get_personnel.assert_called_once()
        # Verify the service was called with correct parameters
        call_args = mock_get_personnel.call_args
        assert call_args.kwargs["role_filter"] == "team_leader"
        assert call_args.kwargs["include_inactive"] is True
    
    @patch('app.core.auth.get_current_user')
    @patch('app.services.personnel.PersonnelService.update_personnel')
    def test_update_personnel(self, mock_update, mock_auth, client, mock_user_context):
        """Test updating personnel"""
        # Setup
        personnel_id = str(uuid4())
        mock_auth.return_value = mock_user_context
        
        updated_personnel = FirmPersonnel(
            id=uuid4(),
            firm_id=uuid4(),
            email="agent@security.com",
            phone="+9876543210",  # Updated phone
            first_name="John",
            last_name="Doe",
            role="team_leader",  # Updated role
            password_hash="hashed_password",
            is_active=True,
            is_locked=False
        )
        updated_personnel.created_at = "2024-01-01T00:00:00"
        updated_personnel.team_id = None
        
        mock_update.return_value = updated_personnel
        
        update_data = {
            "phone": "+9876543210",
            "role": "team_leader"
        }
        
        # Execute
        response = client.put(
            f"/api/v1/personnel/personnel/{personnel_id}",
            json=update_data,
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Verify
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["phone"] == "+9876543210"
        assert data["role"] == "team_leader"
        mock_update.assert_called_once()
    
    @patch('app.core.auth.get_current_user')
    @patch('app.services.personnel.PersonnelService.deactivate_personnel')
    def test_deactivate_personnel(self, mock_deactivate, mock_auth, client, mock_user_context):
        """Test deactivating personnel"""
        # Setup
        personnel_id = str(uuid4())
        mock_auth.return_value = mock_user_context
        
        deactivated_personnel = FirmPersonnel(
            id=uuid4(),
            firm_id=uuid4(),
            email="agent@security.com",
            phone="+1234567890",
            first_name="John",
            last_name="Doe",
            role="field_agent",
            password_hash="hashed_password",
            is_active=False,  # Deactivated
            is_locked=False
        )
        deactivated_personnel.created_at = "2024-01-01T00:00:00"
        deactivated_personnel.team_id = None
        
        mock_deactivate.return_value = deactivated_personnel
        
        # Execute
        response = client.delete(
            f"/api/v1/personnel/personnel/{personnel_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Verify
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_active"] is False
        mock_deactivate.assert_called_once()


class TestTeamManagementAPI:
    """Test team management API endpoints"""
    
    @patch('app.core.auth.get_current_user')
    @patch('app.services.personnel.PersonnelService.create_team')
    def test_create_team(self, mock_create, mock_auth, client, mock_user_context, sample_team_data):
        """Test creating a team"""
        # Setup
        firm_id = str(uuid4())
        mock_auth.return_value = mock_user_context
        
        mock_team = Team(
            id=uuid4(),
            firm_id=uuid4(),
            name=sample_team_data["name"],
            team_leader_id=None,
            coverage_area_id=None,
            is_active=True
        )
        mock_team.created_at = "2024-01-01T00:00:00"
        
        mock_create.return_value = mock_team
        
        # Execute
        response = client.post(
            f"/api/v1/personnel/firms/{firm_id}/teams",
            json=sample_team_data,
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Verify
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == sample_team_data["name"]
        assert data["is_active"] is True
        mock_create.assert_called_once()
    
    @patch('app.core.auth.get_current_user')
    @patch('app.services.personnel.PersonnelService.get_firm_teams')
    def test_get_firm_teams(self, mock_get_teams, mock_auth, client, mock_user_context):
        """Test getting firm teams"""
        # Setup
        firm_id = str(uuid4())
        mock_auth.return_value = mock_user_context
        
        mock_teams = [
            Team(
                id=uuid4(),
                firm_id=uuid4(),
                name=f"Team {i}",
                team_leader_id=None,
                coverage_area_id=None,
                is_active=True
            )
            for i in range(2)
        ]
        
        for team in mock_teams:
            team.created_at = "2024-01-01T00:00:00"
        
        mock_get_teams.return_value = mock_teams
        
        # Execute
        response = client.get(
            f"/api/v1/personnel/firms/{firm_id}/teams",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Verify
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert all(t["is_active"] is True for t in data)
        mock_get_teams.assert_called_once()
    
    @patch('app.core.auth.get_current_user')
    @patch('app.services.personnel.PersonnelService.assign_personnel_to_team')
    def test_assign_personnel_to_team(self, mock_assign, mock_auth, client, mock_user_context):
        """Test assigning personnel to team"""
        # Setup
        personnel_id = str(uuid4())
        team_id = str(uuid4())
        mock_auth.return_value = mock_user_context
        
        assigned_personnel = FirmPersonnel(
            id=uuid4(),
            firm_id=uuid4(),
            email="agent@security.com",
            phone="+1234567890",
            first_name="John",
            last_name="Doe",
            role="field_agent",
            password_hash="hashed_password",
            is_active=True,
            is_locked=False,
            team_id=uuid4()  # Assigned to team
        )
        assigned_personnel.created_at = "2024-01-01T00:00:00"
        
        mock_assign.return_value = assigned_personnel
        
        assignment_data = {
            "personnel_id": personnel_id,
            "team_id": team_id
        }
        
        # Execute
        response = client.post(
            "/api/v1/personnel/teams/assign",
            json=assignment_data,
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Verify
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["team_id"] is not None
        mock_assign.assert_called_once()
    
    @patch('app.core.auth.get_current_user')
    @patch('app.services.personnel.PersonnelService.remove_personnel_from_team')
    def test_remove_personnel_from_team(self, mock_remove, mock_auth, client, mock_user_context):
        """Test removing personnel from team"""
        # Setup
        personnel_id = str(uuid4())
        mock_auth.return_value = mock_user_context
        
        removed_personnel = FirmPersonnel(
            id=uuid4(),
            firm_id=uuid4(),
            email="agent@security.com",
            phone="+1234567890",
            first_name="John",
            last_name="Doe",
            role="field_agent",
            password_hash="hashed_password",
            is_active=True,
            is_locked=False,
            team_id=None  # Removed from team
        )
        removed_personnel.created_at = "2024-01-01T00:00:00"
        
        mock_remove.return_value = removed_personnel
        
        # Execute
        response = client.delete(
            f"/api/v1/personnel/personnel/{personnel_id}/team",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Verify
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["team_id"] is None
        mock_remove.assert_called_once()
    
    @patch('app.core.auth.get_current_user')
    @patch('app.services.personnel.PersonnelService.get_team_members')
    def test_get_team_members(self, mock_get_members, mock_auth, client, mock_user_context):
        """Test getting team members"""
        # Setup
        team_id = str(uuid4())
        mock_auth.return_value = mock_user_context
        
        mock_members = [
            FirmPersonnel(
                id=uuid4(),
                firm_id=uuid4(),
                email=f"agent{i}@security.com",
                phone=f"+123456789{i}",
                first_name=f"Agent{i}",
                last_name="Doe",
                role="field_agent",
                password_hash="hashed_password",
                is_active=True,
                is_locked=False,
                team_id=uuid4()
            )
            for i in range(3)
        ]
        
        for member in mock_members:
            member.created_at = "2024-01-01T00:00:00"
        
        mock_get_members.return_value = mock_members
        
        # Execute
        response = client.get(
            f"/api/v1/personnel/teams/{team_id}/members",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Verify
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 3
        assert all(m["team_id"] is not None for m in data)
        mock_get_members.assert_called_once()


class TestPersonnelRetrievalAPI:
    """Test personnel and team retrieval API endpoints"""
    
    @patch('app.core.auth.get_current_user')
    @patch('app.services.personnel.PersonnelService.get_personnel_by_id')
    def test_get_personnel_by_id(self, mock_get_personnel, mock_auth, client, mock_user_context):
        """Test getting personnel by ID"""
        # Setup
        personnel_id = str(uuid4())
        mock_auth.return_value = mock_user_context
        
        mock_personnel = FirmPersonnel(
            id=uuid4(),
            firm_id=uuid4(),
            email="agent@security.com",
            phone="+1234567890",
            first_name="John",
            last_name="Doe",
            role="field_agent",
            password_hash="hashed_password",
            is_active=True,
            is_locked=False
        )
        mock_personnel.created_at = "2024-01-01T00:00:00"
        mock_personnel.team_id = None
        
        mock_get_personnel.return_value = mock_personnel
        
        # Execute
        response = client.get(
            f"/api/v1/personnel/personnel/{personnel_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Verify
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == "agent@security.com"
        assert data["role"] == "field_agent"
        mock_get_personnel.assert_called_once()
    
    @patch('app.core.auth.get_current_user')
    @patch('app.services.personnel.PersonnelService.get_personnel_by_id')
    def test_get_personnel_by_id_not_found(self, mock_get_personnel, mock_auth, client, mock_user_context):
        """Test getting personnel by ID when not found"""
        # Setup
        personnel_id = str(uuid4())
        mock_auth.return_value = mock_user_context
        mock_get_personnel.return_value = None
        
        # Execute
        response = client.get(
            f"/api/v1/personnel/personnel/{personnel_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Verify
        assert response.status_code == status.HTTP_404_NOT_FOUND
        mock_get_personnel.assert_called_once()
    
    @patch('app.core.auth.get_current_user')
    @patch('app.services.personnel.PersonnelService.get_team_by_id')
    def test_get_team_by_id(self, mock_get_team, mock_auth, client, mock_user_context):
        """Test getting team by ID"""
        # Setup
        team_id = str(uuid4())
        mock_auth.return_value = mock_user_context
        
        mock_team = Team(
            id=uuid4(),
            firm_id=uuid4(),
            name="Alpha Team",
            team_leader_id=None,
            coverage_area_id=None,
            is_active=True
        )
        mock_team.created_at = "2024-01-01T00:00:00"
        
        mock_get_team.return_value = mock_team
        
        # Execute
        response = client.get(
            f"/api/v1/personnel/teams/{team_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Verify
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Alpha Team"
        assert data["is_active"] is True
        mock_get_team.assert_called_once()
    
    @patch('app.core.auth.get_current_user')
    @patch('app.services.personnel.PersonnelService.get_team_by_id')
    def test_get_team_by_id_not_found(self, mock_get_team, mock_auth, client, mock_user_context):
        """Test getting team by ID when not found"""
        # Setup
        team_id = str(uuid4())
        mock_auth.return_value = mock_user_context
        mock_get_team.return_value = None
        
        # Execute
        response = client.get(
            f"/api/v1/personnel/teams/{team_id}",
            headers={"Authorization": "Bearer test_token"}
        )
        
        # Verify
        assert response.status_code == status.HTTP_404_NOT_FOUND
        mock_get_team.assert_called_once()