"""
Unit tests for WebSocket API endpoints
"""
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from fastapi.testclient import TestClient
from fastapi import status

from app.main import app
from app.core.auth import UserContext
from app.services.websocket import connection_manager


class TestWebSocketEndpoints:
    """Test WebSocket API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_user_context(self):
        """Create mock user context"""
        return UserContext(
            user_id=uuid4(),
            role="field_agent",
            email="test@example.com",
            is_verified=True
        )
    
    @pytest.mark.asyncio
    async def test_websocket_connection_without_token(self, client):
        """Test WebSocket connection without authentication token"""
        with client.websocket_connect("/api/v1/ws") as websocket:
            # Connection should be closed due to missing token
            with pytest.raises(Exception):
                websocket.receive_text()
    
    @pytest.mark.asyncio
    async def test_websocket_connection_with_invalid_token(self, client):
        """Test WebSocket connection with invalid token"""
        with patch('app.api.v1.websocket.get_user_from_websocket_token', return_value=None):
            with client.websocket_connect("/api/v1/ws?token=invalid") as websocket:
                # Connection should be closed due to invalid token
                with pytest.raises(Exception):
                    websocket.receive_text()
    
    @pytest.mark.asyncio
    async def test_websocket_connection_success(self, client, mock_user_context):
        """Test successful WebSocket connection"""
        with patch('app.api.v1.websocket.get_user_from_websocket_token', return_value=mock_user_context):
            with patch.object(connection_manager, 'connect') as mock_connect:
                with patch.object(connection_manager, 'disconnect') as mock_disconnect:
                    with client.websocket_connect("/api/v1/ws?token=valid") as websocket:
                        # Send a ping message
                        websocket.send_text(json.dumps({"type": "ping"}))
                        
                        # Should receive pong response
                        response = websocket.receive_text()
                        data = json.loads(response)
                        assert data["type"] == "pong"
                        
                        mock_connect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_websocket_subscribe_request(self, client, mock_user_context):
        """Test subscribing to request updates"""
        with patch('app.api.v1.websocket.get_user_from_websocket_token', return_value=mock_user_context):
            with patch.object(connection_manager, 'connect'):
                with patch.object(connection_manager, 'disconnect'):
                    with patch.object(connection_manager, 'subscribe_to_request') as mock_subscribe:
                        with client.websocket_connect("/api/v1/ws?token=valid") as websocket:
                            # Send subscribe message
                            subscribe_msg = {
                                "type": "subscribe_request",
                                "request_id": "request-123"
                            }
                            websocket.send_text(json.dumps(subscribe_msg))
                            
                            # Give some time for processing
                            import asyncio
                            await asyncio.sleep(0.1)
                            
                            mock_subscribe.assert_called_once_with(
                                str(mock_user_context.user_id),
                                "request-123"
                            )
    
    @pytest.mark.asyncio
    async def test_websocket_unsubscribe_request(self, client, mock_user_context):
        """Test unsubscribing from request updates"""
        with patch('app.api.v1.websocket.get_user_from_websocket_token', return_value=mock_user_context):
            with patch.object(connection_manager, 'connect'):
                with patch.object(connection_manager, 'disconnect'):
                    with patch.object(connection_manager, 'unsubscribe_from_request') as mock_unsubscribe:
                        with client.websocket_connect("/api/v1/ws?token=valid") as websocket:
                            # Send unsubscribe message
                            unsubscribe_msg = {
                                "type": "unsubscribe_request",
                                "request_id": "request-123"
                            }
                            websocket.send_text(json.dumps(unsubscribe_msg))
                            
                            # Give some time for processing
                            import asyncio
                            await asyncio.sleep(0.1)
                            
                            mock_unsubscribe.assert_called_once_with(
                                str(mock_user_context.user_id),
                                "request-123"
                            )
    
    @pytest.mark.asyncio
    async def test_websocket_location_update_from_field_agent(self, client, mock_user_context):
        """Test location update from field agent"""
        with patch('app.api.v1.websocket.get_user_from_websocket_token', return_value=mock_user_context):
            with patch.object(connection_manager, 'connect'):
                with patch.object(connection_manager, 'disconnect'):
                    with patch('app.api.v1.websocket.websocket_service.send_location_update') as mock_location_update:
                        with client.websocket_connect("/api/v1/ws?token=valid") as websocket:
                            # Send location update
                            location_msg = {
                                "type": "location_update",
                                "request_id": str(uuid4()),
                                "location": {"latitude": 40.7128, "longitude": -74.0060},
                                "estimated_arrival_time": 15
                            }
                            websocket.send_text(json.dumps(location_msg))
                            
                            # Give some time for processing
                            import asyncio
                            await asyncio.sleep(0.1)
                            
                            mock_location_update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_websocket_invalid_json(self, client, mock_user_context):
        """Test handling invalid JSON message"""
        with patch('app.api.v1.websocket.get_user_from_websocket_token', return_value=mock_user_context):
            with patch.object(connection_manager, 'connect'):
                with patch.object(connection_manager, 'disconnect'):
                    with client.websocket_connect("/api/v1/ws?token=valid") as websocket:
                        # Send invalid JSON
                        websocket.send_text("invalid json")
                        
                        # Connection should remain open despite invalid message
                        # Send a valid ping to verify
                        websocket.send_text(json.dumps({"type": "ping"}))
                        response = websocket.receive_text()
                        data = json.loads(response)
                        assert data["type"] == "pong"


class TestFieldAgentWebSocket:
    """Test field agent specific WebSocket endpoint"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_field_agent_context(self):
        """Create mock field agent context"""
        return UserContext(
            user_id=uuid4(),
            role="field_agent",
            email="agent@example.com",
            is_verified=True
        )
    
    @pytest.fixture
    def mock_office_staff_context(self):
        """Create mock office staff context"""
        return UserContext(
            user_id=uuid4(),
            role="office_staff",
            email="staff@example.com",
            is_verified=True
        )
    
    @pytest.mark.asyncio
    async def test_field_agent_websocket_access_denied_for_non_agent(self, client, mock_office_staff_context):
        """Test that non-field agents cannot access field agent WebSocket"""
        with patch('app.api.v1.websocket.get_user_from_websocket_token', return_value=mock_office_staff_context):
            with client.websocket_connect("/api/v1/ws/field-agent?token=valid") as websocket:
                # Connection should be closed due to insufficient permissions
                with pytest.raises(Exception):
                    websocket.receive_text()
    
    @pytest.mark.asyncio
    async def test_field_agent_websocket_accept_request(self, client, mock_field_agent_context):
        """Test field agent accepting a request"""
        with patch('app.api.v1.websocket.get_user_from_websocket_token', return_value=mock_field_agent_context):
            with patch.object(connection_manager, 'connect'):
                with patch.object(connection_manager, 'disconnect'):
                    with patch('app.api.v1.websocket.websocket_service.send_request_status_update') as mock_status_update:
                        with client.websocket_connect("/api/v1/ws/field-agent?token=valid") as websocket:
                            # Send accept request message
                            accept_msg = {
                                "type": "accept_request",
                                "request_id": str(uuid4())
                            }
                            websocket.send_text(json.dumps(accept_msg))
                            
                            # Give some time for processing
                            import asyncio
                            await asyncio.sleep(0.1)
                            
                            mock_status_update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_field_agent_websocket_location_update(self, client, mock_field_agent_context):
        """Test field agent sending location update"""
        with patch('app.api.v1.websocket.get_user_from_websocket_token', return_value=mock_field_agent_context):
            with patch.object(connection_manager, 'connect'):
                with patch.object(connection_manager, 'disconnect'):
                    with patch('app.api.v1.websocket.websocket_service.send_location_update') as mock_location_update:
                        with client.websocket_connect("/api/v1/ws/field-agent?token=valid") as websocket:
                            # Send location update
                            location_msg = {
                                "type": "location_update",
                                "request_id": str(uuid4()),
                                "location": {"latitude": 40.7128, "longitude": -74.0060},
                                "estimated_arrival_time": 10
                            }
                            websocket.send_text(json.dumps(location_msg))
                            
                            # Give some time for processing
                            import asyncio
                            await asyncio.sleep(0.1)
                            
                            mock_location_update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_field_agent_websocket_arrived(self, client, mock_field_agent_context):
        """Test field agent reporting arrival"""
        with patch('app.api.v1.websocket.get_user_from_websocket_token', return_value=mock_field_agent_context):
            with patch.object(connection_manager, 'connect'):
                with patch.object(connection_manager, 'disconnect'):
                    with patch('app.api.v1.websocket.websocket_service.send_provider_arrival') as mock_arrival:
                        with client.websocket_connect("/api/v1/ws/field-agent?token=valid") as websocket:
                            # Send arrival message
                            arrival_msg = {
                                "type": "arrived",
                                "request_id": str(uuid4()),
                                "vehicle_details": {
                                    "license_plate": "ABC123",
                                    "vehicle_type": "security_vehicle"
                                }
                            }
                            websocket.send_text(json.dumps(arrival_msg))
                            
                            # Give some time for processing
                            import asyncio
                            await asyncio.sleep(0.1)
                            
                            mock_arrival.assert_called_once()


