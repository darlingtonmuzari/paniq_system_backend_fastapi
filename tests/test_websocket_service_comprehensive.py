"""
Comprehensive unit tests for WebSocket service
"""
import pytest
import asyncio
from datetime import datetime
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import WebSocket

from app.services.websocket import (
    WebSocketService,
    ConnectionManager,
    RealtimeUpdate,
    websocket_service,
    connection_manager
)


class TestRealtimeUpdate:
    """Test RealtimeUpdate model"""
    
    def test_create_realtime_update_minimal(self):
        """Test creating realtime update with minimal fields"""
        update = RealtimeUpdate(
            type="test_update",
            data={"message": "test"},
            timestamp=datetime.utcnow()
        )
        
        assert update.type == "test_update"
        assert update.data["message"] == "test"
        assert update.timestamp is not None
        assert update.request_id is None
        assert update.user_id is None
    
    def test_create_realtime_update_full(self):
        """Test creating realtime update with all fields"""
        request_id = uuid4()
        user_id = uuid4()
        timestamp = datetime.utcnow()
        
        update = RealtimeUpdate(
            type="request_status_update",
            data={"status": "accepted", "agent_id": "123"},
            timestamp=timestamp,
            request_id=request_id,
            user_id=user_id
        )
        
        assert update.type == "request_status_update"
        assert update.data["status"] == "accepted"
        assert update.timestamp == timestamp
        assert update.request_id == request_id
        assert update.user_id == user_id
    
    def test_realtime_update_json_serialization(self):
        """Test JSON serialization of RealtimeUpdate"""
        update = RealtimeUpdate(
            type="test_update",
            data={"key": "value"},
            timestamp=datetime.utcnow(),
            request_id=uuid4()
        )
        
        json_str = update.model_dump_json()
        assert isinstance(json_str, str)
        assert "test_update" in json_str
        assert "key" in json_str
        assert "value" in json_str


