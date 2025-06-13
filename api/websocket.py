# api/websocket.py
from socketio import AsyncServer, ASGIApp
from fastapi import FastAPI
from typing import Dict, Any
import logging
import asyncio
import zstd

sio = AsyncServer(async_mode='asgi', cors_allowed_origins='*', compression=True)  # Enable compression
logger = logging.getLogger(__name__)
fetcher = MarketDataFetcher()

def setup_websocket(app: FastAPI):
    app.mount("/socket.io/", ASGIApp(sio))

    @sio.event
    async def connect(sid, environ):
        logger.info(f"WebSocket connected: {sid}")

    @sio.event
    async def disconnect(sid):
        logger.info(f"WebSocket disconnected: {sid}")

    async def notify_web_clients(message: Dict[str, Any]):
        compressed_message = zstd.compress(json.dumps(message).encode())
        await sio.emit('model_retrained', compressed_message)
        logger.debug(f"WebSocket notification: {message}")

    async def stream_market_data():
        while True:
            data = await fetcher.fetch_ohlcv('BTC/USDT', '1m', limit=1)
            compressed_data = zstd.compress(json.dumps({'price': data[0][4]}).encode())
            await sio.emit('market_data', compressed_data)
            await asyncio.sleep(5)  # 5-second interval

    sio.start_background_task(stream_market_data)
