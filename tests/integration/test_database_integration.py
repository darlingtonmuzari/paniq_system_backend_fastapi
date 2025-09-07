"""
Database Integration Tests
Tests database operations, transactions, and data integrity
"""
import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from geoalchemy2 import WKTElement
from geoalchemy2.shape import to_shape

from app.models.security_firm import SecurityFirm, CoverageArea, FirmPersonnel, Team
from app.models.user import RegisteredUser, UserGroup, GroupMobileNumber
from app.models.subscription import SubscriptionProduct, StoredSubscription
from app.models.emergency import PanicRequest, ServiceProvider, RequestFeedback
from app.models.metrics import ResponseTimeMetric, BusinessMetric


class TestDatabaseSchema:
    """Test database schema and constraints"""
    
    @pytest.mark.asyncio
    async def test_security_firm_constraints(self, db_session):
        """Test security firm table constraints"""
        # Test unique constraints
        firm1 = SecurityFirm(
            name="Test Firm 1",
            registration_number="TF001",
            email="test1@firm.com",
            phone="+1234567890",
            address="123 Test St"
        )
        db_session.add(firm1)
        await db_session.commit()
        
        # Try to create another firm with same registration number
        firm2 = SecurityFirm(
            name="Test Firm 2",
            registration_number="TF001",  # Duplicate
            email="test2@firm.com",
            phone="+1234567891",
            address="456 Test Ave"
        )
        db_session.add(firm2)
        
        with pytest.raises(IntegrityError):
            await db_session.commit()
        
        await db_session.rollback()
        
        # Try to create another firm with same email
        firm3 = SecurityFirm(
            name="Test Firm 3",
            registration_number="TF003",
            email="test1@firm.com",  # Duplicate
            phone="+1234567892",
            address="789 Test Blvd"
        )
        db_session.add(firm3)
        
        with pytest.raises(IntegrityError):
            await db_session.commit()
    
    @pytest.mark.asyncio
    async def test_user_constraints(self, db_session):
        """Test registered user table constraints"""
        # Test unique constraints
        user1 = RegisteredUser(
            email="user1@test.com",
            phone="+1987654321",
            first_name="User",
            last_name="One",
            password_hash="hash1"
        )
        db_session.add(user1)
        await db_session.commit()
        
        # Try to create another user with same email
        user2 = RegisteredUser(
            email="user1@test.com",  # Duplicate
            phone="+1987654322",
            first_name="User",
            last_name="Two",
            password_hash="hash2"
        )
        db_session.add(user2)
        
        with pytest.raises(IntegrityError):
            await db_session.commit()
        
        await db_session.rollback()
        
        # Try to create another user with same phone
        user3 = RegisteredUser(
            email="user3@test.com",
            phone="+1987654321",  # Duplicate
            first_name="User",
            last_name="Three",
            password_hash="hash3"
        )
        db_session.add(user3)
        
        with pytest.raises(IntegrityError):
            await db_session.commit()
    
    @pytest.mark.asyncio
    async def test_foreign_key_constraints(self, db_session, sample_security_firm):
        """Test foreign key constraints"""
        # Test coverage area foreign key
        coverage = CoverageArea(
            firm_id=uuid4(),  # Non-existent firm
            name="Invalid Coverage",
            boundary=WKTElement("POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))", srid=4326)
        )
        db_session.add(coverage)
        
        with pytest.raises(IntegrityError):
            await db_session.commit()
        
        await db_session.rollback()
        
        # Test valid foreign key
        valid_coverage = CoverageArea(
            firm_id=sample_security_firm.id,
            name="Valid Coverage",
            boundary=WKTElement("POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))", srid=4326)
        )
        db_session.add(valid_coverage)
        await db_session.commit()
        
        assert valid_coverage.id is not None
    
    @pytest.mark.asyncio
    async def test_check_constraints(self, db_session, sample_user_group):
        """Test check constraints"""
        # Test invalid user type in group mobile number
        invalid_mobile = GroupMobileNumber(
            group_id=sample_user_group.id,
            phone_number="+1555123456",
            user_type="invalid_type",  # Should fail check constraint
            is_verified=True
        )
        db_session.add(invalid_mobile)
        
        with pytest.raises(IntegrityError):
            await db_session.commit()
        
        await db_session.rollback()
        
        # Test valid user type
        valid_mobile = GroupMobileNumber(
            group_id=sample_user_group.id,
            phone_number="+1555123456",
            user_type="individual",  # Valid type
            is_verified=True
        )
        db_session.add(valid_mobile)
        await db_session.commit()
        
        assert valid_mobile.id is not None


