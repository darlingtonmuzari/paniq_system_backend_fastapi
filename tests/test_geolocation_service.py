"""
Unit tests for geolocation service
"""
import pytest
from unittest.mock import Mock, patch
from uuid import uuid4
from sqlalchemy.orm import Session
from geoalchemy2.shape import from_shape
from shapely.geometry import Point, Polygon

from app.services.geolocation import GeolocationService, get_geolocation_service
from app.models.security_firm import SecurityFirm, CoverageArea
from app.models.emergency import ServiceProvider
from app.models.user import UserGroup


class TestGeolocationService:
    """Test cases for GeolocationService"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return Mock(spec=Session)
    
    @pytest.fixture
    def geolocation_service(self, mock_db):
        """GeolocationService instance with mocked database"""
        return GeolocationService(mock_db)
    
    @pytest.fixture
    def sample_firm_id(self):
        """Sample security firm UUID"""
        return uuid4()
    
    @pytest.fixture
    def sample_coordinates(self):
        """Sample GPS coordinates (Johannesburg, South Africa)"""
        return {
            "latitude": -26.2041,
            "longitude": 28.0473
        }
    
    @pytest.fixture
    def sample_coverage_area_id(self):
        """Sample coverage area UUID"""
        return uuid4()
    
    @pytest.mark.asyncio
    async def test_validate_location_in_coverage_success(
        self, 
        geolocation_service, 
        mock_db, 
        sample_firm_id, 
        sample_coordinates
    ):
        """Test successful location validation within coverage"""
        # Mock database response
        mock_result = Mock()
        mock_result.is_covered = True
        mock_db.execute.return_value.fetchone.return_value = mock_result
        
        result = await geolocation_service.validate_location_in_coverage(
            sample_coordinates["latitude"],
            sample_coordinates["longitude"],
            sample_firm_id
        )
        
        assert result is True
        mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_location_in_coverage_outside(
        self, 
        geolocation_service, 
        mock_db, 
        sample_firm_id, 
        sample_coordinates
    ):
        """Test location validation outside coverage"""
        # Mock database response
        mock_result = Mock()
        mock_result.is_covered = False
        mock_db.execute.return_value.fetchone.return_value = mock_result
        
        result = await geolocation_service.validate_location_in_coverage(
            sample_coordinates["latitude"],
            sample_coordinates["longitude"],
            sample_firm_id
        )
        
        assert result is False
        mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_location_in_coverage_no_result(
        self, 
        geolocation_service, 
        mock_db, 
        sample_firm_id, 
        sample_coordinates
    ):
        """Test location validation with no database result"""
        # Mock database response
        mock_db.execute.return_value.fetchone.return_value = None
        
        result = await geolocation_service.validate_location_in_coverage(
            sample_coordinates["latitude"],
            sample_coordinates["longitude"],
            sample_firm_id
        )
        
        assert result is False
        mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_find_covering_firms(
        self, 
        geolocation_service, 
        mock_db, 
        sample_coordinates
    ):
        """Test finding security firms that cover a location"""
        # Mock database response
        mock_row = Mock()
        mock_row.id = uuid4()
        mock_db.execute.return_value.fetchall.return_value = [mock_row]
        
        # Mock SecurityFirm query
        mock_firm = Mock(spec=SecurityFirm)
        mock_firm.id = mock_row.id
        mock_firm.name = "Test Security Firm"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_firm
        
        result = await geolocation_service.find_covering_firms(
            sample_coordinates["latitude"],
            sample_coordinates["longitude"]
        )
        
        assert len(result) == 1
        assert result[0] == mock_firm
        mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_find_covering_firms_none_found(
        self, 
        geolocation_service, 
        mock_db, 
        sample_coordinates
    ):
        """Test finding covering firms when none exist"""
        # Mock database response
        mock_db.execute.return_value.fetchall.return_value = []
        
        result = await geolocation_service.find_covering_firms(
            sample_coordinates["latitude"],
            sample_coordinates["longitude"]
        )
        
        assert len(result) == 0
        mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_calculate_distance_km(
        self, 
        geolocation_service, 
        mock_db
    ):
        """Test distance calculation using PostGIS"""
        # Mock database response
        mock_result = Mock()
        mock_result.distance_km = 15.5
        mock_db.execute.return_value.fetchone.return_value = mock_result
        
        result = await geolocation_service.calculate_distance_km(
            -26.2041, 28.0473,  # Johannesburg
            -26.1367, 28.0021   # Sandton
        )
        
        assert result == 15.5
        mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_calculate_distance_km_no_result(
        self, 
        geolocation_service, 
        mock_db
    ):
        """Test distance calculation with no database result"""
        # Mock database response
        mock_db.execute.return_value.fetchone.return_value = None
        
        result = await geolocation_service.calculate_distance_km(
            -26.2041, 28.0473,
            -26.1367, 28.0021
        )
        
        assert result == 0.0
        mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_calculate_haversine_distance(
        self, 
        geolocation_service
    ):
        """Test Haversine distance calculation"""
        result = await geolocation_service.calculate_haversine_distance(
            -26.2041, 28.0473,  # Johannesburg
            -26.1367, 28.0021   # Sandton (approximately 10km away)
        )
        
        # Should be approximately 10km (allowing for some variance)
        assert 8.0 <= result <= 12.0
    
    @pytest.mark.asyncio
    async def test_calculate_haversine_distance_same_point(
        self, 
        geolocation_service
    ):
        """Test Haversine distance calculation for same point"""
        result = await geolocation_service.calculate_haversine_distance(
            -26.2041, 28.0473,
            -26.2041, 28.0473
        )
        
        assert result == 0.0
    
    @pytest.mark.asyncio
    async def test_find_nearest_service_providers(
        self, 
        geolocation_service, 
        mock_db, 
        sample_firm_id, 
        sample_coordinates
    ):
        """Test finding nearest service providers"""
        # Mock database response
        mock_row = Mock()
        mock_row.id = uuid4()
        mock_row.distance_km = 5.2
        mock_db.execute.return_value.fetchall.return_value = [mock_row]
        
        # Mock ServiceProvider query
        mock_provider = Mock(spec=ServiceProvider)
        mock_provider.id = mock_row.id
        mock_provider.name = "Test Ambulance Service"
        mock_provider.service_type = "ambulance"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_provider
        
        result = await geolocation_service.find_nearest_service_providers(
            sample_coordinates["latitude"],
            sample_coordinates["longitude"],
            "ambulance",
            sample_firm_id
        )
        
        assert len(result) == 1
        provider, distance = result[0]
        assert provider == mock_provider
        assert distance == 5.2
        mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_find_nearest_service_providers_none_found(
        self, 
        geolocation_service, 
        mock_db, 
        sample_firm_id, 
        sample_coordinates
    ):
        """Test finding nearest service providers when none exist"""
        # Mock database response
        mock_db.execute.return_value.fetchall.return_value = []
        
        result = await geolocation_service.find_nearest_service_providers(
            sample_coordinates["latitude"],
            sample_coordinates["longitude"],
            "ambulance",
            sample_firm_id
        )
        
        assert len(result) == 0
        mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_find_nearest_service_providers_with_limits(
        self, 
        geolocation_service, 
        mock_db, 
        sample_firm_id, 
        sample_coordinates
    ):
        """Test finding nearest service providers with custom limits"""
        # Mock database response
        mock_db.execute.return_value.fetchall.return_value = []
        
        await geolocation_service.find_nearest_service_providers(
            sample_coordinates["latitude"],
            sample_coordinates["longitude"],
            "towing",
            sample_firm_id,
            max_distance_km=25.0,
            limit=5
        )
        
        # Verify the query was called with correct parameters
        call_args = mock_db.execute.call_args
        assert call_args[0][1]["max_distance_km"] == 25.0
        assert call_args[0][1]["limit"] == 5
        assert call_args[0][1]["service_type"] == "towing"
    
    @pytest.mark.asyncio
    async def test_validate_group_location_coverage_success(
        self, 
        geolocation_service, 
        mock_db
    ):
        """Test successful group location coverage validation"""
        group_id = uuid4()
        
        # Mock UserGroup with PostGIS point
        mock_group = Mock(spec=UserGroup)
        mock_group.id = group_id
        mock_group.location = from_shape(Point(28.0473, -26.2041))  # lon, lat
        mock_db.query.return_value.filter.return_value.first.return_value = mock_group
        
        # Mock find_covering_firms
        mock_firm = Mock(spec=SecurityFirm)
        mock_firm.name = "Test Security"
        
        with patch.object(geolocation_service, 'find_covering_firms') as mock_find:
            mock_find.return_value = [mock_firm]
            
            is_covered, covering_firms = await geolocation_service.validate_group_location_coverage(group_id)
            
            assert is_covered is True
            assert len(covering_firms) == 1
            assert covering_firms[0] == mock_firm
            mock_find.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_group_location_coverage_not_covered(
        self, 
        geolocation_service, 
        mock_db
    ):
        """Test group location coverage validation when not covered"""
        group_id = uuid4()
        
        # Mock UserGroup with PostGIS point
        mock_group = Mock(spec=UserGroup)
        mock_group.id = group_id
        mock_group.location = from_shape(Point(28.0473, -26.2041))
        mock_db.query.return_value.filter.return_value.first.return_value = mock_group
        
        # Mock find_covering_firms returning empty list
        with patch.object(geolocation_service, 'find_covering_firms') as mock_find:
            mock_find.return_value = []
            
            is_covered, covering_firms = await geolocation_service.validate_group_location_coverage(group_id)
            
            assert is_covered is False
            assert len(covering_firms) == 0
            mock_find.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_group_location_coverage_group_not_found(
        self, 
        geolocation_service, 
        mock_db
    ):
        """Test group location coverage validation when group doesn't exist"""
        group_id = uuid4()
        
        # Mock UserGroup query returning None
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        is_covered, covering_firms = await geolocation_service.validate_group_location_coverage(group_id)
        
        assert is_covered is False
        assert covering_firms is None
    
    @pytest.mark.asyncio
    async def test_get_coverage_area_center(
        self, 
        geolocation_service, 
        mock_db, 
        sample_coverage_area_id
    ):
        """Test getting coverage area center point"""
        # Mock database response
        mock_result = Mock()
        mock_result.latitude = -26.2041
        mock_result.longitude = 28.0473
        mock_db.execute.return_value.fetchone.return_value = mock_result
        
        result = await geolocation_service.get_coverage_area_center(sample_coverage_area_id)
        
        assert result is not None
        latitude, longitude = result
        assert latitude == -26.2041
        assert longitude == 28.0473
        mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_coverage_area_center_not_found(
        self, 
        geolocation_service, 
        mock_db, 
        sample_coverage_area_id
    ):
        """Test getting coverage area center when area doesn't exist"""
        # Mock database response
        mock_db.execute.return_value.fetchone.return_value = None
        
        result = await geolocation_service.get_coverage_area_center(sample_coverage_area_id)
        
        assert result is None
        mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_coverage_area_bounds(
        self, 
        geolocation_service, 
        mock_db, 
        sample_coverage_area_id
    ):
        """Test getting coverage area bounding box"""
        # Mock database response
        mock_result = Mock()
        mock_result.min_lat = -26.3
        mock_result.min_lon = 27.9
        mock_result.max_lat = -26.1
        mock_result.max_lon = 28.2
        mock_db.execute.return_value.fetchone.return_value = mock_result
        
        result = await geolocation_service.get_coverage_area_bounds(sample_coverage_area_id)
        
        assert result is not None
        min_lat, min_lon, max_lat, max_lon = result
        assert min_lat == -26.3
        assert min_lon == 27.9
        assert max_lat == -26.1
        assert max_lon == 28.2
        mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_coverage_area_bounds_not_found(
        self, 
        geolocation_service, 
        mock_db, 
        sample_coverage_area_id
    ):
        """Test getting coverage area bounds when area doesn't exist"""
        # Mock database response
        mock_db.execute.return_value.fetchone.return_value = None
        
        result = await geolocation_service.get_coverage_area_bounds(sample_coverage_area_id)
        
        assert result is None
        mock_db.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_is_location_within_distance_true(
        self, 
        geolocation_service
    ):
        """Test location within distance check - true case"""
        with patch.object(geolocation_service, 'calculate_distance_km') as mock_calc:
            mock_calc.return_value = 8.5
            
            result = await geolocation_service.is_location_within_distance(
                -26.2041, 28.0473,
                -26.1367, 28.0021,
                10.0
            )
            
            assert result is True
            mock_calc.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_is_location_within_distance_false(
        self, 
        geolocation_service
    ):
        """Test location within distance check - false case"""
        with patch.object(geolocation_service, 'calculate_distance_km') as mock_calc:
            mock_calc.return_value = 15.2
            
            result = await geolocation_service.is_location_within_distance(
                -26.2041, 28.0473,
                -26.1367, 28.0021,
                10.0
            )
            
            assert result is False
            mock_calc.assert_called_once()


