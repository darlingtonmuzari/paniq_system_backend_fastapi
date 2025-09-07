"""
End-to-End Workflow Integration Tests
Tests complete business workflows from start to finish
"""
import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock

from app.core.auth import create_access_token
from app.services.auth import UserContext


class TestUserRegistrationWorkflow:
    """Test complete user registration and verification workflow"""
    
    @pytest.mark.asyncio
    async def test_complete_user_registration_workflow(
        self, 
        client, 
        db_session, 
        mock_external_services
    ):
        """Test complete user registration from signup to verification"""
        
        # Step 1: User registration
        registration_data = {
            "email": "workflow@test.com",
            "phone": "+1555workflow",
            "first_name": "Workflow",
            "last_name": "Test",
            "password": "secure_password123"
        }
        
        with patch('app.services.user.UserService.register_user') as mock_register:
            mock_user = AsyncMock()
            mock_user.id = uuid4()
            mock_user.email = registration_data["email"]
            mock_user.phone = registration_data["phone"]
            mock_user.is_verified = False
            mock_register.return_value = mock_user
            
            response = client.post("/api/v1/users/register", json=registration_data)
            assert response.status_code == 201
            
            user_data = response.json()
            user_id = user_data["id"]
            
            # Step 2: Phone verification request
            with patch('app.services.otp_delivery.OTPDeliveryService.send_sms_otp') as mock_send_otp:
                mock_send_otp.return_value = {
                    "success": True,
                    "message_id": "otp_123"
                }
                
                response = client.post("/api/v1/users/request-verification", json={
                    "phone": registration_data["phone"]
                })
                assert response.status_code == 200
                
                # Step 3: Phone verification
                with patch('app.services.user.UserService.verify_mobile_number') as mock_verify:
                    mock_verify.return_value = True
                    
                    response = client.post("/api/v1/users/verify-phone", json={
                        "phone": registration_data["phone"],
                        "verification_code": "123456"
                    })
                    assert response.status_code == 200
                    
                    # Step 4: Login after verification
                    with patch('app.services.auth.auth_service.authenticate_user') as mock_auth:
                        mock_auth.return_value = {
                            "access_token": "verified.user.token",
                            "refresh_token": "verified.refresh.token",
                            "expires_in": 3600,
                            "token_type": "Bearer"
                        }
                        
                        response = client.post("/api/v1/auth/login", json={
                            "email": registration_data["email"],
                            "password": registration_data["password"],
                            "user_type": "registered_user"
                        })
                        assert response.status_code == 200
                        
                        login_data = response.json()
                        assert "access_token" in login_data