class TestGeospatialOperations:
    """Test PostGIS geospatial operations"""
    
    @pytest.mark.asyncio
    async def test_point_in_polygon_query(self, db_session, sample_coverage_area):
        """Test point-in-polygon queries"""
        # Test point inside coverage area (Manhattan)
        point_inside = WKTElement("POINT(-73.9857 40.7484)", srid=4326)  # Times Square
        
        result = await db_session.execute(
            text("""
                SELECT ST_Contains(boundary, :point) as contains
                FROM coverage_areas 
                WHERE id = :area_id
            """),
            {"point": str(point_inside), "area_id": sample_coverage_area.id}
        )
        
        row = result.fetchone()
        assert row.contains is True
        
        # Test point outside coverage area
        point_outside = WKTElement("POINT(-118.2437 34.0522)", srid=4326)  # Los Angeles
        
        result = await db_session.execute(
            text("""
                SELECT ST_Contains(boundary, :point) as contains
                FROM coverage_areas 
                WHERE id = :area_id
            """),
            {"point": str(point_outside), "area_id": sample_coverage_area.id}
        )
        
        row = result.fetchone()
        assert row.contains is False
    
    @pytest.mark.asyncio
    async def test_distance_calculations(self, db_session):
        """Test distance calculations between points"""
        # Create two service providers at known locations
        provider1 = ServiceProvider(
            firm_id=uuid4(),
            name="Provider 1",
            service_type="ambulance",
            email="provider1@test.com",
            phone="+1555111111",
            address="Times Square, NY",
            location=WKTElement("POINT(-73.9857 40.7484)", srid=4326),  # Times Square
            is_active=True
        )
        
        provider2 = ServiceProvider(
            firm_id=uuid4(),
            name="Provider 2",
            service_type="ambulance",
            email="provider2@test.com",
            phone="+1555222222",
            address="Central Park, NY",
            location=WKTElement("POINT(-73.9654 40.7829)", srid=4326),  # Central Park
            is_active=True
        )
        
        db_session.add_all([provider1, provider2])
        await db_session.commit()
        
        # Calculate distance between providers
        result = await db_session.execute(
            text("""
                SELECT ST_Distance(
                    ST_Transform(p1.location, 3857),
                    ST_Transform(p2.location, 3857)
                ) as distance_meters
                FROM service_providers p1, service_providers p2
                WHERE p1.id = :id1 AND p2.id = :id2
            """),
            {"id1": provider1.id, "id2": provider2.id}
        )
        
        row = result.fetchone()
        # Distance should be approximately 3.8 km (3800 meters)
        assert 3000 < row.distance_meters < 5000
    
    @pytest.mark.asyncio
    async def test_nearest_provider_query(self, db_session):
        """Test finding nearest service providers"""
        # Create multiple providers
        providers = []
        locations = [
            ("POINT(-73.9857 40.7484)", "Times Square"),  # Closest
            ("POINT(-73.9654 40.7829)", "Central Park"),  # Medium
            ("POINT(-74.0060 40.7128)", "Wall Street")    # Farthest
        ]
        
        for i, (location, name) in enumerate(locations):
            provider = ServiceProvider(
                firm_id=uuid4(),
                name=f"Provider {name}",
                service_type="security",
                email=f"provider{i}@test.com",
                phone=f"+155511{i:04d}",
                address=name,
                location=WKTElement(location, srid=4326),
                is_active=True
            )
            providers.append(provider)
        
        db_session.add_all(providers)
        await db_session.commit()
        
        # Find nearest provider to a specific point (close to Times Square)
        search_point = WKTElement("POINT(-73.9850 40.7490)", srid=4326)
        
        result = await db_session.execute(
            text("""
                SELECT name, 
                       ST_Distance(
                           ST_Transform(location, 3857),
                           ST_Transform(:search_point, 3857)
                       ) as distance_meters
                FROM service_providers
                WHERE service_type = 'security' AND is_active = true
                ORDER BY location <-> :search_point
                LIMIT 1
            """),
            {"search_point": str(search_point)}
        )
        
        row = result.fetchone()
        assert "Times Square" in row.name
        assert row.distance_meters < 200  # Should be very close
    
    @pytest.mark.asyncio
    async def test_spatial_indexes(self, db_session):
        """Test that spatial indexes are working"""
        # Check if spatial indexes exist
        result = await db_session.execute(
            text("""
                SELECT indexname, tablename 
                FROM pg_indexes 
                WHERE indexname LIKE '%gist%' 
                AND (tablename = 'coverage_areas' 
                     OR tablename = 'user_groups' 
                     OR tablename = 'panic_requests'
                     OR tablename = 'service_providers')
            """)
        )
        
        indexes = result.fetchall()
        assert len(indexes) >= 4  # Should have spatial indexes on all geospatial tables