class TestServiceProviderWebSocket:
    """Test service provider specific WebSocket endpoint"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_service_provider_context(self):
        """Create mock service provider context"""
        return UserContext(
            user_id=uuid4(),
            role="service_provider",
            email="provider@example.com",
            is_verified=True
        )
    
    @pytest.fixture
    def mock_field_agent_context(self):
        """Create mock field agent context"""
        return UserContext(
            user_id=uuid4(),
            role="field_agent",
            email="agent@example.com",
            is_verified=True
        )
    
    @pytest.mark.asyncio
    async def test_service_provider_websocket_access_denied_for_non_provider(self, client, mock_field_agent_context):
        """Test that non-service providers cannot access service provider WebSocket"""
        with patch('app.api.v1.websocket.get_user_from_websocket_token', return_value=mock_field_agent_context):
            with client.websocket_connect("/api/v1/ws/service-provider?token=valid") as websocket:
                # Connection should be closed due to insufficient permissions
                with pytest.raises(Exception):
                    websocket.receive_text()
    
    @pytest.mark.asyncio
    async def test_service_provider_websocket_accept_request(self, client, mock_service_provider_context):
        """Test service provider accepting a request"""
        with patch('app.api.v1.websocket.get_user_from_websocket_token', return_value=mock_service_provider_context):
            with patch.object(connection_manager, 'connect'):
                with patch.object(connection_manager, 'disconnect'):
                    with patch('app.api.v1.websocket.websocket_service.send_request_status_update') as mock_status_update:
                        with client.websocket_connect("/api/v1/ws/service-provider?token=valid") as websocket:
                            # Send accept request message
                            accept_msg = {
                                "type": "accept_request",
                                "request_id": str(uuid4()),
                                "vehicle_details": {
                                    "license_plate": "XYZ789",
                                    "vehicle_type": "ambulance"
                                }
                            }
                            websocket.send_text(json.dumps(accept_msg))
                            
                            # Give some time for processing
                            import asyncio
                            await asyncio.sleep(0.1)
                            
                            mock_status_update.assert_called_once()
                            call_args = mock_status_update.call_args
                            assert call_args[0][1] == "provider_accepted"  # status
    
    @pytest.mark.asyncio
    async def test_service_provider_websocket_location_update(self, client, mock_service_provider_context):
        """Test service provider sending location update"""
        with patch('app.api.v1.websocket.get_user_from_websocket_token', return_value=mock_service_provider_context):
            with patch.object(connection_manager, 'connect'):
                with patch.object(connection_manager, 'disconnect'):
                    with patch('app.api.v1.websocket.websocket_service.send_location_update') as mock_location_update:
                        with client.websocket_connect("/api/v1/ws/service-provider?token=valid") as websocket:
                            # Send location update
                            location_msg = {
                                "type": "location_update",
                                "request_id": str(uuid4()),
                                "location": {"latitude": 40.7128, "longitude": -74.0060},
                                "estimated_arrival_time": 25
                            }
                            websocket.send_text(json.dumps(location_msg))
                            
                            # Give some time for processing
                            import asyncio
                            await asyncio.sleep(0.1)
                            
                            mock_location_update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_service_provider_websocket_arrived(self, client, mock_service_provider_context):
        """Test service provider reporting arrival"""
        with patch('app.api.v1.websocket.get_user_from_websocket_token', return_value=mock_service_provider_context):
            with patch.object(connection_manager, 'connect'):
                with patch.object(connection_manager, 'disconnect'):
                    with patch('app.api.v1.websocket.websocket_service.send_provider_arrival') as mock_arrival:
                        with client.websocket_connect("/api/v1/ws/service-provider?token=valid") as websocket:
                            # Send arrival message
                            arrival_msg = {
                                "type": "arrived",
                                "request_id": str(uuid4()),
                                "vehicle_details": {
                                    "license_plate": "AMB456",
                                    "vehicle_type": "ambulance",
                                    "color": "white"
                                }
                            }
                            websocket.send_text(json.dumps(arrival_msg))
                            
                            # Give some time for processing
                            import asyncio
                            await asyncio.sleep(0.1)
                            
                            mock_arrival.assert_called_once()


@pytest.mark.asyncio
async def test_websocket_authentication_helper():
    """Test WebSocket authentication helper function"""
    from app.api.v1.websocket import get_user_from_websocket_token
    from fastapi import WebSocket
    
    # Mock WebSocket with token in query params
    mock_websocket = MagicMock(spec=WebSocket)
    mock_websocket.query_params = {"token": "valid_token"}
    
    mock_user_context = UserContext(
        user_id=uuid4(),
        role="field_agent",
        email="test@example.com",
        is_verified=True
    )
    
    with patch('app.api.v1.websocket.get_current_user_from_token', return_value=mock_user_context):
        result = await get_user_from_websocket_token(mock_websocket)
        assert result == mock_user_context
    
    # Test with missing token
    mock_websocket.query_params = {}
    result = await get_user_from_websocket_token(mock_websocket)
    assert result is None
    
    # Test with invalid token
    mock_websocket.query_params = {"token": "invalid_token"}
    with patch('app.api.v1.websocket.get_current_user_from_token', side_effect=Exception("Invalid token")):
        result = await get_user_from_websocket_token(mock_websocket)
        assert result is None