"""
WebSocket service for real-time communication
"""
import json
import asyncio
from typing import Dict, List, Set, Optional, Any
from uuid import UUID
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import structlog

logger = structlog.get_logger()


class RealtimeUpdate(BaseModel):
    """Real-time update message structure"""
    type: str
    data: Dict[str, Any]
    timestamp: datetime
    request_id: Optional[UUID] = None
    user_id: Optional[UUID] = None


class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        # Active connections by user ID
        self.active_connections: Dict[str, WebSocket] = {}
        # Request subscriptions - which users are subscribed to which requests
        self.request_subscriptions: Dict[str, Set[str]] = {}
        # User roles for authorization
        self.user_roles: Dict[str, str] = {}
        
    async def connect(self, websocket: WebSocket, user_id: str, user_role: str):
        """Accept a WebSocket connection and register the user"""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        self.user_roles[user_id] = user_role
        
        logger.info(
            "websocket_connection_established",
            user_id=user_id,
            user_role=user_role,
            total_connections=len(self.active_connections)
        )
        
    def disconnect(self, user_id: str):
        """Remove a WebSocket connection"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            
        if user_id in self.user_roles:
            del self.user_roles[user_id]
            
        # Remove from all request subscriptions
        for request_id in list(self.request_subscriptions.keys()):
            if user_id in self.request_subscriptions[request_id]:
                self.request_subscriptions[request_id].discard(user_id)
                if not self.request_subscriptions[request_id]:
                    del self.request_subscriptions[request_id]
                    
        logger.info(
            "websocket_connection_closed",
            user_id=user_id,
            total_connections=len(self.active_connections)
        )
        
    async def send_personal_message(self, user_id: str, message: RealtimeUpdate):
        """Send a message to a specific user"""
        if user_id in self.active_connections:
            try:
                websocket = self.active_connections[user_id]
                await websocket.send_text(message.model_dump_json())
                
                logger.debug(
                    "websocket_message_sent",
                    user_id=user_id,
                    message_type=message.type,
                    request_id=message.request_id
                )
                
            except Exception as e:
                logger.error(
                    "websocket_send_error",
                    user_id=user_id,
                    error=str(e)
                )
                # Remove broken connection
                self.disconnect(user_id)
                
    async def subscribe_to_request(self, user_id: str, request_id: str):
        """Subscribe a user to updates for a specific request"""
        if request_id not in self.request_subscriptions:
            self.request_subscriptions[request_id] = set()
            
        self.request_subscriptions[request_id].add(user_id)
        
        logger.info(
            "websocket_request_subscription",
            user_id=user_id,
            request_id=request_id
        )
        
    async def unsubscribe_from_request(self, user_id: str, request_id: str):
        """Unsubscribe a user from updates for a specific request"""
        if request_id in self.request_subscriptions:
            self.request_subscriptions[request_id].discard(user_id)
            if not self.request_subscriptions[request_id]:
                del self.request_subscriptions[request_id]
                
        logger.info(
            "websocket_request_unsubscription",
            user_id=user_id,
            request_id=request_id
        )
        
    async def broadcast_to_request_subscribers(self, request_id: str, message: RealtimeUpdate):
        """Send a message to all users subscribed to a specific request"""
        if request_id not in self.request_subscriptions:
            return
            
        subscribers = list(self.request_subscriptions[request_id])
        
        logger.info(
            "websocket_broadcast_to_subscribers",
            request_id=request_id,
            subscriber_count=len(subscribers),
            message_type=message.type
        )
        
        # Send to all subscribers concurrently
        tasks = []
        for user_id in subscribers:
            if user_id in self.active_connections:
                tasks.append(self.send_personal_message(user_id, message))
                
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            
    async def broadcast_to_role(self, role: str, message: RealtimeUpdate):
        """Send a message to all users with a specific role"""
        target_users = [
            user_id for user_id, user_role in self.user_roles.items()
            if user_role == role and user_id in self.active_connections
        ]
        
        logger.info(
            "websocket_broadcast_to_role",
            role=role,
            target_count=len(target_users),
            message_type=message.type
        )
        
        tasks = []
        for user_id in target_users:
            tasks.append(self.send_personal_message(user_id, message))
            
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


# Global connection manager instance
connection_manager = ConnectionManager()


class WebSocketService:
    """Service for managing real-time WebSocket communications"""
    
    def __init__(self):
        self.manager = connection_manager
        
    async def send_request_status_update(
        self, 
        request_id: UUID, 
        status: str, 
        additional_data: Optional[Dict[str, Any]] = None
    ):
        """Send request status update to all subscribers"""
        data = {
            "request_id": str(request_id),
            "status": status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if additional_data:
            data.update(additional_data)
            
        message = RealtimeUpdate(
            type="request_status_update",
            data=data,
            timestamp=datetime.utcnow(),
            request_id=request_id
        )
        
        await self.manager.broadcast_to_request_subscribers(str(request_id), message)
        
    async def send_location_update(
        self,
        request_id: UUID,
        provider_location: Dict[str, float],
        estimated_arrival_time: Optional[int] = None
    ):
        """Send service provider location update with ETA"""
        data = {
            "request_id": str(request_id),
            "provider_location": provider_location,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if estimated_arrival_time:
            data["estimated_arrival_time"] = estimated_arrival_time
            
        message = RealtimeUpdate(
            type="location_update",
            data=data,
            timestamp=datetime.utcnow(),
            request_id=request_id
        )
        
        await self.manager.broadcast_to_request_subscribers(str(request_id), message)
        
    async def send_provider_assignment(
        self,
        request_id: UUID,
        provider_details: Dict[str, Any],
        estimated_arrival_time: int
    ):
        """Send service provider assignment notification"""
        data = {
            "request_id": str(request_id),
            "provider_details": provider_details,
            "estimated_arrival_time": estimated_arrival_time,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        message = RealtimeUpdate(
            type="provider_assigned",
            data=data,
            timestamp=datetime.utcnow(),
            request_id=request_id
        )
        
        await self.manager.broadcast_to_request_subscribers(str(request_id), message)
        
    async def send_provider_arrival(
        self,
        request_id: UUID,
        vehicle_details: Dict[str, Any]
    ):
        """Send service provider arrival notification"""
        data = {
            "request_id": str(request_id),
            "vehicle_details": vehicle_details,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        message = RealtimeUpdate(
            type="provider_arrived",
            data=data,
            timestamp=datetime.utcnow(),
            request_id=request_id
        )
        
        await self.manager.broadcast_to_request_subscribers(str(request_id), message)
        
    async def send_request_confirmation(
        self,
        request_id: UUID,
        user_id: UUID,
        confirmation_details: Dict[str, Any]
    ):
        """Send emergency request confirmation"""
        data = {
            "request_id": str(request_id),
            **confirmation_details,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        message = RealtimeUpdate(
            type="request_confirmed",
            data=data,
            timestamp=datetime.utcnow(),
            request_id=request_id,
            user_id=user_id
        )
        
        await self.manager.send_personal_message(str(user_id), message)
        
    async def notify_field_agent_assignment(
        self,
        agent_id: UUID,
        request_details: Dict[str, Any]
    ):
        """Notify field agent of new request assignment"""
        data = {
            "request_details": request_details,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        message = RealtimeUpdate(
            type="agent_assignment",
            data=data,
            timestamp=datetime.utcnow()
        )
        
        await self.manager.send_personal_message(str(agent_id), message)


# Global WebSocket service instance
websocket_service = WebSocketService()