class TestTransactionIntegrity:
    """Test database transaction integrity"""
    
    @pytest.mark.asyncio
    async def test_subscription_application_transaction(
        self, 
        db_session, 
        sample_registered_user, 
        sample_subscription_product
    ):
        """Test subscription application as atomic transaction"""
        # Create stored subscription
        stored_subscription = StoredSubscription(
            user_id=sample_registered_user.id,
            product_id=sample_subscription_product.id,
            is_applied=False
        )
        db_session.add(stored_subscription)
        await db_session.commit()
        
        # Create user group
        user_group = UserGroup(
            user_id=sample_registered_user.id,
            name="Transaction Test Group",
            address="123 Transaction St",
            location=WKTElement("POINT(-73.9857 40.7484)", srid=4326)
        )
        db_session.add(user_group)
        await db_session.commit()
        
        # Simulate subscription application transaction
        try:
            # Update subscription as applied
            stored_subscription.is_applied = True
            stored_subscription.applied_to_group_id = user_group.id
            stored_subscription.applied_at = datetime.utcnow()
            
            # Update group with subscription details
            user_group.subscription_id = stored_subscription.id
            user_group.subscription_expires_at = datetime.utcnow() + timedelta(days=30)
            
            await db_session.commit()
            
            # Verify both updates were applied
            await db_session.refresh(stored_subscription)
            await db_session.refresh(user_group)
            
            assert stored_subscription.is_applied is True
            assert stored_subscription.applied_to_group_id == user_group.id
            assert user_group.subscription_id == stored_subscription.id
            assert user_group.subscription_expires_at is not None
            
        except Exception:
            await db_session.rollback()
            raise
    
    @pytest.mark.asyncio
    async def test_panic_request_creation_transaction(
        self, 
        db_session, 
        sample_user_group, 
        sample_group_mobile_number
    ):
        """Test panic request creation with related data"""
        # Create panic request with metrics
        panic_request = PanicRequest(
            group_id=sample_user_group.id,
            requester_phone=sample_group_mobile_number.phone_number,
            service_type="security",
            location=WKTElement("POINT(-73.9857 40.7484)", srid=4326),
            address="Emergency Location",
            description="Test emergency",
            status="pending"
        )
        
        # Create initial metric
        metric = ResponseTimeMetric(
            request_id=panic_request.id,
            firm_id=uuid4(),
            zone_name="Manhattan",
            service_type="security",
            request_timestamp=datetime.utcnow(),
            response_time_seconds=None  # Will be updated later
        )
        
        try:
            db_session.add(panic_request)
            await db_session.flush()  # Get the request ID
            
            metric.request_id = panic_request.id
            db_session.add(metric)
            
            await db_session.commit()
            
            # Verify both records were created
            assert panic_request.id is not None
            assert metric.id is not None
            assert metric.request_id == panic_request.id
            
        except Exception:
            await db_session.rollback()
            raise
    
    @pytest.mark.asyncio
    async def test_rollback_on_constraint_violation(self, db_session, sample_security_firm):
        """Test transaction rollback on constraint violations"""
        # Start a transaction with multiple operations
        try:
            # Create valid coverage area
            coverage1 = CoverageArea(
                firm_id=sample_security_firm.id,
                name="Valid Coverage 1",
                boundary=WKTElement("POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))", srid=4326)
            )
            db_session.add(coverage1)
            
            # Create invalid coverage area (duplicate name for same firm)
            coverage2 = CoverageArea(
                firm_id=sample_security_firm.id,
                name="Valid Coverage 1",  # Duplicate name
                boundary=WKTElement("POLYGON((2 2, 3 2, 3 3, 2 3, 2 2))", srid=4326)
            )
            db_session.add(coverage2)
            
            # This should fail and rollback both operations
            await db_session.commit()
            
        except IntegrityError:
            await db_session.rollback()
            
            # Verify that neither coverage area was created
            result = await db_session.execute(
                text("SELECT COUNT(*) as count FROM coverage_areas WHERE firm_id = :firm_id"),
                {"firm_id": sample_security_firm.id}
            )
            count = result.fetchone().count
            assert count == 0  # No coverage areas should exist


