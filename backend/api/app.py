# backend/api/app.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
import logging
from datetime import datetime

from .routes import auth_routes, trading_routes, user_routes, market_routes, portfolio_routes
from .middleware.authentication import AuthMiddleware
from .middleware.rate_limiter import RateLimitMiddleware
from .websocket.manager import WebSocketManager
from ..database.connection import DatabaseManager
from ..core.cache_manager import CacheManager
from ..trading.user_bot_manager import UserBotManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
db_manager = DatabaseManager()
cache_manager = CacheManager()
bot_manager = UserBotManager()
ws_manager = WebSocketManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    logger.info("Starting Trading Platform API...")
    
    # Initialize database
    try:
        db_manager.create_tables()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
    
    # Initialize cache
    await cache_manager.initialize()
    
    # Initialize WebSocket manager
    await ws_manager.initialize()
    
    yield
    
    # Shutdown
    logger.info("Shutting down Trading Platform API...")
    
    # Stop all active bots
    await bot_manager.stop_all_bots()
    
    # Close connections
    await cache_manager.close()
    await ws_manager.close()

# Create FastAPI app
app = FastAPI(
    title="Trading Platform API",
    description="Multi-user cryptocurrency trading platform",
    version="2.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://trading-platform.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.add_middleware(RateLimitMiddleware, calls=100, period=60)
app.add_middleware(AuthMiddleware)

# Include routers
app.include_router(auth_routes.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(user_routes.router, prefix="/api/users", tags=["Users"])
app.include_router(trading_routes.router, prefix="/api/trading", tags=["Trading"])
app.include_router(market_routes.router, prefix="/api/market", tags=["Market Data"])
app.include_router(portfolio_routes.router, prefix="/api/portfolio", tags=["Portfolio"])

# WebSocket endpoint
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket, client_id: str):
    await ws_manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            await ws_manager.handle_message(client_id, data)
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
    finally:
        await ws_manager.disconnect(client_id)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0",
        "services": {
            "database": db_manager.is_healthy(),
            "cache": await cache_manager.is_healthy(),
            "websocket": ws_manager.active_connections_count()
        }
    }

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error occurred"}
    )

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
