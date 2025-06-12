# backend/api/websocket/manager.py
import asyncio
from typing import Dict, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect
import json
import logging
from datetime import datetime
from uuid import UUID

from ...core.cache_manager import CacheManager
from ..auth.jwt_handler import JWTHandler

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages WebSocket connections for all users"""
    
    def __init__(self):
        # Store active connections by user_id
        self.active_connections: Dict[str, WebSocket] = {}
        # Store user subscriptions
        self.subscriptions: Dict[str, Set[str]] = {}
        # JWT handler for authentication
        self.jwt_handler = JWTHandler()
        # Cache manager
        self.cache_manager = CacheManager()
        
    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.subscriptions[client_id] = set()
        logger.info(f"Client {client_id} connected")
        
        # Send connection confirmation
        await self.send_personal_message(
            {
                "type": "connection",
                "status": "connected",
                "timestamp": datetime.utcnow().isoformat()
            },
            client_id
        )
    
    def disconnect(self, client_id: str):
        """Remove WebSocket connection"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            del self.subscriptions[client_id]
            logger.info(f"Client {client_id} disconnected")
    
    async def send_personal_message(self, message: dict, client_id: str):
        """Send message to specific client"""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to {client_id}: {e}")
                self.disconnect(client_id)
    
    async def broadcast(self, message: dict, channel: str = None):
        """Broadcast message to all connected clients or specific channel"""
        disconnected_clients = []
        
        for client_id, websocket in self.active_connections.items():
            # Check if client is subscribed to channel
            if channel and channel not in self.subscriptions.get(client_id, set()):
                continue
                
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to {client_id}: {e}")
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)
    
    async def handle_message(self, client_id: str, data: str):
        """Handle incoming WebSocket message"""
        try:
            message = json.loads(data)
            message_type = message.get("type")
            
            if message_type == "subscribe":
                await self._handle_subscribe(client_id, message)
            elif message_type == "unsubscribe":
                await self._handle_unsubscribe(client_id, message)
            elif message_type == "ping":
                await self._handle_ping(client_id)
            elif message_type == "auth":
                await self._handle_auth(client_id, message)
            else:
                await self.send_personal_message(
                    {"type": "error", "message": f"Unknown message type: {message_type}"},
                    client_id
                )
                
        except json.JSONDecodeError:
            await self.send_personal_message(
                {"type": "error", "message": "Invalid JSON"},
                client_id
            )
        except Exception as e:
            logger.error(f"Error handling message from {client_id}: {e}")
            await self.send_personal_message(
                {"type": "error", "message": "Internal error"},
                client_id
            )
    
    async def _handle_subscribe(self, client_id: str, message: dict):
        """Handle channel subscription"""
        channels = message.get("channels", [])
        if isinstance(channels, str):
            channels = [channels]
        
        for channel in channels:
            self.subscriptions[client_id].add(channel)
        
        await self.send_personal_message(
            {
                "type": "subscribed",
                "channels": list(self.subscriptions[client_id]),
                "timestamp": datetime.utcnow().isoformat()
            },
            client_id
        )
    
    async def _handle_unsubscribe(self, client_id: str, message: dict):
        """Handle channel unsubscription"""
        channels = message.get("channels", [])
        if isinstance(channels, str):
            channels = [channels]
        
        for channel in channels:
            self.subscriptions[client_id].discard(channel)
        
        await self.send_personal_message(
            {
                "type": "unsubscribed",
                "channels": list(self.subscriptions[client_id]),
                "timestamp": datetime.utcnow().isoformat()
            },
            client_id
        )
    
    async def _handle_ping(self, client_id: str):
        """Handle ping message"""
        await self.send_personal_message(
            {
                "type": "pong",
                "timestamp": datetime.utcnow().isoformat()
            },
            client_id
        )
    
    async def _handle_auth(self, client_id: str, message: dict):
        """Handle authentication"""
        token = message.get("token")
        if not token:
            await self.send_personal_message(
                {"type": "auth_error", "message": "No token provided"},
                client_id
            )
            return
        
        try:
            # Verify token
            payload = self.jwt_handler.verify_token(token)
            user_id = payload.get("user_id")
            
            # Store authenticated user
            self.authenticated_users[client_id] = user_id
            
            await self.send_personal_message(
                {
                    "type": "authenticated",
                    "user_id": user_id,
                    "timestamp": datetime.utcnow().isoformat()
                },
                client_id
            )
        except Exception as e:
            await self.send_personal_message(
                {"type": "auth_error", "message": str(e)},
                client_id
            )
    
    def active_connections_count(self) -> int:
        """Get number of active connections"""
        return len(self.active_connections)
    
    def get_subscribed_clients(self, channel: str) -> Set[str]:
        """Get clients subscribed to a channel"""
        clients = set()
        for client_id, channels in self.subscriptions.items():
            if channel in channels:
                clients.add(client_id)
        return clients