class TestGeolocationServiceFactory:
    """Test cases for geolocation service factory function"""
    
    @patch('app.services.geolocation.get_db')
    def test_get_geolocation_service_with_db(self, mock_get_db):
        """Test factory function with provided database session"""
        mock_db = Mock(spec=Session)
        
        service = get_geolocation_service(mock_db)
        
        assert isinstance(service, GeolocationService)
        assert service.db == mock_db
        mock_get_db.assert_not_called()
    
    @patch('app.services.geolocation.get_db')
    def test_get_geolocation_service_without_db(self, mock_get_db):
        """Test factory function without provided database session"""
        mock_db = Mock(spec=Session)
        mock_get_db.return_value = iter([mock_db])
        
        service = get_geolocation_service()
        
        assert isinstance(service, GeolocationService)
        assert service.db == mock_db
        mock_get_db.assert_called_once()


class TestGeolocationServiceIntegration:
    """Integration test cases for GeolocationService with real calculations"""
    
    @pytest.mark.asyncio
    async def test_haversine_distance_accuracy(self):
        """Test Haversine distance calculation accuracy with known distances"""
        service = GeolocationService(Mock())
        
        # Test known distance: Johannesburg to Cape Town (approximately 1265 km)
        distance = await service.calculate_haversine_distance(
            -26.2041, 28.0473,  # Johannesburg
            -33.9249, 18.4241   # Cape Town
        )
        
        # Allow for reasonable variance in calculation
        assert 1250 <= distance <= 1280
    
    @pytest.mark.asyncio
    async def test_haversine_distance_short_distance(self):
        """Test Haversine distance calculation for short distances"""
        service = GeolocationService(Mock())
        
        # Test short distance: within same city
        distance = await service.calculate_haversine_distance(
            -26.2041, 28.0473,  # Johannesburg CBD
            -26.1367, 28.0021   # Sandton (approximately 10km)
        )
        
        # Should be approximately 10km
        assert 8 <= distance <= 12