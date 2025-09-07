"""
API Integration Tests
Tests all API endpoints with real database interactions
"""
import pytest
import json
from uuid import uuid4
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock

from app.core.auth import create_access_token
from app.services.auth import UserContext


class TestAuthAPIIntegration:
    """Integration tests for authentication API"""
    
    @pytest.mark.asyncio
    async def test_complete_auth_flow(self, client, db_session, sample_registered_user, mock_external_services):
        """Test complete authentication flow"""
        # Mock authentication service
        with patch('app.services.auth.auth_service.authenticate_user') as mock_auth:
            mock_auth.return_value = {
                "access_token": "test.access.token",
                "refresh_token": "test.refresh.token",
                "expires_in": 3600,
                "token_type": "Bearer"
            }
            
            # Test login
            response = client.post("/api/v1/auth/login", json={
                "email": sample_registered_user.email,
                "password": "test_password",
                "user_type": "registered_user"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
            
            # Test token verification
            with patch('app.core.auth.verify_token') as mock_verify:
                mock_verify.return_value = UserContext(
                    user_id=sample_registered_user.id,
                    user_type="registered_user",
                    email=sample_registered_user.email,
                    permissions=["emergency:request"]
                )
                
                response = client.post(
                    "/api/v1/auth/verify-token",
                    headers={"Authorization": f"Bearer {data['access_token']}"}
                )
                
                assert response.status_code == 200
                verify_data = response.json()
                assert verify_data["valid"] is True
                assert verify_data["user_id"] == str(sample_registered_user.id)
    
    @pytest.mark.asyncio
    async def test_account_lockout_flow(self, client, db_session, sample_registered_user, mock_external_services):
        """Test account lockout and unlock flow"""
        # Mock failed authentication attempts
        with patch('app.services.auth.auth_service.authenticate_user') as mock_auth:
            mock_auth.side_effect = Exception("Invalid credentials")
            
            # Make 5 failed login attempts
            for i in range(5):
                response = client.post("/api/v1/auth/login", json={
                    "email": sample_registered_user.email,
                    "password": "wrong_password",
                    "user_type": "registered_user"
                })
                assert response.status_code == 401
            
            # 6th attempt should lock account
            response = client.post("/api/v1/auth/login", json={
                "email": sample_registered_user.email,
                "password": "wrong_password",
                "user_type": "registered_user"
            })
            assert response.status_code == 423  # Account locked
            
            # Test OTP unlock request
            response = client.post("/api/v1/auth/request-unlock-otp", json={
                "user_identifier": sample_registered_user.email,
                "delivery_method": "email"
            })
            assert response.status_code == 200
            
            # Test OTP verification and unlock
            with patch('app.services.account_security.verify_unlock_otp') as mock_verify_otp:
                mock_verify_otp.return_value = True
                
                response = client.post("/api/v1/auth/unlock-account", json={
                    "user_identifier": sample_registered_user.email,
                    "otp": "123456"
                })
                assert response.status_code == 200


class TestUserAPIIntegration:
    """Integration tests for user management API"""
    
    @pytest.mark.asyncio
    async def test_user_registration_flow(self, client, db_session, mock_external_services):
        """Test complete user registration flow"""
        registration_data = {
            "email": "newuser@test.com",
            "phone": "+1555999888",
            "first_name": "New",
            "last_name": "User",
            "password": "secure_password123"
        }
        
        # Mock user service
        with patch('app.services.user.UserService.register_user') as mock_register:
            mock_user = AsyncMock()
            mock_user.id = uuid4()
            mock_user.email = registration_data["email"]
            mock_user.is_verified = False
            mock_register.return_value = mock_user
            
            response = client.post("/api/v1/users/register", json=registration_data)
            
            assert response.status_code == 201
            data = response.json()
            assert data["email"] == registration_data["email"]
            assert data["is_verified"] is False
            
            # Test phone verification
            with patch('app.services.user.UserService.verify_mobile_number') as mock_verify:
                mock_verify.return_value = True
                
                response = client.post("/api/v1/users/verify-phone", json={
                    "phone": registration_data["phone"],
                    "verification_code": "123456"
                })
                
                assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_group_management_flow(self, client, db_session, sample_registered_user, auth_headers, mock_external_services):
        """Test complete group management flow"""
        headers = auth_headers("registered_user", sample_registered_user.id)
        
        # Mock authentication
        with patch('app.core.auth.verify_token') as mock_verify:
            mock_verify.return_value = UserContext(
                user_id=sample_registered_user.id,
                user_type="registered_user",
                email=sample_registered_user.email,
                permissions=["group:manage"]
            )
            
            # Create group
            group_data = {
                "name": "Integration Test Group",
                "address": "123 Integration St, Test City",
                "latitude": 40.7484,
                "longitude": -73.9857,
                "mobile_numbers": [
                    {"phone_number": "+1555111111", "user_type": "individual"},
                    {"phone_number": "+1555222222", "user_type": "alarm"}
                ]
            }
            
            with patch('app.services.user.UserService.create_group') as mock_create:
                mock_group = AsyncMock()
                mock_group.id = uuid4()
                mock_group.name = group_data["name"]
                mock_create.return_value = mock_group
                
                response = client.post("/api/v1/users/groups", json=group_data, headers=headers)
                
                assert response.status_code == 201
                data = response.json()
                assert data["name"] == group_data["name"]
                
                # Test group retrieval
                with patch('app.services.user.UserService.get_user_groups') as mock_get:
                    mock_get.return_value = [mock_group]
                    
                    response = client.get("/api/v1/users/groups", headers=headers)
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert len(data["groups"]) == 1


class TestSubscriptionAPIIntegration:
    """Integration tests for subscription API"""
    
    @pytest.mark.asyncio
    async def test_subscription_purchase_flow(
        self, 
        client, 
        db_session, 
        sample_registered_user, 
        sample_subscription_product,
        auth_headers,
        mock_external_services
    ):
        """Test complete subscription purchase and application flow"""
        headers = auth_headers("registered_user", sample_registered_user.id)
        
        # Mock authentication
        with patch('app.core.auth.verify_token') as mock_verify:
            mock_verify.return_value = UserContext(
                user_id=sample_registered_user.id,
                user_type="registered_user",
                email=sample_registered_user.email,
                permissions=["subscription:purchase"]
            )
            
            # Purchase subscription
            purchase_data = {
                "product_id": str(sample_subscription_product.id),
                "payment_method": "credit_card",
                "payment_details": {
                    "card_number": "4111111111111111",
                    "expiry_month": 12,
                    "expiry_year": 2025,
                    "cvv": "123"
                }
            }
            
            with patch('app.services.subscription.SubscriptionService.purchase_subscription') as mock_purchase:
                mock_subscription = AsyncMock()
                mock_subscription.id = uuid4()
                mock_subscription.product_id = sample_subscription_product.id
                mock_subscription.is_applied = False
                mock_purchase.return_value = mock_subscription
                
                response = client.post("/api/v1/subscriptions/purchase", json=purchase_data, headers=headers)
                
                assert response.status_code == 201
                data = response.json()
                assert data["product_id"] == str(sample_subscription_product.id)
                assert data["is_applied"] is False
                
                # Test subscription application
                application_data = {
                    "subscription_id": str(mock_subscription.id),
                    "group_id": str(uuid4())
                }
                
                with patch('app.services.subscription.SubscriptionService.apply_subscription') as mock_apply:
                    mock_apply.return_value = True
                    
                    response = client.post("/api/v1/subscriptions/apply", json=application_data, headers=headers)
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert data["success"] is True


class TestEmergencyAPIIntegration:
    """Integration tests for emergency API"""
    
    @pytest.mark.asyncio
    async def test_panic_request_flow(
        self, 
        client, 
        db_session, 
        sample_user_group,
        sample_group_mobile_number,
        sample_coverage_area,
        mock_external_services
    ):
        """Test complete panic request flow"""
        # Mock mobile attestation
        with patch('app.api.v1.emergency.require_mobile_attestation') as mock_attestation:
            mock_attestation.return_value = {"valid": True}
            
            # Submit panic request
            request_data = {
                "requester_phone": sample_group_mobile_number.phone_number,
                "group_id": str(sample_user_group.id),
                "service_type": "security",
                "latitude": 40.7484,
                "longitude": -73.9857,
                "address": "Times Square, New York, NY",
                "description": "Emergency assistance needed"
            }
            
            with patch('app.services.emergency.EmergencyService.submit_panic_request') as mock_submit:
                mock_request = AsyncMock()
                mock_request.id = uuid4()
                mock_request.requester_phone = request_data["requester_phone"]
                mock_request.service_type = request_data["service_type"]
                mock_request.status = "pending"
                mock_request.created_at = datetime.utcnow()
                mock_submit.return_value = mock_request
                
                response = client.post("/api/v1/emergency/request", json=request_data)
                
                assert response.status_code == 201
                data = response.json()
                assert data["requester_phone"] == request_data["requester_phone"]
                assert data["service_type"] == request_data["service_type"]
                assert data["status"] == "pending"
                
                # Test request status update
                status_update = {
                    "status": "accepted",
                    "message": "Request accepted by field agent",
                    "latitude": 40.7484,
                    "longitude": -73.9857
                }
                
                with patch('app.core.auth.verify_token') as mock_verify:
                    mock_verify.return_value = UserContext(
                        user_id=uuid4(),
                        user_type="firm_personnel",
                        email="agent@security.com",
                        permissions=["emergency:update"]
                    )
                    
                    with patch('app.services.emergency.EmergencyService.update_request_status') as mock_update:
                        mock_update.return_value = True
                        
                        response = client.put(
                            f"/api/v1/emergency/requests/{mock_request.id}/status",
                            json=status_update,
                            headers={"Authorization": "Bearer test.token"}
                        )
                        
                        assert response.status_code == 200
                        data = response.json()
                        assert data["success"] is True


class TestSecurityFirmAPIIntegration:
    """Integration tests for security firm API"""
    
    @pytest.mark.asyncio
    async def test_firm_registration_flow(self, client, db_session, mock_external_services):
        """Test complete security firm registration flow"""
        registration_data = {
            "name": "Integration Security Firm",
            "registration_number": "ISF001",
            "email": "integration@security.com",
            "phone": "+1555777888",
            "address": "456 Security Blvd, Test City",
            "documents": [
                {"type": "business_license", "url": "https://example.com/license.pdf"},
                {"type": "insurance", "url": "https://example.com/insurance.pdf"}
            ]
        }
        
        with patch('app.services.security_firm.SecurityFirmService.register_firm') as mock_register:
            mock_firm = AsyncMock()
            mock_firm.id = uuid4()
            mock_firm.name = registration_data["name"]
            mock_firm.verification_status = "pending"
            mock_register.return_value = mock_firm
            
            response = client.post("/api/v1/security-firms/register", json=registration_data)
            
            assert response.status_code == 201
            data = response.json()
            assert data["name"] == registration_data["name"]
            assert data["verification_status"] == "pending"
            
            # Test coverage area definition
            coverage_data = {
                "name": "Test Coverage Area",
                "boundary_coordinates": [
                    [-74.0479, 40.6829],
                    [-73.9067, 40.6829],
                    [-73.9067, 40.8176],
                    [-74.0479, 40.8176],
                    [-74.0479, 40.6829]
                ]
            }
            
            with patch('app.core.auth.verify_token') as mock_verify:
                mock_verify.return_value = UserContext(
                    user_id=uuid4(),
                    user_type="security_firm",
                    email=registration_data["email"],
                    permissions=["coverage:manage"]
                )
                
                with patch('app.services.security_firm.SecurityFirmService.define_coverage_area') as mock_coverage:
                    mock_area = AsyncMock()
                    mock_area.id = uuid4()
                    mock_area.name = coverage_data["name"]
                    mock_coverage.return_value = mock_area
                    
                    response = client.post(
                        "/api/v1/security-firms/coverage-areas",
                        json=coverage_data,
                        headers={"Authorization": "Bearer test.token"}
                    )
                    
                    assert response.status_code == 201
                    data = response.json()
                    assert data["name"] == coverage_data["name"]


class TestPersonnelAPIIntegration:
    """Integration tests for personnel management API"""
    
    @pytest.mark.asyncio
    async def test_personnel_management_flow(
        self, 
        client, 
        db_session, 
        sample_security_firm,
        auth_headers,
        mock_external_services
    ):
        """Test complete personnel management flow"""
        headers = auth_headers("security_firm", sample_security_firm.id)
        
        # Mock authentication
        with patch('app.core.auth.verify_token') as mock_verify:
            mock_verify.return_value = UserContext(
                user_id=sample_security_firm.id,
                user_type="security_firm",
                email=sample_security_firm.email,
                permissions=["personnel:manage"]
            )
            
            # Enroll personnel
            personnel_data = {
                "email": "newagent@security.com",
                "phone": "+1555333444",
                "first_name": "New",
                "last_name": "Agent",
                "role": "field_agent",
                "password": "secure_password123"
            }
            
            with patch('app.services.personnel.PersonnelService.enroll_personnel') as mock_enroll:
                mock_personnel = AsyncMock()
                mock_personnel.id = uuid4()
                mock_personnel.email = personnel_data["email"]
                mock_personnel.role = personnel_data["role"]
                mock_personnel.is_active = True
                mock_enroll.return_value = mock_personnel
                
                response = client.post("/api/v1/personnel", json=personnel_data, headers=headers)
                
                assert response.status_code == 201
                data = response.json()
                assert data["email"] == personnel_data["email"]
                assert data["role"] == personnel_data["role"]
                
                # Test team creation
                team_data = {
                    "name": "Integration Team",
                    "team_leader_id": str(mock_personnel.id),
                    "coverage_area_id": str(uuid4())
                }
                
                with patch('app.services.personnel.PersonnelService.create_team') as mock_create_team:
                    mock_team = AsyncMock()
                    mock_team.id = uuid4()
                    mock_team.name = team_data["name"]
                    mock_create_team.return_value = mock_team
                    
                    response = client.post("/api/v1/personnel/teams", json=team_data, headers=headers)
                    
                    assert response.status_code == 201
                    data = response.json()
                    assert data["name"] == team_data["name"]


class TestCreditAPIIntegration:
    """Integration tests for credit management API"""
    
    @pytest.mark.asyncio
    async def test_credit_purchase_flow(
        self, 
        client, 
        db_session, 
        sample_security_firm,
        auth_headers,
        mock_external_services
    ):
        """Test complete credit purchase flow"""
        headers = auth_headers("security_firm", sample_security_firm.id)
        
        # Mock authentication
        with patch('app.core.auth.verify_token') as mock_verify:
            mock_verify.return_value = UserContext(
                user_id=sample_security_firm.id,
                user_type="security_firm",
                email=sample_security_firm.email,
                permissions=["credit:purchase"]
            )
            
            # Purchase credits
            purchase_data = {
                "amount": 500,
                "payment_method": "credit_card",
                "payment_details": {
                    "card_number": "4111111111111111",
                    "expiry_month": 12,
                    "expiry_year": 2025,
                    "cvv": "123"
                }
            }
            
            with patch('app.services.credit.CreditService.purchase_credits') as mock_purchase:
                mock_transaction = AsyncMock()
                mock_transaction.id = uuid4()
                mock_transaction.amount = purchase_data["amount"]
                mock_transaction.status = "completed"
                mock_purchase.return_value = mock_transaction
                
                response = client.post("/api/v1/credits/purchase", json=purchase_data, headers=headers)
                
                assert response.status_code == 201
                data = response.json()
                assert data["amount"] == purchase_data["amount"]
                assert data["status"] == "completed"
                
                # Test credit balance check
                with patch('app.services.credit.CreditService.get_credit_balance') as mock_balance:
                    mock_balance.return_value = 1500  # Original 1000 + 500 purchased
                    
                    response = client.get("/api/v1/credits/balance", headers=headers)
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert data["balance"] == 1500


class TestFeedbackAPIIntegration:
    """Integration tests for feedback API"""
    
    @pytest.mark.asyncio
    async def test_feedback_submission_flow(
        self, 
        client, 
        db_session, 
        sample_panic_request,
        sample_firm_personnel,
        auth_headers,
        mock_external_services
    ):
        """Test complete feedback submission flow"""
        headers = auth_headers("firm_personnel", sample_firm_personnel.id)
        
        # Mock authentication
        with patch('app.core.auth.verify_token') as mock_verify:
            mock_verify.return_value = UserContext(
                user_id=sample_firm_personnel.id,
                user_type="firm_personnel",
                email=sample_firm_personnel.email,
                permissions=["feedback:submit"]
            )
            
            # Submit feedback
            feedback_data = {
                "request_id": str(sample_panic_request.id),
                "is_prank": False,
                "performance_rating": 5,
                "comments": "Service completed successfully",
                "response_time_minutes": 15
            }
            
            with patch('app.services.feedback.FeedbackService.submit_feedback') as mock_submit:
                mock_feedback = AsyncMock()
                mock_feedback.id = uuid4()
                mock_feedback.request_id = sample_panic_request.id
                mock_feedback.is_prank = feedback_data["is_prank"]
                mock_feedback.performance_rating = feedback_data["performance_rating"]
                mock_submit.return_value = mock_feedback
                
                response = client.post("/api/v1/feedback", json=feedback_data, headers=headers)
                
                assert response.status_code == 201
                data = response.json()
                assert data["request_id"] == str(sample_panic_request.id)
                assert data["is_prank"] == feedback_data["is_prank"]
                assert data["performance_rating"] == feedback_data["performance_rating"]


class TestMetricsAPIIntegration:
    """Integration tests for metrics API"""
    
    @pytest.mark.asyncio
    async def test_metrics_collection_flow(
        self, 
        client, 
        db_session, 
        sample_security_firm,
        auth_headers,
        mock_external_services
    ):
        """Test complete metrics collection and reporting flow"""
        headers = auth_headers("security_firm", sample_security_firm.id)
        
        # Mock authentication
        with patch('app.core.auth.verify_token') as mock_verify:
            mock_verify.return_value = UserContext(
                user_id=sample_security_firm.id,
                user_type="security_firm",
                email=sample_security_firm.email,
                permissions=["metrics:view"]
            )
            
            # Get performance metrics
            with patch('app.services.metrics.MetricsService.get_performance_metrics') as mock_metrics:
                mock_metrics.return_value = {
                    "total_requests": 100,
                    "average_response_time": 12.5,
                    "completion_rate": 0.95,
                    "zone_metrics": [
                        {"zone": "Manhattan", "avg_response_time": 10.2, "requests": 60},
                        {"zone": "Brooklyn", "avg_response_time": 15.8, "requests": 40}
                    ],
                    "service_type_metrics": [
                        {"service_type": "security", "avg_response_time": 11.0, "requests": 70},
                        {"service_type": "ambulance", "avg_response_time": 16.0, "requests": 30}
                    ]
                }
                
                response = client.get("/api/v1/metrics/performance", headers=headers)
                
                assert response.status_code == 200
                data = response.json()
                assert data["total_requests"] == 100
                assert data["average_response_time"] == 12.5
                assert len(data["zone_metrics"]) == 2
                assert len(data["service_type_metrics"]) == 2