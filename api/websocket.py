# api/websocket.py
from socketio import AsyncServer, ASGIApp
from fastapi import FastAPI
from typing import Dict, Any
import logging

sio = AsyncServer(async_mode='asgi', cors_allowed_origins='*')
logger = logging.getLogger(__name__)

def setup_websocket(app: FastAPI):
    app.mount("/socket.io/", ASGIApp(sio))

    @sio.event
    async def connect(sid, environ):
        logger.info(f"WebSocket connected: {sid}")

    @sio.event
    async def disconnect(sid):
        logger.info(f"WebSocket disconnected: {sid}")

    async def notify_web_clients(message: Dict[str, Any]):
        await sio.emit('model_retrained', message)
        logger.debug(f"WebSocket notification: {message}")

    async def stream_market_data(data: Dict[str, Any]):
        await sio.emit('market_data', data)
