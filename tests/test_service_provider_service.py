"""
Unit tests for service provider location management service
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from app.services.service_provider import ServiceProviderLocationService, get_service_provider_service
from app.services.geolocation import GeolocationService
from app.models.emergency import ServiceProvider
from app.models.security_firm import SecurityFirm


class TestServiceProviderLocationService:
    """Test cases for ServiceProviderLocationService"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return Mock(spec=Session)
    
    @pytest.fixture
    def mock_geolocation_service(self):
        """Mock geolocation service"""
        return Mock(spec=GeolocationService)
    
    @pytest.fixture
    def service_provider_service(self, mock_db):
        """ServiceProviderLocationService instance with mocked database"""
        service = ServiceProviderLocationService(mock_db)
        service.geolocation_service = Mock(spec=GeolocationService)
        return service
    
    @pytest.fixture
    def sample_firm_id(self):
        """Sample security firm UUID"""
        return uuid4()
    
    @pytest.fixture
    def sample_provider_id(self):
        """Sample service provider UUID"""
        return uuid4()
    
    @pytest.fixture
    def sample_coordinates(self):
        """Sample GPS coordinates"""
        return {"latitude": -26.2041, "longitude": 28.0473}
    
    @pytest.fixture
    def sample_provider_data(self, sample_firm_id):
        """Sample service provider data"""
        return {
            "firm_id": sample_firm_id,
            "name": "Emergency Ambulance Services",
            "service_type": "ambulance",
            "email": "contact@ambulance.com",
            "phone": "+27123456789",
            "address": "123 Medical Street, Johannesburg",
            "latitude": -26.2041,
            "longitude": 28.0473
        }
    
    @pytest.mark.asyncio
    async def test_register_service_provider_success(
        self, 
        service_provider_service, 
        mock_db, 
        sample_provider_data
    ):
        """Test successful service provider registration"""
        # Mock database operations
        mock_provider = Mock(spec=ServiceProvider)
        mock_provider.id = uuid4()
        mock_provider.name = sample_provider_data["name"]
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        
        # Mock ServiceProvider constructor
        with patch('app.services.service_provider.ServiceProvider') as mock_constructor:
            mock_constructor.return_value = mock_provider
            
            result = await service_provider_service.register_service_provider(**sample_provider_data)
            
            assert result == mock_provider
            mock_db.add.assert_called_once_with(mock_provider)
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once_with(mock_provider)
    
    @pytest.mark.asyncio
    async def test_register_service_provider_invalid_type(
        self, 
        service_provider_service, 
        sample_provider_data
    ):
        """Test service provider registration with invalid service type"""
        sample_provider_data["service_type"] = "invalid_type"
        
        with pytest.raises(ValueError, match="Invalid service type"):
            await service_provider_service.register_service_provider(**sample_provider_data)
    
    @pytest.mark.asyncio
    async def test_update_service_provider_location_success(
        self, 
        service_provider_service, 
        mock_db, 
        sample_provider_id, 
        sample_coordinates
    ):
        """Test successful service provider location update"""
        # Mock existing provider
        mock_provider = Mock(spec=ServiceProvider)
        mock_provider.id = sample_provider_id
        mock_db.query.return_value.filter.return_value.first.return_value = mock_provider
        
        result = await service_provider_service.update_service_provider_location(
            sample_provider_id,
            sample_coordinates["latitude"],
            sample_coordinates["longitude"],
            "New Address"
        )
        
        assert result == mock_provider
        assert mock_provider.address == "New Address"
        assert hasattr(mock_provider, 'updated_at')
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_provider)
    
    @pytest.mark.asyncio
    async def test_update_service_provider_location_not_found(
        self, 
        service_provider_service, 
        mock_db, 
        sample_provider_id, 
        sample_coordinates
    ):
        """Test service provider location update when provider not found"""
        # Mock provider not found
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = await service_provider_service.update_service_provider_location(
            sample_provider_id,
            sample_coordinates["latitude"],
            sample_coordinates["longitude"]
        )
        
        assert result is None
        mock_db.commit.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_find_providers_by_location(
        self, 
        service_provider_service, 
        mock_db, 
        sample_coordinates
    ):
        """Test finding providers by location"""
        # Mock database response
        mock_row = Mock()
        mock_row.id = uuid4()
        mock_row.distance_km = 5.2
        mock_db.execute.return_value.fetchall.return_value = [mock_row]
        
        # Mock ServiceProvider query
        mock_provider = Mock(spec=ServiceProvider)
        mock_provider.id = mock_row.id
        mock_provider.name = "Test Ambulance"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_provider
        
        result = await service_provider_service.find_providers_by_location(
            sample_coordinates["latitude"],
            sample_coordinates["longitude"],
            service_type="ambulance"
        )
        
        assert len(result) == 1
        provider, distance = result[0]
        assert provider == mock_provider
        assert distance == 5.2
        mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_find_providers_by_location_with_filters(
        self, 
        service_provider_service, 
        mock_db, 
        sample_coordinates, 
        sample_firm_id
    ):
        """Test finding providers by location with filters"""
        # Mock database response
        mock_db.execute.return_value.fetchall.return_value = []
        
        await service_provider_service.find_providers_by_location(
            sample_coordinates["latitude"],
            sample_coordinates["longitude"],
            service_type="towing",
            firm_id=sample_firm_id,
            max_distance_km=25.0,
            limit=10
        )
        
        # Verify the query was called with correct parameters
        call_args = mock_db.execute.call_args
        params = call_args[0][1]
        assert params["service_type"] == "towing"
        assert params["firm_id"] == str(sample_firm_id)
        assert params["max_distance_km"] == 25.0
        assert params["limit"] == 10
    
    @pytest.mark.asyncio
    async def test_find_providers_in_coverage_area(
        self, 
        service_provider_service, 
        mock_db
    ):
        """Test finding providers in coverage area"""
        coverage_area_id = uuid4()
        
        # Mock database response
        mock_row = Mock()
        mock_row.id = uuid4()
        mock_db.execute.return_value.fetchall.return_value = [mock_row]
        
        # Mock ServiceProvider query
        mock_provider = Mock(spec=ServiceProvider)
        mock_provider.id = mock_row.id
        mock_provider.name = "Coverage Area Provider"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_provider
        
        result = await service_provider_service.find_providers_in_coverage_area(
            coverage_area_id,
            service_type="fire"
        )
        
        assert len(result) == 1
        assert result[0] == mock_provider
        mock_db.execute.assert_called_once()
        
        # Verify query parameters
        call_args = mock_db.execute.call_args
        params = call_args[0][1]
        assert params["coverage_area_id"] == str(coverage_area_id)
        assert params["service_type"] == "fire"
    
    @pytest.mark.asyncio
    async def test_rank_providers_by_distance(
        self, 
        service_provider_service, 
        sample_coordinates
    ):
        """Test ranking providers by distance"""
        # Create mock providers with locations
        provider1 = Mock(spec=ServiceProvider)
        provider1.location = from_shape(Point(28.0473, -26.2041))  # Same location
        provider1.name = "Close Provider"
        
        provider2 = Mock(spec=ServiceProvider)
        provider2.location = from_shape(Point(28.1, -26.3))  # Further away
        provider2.name = "Far Provider"
        
        providers = [provider2, provider1]  # Intentionally unsorted
        
        # Mock distance calculations
        service_provider_service.geolocation_service.calculate_distance_km.side_effect = [
            15.5,  # Distance to provider2
            0.0    # Distance to provider1
        ]
        
        result = await service_provider_service.rank_providers_by_distance(
            providers,
            sample_coordinates["latitude"],
            sample_coordinates["longitude"]
        )
        
        assert len(result) == 2
        # Should be sorted by distance (closest first)
        assert result[0][0] == provider1  # Closest
        assert result[0][1] == 0.0
        assert result[1][0] == provider2  # Furthest
        assert result[1][1] == 15.5
    
    @pytest.mark.asyncio
    async def test_get_provider_availability_status_available(
        self, 
        service_provider_service, 
        mock_db, 
        sample_provider_id
    ):
        """Test getting provider availability status - available"""
        # Mock provider
        mock_provider = Mock(spec=ServiceProvider)
        mock_provider.id = sample_provider_id
        mock_provider.is_active = True
        mock_provider.name = "Available Provider"
        mock_provider.service_type = "ambulance"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_provider
        
        # Mock database response for requests
        mock_result = Mock()
        mock_result.active_requests = 2
        mock_result.pending_requests = 0
        mock_result.last_request_time = datetime.utcnow()
        mock_db.execute.return_value.fetchone.return_value = mock_result
        
        result = await service_provider_service.get_provider_availability_status(sample_provider_id)
        
        assert result["available"] is True
        assert result["status"] == "available"
        assert result["active_requests"] == 2
        assert result["pending_requests"] == 0
        assert result["provider_name"] == "Available Provider"
        assert result["service_type"] == "ambulance"
    
    @pytest.mark.asyncio
    async def test_get_provider_availability_status_busy(
        self, 
        service_provider_service, 
        mock_db, 
        sample_provider_id
    ):
        """Test getting provider availability status - busy"""
        # Mock provider
        mock_provider = Mock(spec=ServiceProvider)
        mock_provider.id = sample_provider_id
        mock_provider.is_active = True
        mock_provider.name = "Busy Provider"
        mock_provider.service_type = "towing"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_provider
        
        # Mock database response for requests
        mock_result = Mock()
        mock_result.active_requests = 5
        mock_result.pending_requests = 3  # >= 3 means busy
        mock_result.last_request_time = datetime.utcnow()
        mock_db.execute.return_value.fetchone.return_value = mock_result
        
        result = await service_provider_service.get_provider_availability_status(sample_provider_id)
        
        assert result["available"] is False
        assert result["status"] == "busy"
        assert result["pending_requests"] == 3
    
    @pytest.mark.asyncio
    async def test_get_provider_availability_status_limited(
        self, 
        service_provider_service, 
        mock_db, 
        sample_provider_id
    ):
        """Test getting provider availability status - limited"""
        # Mock provider
        mock_provider = Mock(spec=ServiceProvider)
        mock_provider.id = sample_provider_id
        mock_provider.is_active = True
        mock_provider.name = "Limited Provider"
        mock_provider.service_type = "fire"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_provider
        
        # Mock database response for requests
        mock_result = Mock()
        mock_result.active_requests = 3
        mock_result.pending_requests = 1  # 1-2 means limited
        mock_result.last_request_time = datetime.utcnow()
        mock_db.execute.return_value.fetchone.return_value = mock_result
        
        result = await service_provider_service.get_provider_availability_status(sample_provider_id)
        
        assert result["available"] is True
        assert result["status"] == "limited"
        assert result["pending_requests"] == 1
    
    @pytest.mark.asyncio
    async def test_get_provider_availability_status_inactive(
        self, 
        service_provider_service, 
        mock_db, 
        sample_provider_id
    ):
        """Test getting provider availability status - inactive"""
        # Mock inactive provider
        mock_provider = Mock(spec=ServiceProvider)
        mock_provider.id = sample_provider_id
        mock_provider.is_active = False
        mock_db.query.return_value.filter.return_value.first.return_value = mock_provider
        
        result = await service_provider_service.get_provider_availability_status(sample_provider_id)
        
        assert result["available"] is False
        assert result["reason"] == "Provider inactive"
    
    @pytest.mark.asyncio
    async def test_get_provider_availability_status_not_found(
        self, 
        service_provider_service, 
        mock_db, 
        sample_provider_id
    ):
        """Test getting provider availability status - not found"""
        # Mock provider not found
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = await service_provider_service.get_provider_availability_status(sample_provider_id)
        
        assert result["available"] is False
        assert result["reason"] == "Provider not found"
    
    @pytest.mark.asyncio
    async def test_update_provider_availability_success(
        self, 
        service_provider_service, 
        mock_db, 
        sample_provider_id
    ):
        """Test successful provider availability update"""
        # Mock existing provider
        mock_provider = Mock(spec=ServiceProvider)
        mock_provider.id = sample_provider_id
        mock_db.query.return_value.filter.return_value.first.return_value = mock_provider
        
        result = await service_provider_service.update_provider_availability(
            sample_provider_id, False
        )
        
        assert result == mock_provider
        assert mock_provider.is_active is False
        assert hasattr(mock_provider, 'updated_at')
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_provider)
    
    @pytest.mark.asyncio
    async def test_update_provider_availability_not_found(
        self, 
        service_provider_service, 
        mock_db, 
        sample_provider_id
    ):
        """Test provider availability update when provider not found"""
        # Mock provider not found
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = await service_provider_service.update_provider_availability(
            sample_provider_id, True
        )
        
        assert result is None
        mock_db.commit.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_providers_by_firm(
        self, 
        service_provider_service, 
        mock_db, 
        sample_firm_id
    ):
        """Test getting providers by firm"""
        # Mock providers
        mock_provider1 = Mock(spec=ServiceProvider)
        mock_provider1.name = "Provider 1"
        mock_provider2 = Mock(spec=ServiceProvider)
        mock_provider2.name = "Provider 2"
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value.all.return_value = [mock_provider1, mock_provider2]
        mock_db.query.return_value = mock_query
        
        result = await service_provider_service.get_providers_by_firm(
            sample_firm_id,
            service_type="ambulance",
            active_only=True
        )
        
        assert len(result) == 2
        assert result[0] == mock_provider1
        assert result[1] == mock_provider2
        
        # Verify filters were applied
        assert mock_query.filter.call_count == 3  # firm_id, service_type, active_only
    
    @pytest.mark.asyncio
    async def test_get_provider_statistics(
        self, 
        service_provider_service, 
        mock_db, 
        sample_provider_id
    ):
        """Test getting provider statistics"""
        # Mock database response
        mock_result = Mock()
        mock_result.total_requests = 20
        mock_result.completed_requests = 18
        mock_result.cancelled_requests = 2
        mock_result.avg_response_time_minutes = 12.5
        mock_result.avg_rating = 4.2
        mock_db.execute.return_value.fetchone.return_value = mock_result
        
        result = await service_provider_service.get_provider_statistics(sample_provider_id)
        
        assert result["total_requests"] == 20
        assert result["completed_requests"] == 18
        assert result["cancelled_requests"] == 2
        assert result["completion_rate"] == 90.0  # 18/20 * 100
        assert result["avg_response_time_minutes"] == 12.5
        assert result["avg_rating"] == 4.2
    
    @pytest.mark.asyncio
    async def test_get_provider_statistics_no_data(
        self, 
        service_provider_service, 
        mock_db, 
        sample_provider_id
    ):
        """Test getting provider statistics with no data"""
        # Mock database response
        mock_db.execute.return_value.fetchone.return_value = None
        
        result = await service_provider_service.get_provider_statistics(sample_provider_id)
        
        assert result["total_requests"] == 0
        assert result["completed_requests"] == 0
        assert result["completion_rate"] == 0.0
        assert result["avg_response_time_minutes"] is None
        assert result["avg_rating"] is None
    
    @pytest.mark.asyncio
    async def test_find_optimal_provider_success(
        self, 
        service_provider_service, 
        sample_coordinates, 
        sample_firm_id
    ):
        """Test finding optimal provider successfully"""
        # Mock provider
        mock_provider = Mock(spec=ServiceProvider)
        mock_provider.id = uuid4()
        mock_provider.name = "Optimal Provider"
        
        # Mock find_providers_by_location
        with patch.object(service_provider_service, 'find_providers_by_location') as mock_find:
            mock_find.return_value = [(mock_provider, 5.0)]
            
            # Mock get_provider_availability_status
            with patch.object(service_provider_service, 'get_provider_availability_status') as mock_availability:
                mock_availability.return_value = {
                    "available": True,
                    "status": "available",
                    "pending_requests": 0
                }
                
                result = await service_provider_service.find_optimal_provider(
                    sample_coordinates["latitude"],
                    sample_coordinates["longitude"],
                    "ambulance",
                    sample_firm_id
                )
                
                assert result is not None
                provider, distance, availability = result
                assert provider == mock_provider
                assert distance == 5.0
                assert availability["available"] is True
    
    @pytest.mark.asyncio
    async def test_find_optimal_provider_none_available(
        self, 
        service_provider_service, 
        sample_coordinates, 
        sample_firm_id
    ):
        """Test finding optimal provider when none are available"""
        # Mock find_providers_by_location returning empty list
        with patch.object(service_provider_service, 'find_providers_by_location') as mock_find:
            mock_find.return_value = []
            
            result = await service_provider_service.find_optimal_provider(
                sample_coordinates["latitude"],
                sample_coordinates["longitude"],
                "ambulance",
                sample_firm_id
            )
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_find_optimal_provider_all_busy(
        self, 
        service_provider_service, 
        sample_coordinates, 
        sample_firm_id
    ):
        """Test finding optimal provider when all are busy"""
        # Mock provider
        mock_provider = Mock(spec=ServiceProvider)
        mock_provider.id = uuid4()
        mock_provider.name = "Busy Provider"
        
        # Mock find_providers_by_location
        with patch.object(service_provider_service, 'find_providers_by_location') as mock_find:
            mock_find.return_value = [(mock_provider, 5.0)]
            
            # Mock get_provider_availability_status - all busy
            with patch.object(service_provider_service, 'get_provider_availability_status') as mock_availability:
                mock_availability.return_value = {
                    "available": False,
                    "status": "busy",
                    "pending_requests": 3
                }
                
                result = await service_provider_service.find_optimal_provider(
                    sample_coordinates["latitude"],
                    sample_coordinates["longitude"],
                    "ambulance",
                    sample_firm_id
                )
                
                assert result is None