class TestDataIntegrity:
    """Test data integrity and business rules"""
    
    @pytest.mark.asyncio
    async def test_subscription_expiry_logic(
        self, 
        db_session, 
        sample_user_group, 
        sample_stored_subscription
    ):
        """Test subscription expiry business logic"""
        # Apply subscription to group
        sample_stored_subscription.is_applied = True
        sample_stored_subscription.applied_to_group_id = sample_user_group.id
        sample_stored_subscription.applied_at = datetime.utcnow()
        
        # Set group subscription expiry
        sample_user_group.subscription_id = sample_stored_subscription.id
        sample_user_group.subscription_expires_at = datetime.utcnow() + timedelta(days=30)
        
        await db_session.commit()
        
        # Query for active subscriptions
        result = await db_session.execute(
            text("""
                SELECT ug.id, ug.name, ug.subscription_expires_at,
                       CASE 
                           WHEN ug.subscription_expires_at > NOW() THEN true
                           ELSE false
                       END as is_active
                FROM user_groups ug
                WHERE ug.subscription_id IS NOT NULL
            """)
        )
        
        row = result.fetchone()
        assert row.is_active is True
        
        # Test expired subscription
        sample_user_group.subscription_expires_at = datetime.utcnow() - timedelta(days=1)
        await db_session.commit()
        
        result = await db_session.execute(
            text("""
                SELECT CASE 
                           WHEN ug.subscription_expires_at > NOW() THEN true
                           ELSE false
                       END as is_active
                FROM user_groups ug
                WHERE ug.id = :group_id
            """),
            {"group_id": sample_user_group.id}
        )
        
        row = result.fetchone()
        assert row.is_active is False
    
    @pytest.mark.asyncio
    async def test_prank_detection_accumulation(self, db_session, sample_registered_user):
        """Test prank flag accumulation logic"""
        # Create multiple panic requests and feedback
        requests = []
        for i in range(3):
            # Create group for each request
            group = UserGroup(
                user_id=sample_registered_user.id,
                name=f"Test Group {i}",
                address=f"Address {i}",
                location=WKTElement("POINT(-73.9857 40.7484)", srid=4326)
            )
            db_session.add(group)
            await db_session.flush()
            
            # Create panic request
            request = PanicRequest(
                group_id=group.id,
                requester_phone=f"+155512345{i}",
                service_type="security",
                location=WKTElement("POINT(-73.9857 40.7484)", srid=4326),
                address=f"Emergency {i}",
                status="completed"
            )
            db_session.add(request)
            await db_session.flush()
            
            # Create feedback marking as prank
            feedback = RequestFeedback(
                request_id=request.id,
                team_member_id=uuid4(),
                is_prank=True,
                performance_rating=1,
                comments=f"Prank call {i}"
            )
            db_session.add(feedback)
            requests.append(request)
        
        await db_session.commit()
        
        # Query prank count for user
        result = await db_session.execute(
            text("""
                SELECT COUNT(*) as prank_count
                FROM request_feedback rf
                JOIN panic_requests pr ON rf.request_id = pr.id
                JOIN user_groups ug ON pr.group_id = ug.id
                WHERE ug.user_id = :user_id AND rf.is_prank = true
            """),
            {"user_id": sample_registered_user.id}
        )
        
        prank_count = result.fetchone().prank_count
        assert prank_count == 3
        
        # Update user prank flags
        sample_registered_user.prank_flags = prank_count
        await db_session.commit()
        
        assert sample_registered_user.prank_flags == 3
    
    @pytest.mark.asyncio
    async def test_response_time_calculations(self, db_session):
        """Test response time calculation accuracy"""
        base_time = datetime.utcnow()
        
        # Create panic request with timestamps
        request = PanicRequest(
            group_id=uuid4(),
            requester_phone="+1555123456",
            service_type="ambulance",
            location=WKTElement("POINT(-73.9857 40.7484)", srid=4326),
            address="Test Emergency",
            status="completed",
            created_at=base_time,
            accepted_at=base_time + timedelta(minutes=2),
            arrived_at=base_time + timedelta(minutes=15),
            completed_at=base_time + timedelta(minutes=25)
        )
        db_session.add(request)
        await db_session.commit()
        
        # Calculate response times using SQL
        result = await db_session.execute(
            text("""
                SELECT 
                    EXTRACT(EPOCH FROM (accepted_at - created_at))/60 as acceptance_time_minutes,
                    EXTRACT(EPOCH FROM (arrived_at - created_at))/60 as response_time_minutes,
                    EXTRACT(EPOCH FROM (completed_at - created_at))/60 as total_time_minutes
                FROM panic_requests
                WHERE id = :request_id
            """),
            {"request_id": request.id}
        )
        
        row = result.fetchone()
        assert abs(row.acceptance_time_minutes - 2.0) < 0.1
        assert abs(row.response_time_minutes - 15.0) < 0.1
        assert abs(row.total_time_minutes - 25.0) < 0.1