class TestConnectionManager:
    """Test WebSocket connection manager"""
    
    @pytest.fixture
    def manager(self):
        """Fresh connection manager for each test"""
        return ConnectionManager()
    
    @pytest.fixture
    def mock_websocket(self):
        """Mock WebSocket connection"""
        websocket = AsyncMock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.send_text = AsyncMock()
        return websocket
    
    @pytest.mark.asyncio
    async def test_connect_user(self, manager, mock_websocket):
        """Test connecting a user"""
        user_id = "user_123"
        user_role = "registered_user"
        
        await manager.connect(mock_websocket, user_id, user_role)
        
        assert user_id in manager.active_connections
        assert manager.active_connections[user_id] == mock_websocket
        assert manager.user_roles[user_id] == user_role
        mock_websocket.accept.assert_called_once()
    
    def test_disconnect_user(self, manager, mock_websocket):
        """Test disconnecting a user"""
        user_id = "user_123"
        user_role = "registered_user"
        
        # First connect the user
        manager.active_connections[user_id] = mock_websocket
        manager.user_roles[user_id] = user_role
        
        # Add user to request subscription
        request_id = "request_456"
        manager.request_subscriptions[request_id] = {user_id}
        
        # Disconnect
        manager.disconnect(user_id)
        
        assert user_id not in manager.active_connections
        assert user_id not in manager.user_roles
        assert request_id not in manager.request_subscriptions  # Should be cleaned up
    
    def test_disconnect_user_not_connected(self, manager):
        """Test disconnecting a user that wasn't connected"""
        user_id = "nonexistent_user"
        
        # Should not raise an exception
        manager.disconnect(user_id)
        
        assert user_id not in manager.active_connections
        assert user_id not in manager.user_roles
    
    @pytest.mark.asyncio
    async def test_send_personal_message_success(self, manager, mock_websocket):
        """Test sending personal message successfully"""
        user_id = "user_123"
        manager.active_connections[user_id] = mock_websocket
        
        message = RealtimeUpdate(
            type="test_message",
            data={"content": "Hello"},
            timestamp=datetime.utcnow()
        )
        
        await manager.send_personal_message(user_id, message)
        
        mock_websocket.send_text.assert_called_once()
        sent_data = mock_websocket.send_text.call_args[0][0]
        assert "test_message" in sent_data
        assert "Hello" in sent_data
    
    @pytest.mark.asyncio
    async def test_send_personal_message_user_not_connected(self, manager):
        """Test sending message to non-connected user"""
        user_id = "nonexistent_user"
        
        message = RealtimeUpdate(
            type="test_message",
            data={"content": "Hello"},
            timestamp=datetime.utcnow()
        )
        
        # Should not raise an exception
        await manager.send_personal_message(user_id, message)
    
    @pytest.mark.asyncio
    async def test_send_personal_message_websocket_error(self, manager, mock_websocket):
        """Test handling WebSocket send error"""
        user_id = "user_123"
        manager.active_connections[user_id] = mock_websocket
        
        # Mock WebSocket error
        mock_websocket.send_text.side_effect = Exception("Connection closed")
        
        message = RealtimeUpdate(
            type="test_message",
            data={"content": "Hello"},
            timestamp=datetime.utcnow()
        )
        
        await manager.send_personal_message(user_id, message)
        
        # User should be disconnected after error
        assert user_id not in manager.active_connections
    
    @pytest.mark.asyncio
    async def test_subscribe_to_request(self, manager):
        """Test subscribing user to request updates"""
        user_id = "user_123"
        request_id = "request_456"
        
        await manager.subscribe_to_request(user_id, request_id)
        
        assert request_id in manager.request_subscriptions
        assert user_id in manager.request_subscriptions[request_id]
    
    @pytest.mark.asyncio
    async def test_subscribe_multiple_users_to_request(self, manager):
        """Test subscribing multiple users to same request"""
        user1_id = "user_123"
        user2_id = "user_456"
        request_id = "request_789"
        
        await manager.subscribe_to_request(user1_id, request_id)
        await manager.subscribe_to_request(user2_id, request_id)
        
        assert request_id in manager.request_subscriptions
        assert user1_id in manager.request_subscriptions[request_id]
        assert user2_id in manager.request_subscriptions[request_id]
        assert len(manager.request_subscriptions[request_id]) == 2
    
    @pytest.mark.asyncio
    async def test_unsubscribe_from_request(self, manager):
        """Test unsubscribing user from request updates"""
        user_id = "user_123"
        request_id = "request_456"
        
        # First subscribe
        await manager.subscribe_to_request(user_id, request_id)
        assert user_id in manager.request_subscriptions[request_id]
        
        # Then unsubscribe
        await manager.unsubscribe_from_request(user_id, request_id)
        
        # Request should be removed entirely if no subscribers
        assert request_id not in manager.request_subscriptions
    
    @pytest.mark.asyncio
    async def test_unsubscribe_one_of_multiple_subscribers(self, manager):
        """Test unsubscribing one user when multiple are subscribed"""
        user1_id = "user_123"
        user2_id = "user_456"
        request_id = "request_789"
        
        # Subscribe both users
        await manager.subscribe_to_request(user1_id, request_id)
        await manager.subscribe_to_request(user2_id, request_id)
        
        # Unsubscribe one user
        await manager.unsubscribe_from_request(user1_id, request_id)
        
        # Request should still exist with remaining subscriber
        assert request_id in manager.request_subscriptions
        assert user1_id not in manager.request_subscriptions[request_id]
        assert user2_id in manager.request_subscriptions[request_id]
    
    @pytest.mark.asyncio
    async def test_broadcast_to_request_subscribers(self, manager):
        """Test broadcasting message to request subscribers"""
        user1_id = "user_123"
        user2_id = "user_456"
        request_id = "request_789"
        
        # Setup mock websockets
        mock_ws1 = AsyncMock(spec=WebSocket)
        mock_ws2 = AsyncMock(spec=WebSocket)
        manager.active_connections[user1_id] = mock_ws1
        manager.active_connections[user2_id] = mock_ws2
        
        # Subscribe users to request
        await manager.subscribe_to_request(user1_id, request_id)
        await manager.subscribe_to_request(user2_id, request_id)
        
        message = RealtimeUpdate(
            type="broadcast_test",
            data={"message": "Hello all"},
            timestamp=datetime.utcnow()
        )
        
        with patch.object(manager, 'send_personal_message') as mock_send:
            mock_send.return_value = None
            
            await manager.broadcast_to_request_subscribers(request_id, message)
            
            # Should send to both subscribers
            assert mock_send.call_count == 2
            call_args = [call[0] for call in mock_send.call_args_list]
            assert (user1_id, message) in call_args
            assert (user2_id, message) in call_args
    
    @pytest.mark.asyncio
    async def test_broadcast_to_request_no_subscribers(self, manager):
        """Test broadcasting to request with no subscribers"""
        request_id = "request_789"
        
        message = RealtimeUpdate(
            type="broadcast_test",
            data={"message": "Hello all"},
            timestamp=datetime.utcnow()
        )
        
        with patch.object(manager, 'send_personal_message') as mock_send:
            await manager.broadcast_to_request_subscribers(request_id, message)
            
            # Should not send any messages
            mock_send.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_broadcast_to_role(self, manager):
        """Test broadcasting message to users with specific role"""
        user1_id = "user_123"
        user2_id = "user_456"
        user3_id = "user_789"
        
        # Setup users with different roles
        mock_ws1 = AsyncMock(spec=WebSocket)
        mock_ws2 = AsyncMock(spec=WebSocket)
        mock_ws3 = AsyncMock(spec=WebSocket)
        
        manager.active_connections[user1_id] = mock_ws1
        manager.active_connections[user2_id] = mock_ws2
        manager.active_connections[user3_id] = mock_ws3
        
        manager.user_roles[user1_id] = "field_agent"
        manager.user_roles[user2_id] = "field_agent"
        manager.user_roles[user3_id] = "registered_user"
        
        message = RealtimeUpdate(
            type="role_broadcast",
            data={"message": "Message for field agents"},
            timestamp=datetime.utcnow()
        )
        
        with patch.object(manager, 'send_personal_message') as mock_send:
            mock_send.return_value = None
            
            await manager.broadcast_to_role("field_agent", message)
            
            # Should send to only field agents
            assert mock_send.call_count == 2
            call_args = [call[0][0] for call in mock_send.call_args_list]
            assert user1_id in call_args
            assert user2_id in call_args
            assert user3_id not in call_args
    
    @pytest.mark.asyncio
    async def test_broadcast_to_role_no_users(self, manager):
        """Test broadcasting to role with no users"""
        message = RealtimeUpdate(
            type="role_broadcast",
            data={"message": "Message for admins"},
            timestamp=datetime.utcnow()
        )
        
        with patch.object(manager, 'send_personal_message') as mock_send:
            await manager.broadcast_to_role("admin", message)
            
            # Should not send any messages
            mock_send.assert_not_called()