class TestServiceProviderServiceFactory:
    """Test cases for service provider service factory function"""
    
    @patch('app.services.service_provider.get_db')
    def test_get_service_provider_service_with_db(self, mock_get_db):
        """Test factory function with provided database session"""
        mock_db = Mock(spec=Session)
        
        service = get_service_provider_service(mock_db)
        
        assert isinstance(service, ServiceProviderLocationService)
        assert service.db == mock_db
        mock_get_db.assert_not_called()
    
    @patch('app.services.service_provider.get_db')
    def test_get_service_provider_service_without_db(self, mock_get_db):
        """Test factory function without provided database session"""
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = iter([mock_db])
        
        service = get_service_provider_service()
        
        assert isinstance(service, ServiceProviderLocationService)
        assert service.db == mock_db
        mock_get_db.assert_called_once()


class TestServiceProviderServiceIntegration:
    """Integration test cases for ServiceProviderLocationService"""
    
    @pytest.mark.asyncio
    async def test_provider_scoring_algorithm(self):
        """Test the provider scoring algorithm for optimal selection"""
        mock_db = Mock(spec=Session)
        service = ServiceProviderLocationService(mock_db)
        
        # Mock providers with different distances and availability
        provider1 = Mock(spec=ServiceProvider)
        provider1.id = uuid4()
        provider1.name = "Close but Busy"
        
        provider2 = Mock(spec=ServiceProvider)
        provider2.id = uuid4()
        provider2.name = "Far but Available"
        
        # Mock find_providers_by_location
        with patch.object(service, 'find_providers_by_location') as mock_find:
            mock_find.return_value = [
                (provider1, 2.0),  # Close but will be busy
                (provider2, 8.0)   # Far but available
            ]
            
            # Mock availability - provider1 busy, provider2 available
            availability_responses = [
                {"available": True, "pending_requests": 2},  # provider1 - limited
                {"available": True, "pending_requests": 0}   # provider2 - available
            ]
            
            with patch.object(service, 'get_provider_availability_status') as mock_availability:
                mock_availability.side_effect = availability_responses
                
                result = await service.find_optimal_provider(-26.2041, 28.0473, "ambulance", uuid4())
                
                # Should select provider2 despite being further due to better availability
                # Score calculation: provider1 = 2.0 + (2 * 5.0) = 12.0
                #                   provider2 = 8.0 + (0 * 5.0) = 8.0
                assert result is not None
                provider, distance, availability = result
                assert provider == provider2
                assert distance == 8.0