class TestPerformanceQueries:
    """Test database query performance"""
    
    @pytest.mark.asyncio
    async def test_coverage_query_performance(self, db_session, sample_security_firm):
        """Test performance of coverage area queries"""
        # Create multiple coverage areas
        coverage_areas = []
        for i in range(10):
            coverage = CoverageArea(
                firm_id=sample_security_firm.id,
                name=f"Coverage Area {i}",
                boundary=WKTElement(
                    f"POLYGON(({i} {i}, {i+1} {i}, {i+1} {i+1}, {i} {i+1}, {i} {i}))",
                    srid=4326
                )
            )
            coverage_areas.append(coverage)
        
        db_session.add_all(coverage_areas)
        await db_session.commit()
        
        # Test point-in-polygon query performance
        test_point = WKTElement("POINT(5.5 5.5)", srid=4326)
        
        import time
        start_time = time.time()
        
        result = await db_session.execute(
            text("""
                SELECT ca.id, ca.name
                FROM coverage_areas ca
                WHERE ST_Contains(ca.boundary, :point)
                AND ca.firm_id = :firm_id
            """),
            {"point": str(test_point), "firm_id": sample_security_firm.id}
        )
        
        end_time = time.time()
        query_time = end_time - start_time
        
        rows = result.fetchall()
        assert len(rows) == 1  # Should find one containing area
        assert query_time < 0.1  # Should be fast with spatial index
    
    @pytest.mark.asyncio
    async def test_metrics_aggregation_performance(self, db_session):
        """Test performance of metrics aggregation queries"""
        # Create multiple response time metrics
        base_time = datetime.utcnow() - timedelta(days=30)
        firm_id = uuid4()
        
        metrics = []
        for i in range(100):
            metric = ResponseTimeMetric(
                request_id=uuid4(),
                firm_id=firm_id,
                zone_name=f"Zone {i % 5}",  # 5 different zones
                service_type=["security", "ambulance", "fire"][i % 3],  # 3 service types
                request_timestamp=base_time + timedelta(hours=i),
                response_time_seconds=300 + (i % 600)  # 5-15 minutes
            )
            metrics.append(metric)
        
        db_session.add_all(metrics)
        await db_session.commit()
        
        # Test aggregation query performance
        import time
        start_time = time.time()
        
        result = await db_session.execute(
            text("""
                SELECT 
                    zone_name,
                    service_type,
                    COUNT(*) as request_count,
                    AVG(response_time_seconds) as avg_response_time,
                    MIN(response_time_seconds) as min_response_time,
                    MAX(response_time_seconds) as max_response_time
                FROM response_time_metrics
                WHERE firm_id = :firm_id
                AND request_timestamp >= :start_date
                GROUP BY zone_name, service_type
                ORDER BY zone_name, service_type
            """),
            {
                "firm_id": firm_id,
                "start_date": base_time
            }
        )
        
        end_time = time.time()
        query_time = end_time - start_time
        
        rows = result.fetchall()
        assert len(rows) == 15  # 5 zones × 3 service types
        assert query_time < 0.5  # Should be reasonably fast
        
        # Verify aggregation accuracy
        for row in rows:
            assert row.request_count > 0
            assert row.avg_response_time >= row.min_response_time
            assert row.avg_response_time <= row.max_response_time