class TestWebSocketService:
    """Test WebSocket service"""
    
    @pytest.fixture
    def service(self):
        """WebSocket service instance"""
        return WebSocketService()
    
    @pytest.fixture
    def mock_manager(self):
        """Mock connection manager"""
        manager = AsyncMock(spec=ConnectionManager)
        return manager
    
    @pytest.mark.asyncio
    async def test_send_request_status_update(self, service, mock_manager):
        """Test sending request status update"""
        service.manager = mock_manager
        
        request_id = uuid4()
        status = "accepted"
        additional_data = {"agent_id": "123", "eta": 15}
        
        await service.send_request_status_update(request_id, status, additional_data)
        
        mock_manager.broadcast_to_request_subscribers.assert_called_once()
        call_args = mock_manager.broadcast_to_request_subscribers.call_args
        
        assert call_args[0][0] == str(request_id)  # request_id
        message = call_args[0][1]  # message
        assert message.type == "request_status_update"
        assert message.data["request_id"] == str(request_id)
        assert message.data["status"] == status
        assert message.data["agent_id"] == "123"
        assert message.data["eta"] == 15
        assert "timestamp" in message.data
    
    @pytest.mark.asyncio
    async def test_send_request_status_update_no_additional_data(self, service, mock_manager):
        """Test sending request status update without additional data"""
        service.manager = mock_manager
        
        request_id = uuid4()
        status = "pending"
        
        await service.send_request_status_update(request_id, status)
        
        mock_manager.broadcast_to_request_subscribers.assert_called_once()
        call_args = mock_manager.broadcast_to_request_subscribers.call_args
        
        message = call_args[0][1]
        assert message.type == "request_status_update"
        assert message.data["request_id"] == str(request_id)
        assert message.data["status"] == status
        assert "agent_id" not in message.data
        assert "timestamp" in message.data
    
    @pytest.mark.asyncio
    async def test_send_location_update(self, service, mock_manager):
        """Test sending location update"""
        service.manager = mock_manager
        
        request_id = uuid4()
        provider_location = {"latitude": 40.7128, "longitude": -74.0060}
        eta = 10
        
        await service.send_location_update(request_id, provider_location, eta)
        
        mock_manager.broadcast_to_request_subscribers.assert_called_once()
        call_args = mock_manager.broadcast_to_request_subscribers.call_args
        
        message = call_args[0][1]
        assert message.type == "location_update"
        assert message.data["request_id"] == str(request_id)
        assert message.data["provider_location"] == provider_location
        assert message.data["estimated_arrival_time"] == eta
        assert "timestamp" in message.data
    
    @pytest.mark.asyncio
    async def test_send_location_update_no_eta(self, service, mock_manager):
        """Test sending location update without ETA"""
        service.manager = mock_manager
        
        request_id = uuid4()
        provider_location = {"latitude": 40.7128, "longitude": -74.0060}
        
        await service.send_location_update(request_id, provider_location)
        
        mock_manager.broadcast_to_request_subscribers.assert_called_once()
        call_args = mock_manager.broadcast_to_request_subscribers.call_args
        
        message = call_args[0][1]
        assert message.type == "location_update"
        assert message.data["request_id"] == str(request_id)
        assert message.data["provider_location"] == provider_location
        assert "estimated_arrival_time" not in message.data
    
    @pytest.mark.asyncio
    async def test_send_provider_assignment(self, service, mock_manager):
        """Test sending provider assignment notification"""
        service.manager = mock_manager
        
        request_id = uuid4()
        provider_details = {
            "name": "ABC Security",
            "phone": "+1234567890",
            "vehicle": "White SUV"
        }
        eta = 15
        
        await service.send_provider_assignment(request_id, provider_details, eta)
        
        mock_manager.broadcast_to_request_subscribers.assert_called_once()
        call_args = mock_manager.broadcast_to_request_subscribers.call_args
        
        message = call_args[0][1]
        assert message.type == "provider_assigned"
        assert message.data["request_id"] == str(request_id)
        assert message.data["provider_details"] == provider_details
        assert message.data["estimated_arrival_time"] == eta
        assert "timestamp" in message.data
    
    @pytest.mark.asyncio
    async def test_send_provider_arrival(self, service, mock_manager):
        """Test sending provider arrival notification"""
        service.manager = mock_manager
        
        request_id = uuid4()
        vehicle_details = {
            "description": "White SUV",
            "license_plate": "ABC123",
            "driver_name": "John Doe"
        }
        
        await service.send_provider_arrival(request_id, vehicle_details)
        
        mock_manager.broadcast_to_request_subscribers.assert_called_once()
        call_args = mock_manager.broadcast_to_request_subscribers.call_args
        
        message = call_args[0][1]
        assert message.type == "provider_arrived"
        assert message.data["request_id"] == str(request_id)
        assert message.data["vehicle_details"] == vehicle_details
        assert "timestamp" in message.data
    
    @pytest.mark.asyncio
    async def test_send_request_confirmation(self, service, mock_manager):
        """Test sending request confirmation"""
        service.manager = mock_manager
        
        request_id = uuid4()
        user_id = uuid4()
        confirmation_details = {
            "service_type": "security",
            "address": "123 Main St",
            "status": "pending"
        }
        
        await service.send_request_confirmation(request_id, user_id, confirmation_details)
        
        mock_manager.send_personal_message.assert_called_once()
        call_args = mock_manager.send_personal_message.call_args
        
        assert call_args[0][0] == str(user_id)  # user_id
        message = call_args[0][1]  # message
        assert message.type == "request_confirmed"
        assert message.data["request_id"] == str(request_id)
        assert message.data["service_type"] == "security"
        assert message.data["address"] == "123 Main St"
        assert message.data["status"] == "pending"
        assert "timestamp" in message.data
        assert message.request_id == request_id
        assert message.user_id == user_id
    
    @pytest.mark.asyncio
    async def test_notify_field_agent_assignment(self, service, mock_manager):
        """Test notifying field agent of assignment"""
        service.manager = mock_manager
        
        agent_id = uuid4()
        request_details = {
            "request_id": str(uuid4()),
            "service_type": "security",
            "location": "123 Main St",
            "description": "Suspicious activity"
        }
        
        await service.notify_field_agent_assignment(agent_id, request_details)
        
        mock_manager.send_personal_message.assert_called_once()
        call_args = mock_manager.send_personal_message.call_args
        
        assert call_args[0][0] == str(agent_id)  # agent_id
        message = call_args[0][1]  # message
        assert message.type == "agent_assignment"
        assert message.data["request_details"] == request_details
        assert "timestamp" in message.data


