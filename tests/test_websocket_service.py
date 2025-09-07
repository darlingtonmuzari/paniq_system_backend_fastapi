"""
Unit tests for WebSocket service
"""
import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID
from datetime import datetime
from fastapi import WebSocket

from app.services.websocket import (
    ConnectionManager,
    WebSocketService,
    RealtimeUpdate,
    websocket_service,
    connection_manager
)


class TestRealtimeUpdate:
    """Test RealtimeUpdate model"""
    
    def test_realtime_update_creation(self):
        """Test creating a RealtimeUpdate instance"""
        request_id = uuid4()
        user_id = uuid4()
        
        update = RealtimeUpdate(
            type="request_status_update",
            data={"status": "pending", "request_id": str(request_id)},
            timestamp=datetime.utcnow(),
            request_id=request_id,
            user_id=user_id
        )
        
        assert update.type == "request_status_update"
        assert update.data["status"] == "pending"
        assert update.request_id == request_id
        assert update.user_id == user_id
        assert isinstance(update.timestamp, datetime)
    
    def test_realtime_update_json_serialization(self):
        """Test JSON serialization of RealtimeUpdate"""
        request_id = uuid4()
        
        update = RealtimeUpdate(
            type="location_update",
            data={"latitude": 40.7128, "longitude": -74.0060},
            timestamp=datetime.utcnow(),
            request_id=request_id
        )
        
        json_str = update.model_dump_json()
        assert isinstance(json_str, str)
        
        # Verify it can be parsed back
        parsed = json.loads(json_str)
        assert parsed["type"] == "location_update"
        assert parsed["data"]["latitude"] == 40.7128