class TestSecurityFirmOnboardingWorkflow:
    """Test complete security firm onboarding workflow"""
    
    @pytest.mark.asyncio
    async def test_complete_firm_onboarding_workflow(
        self, 
        client, 
        db_session, 
        mock_external_services
    ):
        """Test complete security firm onboarding from registration to service activation"""
        
        # Step 1: Firm registration
        firm_data = {
            "name": "Workflow Security Firm",
            "registration_number": "WSF001",
            "email": "workflow@security.com",
            "phone": "+1555security",
            "address": "123 Security Blvd, Test City",
            "documents": [
                {"type": "business_license", "url": "https://example.com/license.pdf"},
                {"type": "insurance", "url": "https://example.com/insurance.pdf"}
            ]
        }
        
        with patch('app.services.security_firm.SecurityFirmService.register_firm') as mock_register:
            mock_firm = AsyncMock()
            mock_firm.id = uuid4()
            mock_firm.name = firm_data["name"]
            mock_firm.email = firm_data["email"]
            mock_firm.verification_status = "pending"
            mock_firm.credit_balance = 0
            mock_register.return_value = mock_firm
            
            response = client.post("/api/v1/security-firms/register", json=firm_data)
            assert response.status_code == 201
            
            firm_response = response.json()
            firm_id = firm_response["id"]
            
            # Step 2: Admin approval (simulated)
            with patch('app.services.security_firm.SecurityFirmService.approve_firm') as mock_approve:
                mock_firm.verification_status = "approved"
                mock_approve.return_value = mock_firm
                
                # Simulate admin approval
                admin_headers = {"Authorization": "Bearer admin.token"}
                response = client.put(
                    f"/api/v1/admin/security-firms/{firm_id}/approve",
                    headers=admin_headers
                )
                assert response.status_code == 200
                
                # Step 3: Credit purchase
                with patch('app.core.auth.verify_token') as mock_verify:
                    mock_verify.return_value = UserContext(
                        user_id=uuid4(firm_id),
                        user_type="security_firm",
                        email=firm_data["email"],
                        permissions=["credit:purchase"]
                    )
                    
                    credit_data = {
                        "amount": 1000,
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
                        mock_transaction.amount = 1000
                        mock_transaction.status = "completed"
                        mock_purchase.return_value = mock_transaction
                        
                        firm_headers = {"Authorization": "Bearer firm.token"}
                        response = client.post(
                            "/api/v1/credits/purchase",
                            json=credit_data,
                            headers=firm_headers
                        )
                        assert response.status_code == 201
                        
                        # Step 4: Coverage area definition
                        coverage_data = {
                            "name": "Manhattan Coverage",
                            "boundary_coordinates": [
                                [-74.0479, 40.6829],
                                [-73.9067, 40.6829],
                                [-73.9067, 40.8176],
                                [-74.0479, 40.8176],
                                [-74.0479, 40.6829]
                            ]
                        }
                        
                        with patch('app.services.security_firm.SecurityFirmService.define_coverage_area') as mock_coverage:
                            mock_area = AsyncMock()
                            mock_area.id = uuid4()
                            mock_area.name = coverage_data["name"]
                            mock_coverage.return_value = mock_area
                            
                            response = client.post(
                                "/api/v1/security-firms/coverage-areas",
                                json=coverage_data,
                                headers=firm_headers
                            )
                            assert response.status_code == 201
                            
                            # Step 5: Personnel enrollment
                            personnel_data = {
                                "email": "agent@workflow.com",
                                "phone": "+1555agent",
                                "first_name": "Field",
                                "last_name": "Agent",
                                "role": "field_agent",
                                "password": "agent_password123"
                            }
                            
                            with patch('app.services.personnel.PersonnelService.enroll_personnel') as mock_enroll:
                                mock_personnel = AsyncMock()
                                mock_personnel.id = uuid4()
                                mock_personnel.email = personnel_data["email"]
                                mock_personnel.role = personnel_data["role"]
                                mock_enroll.return_value = mock_personnel
                                
                                response = client.post(
                                    "/api/v1/personnel",
                                    json=personnel_data,
                                    headers=firm_headers
                                )
                                assert response.status_code == 201
                                
                                # Step 6: Subscription product creation
                                product_data = {
                                    "name": "Basic Security Package",
                                    "description": "Basic emergency response services",
                                    "max_users": 10,
                                    "price": 99.99,
                                    "credit_cost": 50
                                }
                                
                                with patch('app.services.subscription.SubscriptionService.create_product') as mock_create_product:
                                    mock_product = AsyncMock()
                                    mock_product.id = uuid4()
                                    mock_product.name = product_data["name"]
                                    mock_product.price = product_data["price"]
                                    mock_create_product.return_value = mock_product
                                    
                                    response = client.post(
                                        "/api/v1/subscription-products",
                                        json=product_data,
                                        headers=firm_headers
                                    )
                                    assert response.status_code == 201
                                    
                                    product_response = response.json()
                                    assert product_response["name"] == product_data["name"]


class TestEmergencyResponseWorkflow:
    """Test complete emergency response workflow"""
    
    @pytest.mark.asyncio
    async def test_complete_emergency_response_workflow(
        self, 
        client, 
        db_session, 
        sample_user_group,
        sample_group_mobile_number,
        sample_firm_personnel,
        sample_team,
        mock_external_services
    ):
        """Test complete emergency response from request to completion"""
        
        # Step 1: Panic request submission
        with patch('app.api.v1.emergency.require_mobile_attestation') as mock_attestation:
            mock_attestation.return_value = {"valid": True}
            
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
                
                request_response = response.json()
                request_id = request_response["id"]
                
                # Step 2: Office staff allocates request to team
                with patch('app.core.auth.verify_token') as mock_verify:
                    mock_verify.return_value = UserContext(
                        user_id=uuid4(),
                        user_type="firm_personnel",
                        email="office@security.com",
                        permissions=["emergency:allocate"]
                    )
                    
                    allocation_data = {
                        "team_id": str(sample_team.id),
                        "priority": "high",
                        "notes": "Urgent response required"
                    }
                    
                    with patch('app.services.emergency.EmergencyService.allocate_request') as mock_allocate:
                        mock_allocate.return_value = True
                        
                        office_headers = {"Authorization": "Bearer office.token"}
                        response = client.post(
                            f"/api/v1/emergency/requests/{request_id}/allocate",
                            json=allocation_data,
                            headers=office_headers
                        )
                        assert response.status_code == 200
                        
                        # Step 3: Field agent accepts request
                        mock_verify.return_value = UserContext(
                            user_id=sample_firm_personnel.id,
                            user_type="firm_personnel",
                            email=sample_firm_personnel.email,
                            permissions=["emergency:accept"]
                        )
                        
                        acceptance_data = {
                            "status": "accepted",
                            "message": "En route to location",
                            "latitude": 40.7500,
                            "longitude": -73.9800
                        }
                        
                        with patch('app.services.emergency.EmergencyService.update_request_status') as mock_update:
                            mock_update.return_value = True
                            
                            agent_headers = {"Authorization": "Bearer agent.token"}
                            response = client.put(
                                f"/api/v1/emergency/requests/{request_id}/status",
                                json=acceptance_data,
                                headers=agent_headers
                            )
                            assert response.status_code == 200
                            
                            # Step 4: Agent arrives at location
                            arrival_data = {
                                "status": "arrived",
                                "message": "Arrived at location",
                                "latitude": 40.7484,
                                "longitude": -73.9857
                            }
                            
                            response = client.put(
                                f"/api/v1/emergency/requests/{request_id}/status",
                                json=arrival_data,
                                headers=agent_headers
                            )
                            assert response.status_code == 200
                            
                            # Step 5: Service completion
                            completion_data = {
                                "status": "completed",
                                "message": "Service completed successfully",
                                "latitude": 40.7484,
                                "longitude": -73.9857
                            }
                            
                            response = client.put(
                                f"/api/v1/emergency/requests/{request_id}/status",
                                json=completion_data,
                                headers=agent_headers
                            )
                            assert response.status_code == 200
                            
                            # Step 6: Feedback submission
                            feedback_data = {
                                "request_id": request_id,
                                "is_prank": False,
                                "performance_rating": 5,
                                "comments": "Service completed successfully",
                                "response_time_minutes": 15
                            }
                            
                            with patch('app.services.feedback.FeedbackService.submit_feedback') as mock_feedback:
                                mock_feedback_obj = AsyncMock()
                                mock_feedback_obj.id = uuid4()
                                mock_feedback_obj.request_id = uuid4(request_id)
                                mock_feedback_obj.is_prank = False
                                mock_feedback_obj.performance_rating = 5
                                mock_feedback.return_value = mock_feedback_obj
                                
                                response = client.post(
                                    "/api/v1/feedback",
                                    json=feedback_data,
                                    headers=agent_headers
                                )
                                assert response.status_code == 201
                                
                                feedback_response = response.json()
                                assert feedback_response["is_prank"] is False
                                assert feedback_response["performance_rating"] == 5


class TestSubscriptionLifecycleWorkflow:
    """Test complete subscription lifecycle workflow"""
    
    @pytest.mark.asyncio
    async def test_complete_subscription_lifecycle_workflow(
        self, 
        client, 
        db_session, 
        sample_registered_user,
        sample_subscription_product,
        mock_external_services
    ):
        """Test complete subscription lifecycle from purchase to expiry"""
        
        # Step 1: User purchases subscription
        with patch('app.core.auth.verify_token') as mock_verify:
            mock_verify.return_value = UserContext(
                user_id=sample_registered_user.id,
                user_type="registered_user",
                email=sample_registered_user.email,
                permissions=["subscription:purchase"]
            )
            
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
                
                user_headers = {"Authorization": "Bearer user.token"}
                response = client.post(
                    "/api/v1/subscriptions/purchase",
                    json=purchase_data,
                    headers=user_headers
                )
                assert response.status_code == 201
                
                subscription_response = response.json()
                subscription_id = subscription_response["id"]
                
                # Step 2: User creates group
                group_data = {
                    "name": "Subscription Test Group",
                    "address": "123 Subscription St, Test City",
                    "latitude": 40.7484,
                    "longitude": -73.9857,
                    "mobile_numbers": [
                        {"phone_number": "+1555sub1", "user_type": "individual"},
                        {"phone_number": "+1555sub2", "user_type": "alarm"}
                    ]
                }
                
                with patch('app.services.user.UserService.create_group') as mock_create_group:
                    mock_group = AsyncMock()
                    mock_group.id = uuid4()
                    mock_group.name = group_data["name"]
                    mock_create_group.return_value = mock_group
                    
                    response = client.post(
                        "/api/v1/users/groups",
                        json=group_data,
                        headers=user_headers
                    )
                    assert response.status_code == 201
                    
                    group_response = response.json()
                    group_id = group_response["id"]
                    
                    # Step 3: User applies subscription to group
                    application_data = {
                        "subscription_id": subscription_id,
                        "group_id": group_id
                    }
                    
                    with patch('app.services.subscription.SubscriptionService.apply_subscription') as mock_apply:
                        mock_apply.return_value = True
                        
                        response = client.post(
                            "/api/v1/subscriptions/apply",
                            json=application_data,
                            headers=user_headers
                        )
                        assert response.status_code == 200
                        
                        application_response = response.json()
                        assert application_response["success"] is True
                        
                        # Step 4: Verify active subscription
                        with patch('app.services.subscription.SubscriptionService.get_active_subscriptions') as mock_active:
                            mock_active.return_value = [{
                                "id": subscription_id,
                                "group_id": group_id,
                                "product_name": sample_subscription_product.name,
                                "expires_at": datetime.utcnow() + timedelta(days=30),
                                "is_active": True
                            }]
                            
                            response = client.get(
                                "/api/v1/subscriptions/active",
                                headers=user_headers
                            )
                            assert response.status_code == 200
                            
                            active_response = response.json()
                            assert len(active_response["subscriptions"]) == 1
                            assert active_response["subscriptions"][0]["is_active"] is True
                            
                            # Step 5: Subscription renewal
                            renewal_data = {
                                "subscription_id": subscription_id,
                                "payment_method": "credit_card",
                                "payment_details": {
                                    "card_number": "4111111111111111",
                                    "expiry_month": 12,
                                    "expiry_year": 2025,
                                    "cvv": "123"
                                }
                            }
                            
                            with patch('app.services.subscription.SubscriptionService.renew_subscription') as mock_renew:
                                mock_renew.return_value = {
                                    "success": True,
                                    "new_expiry": datetime.utcnow() + timedelta(days=60)
                                }
                                
                                response = client.post(
                                    "/api/v1/subscriptions/renew",
                                    json=renewal_data,
                                    headers=user_headers
                                )
                                assert response.status_code == 200
                                
                                renewal_response = response.json()
                                assert renewal_response["success"] is True


class TestPrankDetectionWorkflow:
    """Test complete prank detection and user fining workflow"""
    
    @pytest.mark.asyncio
    async def test_complete_prank_detection_workflow(
        self, 
        client, 
        db_session, 
        sample_registered_user,
        sample_user_group,
        sample_group_mobile_number,
        sample_firm_personnel,
        mock_external_services
    ):
        """Test complete prank detection from multiple false alarms to user suspension"""
        
        # Create multiple panic requests and mark them as pranks
        prank_requests = []
        
        for i in range(3):  # Create 3 prank requests
            # Step 1: Submit panic request
            with patch('app.api.v1.emergency.require_mobile_attestation') as mock_attestation:
                mock_attestation.return_value = {"valid": True}
                
                request_data = {
                    "requester_phone": sample_group_mobile_number.phone_number,
                    "group_id": str(sample_user_group.id),
                    "service_type": "security",
                    "latitude": 40.7484,
                    "longitude": -73.9857,
                    "address": f"Prank Location {i}",
                    "description": f"Prank emergency {i}"
                }
                
                with patch('app.services.emergency.EmergencyService.submit_panic_request') as mock_submit:
                    mock_request = AsyncMock()
                    mock_request.id = uuid4()
                    mock_request.requester_phone = request_data["requester_phone"]
                    mock_request.service_type = request_data["service_type"]
                    mock_request.status = "completed"
                    mock_submit.return_value = mock_request
                    
                    response = client.post("/api/v1/emergency/request", json=request_data)
                    assert response.status_code == 201
                    
                    request_response = response.json()
                    request_id = request_response["id"]
                    prank_requests.append(request_id)
                    
                    # Step 2: Submit feedback marking as prank
                    with patch('app.core.auth.verify_token') as mock_verify:
                        mock_verify.return_value = UserContext(
                            user_id=sample_firm_personnel.id,
                            user_type="firm_personnel",
                            email=sample_firm_personnel.email,
                            permissions=["feedback:submit"]
                        )
                        
                        feedback_data = {
                            "request_id": request_id,
                            "is_prank": True,
                            "performance_rating": 1,
                            "comments": f"Prank call {i} - no emergency found",
                            "response_time_minutes": 10
                        }
                        
                        with patch('app.services.feedback.FeedbackService.submit_feedback') as mock_feedback:
                            mock_feedback_obj = AsyncMock()
                            mock_feedback_obj.id = uuid4()
                            mock_feedback_obj.request_id = uuid4(request_id)
                            mock_feedback_obj.is_prank = True
                            mock_feedback.return_value = mock_feedback_obj
                            
                            agent_headers = {"Authorization": "Bearer agent.token"}
                            response = client.post(
                                "/api/v1/feedback",
                                json=feedback_data,
                                headers=agent_headers
                            )
                            assert response.status_code == 201
        
        # Step 3: Check prank detection and fine calculation
        with patch('app.services.prank_detection.PrankDetectionService.calculate_user_fine') as mock_calculate_fine:
            mock_fine = AsyncMock()
            mock_fine.id = uuid4()
            mock_fine.user_id = sample_registered_user.id
            mock_fine.amount = 150.00  # $50 per prank
            mock_fine.prank_count = 3
            mock_fine.status = "pending"
            mock_calculate_fine.return_value = mock_fine
            
            # Simulate prank detection service running
            with patch('app.core.auth.verify_token') as mock_verify:
                mock_verify.return_value = UserContext(
                    user_id=uuid4(),
                    user_type="admin",
                    email="admin@panic.com",
                    permissions=["prank:manage"]
                )
                
                admin_headers = {"Authorization": "Bearer admin.token"}
                response = client.post(
                    f"/api/v1/admin/users/{sample_registered_user.id}/calculate-fine",
                    headers=admin_headers
                )
                assert response.status_code == 200
                
                fine_response = response.json()
                assert fine_response["amount"] == 150.00
                assert fine_response["prank_count"] == 3
                
                # Step 4: User pays fine
                payment_data = {
                    "fine_id": str(mock_fine.id),
                    "payment_method": "credit_card",
                    "payment_details": {
                        "card_number": "4111111111111111",
                        "expiry_month": 12,
                        "expiry_year": 2025,
                        "cvv": "123"
                    }
                }
                
                with patch('app.services.prank_detection.PrankDetectionService.process_fine_payment') as mock_pay_fine:
                    mock_pay_fine.return_value = {
                        "success": True,
                        "transaction_id": "fine_payment_123",
                        "amount": 150.00
                    }
                    
                    user_headers = {"Authorization": "Bearer user.token"}
                    response = client.post(
                        "/api/v1/fines/pay",
                        json=payment_data,
                        headers=user_headers
                    )
                    assert response.status_code == 200
                    
                    payment_response = response.json()
                    assert payment_response["success"] is True
                    assert payment_response["amount"] == 150.00


class TestMetricsAndReportingWorkflow:
    """Test complete metrics collection and reporting workflow"""
    
    @pytest.mark.asyncio
    async def test_complete_metrics_workflow(
        self, 
        client, 
        db_session, 
        sample_security_firm,
        mock_external_services
    ):
        """Test complete metrics collection from request to reporting"""
        
        # Step 1: Generate sample metrics data
        with patch('app.core.auth.verify_token') as mock_verify:
            mock_verify.return_value = UserContext(
                user_id=sample_security_firm.id,
                user_type="security_firm",
                email=sample_security_firm.email,
                permissions=["metrics:view"]
            )
            
            # Step 2: Get performance metrics
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
                    ],
                    "date_range": {
                        "from": "2024-01-01",
                        "to": "2024-01-31"
                    }
                }
                
                firm_headers = {"Authorization": "Bearer firm.token"}
                response = client.get(
                    "/api/v1/metrics/performance?from=2024-01-01&to=2024-01-31",
                    headers=firm_headers
                )
                assert response.status_code == 200
                
                metrics_response = response.json()
                assert metrics_response["total_requests"] == 100
                assert metrics_response["average_response_time"] == 12.5
                assert len(metrics_response["zone_metrics"]) == 2
                
                # Step 3: Generate detailed report
                with patch('app.services.metrics.MetricsService.generate_detailed_report') as mock_report:
                    mock_report.return_value = {
                        "report_id": str(uuid4()),
                        "generated_at": datetime.utcnow().isoformat(),
                        "summary": {
                            "total_requests": 100,
                            "successful_responses": 95,
                            "average_response_time": 12.5,
                            "customer_satisfaction": 4.2
                        },
                        "trends": {
                            "response_time_trend": "improving",
                            "request_volume_trend": "stable",
                            "satisfaction_trend": "improving"
                        },
                        "recommendations": [
                            "Consider adding more field agents in Brooklyn area",
                            "Response times in Manhattan are excellent",
                            "Customer satisfaction is above industry average"
                        ]
                    }
                    
                    response = client.post(
                        "/api/v1/metrics/generate-report",
                        json={"date_range": {"from": "2024-01-01", "to": "2024-01-31"}},
                        headers=firm_headers
                    )
                    assert response.status_code == 200
                    
                    report_response = response.json()
                    assert "report_id" in report_response
                    assert report_response["summary"]["total_requests"] == 100
                    assert len(report_response["recommendations"]) == 3