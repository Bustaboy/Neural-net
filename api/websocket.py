# api/websocket.py
from socketio import AsyncServer, ASGIApp
from fastapi import FastAPI
from typing import Dict, Any
import logging
from market.data_fetcher import MarketDataFetcher

sio = AsyncServer(async_mode='asgi', cors_allowed_origins='*')
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
        await sio.emit('model_retrained', message)
        logger.debug(f"WebSocket notification: {message}")

    async def stream_market_data():
        while True:
            data = await fetcher.fetch_ohlcv('BTC/USDT', '1m', limit=1)
            await sio.emit('market_data', {'price': data[0][4]})
            await asyncio.sleep(60)

    # Start streaming in background
    sio.start_background_task(stream_market_data)
