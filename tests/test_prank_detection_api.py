"""
Tests for prank detection API endpoints
"""
import pytest
from decimal import Decimal
from datetime import datetime
from uuid import uuid4
from unittest.mock import AsyncMock, patch

from app.models.user import RegisteredUser, UserFine
from app.models.security_firm import SecurityFirm, FirmPersonnel


@pytest.fixture
async def test_user(db_session):
    """Create test user"""
    user = RegisteredUser(
        email="test@example.com",
        phone="+1234567890",
        first_name="Test",
        last_name="User",
        prank_flags=3,
        total_fines=Decimal("0.00"),
        is_suspended=False
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_admin_user(db_session):
    """Create test admin user"""
    # Create security firm first
    firm = SecurityFirm(
        name="Test Security Firm",
        registration_number="TSF001",
        email="firm@test.com",
        phone="+1234567890",
        address="123 Test St",
        verification_status="approved"
    )
    db_session.add(firm)
    await db_session.commit()
    await db_session.refresh(firm)
    
    # Create admin personnel
    admin = FirmPersonnel(
        firm_id=firm.id,
        email="admin@test.com",
        phone="+1234567891",
        first_name="Admin",
        last_name="User",
        role="admin",
        is_active=True
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest.fixture
async def test_fine(db_session, test_user):
    """Create test fine"""
    fine = UserFine(
        user_id=test_user.id,
        amount=Decimal("50.00"),
        reason="Test fine for prank behavior",
        is_paid=False
    )
    db_session.add(fine)
    await db_session.commit()
    await db_session.refresh(fine)
    return fine


class TestPrankDetectionAPI:
    """Test prank detection API endpoints"""
    
    async def test_get_user_prank_tracking_own_data(self, client, test_user, auth_headers):
        """Test getting own prank tracking data"""
        with patch('app.core.auth.get_current_user', return_value=test_user):
            response = await client.get(
                f"/api/v1/admin/prank-detection/users/{test_user.id}/tracking",
                headers=auth_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == str(test_user.id)
        assert data["total_prank_flags"] == 3
        assert "calculated_fine_amount" in data
    
    async def test_get_user_prank_tracking_unauthorized(self, client, test_user, auth_headers):
        """Test getting prank tracking data for another user without permission"""
        other_user = RegisteredUser(
            email="other@example.com",
            phone="+1234567892",
            first_name="Other",
            last_name="User"
        )
        
        with patch('app.core.auth.get_current_user', return_value=other_user):
            response = await client.get(
                f"/api/v1/admin/prank-detection/users/{test_user.id}/tracking",
                headers=auth_headers
            )
        
        assert response.status_code == 403
    
    async def test_get_user_prank_tracking_admin_access(self, client, test_user, test_admin_user, auth_headers):
        """Test admin accessing any user's prank tracking data"""
        with patch('app.core.auth.get_current_user', return_value=test_admin_user):
            response = await client.get(
                f"/api/v1/admin/prank-detection/users/{test_user.id}/tracking",
                headers=auth_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == str(test_user.id)
    
    async def test_get_user_prank_tracking_not_found(self, client, test_admin_user, auth_headers):
        """Test getting prank tracking for non-existent user"""
        with patch('app.core.auth.get_current_user', return_value=test_admin_user):
            response = await client.get(
                f"/api/v1/admin/prank-detection/users/{uuid4()}/tracking",
                headers=auth_headers
            )
        
        assert response.status_code == 400
    
    async def test_calculate_automatic_fine_success(self, client, test_user, test_admin_user, auth_headers):
        """Test successful automatic fine calculation"""
        with patch('app.core.auth.require_roles') as mock_auth:
            mock_auth.return_value = lambda: test_admin_user
            
            response = await client.post(
                f"/api/v1/admin/prank-detection/users/{test_user.id}/calculate-fine",
                headers=auth_headers
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data is not None
        assert data["user_id"] == str(test_user.id)
        assert data["amount"] == 50.0  # Base fine amount
        assert data["is_paid"] is False
    
    async def test_calculate_automatic_fine_no_fine_needed(self, client, test_admin_user, auth_headers, db_session):
        """Test automatic fine calculation when no fine is needed"""
        # Create user with insufficient pranks
        user = RegisteredUser(
            email="noprank@example.com",
            phone="+1234567893",
            first_name="No",
            last_name="Prank",
            prank_flags=1
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        
        with patch('app.core.auth.require_roles') as mock_auth:
            mock_auth.return_value = lambda: test_admin_user
            
            response = await client.post(
                f"/api/v1/admin/prank-detection/users/{user.id}/calculate-fine",
                headers=auth_headers
            )
        
        assert response.status_code == 200
        assert response.json() is None
    
    async def test_calculate_automatic_fine_unauthorized(self, client, test_user, auth_headers):
        """Test automatic fine calculation without proper permissions"""
        with patch('app.core.auth.require_roles') as mock_auth:
            mock_auth.side_effect = Exception("Insufficient permissions")
            
            response = await client.post(
                f"/api/v1/admin/prank-detection/users/{test_user.id}/calculate-fine",
                headers=auth_headers
            )
        
        assert response.status_code == 500  # Exception handling
    
    @patch('app.services.prank_detection.PrankDetectionService.process_fine_payment')
    async def test_pay_fine_success(self, mock_payment, client, test_user, test_fine, auth_headers):
        """Test successful fine payment"""
        # Mock the payment processing
        test_fine.is_paid = True
        test_fine.paid_at = datetime.utcnow()
        mock_payment.return_value = test_fine
        
        with patch('app.core.auth.get_current_user', return_value=test_user):
            with patch('app.services.prank_detection.PrankDetectionService.get_user_fines', return_value=[test_fine]):
                response = await client.post(
                    f"/api/v1/admin/prank-detection/fines/{test_fine.id}/pay",
                    json={
                        "payment_method": "card",
                        "payment_reference": "txn_123"
                    },
                    headers=auth_headers
                )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_fine.id)
        assert data["is_paid"] is True
        assert data["paid_at"] is not None
    
    async def test_pay_fine_unauthorized(self, client, test_fine, auth_headers):
        """Test paying fine that doesn't belong to user"""
        other_user = RegisteredUser(
            email="other@example.com",
            phone="+1234567894",
            first_name="Other",
            last_name="User"
        )
        
        with patch('app.core.auth.get_current_user', return_value=other_user):
            with patch('app.services.prank_detection.PrankDetectionService.get_user_fines', return_value=[]):
                response = await client.post(
                    f"/api/v1/admin/prank-detection/fines/{test_fine.id}/pay",
                    json={
                        "payment_method": "card",
                        "payment_reference": "txn_123"
                    },
                    headers=auth_headers
                )
        
        assert response.status_code == 403
    
    async def test_suspend_user_account_success(self, client, test_user, test_admin_user, auth_headers):
        """Test successful user account suspension"""
        with patch('app.core.auth.require_roles') as mock_auth:
            mock_auth.return_value = lambda: test_admin_user
            
            with patch('app.services.prank_detection.PrankDetectionService.suspend_account_for_unpaid_fines', return_value=True):
                response = await client.post(
                    f"/api/v1/admin/prank-detection/users/{test_user.id}/suspend",
                    headers=auth_headers
                )
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == str(test_user.id)
        assert data["suspended"] is True
        assert "suspended for unpaid fines" in data["message"]
    
    async def test_suspend_user_account_already_suspended(self, client, test_user, test_admin_user, auth_headers):
        """Test suspending already suspended account"""
        with patch('app.core.auth.require_roles') as mock_auth:
            mock_auth.return_value = lambda: test_admin_user
            
            with patch('app.services.prank_detection.PrankDetectionService.suspend_account_for_unpaid_fines', return_value=False):
                response = await client.post(
                    f"/api/v1/admin/prank-detection/users/{test_user.id}/suspend",
                    headers=auth_headers
                )
        
        assert response.status_code == 200
        data = response.json()
        assert data["suspended"] is False
        assert "already suspended" in data["message"]
    
    async def test_ban_user_permanently_success(self, client, test_user, test_admin_user, auth_headers):
        """Test successful permanent user ban"""
        with patch('app.core.auth.require_roles') as mock_auth:
            mock_auth.return_value = lambda: test_admin_user
            
            with patch('app.services.prank_detection.PrankDetectionService.create_permanent_ban', return_value=True):
                response = await client.post(
                    f"/api/v1/admin/prank-detection/users/{test_user.id}/ban",
                    params={"reason": "Excessive prank behavior"},
                    headers=auth_headers
                )
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == str(test_user.id)
        assert data["banned"] is True
        assert data["reason"] == "Excessive prank behavior"
        assert "permanently banned" in data["message"]
    
    async def test_ban_user_permanently_insufficient_pranks(self, client, test_user, test_admin_user, auth_headers):
        """Test permanent ban with insufficient prank flags"""
        with patch('app.core.auth.require_roles') as mock_auth:
            mock_auth.return_value = lambda: test_admin_user
            
            with patch('app.services.prank_detection.PrankDetectionService.create_permanent_ban', return_value=False):
                response = await client.post(
                    f"/api/v1/admin/prank-detection/users/{test_user.id}/ban",
                    headers=auth_headers
                )
        
        assert response.status_code == 200
        data = response.json()
        assert data["banned"] is False
        assert "does not meet ban criteria" in data["message"]
    
    async def test_get_user_fines_own_fines(self, client, test_user, test_fine, auth_headers):
        """Test getting own fines"""
        with patch('app.core.auth.get_current_user', return_value=test_user):
            with patch('app.services.prank_detection.PrankDetectionService.get_user_fines', return_value=[test_fine]):
                response = await client.get(
                    f"/api/v1/admin/prank-detection/users/{test_user.id}/fines",
                    headers=auth_headers
                )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == str(test_fine.id)
        assert data[0]["user_id"] == str(test_user.id)
    
    async def test_get_user_fines_with_filters(self, client, test_user, auth_headers):
        """Test getting user fines with filters"""
        with patch('app.core.auth.get_current_user', return_value=test_user):
            with patch('app.services.prank_detection.PrankDetectionService.get_user_fines', return_value=[]):
                response = await client.get(
                    f"/api/v1/admin/prank-detection/users/{test_user.id}/fines",
                    params={
                        "include_paid": "false",
                        "limit": "10",
                        "offset": "0"
                    },
                    headers=auth_headers
                )
        
        assert response.status_code == 200
        assert response.json() == []
    
    async def test_get_user_fines_unauthorized(self, client, test_user, auth_headers):
        """Test getting fines for another user without permission"""
        other_user = RegisteredUser(
            email="other@example.com",
            phone="+1234567895",
            first_name="Other",
            last_name="User"
        )
        
        with patch('app.core.auth.get_current_user', return_value=other_user):
            response = await client.get(
                f"/api/v1/admin/prank-detection/users/{test_user.id}/fines",
                headers=auth_headers
            )
        
        assert response.status_code == 403
    
    async def test_get_fine_statistics_success(self, client, test_admin_user, auth_headers):
        """Test getting fine statistics"""
        mock_stats = {
            "total_fines": 10,
            "paid_fines": 7,
            "unpaid_fines": 3,
            "total_amount": 500.0,
            "paid_amount": 350.0,
            "unpaid_amount": 150.0,
            "payment_rate_percentage": 70.0,
            "date_range": {"from": None, "to": None}
        }
        
        with patch('app.core.auth.require_roles') as mock_auth:
            mock_auth.return_value = lambda: test_admin_user
            
            with patch('app.services.prank_detection.PrankDetectionService.get_fine_statistics', return_value=mock_stats):
                response = await client.get(
                    "/api/v1/admin/prank-detection/statistics",
                    headers=auth_headers
                )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_fines"] == 10
        assert data["paid_fines"] == 7
        assert data["payment_rate_percentage"] == 70.0
    
    async def test_get_fine_statistics_with_date_filter(self, client, test_admin_user, auth_headers):
        """Test getting fine statistics with date filters"""
        with patch('app.core.auth.require_roles') as mock_auth:
            mock_auth.return_value = lambda: test_admin_user
            
            with patch('app.services.prank_detection.PrankDetectionService.get_fine_statistics', return_value={}):
                response = await client.get(
                    "/api/v1/admin/prank-detection/statistics",
                    params={
                        "date_from": "2024-01-01T00:00:00",
                        "date_to": "2024-12-31T23:59:59"
                    },
                    headers=auth_headers
                )
        
        assert response.status_code == 200
    
    async def test_get_fine_statistics_unauthorized(self, client, test_user, auth_headers):
        """Test getting fine statistics without proper permissions"""
        with patch('app.core.auth.require_roles') as mock_auth:
            mock_auth.side_effect = Exception("Insufficient permissions")
            
            response = await client.get(
                "/api/v1/admin/prank-detection/statistics",
                headers=auth_headers
            )
        
        assert response.status_code == 500  # Exception handling
    
    async def test_invalid_payment_request_format(self, client, test_user, test_fine, auth_headers):
        """Test fine payment with invalid request format"""
        with patch('app.core.auth.get_current_user', return_value=test_user):
            response = await client.post(
                f"/api/v1/admin/prank-detection/fines/{test_fine.id}/pay",
                json={
                    "invalid_field": "value"
                },
                headers=auth_headers
            )
        
        assert response.status_code == 422  # Validation error
    
    async def test_invalid_uuid_format(self, client, test_admin_user, auth_headers):
        """Test endpoints with invalid UUID format"""
        with patch('app.core.auth.require_roles') as mock_auth:
            mock_auth.return_value = lambda: test_admin_user
            
            response = await client.get(
                "/api/v1/admin/prank-detection/users/invalid-uuid/tracking",
                headers=auth_headers
            )
        
        assert response.status_code == 422  # Validation error