"""
Integration tests for prank detection and fining system
"""
import pytest
from decimal import Decimal
from datetime import datetime
from uuid import uuid4
from unittest.mock import patch

from app.services.feedback import FeedbackService
from app.services.prank_detection import PrankDetectionService
from app.models.user import RegisteredUser, UserGroup, UserFine
from app.models.emergency import PanicRequest, RequestFeedback
from app.models.security_firm import SecurityFirm, FirmPersonnel


@pytest.fixture
async def test_security_firm(db_session):
    """Create test security firm"""
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
    return firm


@pytest.fixture
async def test_team_member(db_session, test_security_firm):
    """Create test team member"""
    member = FirmPersonnel(
        firm_id=test_security_firm.id,
        email="member@test.com",
        phone="+1234567891",
        first_name="Team",
        last_name="Member",
        role="field_agent",
        is_active=True
    )
    db_session.add(member)
    await db_session.commit()
    await db_session.refresh(member)
    return member


@pytest.fixture
async def test_user_with_group(db_session):
    """Create test user with group"""
    user = RegisteredUser(
        email="user@example.com",
        phone="+1234567892",
        first_name="Test",
        last_name="User",
        prank_flags=0,
        total_fines=Decimal("0.00"),
        is_suspended=False
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    # Create user group
    group = UserGroup(
        user_id=user.id,
        name="Test Group",
        address="123 User St",
        location="POINT(-74.006 40.7128)"  # NYC coordinates
    )
    db_session.add(group)
    await db_session.commit()
    await db_session.refresh(group)
    
    return user, group


@pytest.fixture
async def test_panic_request(db_session, test_user_with_group):
    """Create test panic request"""
    user, group = test_user_with_group
    
    request = PanicRequest(
        group_id=group.id,
        requester_phone=user.phone,
        service_type="security",
        location="POINT(-74.006 40.7128)",
        address="123 Emergency St",
        description="Test emergency",
        status="completed"
    )
    db_session.add(request)
    await db_session.commit()
    await db_session.refresh(request)
    return request


class TestPrankDetectionIntegration:
    """Integration tests for prank detection system"""
    
    async def test_complete_prank_detection_workflow(
        self, 
        db_session, 
        test_user_with_group, 
        test_panic_request, 
        test_team_member
    ):
        """Test complete workflow from prank flag to fine creation"""
        user, group = test_user_with_group
        
        # Initialize services
        feedback_service = FeedbackService(db_session)
        prank_service = PrankDetectionService(db_session)
        
        # Step 1: Submit feedback flagging request as prank
        feedback = await feedback_service.submit_feedback(
            request_id=test_panic_request.id,
            team_member_id=test_team_member.id,
            is_prank=True,
            performance_rating=1,
            comments="This was clearly a prank call"
        )
        
        assert feedback.is_prank is True
        
        # Refresh user to see updated prank flags
        await db_session.refresh(user)
        assert user.prank_flags == 1
        
        # Step 2: Submit more prank feedback to reach fine threshold
        for i in range(2):  # Add 2 more pranks to reach threshold of 3
            # Create additional panic requests
            request = PanicRequest(
                group_id=group.id,
                requester_phone=user.phone,
                service_type="security",
                location="POINT(-74.006 40.7128)",
                address=f"123 Emergency St #{i+2}",
                description=f"Test emergency {i+2}",
                status="completed"
            )
            db_session.add(request)
            await db_session.commit()
            await db_session.refresh(request)
            
            # Submit prank feedback
            await feedback_service.submit_feedback(
                request_id=request.id,
                team_member_id=test_team_member.id,
                is_prank=True,
                performance_rating=1,
                comments=f"Prank call #{i+2}"
            )
        
        # Refresh user
        await db_session.refresh(user)
        assert user.prank_flags == 3
        
        # Step 3: Verify automatic fine was created
        user_fines = await prank_service.get_user_fines(user.id, include_paid=False)
        assert len(user_fines) == 1
        assert user_fines[0].amount == Decimal("50.00")  # Base fine amount
        assert user_fines[0].is_paid is False
        
        # Step 4: Verify user's total fines updated
        await db_session.refresh(user)
        assert user.total_fines == Decimal("50.00")
        
        # Step 5: Process fine payment
        with patch('app.services.prank_detection.PrankDetectionService._process_payment_gateway', return_value=True):
            paid_fine = await prank_service.process_fine_payment(
                fine_id=user_fines[0].id,
                payment_method="card",
                payment_reference="txn_123"
            )
        
        assert paid_fine.is_paid is True
        assert paid_fine.paid_at is not None
    
    async def test_progressive_fine_calculation(
        self, 
        db_session, 
        test_user_with_group, 
        test_team_member
    ):
        """Test progressive fine calculation as prank flags increase"""
        user, group = test_user_with_group
        
        feedback_service = FeedbackService(db_session)
        prank_service = PrankDetectionService(db_session)
        
        # Create multiple prank requests and track fine progression
        expected_fines = [
            (3, Decimal("50.00")),   # Base fine
            (4, Decimal("75.00")),   # 50 * 1.5^1
            (5, Decimal("112.50")),  # 50 * 1.5^2
        ]
        
        for prank_count, expected_amount in expected_fines:
            # Add prank flags to reach target count
            while user.prank_flags < prank_count:
                # Create panic request
                request = PanicRequest(
                    group_id=group.id,
                    requester_phone=user.phone,
                    service_type="security",
                    location="POINT(-74.006 40.7128)",
                    address=f"123 Emergency St #{user.prank_flags + 1}",
                    description=f"Test emergency {user.prank_flags + 1}",
                    status="completed"
                )
                db_session.add(request)
                await db_session.commit()
                await db_session.refresh(request)
                
                # Submit prank feedback
                await feedback_service.submit_feedback(
                    request_id=request.id,
                    team_member_id=test_team_member.id,
                    is_prank=True,
                    performance_rating=1,
                    comments=f"Prank call #{user.prank_flags + 1}"
                )
                
                await db_session.refresh(user)
            
            # Verify fine amount for current prank count
            user_fines = await prank_service.get_user_fines(user.id, include_paid=False)
            latest_fine = max(user_fines, key=lambda f: f.created_at)
            assert latest_fine.amount == expected_amount
    
    async def test_account_suspension_workflow(
        self, 
        db_session, 
        test_user_with_group, 
        test_team_member
    ):
        """Test account suspension for unpaid fines"""
        user, group = test_user_with_group
        
        feedback_service = FeedbackService(db_session)
        prank_service = PrankDetectionService(db_session)
        
        # Create enough pranks to trigger suspension threshold
        for i in range(5):  # Reach suspension threshold
            request = PanicRequest(
                group_id=group.id,
                requester_phone=user.phone,
                service_type="security",
                location="POINT(-74.006 40.7128)",
                address=f"123 Emergency St #{i+1}",
                description=f"Test emergency {i+1}",
                status="completed"
            )
            db_session.add(request)
            await db_session.commit()
            await db_session.refresh(request)
            
            await feedback_service.submit_feedback(
                request_id=request.id,
                team_member_id=test_team_member.id,
                is_prank=True,
                performance_rating=1,
                comments=f"Prank call #{i+1}"
            )
        
        # Refresh user
        await db_session.refresh(user)
        assert user.prank_flags == 5
        assert user.is_suspended is True  # Should be auto-suspended due to unpaid fines
        
        # Verify unpaid fines exist
        unpaid_fines = await prank_service.get_user_fines(user.id, include_paid=False)
        assert len(unpaid_fines) > 0
        
        # Pay all fines
        with patch('app.services.prank_detection.PrankDetectionService._process_payment_gateway', return_value=True):
            for fine in unpaid_fines:
                await prank_service.process_fine_payment(
                    fine_id=fine.id,
                    payment_method="card",
                    payment_reference=f"txn_{fine.id}"
                )
        
        # Refresh user - should be unsuspended after paying last fine
        await db_session.refresh(user)
        assert user.is_suspended is False
    
    async def test_permanent_ban_workflow(
        self, 
        db_session, 
        test_user_with_group, 
        test_team_member
    ):
        """Test permanent ban for repeat offenders"""
        user, group = test_user_with_group
        
        feedback_service = FeedbackService(db_session)
        prank_service = PrankDetectionService(db_session)
        
        # Create enough pranks to trigger permanent ban
        for i in range(10):  # Reach ban threshold
            request = PanicRequest(
                group_id=group.id,
                requester_phone=user.phone,
                service_type="security",
                location="POINT(-74.006 40.7128)",
                address=f"123 Emergency St #{i+1}",
                description=f"Test emergency {i+1}",
                status="completed"
            )
            db_session.add(request)
            await db_session.commit()
            await db_session.refresh(request)
            
            await feedback_service.submit_feedback(
                request_id=request.id,
                team_member_id=test_team_member.id,
                is_prank=True,
                performance_rating=1,
                comments=f"Prank call #{i+1}"
            )
        
        # Refresh user
        await db_session.refresh(user)
        assert user.prank_flags == 10
        assert user.is_suspended is True  # Should be permanently banned (suspended)
        
        # Verify ban was applied
        tracking_info = await prank_service.track_prank_accumulation(user.id)
        assert tracking_info["should_ban"] is True
        assert tracking_info["days_until_ban"] == 0
    
    async def test_feedback_update_prank_flag_changes(
        self, 
        db_session, 
        test_user_with_group, 
        test_panic_request, 
        test_team_member
    ):
        """Test prank flag changes when feedback is updated"""
        user, group = test_user_with_group
        
        feedback_service = FeedbackService(db_session)
        prank_service = PrankDetectionService(db_session)
        
        # Step 1: Submit non-prank feedback
        feedback = await feedback_service.submit_feedback(
            request_id=test_panic_request.id,
            team_member_id=test_team_member.id,
            is_prank=False,
            performance_rating=5,
            comments="Legitimate emergency"
        )
        
        await db_session.refresh(user)
        assert user.prank_flags == 0
        
        # Step 2: Update feedback to mark as prank
        updated_feedback = await feedback_service.update_feedback(
            feedback_id=feedback.id,
            team_member_id=test_team_member.id,
            is_prank=True,
            performance_rating=1,
            comments="Actually was a prank"
        )
        
        await db_session.refresh(user)
        assert user.prank_flags == 1
        
        # Step 3: Update feedback back to non-prank
        await feedback_service.update_feedback(
            feedback_id=feedback.id,
            team_member_id=test_team_member.id,
            is_prank=False,
            performance_rating=5,
            comments="Confirmed legitimate emergency"
        )
        
        await db_session.refresh(user)
        assert user.prank_flags == 0
    
    async def test_fine_statistics_accuracy(
        self, 
        db_session, 
        test_user_with_group, 
        test_team_member
    ):
        """Test fine statistics calculation accuracy"""
        user, group = test_user_with_group
        
        feedback_service = FeedbackService(db_session)
        prank_service = PrankDetectionService(db_session)
        
        # Create multiple users with different fine scenarios
        users_data = []
        for i in range(3):
            test_user = RegisteredUser(
                email=f"user{i}@example.com",
                phone=f"+123456789{i}",
                first_name=f"User{i}",
                last_name="Test",
                prank_flags=0,
                total_fines=Decimal("0.00"),
                is_suspended=False
            )
            db_session.add(test_user)
            await db_session.commit()
            await db_session.refresh(test_user)
            
            test_group = UserGroup(
                user_id=test_user.id,
                name=f"Test Group {i}",
                address=f"123 User St {i}",
                location="POINT(-74.006 40.7128)"
            )
            db_session.add(test_group)
            await db_session.commit()
            await db_session.refresh(test_group)
            
            users_data.append((test_user, test_group))
        
        # Create different fine scenarios
        total_expected_fines = 0
        total_expected_amount = Decimal("0.00")
        paid_expected_fines = 0
        paid_expected_amount = Decimal("0.00")
        
        for i, (test_user, test_group) in enumerate(users_data):
            # Create 3-5 pranks per user
            prank_count = 3 + i
            for j in range(prank_count):
                request = PanicRequest(
                    group_id=test_group.id,
                    requester_phone=test_user.phone,
                    service_type="security",
                    location="POINT(-74.006 40.7128)",
                    address=f"123 Emergency St {i}-{j}",
                    description=f"Test emergency {i}-{j}",
                    status="completed"
                )
                db_session.add(request)
                await db_session.commit()
                await db_session.refresh(request)
                
                await feedback_service.submit_feedback(
                    request_id=request.id,
                    team_member_id=test_team_member.id,
                    is_prank=True,
                    performance_rating=1,
                    comments=f"Prank call {i}-{j}"
                )
            
            # Get user's fines
            user_fines = await prank_service.get_user_fines(test_user.id, include_paid=True)
            total_expected_fines += len(user_fines)
            
            for fine in user_fines:
                total_expected_amount += fine.amount
                
                # Pay some fines (pay fines for even-indexed users)
                if i % 2 == 0:
                    with patch('app.services.prank_detection.PrankDetectionService._process_payment_gateway', return_value=True):
                        await prank_service.process_fine_payment(
                            fine_id=fine.id,
                            payment_method="card",
                            payment_reference=f"txn_{fine.id}"
                        )
                    paid_expected_fines += 1
                    paid_expected_amount += fine.amount
        
        # Get statistics and verify accuracy
        stats = await prank_service.get_fine_statistics()
        
        assert stats["total_fines"] == total_expected_fines
        assert Decimal(str(stats["total_amount"])) == total_expected_amount
        assert stats["paid_fines"] == paid_expected_fines
        assert Decimal(str(stats["paid_amount"])) == paid_expected_amount
        assert stats["unpaid_fines"] == total_expected_fines - paid_expected_fines
        assert Decimal(str(stats["unpaid_amount"])) == total_expected_amount - paid_expected_amount
        
        expected_payment_rate = (paid_expected_fines / total_expected_fines * 100) if total_expected_fines > 0 else 0
        assert abs(stats["payment_rate_percentage"] - expected_payment_rate) < 0.01  # Allow small floating point differences
    
    async def test_concurrent_prank_flag_updates(
        self, 
        db_session, 
        test_user_with_group, 
        test_team_member
    ):
        """Test handling of concurrent prank flag updates"""
        user, group = test_user_with_group
        
        feedback_service = FeedbackService(db_session)
        prank_service = PrankDetectionService(db_session)
        
        # Create multiple panic requests
        requests = []
        for i in range(3):
            request = PanicRequest(
                group_id=group.id,
                requester_phone=user.phone,
                service_type="security",
                location="POINT(-74.006 40.7128)",
                address=f"123 Emergency St #{i+1}",
                description=f"Test emergency {i+1}",
                status="completed"
            )
            db_session.add(request)
            requests.append(request)
        
        await db_session.commit()
        
        # Submit feedback for all requests simultaneously
        import asyncio
        feedback_tasks = []
        for i, request in enumerate(requests):
            task = feedback_service.submit_feedback(
                request_id=request.id,
                team_member_id=test_team_member.id,
                is_prank=True,
                performance_rating=1,
                comments=f"Concurrent prank call #{i+1}"
            )
            feedback_tasks.append(task)
        
        # Execute all feedback submissions concurrently
        await asyncio.gather(*feedback_tasks)
        
        # Verify final state
        await db_session.refresh(user)
        assert user.prank_flags == 3
        
        # Verify fine was created
        user_fines = await prank_service.get_user_fines(user.id, include_paid=False)
        assert len(user_fines) == 1  # Should only create one fine despite concurrent updates