class WebSocketManager:
    """High-level WebSocket manager with business logic"""
    
    def __init__(self):
        self.connection_manager = ConnectionManager()
        self.cache_manager = CacheManager()
        self._notification_task = None
        
    async def initialize(self):
        """Initialize WebSocket manager"""
        await self.cache_manager.initialize()
        # Start background tasks
        self._notification_task = asyncio.create_task(self._process_notifications())
    
    async def close(self):
        """Close WebSocket manager"""
        if self._notification_task:
            self._notification_task.cancel()
            try:
                await self._notification_task
            except asyncio.CancelledError:
                pass
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """Handle new WebSocket connection"""
        await self.connection_manager.connect(websocket, client_id)
    
    async def disconnect(self, client_id: str):
        """Handle WebSocket disconnection"""
        self.connection_manager.disconnect(client_id)
    
    async def handle_message(self, client_id: str, data: str):
        """Handle incoming message"""
        await self.connection_manager.handle_message(client_id, data)
    
    async def send_to_user(self, user_id: str, message: dict):
        """Send message to specific user"""
        # Find client connections for this user
        for client_id in self.connection_manager.active_connections:
            if client_id.startswith(f"user_{user_id}"):
                await self.connection_manager.send_personal_message(message, client_id)
    
    async def broadcast_market_update(self, symbol: str, data: dict):
        """Broadcast market update"""
        message = {
            "type": "market_update",
            "symbol": symbol,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.connection_manager.broadcast(message, f"market_{symbol}")
    
    async def broadcast_portfolio_update(self, user_id: str, data: dict):
        """Broadcast portfolio update to user"""
        message = {
            "type": "portfolio_update",
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_to_user(user_id, message)
    
    async def broadcast_trade_update(self, user_id: str, trade_data: dict):
        """Broadcast trade execution update"""
        message = {
            "type": "trade_executed",
            "data": trade_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_to_user(user_id, message)
    
    async def broadcast_bot_status(self, user_id: str, status_data: dict):
        """Broadcast bot status update"""
        message = {
            "type": "bot_status",
            "data": status_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.send_to_user(user_id, message)
    
    async def _process_notifications(self):
        """Process notifications from cache and send via WebSocket"""
        while True:
            try:
                # Check for pending notifications in cache
                pattern = "ws_notification:*"
                keys = await self.cache_manager.redis_client.keys(pattern)
                
                for key in keys:
                    try:
                        notification = await self.cache_manager.get(key)
                        if notification:
                            # Extract user_id from key
                            parts = key.split(":")
                            if len(parts) >= 3:
                                user_id = parts[1]
                                await self.send_to_user(user_id, notification)
                            
                            # Delete from cache after sending
                            await self.cache_manager.delete(key)
                    except Exception as e:
                        logger.error(f"Error processing notification {key}: {e}")
                
                # Sleep before next check
                await asyncio.sleep(1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in notification processor: {e}")
                await asyncio.sleep(5)
    
    def active_connections_count(self) -> int:
        """Get active connections count"""
        return self.connection_manager.active_connections_count()
