"""
WebSocket API endpoints for real-time communication
"""
import json
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.security import HTTPBearer
import structlog

from app.services.websocket import connection_manager, websocket_service
from app.core.auth import get_current_user_from_token, UserContext
from app.services.auth import AuthenticationError

logger = structlog.get_logger()
router = APIRouter()
security = HTTPBearer()


async def get_user_from_websocket_token(websocket: WebSocket) -> Optional[UserContext]:
    """Extract and validate user from WebSocket connection token"""
    try:
        # Get token from query parameters
        token = websocket.query_params.get("token")
        if not token:
            return None
            
        # Validate token and get user context
        user_context = await get_current_user_from_token(token)
        return user_context
        
    except Exception as e:
        logger.error("websocket_auth_error", error=str(e))
        return None


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates
    
    Query parameters:
    - token: JWT authentication token
    
    Message types sent to client:
    - request_status_update: Emergency request status changes
    - location_update: Service provider location updates with ETA
    - provider_assigned: Service provider assignment notification
    - provider_arrived: Service provider arrival notification
    - request_confirmed: Emergency request confirmation
    - agent_assignment: Field agent assignment notification
    
    Message types received from client:
    - subscribe_request: Subscribe to updates for a specific request
    - unsubscribe_request: Unsubscribe from request updates
    - location_update: Service provider location update (from field agents)
    """
    user_context = await get_user_from_websocket_token(websocket)
    
    if not user_context:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication required")
        return
        
    user_id = str(user_context.user_id)
    user_role = user_context.role
    
    await connection_manager.connect(websocket, user_id, user_role)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                message_type = message.get("type")
                
                logger.debug(
                    "websocket_message_received",
                    user_id=user_id,
                    message_type=message_type
                )
                
                if message_type == "subscribe_request":
                    request_id = message.get("request_id")
                    if request_id:
                        await connection_manager.subscribe_to_request(user_id, request_id)
                        
                elif message_type == "unsubscribe_request":
                    request_id = message.get("request_id")
                    if request_id:
                        await connection_manager.unsubscribe_from_request(user_id, request_id)
                        
                elif message_type == "location_update" and user_role in ["field_agent", "service_provider"]:
                    # Handle location updates from field agents/service providers
                    request_id = message.get("request_id")
                    location = message.get("location")
                    eta = message.get("estimated_arrival_time")
                    
                    if request_id and location:
                        await websocket_service.send_location_update(
                            UUID(request_id),
                            location,
                            eta
                        )
                        
                elif message_type == "ping":
                    # Handle ping/pong for connection health
                    await websocket.send_text(json.dumps({"type": "pong"}))
                    
                else:
                    logger.warning(
                        "websocket_unknown_message_type",
                        user_id=user_id,
                        message_type=message_type
                    )
                    
            except json.JSONDecodeError:
                logger.error(
                    "websocket_invalid_json",
                    user_id=user_id,
                    data=data
                )
                
            except Exception as e:
                logger.error(
                    "websocket_message_processing_error",
                    user_id=user_id,
                    error=str(e)
                )
                
    except WebSocketDisconnect:
        logger.info("websocket_client_disconnected", user_id=user_id)
        
    except Exception as e:
        logger.error(
            "websocket_connection_error",
            user_id=user_id,
            error=str(e)
        )
        
    finally:
        connection_manager.disconnect(user_id)


@router.websocket("/ws/field-agent")
async def field_agent_websocket(websocket: WebSocket):
    """
    Dedicated WebSocket endpoint for field agents
    
    Provides:
    - Request assignments
    - Status updates
    - Location tracking coordination
    """
    user_context = await get_user_from_websocket_token(websocket)
    
    if not user_context or user_context.role not in ["field_agent", "team_leader"]:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Field agent access required")
        return
        
    user_id = str(user_context.user_id)
    
    await connection_manager.connect(websocket, user_id, "field_agent")
    
    try:
        while True:
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                message_type = message.get("type")
                
                if message_type == "accept_request":
                    request_id = message.get("request_id")
                    if request_id:
                        # Notify all parties that agent accepted the request
                        await websocket_service.send_request_status_update(
                            UUID(request_id),
                            "accepted",
                            {"accepted_by": user_id}
                        )
                        
                elif message_type == "location_update":
                    request_id = message.get("request_id")
                    location = message.get("location")
                    eta = message.get("estimated_arrival_time")
                    
                    if request_id and location:
                        await websocket_service.send_location_update(
                            UUID(request_id),
                            location,
                            eta
                        )
                        
                elif message_type == "arrived":
                    request_id = message.get("request_id")
                    vehicle_details = message.get("vehicle_details", {})
                    
                    if request_id:
                        await websocket_service.send_provider_arrival(
                            UUID(request_id),
                            vehicle_details
                        )
                        
                elif message_type == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                    
            except json.JSONDecodeError:
                logger.error("field_agent_websocket_invalid_json", user_id=user_id)
                
            except Exception as e:
                logger.error("field_agent_websocket_error", user_id=user_id, error=str(e))
                
    except WebSocketDisconnect:
        logger.info("field_agent_websocket_disconnected", user_id=user_id)
        
    finally:
        connection_manager.disconnect(user_id)


@router.websocket("/ws/service-provider")
async def service_provider_websocket(websocket: WebSocket):
    """
    Dedicated WebSocket endpoint for external service providers
    
    Provides:
    - Emergency request assignments
    - Location tracking
    - Status updates
    """
    user_context = await get_user_from_websocket_token(websocket)
    
    if not user_context or user_context.role != "service_provider":
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Service provider access required")
        return
        
    user_id = str(user_context.user_id)
    
    await connection_manager.connect(websocket, user_id, "service_provider")
    
    try:
        while True:
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                message_type = message.get("type")
                
                if message_type == "accept_request":
                    request_id = message.get("request_id")
                    vehicle_details = message.get("vehicle_details", {})
                    
                    if request_id:
                        await websocket_service.send_request_status_update(
                            UUID(request_id),
                            "provider_accepted",
                            {
                                "provider_id": user_id,
                                "vehicle_details": vehicle_details
                            }
                        )
                        
                elif message_type == "location_update":
                    request_id = message.get("request_id")
                    location = message.get("location")
                    eta = message.get("estimated_arrival_time")
                    
                    if request_id and location:
                        await websocket_service.send_location_update(
                            UUID(request_id),
                            location,
                            eta
                        )
                        
                elif message_type == "arrived":
                    request_id = message.get("request_id")
                    vehicle_details = message.get("vehicle_details", {})
                    
                    if request_id:
                        await websocket_service.send_provider_arrival(
                            UUID(request_id),
                            vehicle_details
                        )
                        
                elif message_type == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                    
            except json.JSONDecodeError:
                logger.error("service_provider_websocket_invalid_json", user_id=user_id)
                
            except Exception as e:
                logger.error("service_provider_websocket_error", user_id=user_id, error=str(e))
                
    except WebSocketDisconnect:
        logger.info("service_provider_websocket_disconnected", user_id=user_id)
        
    finally:
        connection_manager.disconnect(user_id)