class TestWebSocketServiceIntegration:
    """Integration tests for WebSocket service"""
    
    @pytest.fixture
    def service(self):
        """WebSocket service with real connection manager"""
        service = WebSocketService()
        service.manager = ConnectionManager()  # Use real manager for integration tests
        return service
    
    @pytest.fixture
    def mock_websockets(self):
        """Multiple mock WebSocket connections"""
        websockets = {}
        for i in range(3):
            ws = AsyncMock(spec=WebSocket)
            ws.accept = AsyncMock()
            ws.send_text = AsyncMock()
            websockets[f"user_{i}"] = ws
        return websockets
    
    @pytest.mark.asyncio
    async def test_full_request_lifecycle_notifications(self, service, mock_websockets):
        """Test complete request lifecycle with real-time notifications"""
        request_id = uuid4()
        user_id = uuid4()
        agent_id = uuid4()
        
        # Connect users
        await service.manager.connect(mock_websockets["user_0"], str(user_id), "registered_user")
        await service.manager.connect(mock_websockets["user_1"], str(agent_id), "field_agent")
        
        # Subscribe user to request updates
        await service.manager.subscribe_to_request(str(user_id), str(request_id))
        await service.manager.subscribe_to_request(str(agent_id), str(request_id))
        
        # 1. Send request confirmation
        await service.send_request_confirmation(
            request_id, 
            user_id, 
            {"service_type": "security", "status": "pending"}
        )
        
        # 2. Notify agent of assignment
        await service.notify_field_agent_assignment(
            agent_id,
            {"request_id": str(request_id), "service_type": "security"}
        )
        
        # 3. Send status update (agent accepted)
        await service.send_request_status_update(
            request_id, 
            "accepted", 
            {"agent_id": str(agent_id)}
        )
        
        # 4. Send location updates
        await service.send_location_update(
            request_id,
            {"latitude": 40.7128, "longitude": -74.0060},
            10
        )
        
        # 5. Send provider assignment
        await service.send_provider_assignment(
            request_id,
            {"name": "ABC Security", "vehicle": "White SUV"},
            5
        )
        
        # 6. Send arrival notification
        await service.send_provider_arrival(
            request_id,
            {"description": "White SUV", "license_plate": "ABC123"}
        )
        
        # Verify messages were sent
        user_ws = mock_websockets["user_0"]
        agent_ws = mock_websockets["user_1"]
        
        # User should receive: confirmation + 4 broadcast messages
        assert user_ws.send_text.call_count == 5
        
        # Agent should receive: assignment + 4 broadcast messages  
        assert agent_ws.send_text.call_count == 5
        
        # Verify message types
        user_messages = [call[0][0] for call in user_ws.send_text.call_args_list]
        agent_messages = [call[0][0] for call in agent_ws.send_text.call_args_list]
        
        # Check that different message types are present
        assert any("request_confirmed" in msg for msg in user_messages)
        assert any("agent_assignment" in msg for msg in agent_messages)
        assert any("request_status_update" in msg for msg in user_messages)
        assert any("location_update" in msg for msg in user_messages)
        assert any("provider_assigned" in msg for msg in user_messages)
        assert any("provider_arrived" in msg for msg in user_messages)
    
    @pytest.mark.asyncio
    async def test_role_based_broadcasting(self, service, mock_websockets):
        """Test broadcasting messages to specific roles"""
        # Connect users with different roles
        await service.manager.connect(mock_websockets["user_0"], "agent_1", "field_agent")
        await service.manager.connect(mock_websockets["user_1"], "agent_2", "field_agent")
        await service.manager.connect(mock_websockets["user_2"], "user_1", "registered_user")
        
        # Broadcast to field agents only
        message = RealtimeUpdate(
            type="emergency_alert",
            data={"message": "All units respond to downtown area"},
            timestamp=datetime.utcnow()
        )
        
        await service.manager.broadcast_to_role("field_agent", message)
        
        # Only field agents should receive the message
        assert mock_websockets["user_0"].send_text.call_count == 1
        assert mock_websockets["user_1"].send_text.call_count == 1
        assert mock_websockets["user_2"].send_text.call_count == 0
    
    @pytest.mark.asyncio
    async def test_connection_cleanup_on_error(self, service):
        """Test that connections are cleaned up when WebSocket errors occur"""
        user_id = "user_123"
        request_id = "request_456"
        
        # Create mock WebSocket that will fail
        mock_ws = AsyncMock(spec=WebSocket)
        mock_ws.accept = AsyncMock()
        mock_ws.send_text = AsyncMock(side_effect=Exception("Connection closed"))
        
        # Connect user and subscribe to request
        await service.manager.connect(mock_ws, user_id, "registered_user")
        await service.manager.subscribe_to_request(user_id, request_id)
        
        # Verify user is connected and subscribed
        assert user_id in service.manager.active_connections
        assert user_id in service.manager.request_subscriptions[request_id]
        
        # Try to send message (should fail and clean up)
        message = RealtimeUpdate(
            type="test_message",
            data={"content": "test"},
            timestamp=datetime.utcnow()
        )
        
        await service.manager.send_personal_message(user_id, message)
        
        # User should be disconnected and cleaned up
        assert user_id not in service.manager.active_connections
        assert user_id not in service.manager.user_roles
        # Request subscription should be cleaned up too
        assert request_id not in service.manager.request_subscriptions


class TestGlobalInstances:
    """Test global service instances"""
    
    def test_websocket_service_instance(self):
        """Test that global websocket_service instance exists"""
        assert websocket_service is not None
        assert isinstance(websocket_service, WebSocketService)
        assert hasattr(websocket_service, 'manager')
    
    def test_connection_manager_instance(self):
        """Test that global connection_manager instance exists"""
        assert connection_manager is not None
        assert isinstance(connection_manager, ConnectionManager)
        assert hasattr(connection_manager, 'active_connections')
        assert hasattr(connection_manager, 'request_subscriptions')
        assert hasattr(connection_manager, 'user_roles')
    
    def test_websocket_service_uses_global_manager(self):
        """Test that websocket_service uses the global connection manager"""
        assert websocket_service.manager is connection_manager