class TestConnectionManager:
    """Test ConnectionManager functionality"""
    
    @pytest.fixture
    def manager(self):
        """Create a fresh ConnectionManager for each test"""
        return ConnectionManager()
    
    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket"""
        websocket = AsyncMock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.send_text = AsyncMock()
        return websocket
    
    @pytest.mark.asyncio
    async def test_connect_user(self, manager, mock_websocket):
        """Test connecting a user"""
        user_id = "test-user-123"
        user_role = "field_agent"
        
        await manager.connect(mock_websocket, user_id, user_role)
        
        assert user_id in manager.active_connections
        assert manager.active_connections[user_id] == mock_websocket
        assert manager.user_roles[user_id] == user_role
        mock_websocket.accept.assert_called_once()
    
    def test_disconnect_user(self, manager, mock_websocket):
        """Test disconnecting a user"""
        user_id = "test-user-123"
        user_role = "field_agent"
        
        # First connect the user
        manager.active_connections[user_id] = mock_websocket
        manager.user_roles[user_id] = user_role
        manager.request_subscriptions["request-123"] = {user_id}
        
        # Then disconnect
        manager.disconnect(user_id)
        
        assert user_id not in manager.active_connections
        assert user_id not in manager.user_roles
        assert "request-123" not in manager.request_subscriptions
    
    @pytest.mark.asyncio
    async def test_send_personal_message(self, manager, mock_websocket):
        """Test sending a personal message"""
        user_id = "test-user-123"
        manager.active_connections[user_id] = mock_websocket
        
        message = RealtimeUpdate(
            type="test_message",
            data={"content": "Hello"},
            timestamp=datetime.utcnow()
        )
        
        await manager.send_personal_message(user_id, message)
        
        mock_websocket.send_text.assert_called_once()
        sent_data = mock_websocket.send_text.call_args[0][0]
        parsed_data = json.loads(sent_data)
        assert parsed_data["type"] == "test_message"
        assert parsed_data["data"]["content"] == "Hello"
    
    @pytest.mark.asyncio
    async def test_send_personal_message_connection_error(self, manager, mock_websocket):
        """Test handling connection error when sending message"""
        user_id = "test-user-123"
        manager.active_connections[user_id] = mock_websocket
        manager.user_roles[user_id] = "field_agent"
        
        # Make send_text raise an exception
        mock_websocket.send_text.side_effect = Exception("Connection broken")
        
        message = RealtimeUpdate(
            type="test_message",
            data={"content": "Hello"},
            timestamp=datetime.utcnow()
        )
        
        await manager.send_personal_message(user_id, message)
        
        # User should be disconnected after error
        assert user_id not in manager.active_connections
        assert user_id not in manager.user_roles
    
    @pytest.mark.asyncio
    async def test_subscribe_to_request(self, manager):
        """Test subscribing to request updates"""
        user_id = "test-user-123"
        request_id = "request-456"
        
        await manager.subscribe_to_request(user_id, request_id)
        
        assert request_id in manager.request_subscriptions
        assert user_id in manager.request_subscriptions[request_id]
    
    @pytest.mark.asyncio
    async def test_unsubscribe_from_request(self, manager):
        """Test unsubscribing from request updates"""
        user_id = "test-user-123"
        request_id = "request-456"
        
        # First subscribe
        manager.request_subscriptions[request_id] = {user_id}
        
        # Then unsubscribe
        await manager.unsubscribe_from_request(user_id, request_id)
        
        assert request_id not in manager.request_subscriptions
    
    @pytest.mark.asyncio
    async def test_broadcast_to_request_subscribers(self, manager):
        """Test broadcasting to request subscribers"""
        user1 = "user-1"
        user2 = "user-2"
        request_id = "request-123"
        
        # Set up subscribers
        mock_ws1 = AsyncMock(spec=WebSocket)
        mock_ws2 = AsyncMock(spec=WebSocket)
        manager.active_connections[user1] = mock_ws1
        manager.active_connections[user2] = mock_ws2
        manager.request_subscriptions[request_id] = {user1, user2}
        
        message = RealtimeUpdate(
            type="broadcast_test",
            data={"message": "Hello all"},
            timestamp=datetime.utcnow()
        )
        
        await manager.broadcast_to_request_subscribers(request_id, message)
        
        # Both users should receive the message
        mock_ws1.send_text.assert_called_once()
        mock_ws2.send_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_broadcast_to_role(self, manager):
        """Test broadcasting to users with specific role"""
        user1 = "user-1"
        user2 = "user-2"
        user3 = "user-3"
        
        # Set up users with different roles
        mock_ws1 = AsyncMock(spec=WebSocket)
        mock_ws2 = AsyncMock(spec=WebSocket)
        mock_ws3 = AsyncMock(spec=WebSocket)
        
        manager.active_connections[user1] = mock_ws1
        manager.active_connections[user2] = mock_ws2
        manager.active_connections[user3] = mock_ws3
        
        manager.user_roles[user1] = "field_agent"
        manager.user_roles[user2] = "field_agent"
        manager.user_roles[user3] = "office_staff"
        
        message = RealtimeUpdate(
            type="role_broadcast",
            data={"message": "Field agents only"},
            timestamp=datetime.utcnow()
        )
        
        await manager.broadcast_to_role("field_agent", message)
        
        # Only field agents should receive the message
        mock_ws1.send_text.assert_called_once()
        mock_ws2.send_text.assert_called_once()
        mock_ws3.send_text.assert_not_called()


class TestWebSocketService:
    """Test WebSocketService functionality"""
    
    @pytest.fixture
    def service(self):
        """Create a WebSocketService instance"""
        return WebSocketService()
    
    @pytest.mark.asyncio
    async def test_send_request_status_update(self, service):
        """Test sending request status update"""
        request_id = uuid4()
        
        with patch.object(service.manager, 'broadcast_to_request_subscribers') as mock_broadcast:
            await service.send_request_status_update(
                request_id,
                "accepted",
                {"accepted_by": "agent-123"}
            )
            
            mock_broadcast.assert_called_once()
            call_args = mock_broadcast.call_args
            assert call_args[0][0] == str(request_id)  # request_id
            
            message = call_args[0][1]  # RealtimeUpdate object
            assert message.type == "request_status_update"
            assert message.data["status"] == "accepted"
            assert message.data["accepted_by"] == "agent-123"
            assert message.request_id == request_id
    
    @pytest.mark.asyncio
    async def test_send_location_update(self, service):
        """Test sending location update"""
        request_id = uuid4()
        location = {"latitude": 40.7128, "longitude": -74.0060}
        eta = 15
        
        with patch.object(service.manager, 'broadcast_to_request_subscribers') as mock_broadcast:
            await service.send_location_update(request_id, location, eta)
            
            mock_broadcast.assert_called_once()
            call_args = mock_broadcast.call_args
            
            message = call_args[0][1]  # RealtimeUpdate object
            assert message.type == "location_update"
            assert message.data["provider_location"] == location
            assert message.data["estimated_arrival_time"] == eta
            assert message.request_id == request_id
    
    @pytest.mark.asyncio
    async def test_send_provider_assignment(self, service):
        """Test sending provider assignment notification"""
        request_id = uuid4()
        provider_details = {
            "provider_id": "provider-123",
            "provider_name": "Emergency Services Inc",
            "phone": "+1234567890"
        }
        eta = 20
        
        with patch.object(service.manager, 'broadcast_to_request_subscribers') as mock_broadcast:
            await service.send_provider_assignment(request_id, provider_details, eta)
            
            mock_broadcast.assert_called_once()
            call_args = mock_broadcast.call_args
            
            message = call_args[0][1]  # RealtimeUpdate object
            assert message.type == "provider_assigned"
            assert message.data["provider_details"] == provider_details
            assert message.data["estimated_arrival_time"] == eta
            assert message.request_id == request_id
    
    @pytest.mark.asyncio
    async def test_send_provider_arrival(self, service):
        """Test sending provider arrival notification"""
        request_id = uuid4()
        vehicle_details = {
            "license_plate": "ABC123",
            "vehicle_type": "ambulance",
            "color": "white"
        }
        
        with patch.object(service.manager, 'broadcast_to_request_subscribers') as mock_broadcast:
            await service.send_provider_arrival(request_id, vehicle_details)
            
            mock_broadcast.assert_called_once()
            call_args = mock_broadcast.call_args
            
            message = call_args[0][1]  # RealtimeUpdate object
            assert message.type == "provider_arrived"
            assert message.data["vehicle_details"] == vehicle_details
            assert message.request_id == request_id
    
    @pytest.mark.asyncio
    async def test_send_request_confirmation(self, service):
        """Test sending request confirmation"""
        request_id = uuid4()
        user_id = uuid4()
        confirmation_details = {
            "service_type": "ambulance",
            "status": "pending",
            "address": "123 Main St"
        }
        
        with patch.object(service.manager, 'send_personal_message') as mock_send:
            await service.send_request_confirmation(request_id, user_id, confirmation_details)
            
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert call_args[0][0] == str(user_id)  # user_id
            
            message = call_args[0][1]  # RealtimeUpdate object
            assert message.type == "request_confirmed"
            assert message.data["service_type"] == "ambulance"
            assert message.data["status"] == "pending"
            assert message.request_id == request_id
            assert message.user_id == user_id
    
    @pytest.mark.asyncio
    async def test_notify_field_agent_assignment(self, service):
        """Test notifying field agent of assignment"""
        agent_id = uuid4()
        request_details = {
            "request_id": "request-123",
            "service_type": "security",
            "address": "456 Oak Ave",
            "description": "Security assistance needed"
        }
        
        with patch.object(service.manager, 'send_personal_message') as mock_send:
            await service.notify_field_agent_assignment(agent_id, request_details)
            
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert call_args[0][0] == str(agent_id)  # agent_id
            
            message = call_args[0][1]  # RealtimeUpdate object
            assert message.type == "agent_assignment"
            assert message.data["request_details"] == request_details


@pytest.mark.asyncio
async def test_global_websocket_service():
    """Test that global websocket_service instance works correctly"""
    request_id = uuid4()
    
    with patch.object(websocket_service.manager, 'broadcast_to_request_subscribers') as mock_broadcast:
        await websocket_service.send_request_status_update(request_id, "pending")
        
        mock_broadcast.assert_called_once()
        call_args = mock_broadcast.call_args
        assert call_args[0][0] == str(request_id)
        
        message = call_args[0][1]
        assert message.type == "request_status_update"
        assert message.data["status"] == "pending"


@pytest.mark.asyncio
async def test_global_connection_manager():
    """Test that global connection_manager instance works correctly"""
    user_id = "test-user"
    mock_websocket = AsyncMock(spec=WebSocket)
    
    await connection_manager.connect(mock_websocket, user_id, "field_agent")
    
    assert user_id in connection_manager.active_connections
    assert connection_manager.user_roles[user_id] == "field_agent"
    
    # Clean up
    connection_manager.disconnect(user_id)