"""
Shared fixtures for integration tests
"""
import pytest
import asyncio
import asyncpg
from typing import AsyncGenerator
from uuid import uuid4
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import get_db, Base
from app.core.config import settings
from app.models.security_firm import SecurityFirm, CoverageArea, FirmPersonnel, Team
from app.models.user import RegisteredUser, UserGroup, GroupMobileNumber
from app.models.subscription import SubscriptionProduct, StoredSubscription
from app.models.emergency import PanicRequest, ServiceProvider, RequestFeedback


# Test database URL
TEST_DATABASE_URL = settings.DATABASE_URL.replace("/panic_system", "/panic_system_test")


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    # Create test database if it doesn't exist
    try:
        conn = await asyncpg.connect(settings.database_url)
        await conn.execute("CREATE DATABASE panic_system_test")
        await conn.close()
    except asyncpg.DuplicateDatabaseError:
        pass
    except Exception:
        # Database might already exist or we don't have permissions
        pass
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a database session for testing"""
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def client(db_session):
    """Create test client with database override"""
    def override_get_db():
        return db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
async def sample_security_firm(db_session) -> SecurityFirm:
    """Create a sample security firm"""
    firm = SecurityFirm(
        name="Test Security Firm",
        registration_number="TSF001",
        email="test@security.com",
        phone="+1234567890",
        address="123 Security St, Test City",
        verification_status="approved",
        credit_balance=1000
    )
    db_session.add(firm)
    await db_session.commit()
    await db_session.refresh(firm)
    return firm


@pytest.fixture
async def sample_coverage_area(db_session, sample_security_firm) -> CoverageArea:
    """Create a sample coverage area"""
    from geoalchemy2 import WKTElement
    
    # Simple polygon covering Manhattan area
    polygon_wkt = """POLYGON((-74.0479 40.6829, -73.9067 40.6829, 
                             -73.9067 40.8176, -74.0479 40.8176, 
                             -74.0479 40.6829))"""
    
    coverage = CoverageArea(
        firm_id=sample_security_firm.id,
        name="Manhattan Coverage",
        boundary=WKTElement(polygon_wkt, srid=4326)
    )
    db_session.add(coverage)
    await db_session.commit()
    await db_session.refresh(coverage)
    return coverage


@pytest.fixture
async def sample_registered_user(db_session) -> RegisteredUser:
    """Create a sample registered user"""
    user = RegisteredUser(
        email="user@test.com",
        phone="+1987654321",
        first_name="Test",
        last_name="User",
        is_verified=True,
        password_hash="$2b$12$test_hash"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def sample_user_group(db_session, sample_registered_user) -> UserGroup:
    """Create a sample user group"""
    from geoalchemy2 import WKTElement
    
    group = UserGroup(
        user_id=sample_registered_user.id,
        name="Test Group",
        address="456 Test Ave, Test City",
        location=WKTElement("POINT(-73.9857 40.7484)", srid=4326),  # Times Square
        subscription_expires_at=datetime.utcnow() + timedelta(days=30)
    )
    db_session.add(group)
    await db_session.commit()
    await db_session.refresh(group)
    return group


@pytest.fixture
async def sample_group_mobile_number(db_session, sample_user_group) -> GroupMobileNumber:
    """Create a sample group mobile number"""
    mobile = GroupMobileNumber(
        group_id=sample_user_group.id,
        phone_number="+1555123456",
        user_type="individual",
        is_verified=True
    )
    db_session.add(mobile)
    await db_session.commit()
    await db_session.refresh(mobile)
    return mobile


@pytest.fixture
async def sample_subscription_product(db_session, sample_security_firm) -> SubscriptionProduct:
    """Create a sample subscription product"""
    product = SubscriptionProduct(
        firm_id=sample_security_firm.id,
        name="Basic Security Package",
        description="Basic emergency response services",
        max_users=10,
        price=99.99,
        credit_cost=50,
        is_active=True
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest.fixture
async def sample_stored_subscription(
    db_session, 
    sample_registered_user, 
    sample_subscription_product
) -> StoredSubscription:
    """Create a sample stored subscription"""
    subscription = StoredSubscription(
        user_id=sample_registered_user.id,
        product_id=sample_subscription_product.id,
        is_applied=False
    )
    db_session.add(subscription)
    await db_session.commit()
    await db_session.refresh(subscription)
    return subscription


@pytest.fixture
async def sample_firm_personnel(db_session, sample_security_firm) -> FirmPersonnel:
    """Create a sample firm personnel"""
    personnel = FirmPersonnel(
        firm_id=sample_security_firm.id,
        email="agent@security.com",
        phone="+1555987654",
        first_name="Field",
        last_name="Agent",
        role="field_agent",
        is_active=True,
        password_hash="$2b$12$test_hash"
    )
    db_session.add(personnel)
    await db_session.commit()
    await db_session.refresh(personnel)
    return personnel


@pytest.fixture
async def sample_team(
    db_session, 
    sample_security_firm, 
    sample_firm_personnel, 
    sample_coverage_area
) -> Team:
    """Create a sample team"""
    team = Team(
        firm_id=sample_security_firm.id,
        name="Alpha Team",
        team_leader_id=sample_firm_personnel.id,
        coverage_area_id=sample_coverage_area.id,
        is_active=True
    )
    db_session.add(team)
    await db_session.commit()
    await db_session.refresh(team)
    return team


@pytest.fixture
async def sample_panic_request(
    db_session, 
    sample_user_group, 
    sample_group_mobile_number
) -> PanicRequest:
    """Create a sample panic request"""
    from geoalchemy2 import WKTElement
    
    request = PanicRequest(
        group_id=sample_user_group.id,
        requester_phone=sample_group_mobile_number.phone_number,
        service_type="security",
        location=WKTElement("POINT(-73.9857 40.7484)", srid=4326),
        address="Times Square, New York, NY",
        description="Emergency assistance needed",
        status="pending"
    )
    db_session.add(request)
    await db_session.commit()
    await db_session.refresh(request)
    return request


@pytest.fixture
async def sample_service_provider(db_session, sample_security_firm) -> ServiceProvider:
    """Create a sample service provider"""
    from geoalchemy2 import WKTElement
    
    provider = ServiceProvider(
        firm_id=sample_security_firm.id,
        name="Test Ambulance Service",
        service_type="ambulance",
        email="ambulance@test.com",
        phone="+1555111222",
        address="789 Medical St, Test City",
        location=WKTElement("POINT(-73.9857 40.7484)", srid=4326),
        is_active=True
    )
    db_session.add(provider)
    await db_session.commit()
    await db_session.refresh(provider)
    return provider


@pytest.fixture
def mock_external_services():
    """Mock external services for integration tests"""
    from unittest.mock import patch, AsyncMock
    
    mocks = {}
    
    # Mock Google Play Integrity API
    with patch('app.services.attestation.verify_android_integrity') as mock_android:
        mock_android.return_value = True
        mocks['android_attestation'] = mock_android
        
        # Mock Apple App Attest
        with patch('app.services.attestation.verify_ios_attestation') as mock_ios:
            mock_ios.return_value = True
            mocks['ios_attestation'] = mock_ios
            
            # Mock SMS service
            with patch('app.services.otp_delivery.send_sms') as mock_sms:
                mock_sms.return_value = True
                mocks['sms_service'] = mock_sms
                
                # Mock email service
                with patch('app.services.otp_delivery.send_email') as mock_email:
                    mock_email.return_value = True
                    mocks['email_service'] = mock_email
                    
                    # Mock push notifications
                    with patch('app.services.notification.send_push_notification') as mock_push:
                        mock_push.return_value = True
                        mocks['push_service'] = mock_push
                        
                        # Mock payment gateway
                        with patch('app.services.credit.process_payment') as mock_payment:
                            mock_payment.return_value = {"success": True, "transaction_id": "test_123"}
                            mocks['payment_service'] = mock_payment
                            
                            yield mocks


@pytest.fixture
def auth_headers():
    """Generate auth headers for testing"""
    def _generate_headers(user_type="registered_user", user_id=None):
        # Mock JWT token for testing
        token = f"test.jwt.token.{user_type}.{user_id or uuid4()}"
        return {
            "Authorization": f"Bearer {token}",
            "X-Platform": "android",
            "Content-Type": "application/json"
        }
    return _generate_headers


@pytest.fixture
async def cleanup_db(db_session):
    """Cleanup database after tests"""
    yield
    
    # Clean up all tables in reverse dependency order
    tables = [
        RequestFeedback,
        PanicRequest,
        StoredSubscription,
        SubscriptionProduct,
        GroupMobileNumber,
        UserGroup,
        RegisteredUser,
        Team,
        FirmPersonnel,
        ServiceProvider,
        CoverageArea,
        SecurityFirm
    ]
    
    for table in tables:
        await db_session.execute(f"DELETE FROM {table.__tablename__}")
    
    await db_session.commit()