# api/app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORS
from starlette.middleware.sessions import SessionMiddleware
from api.routes import alerts, auth, backtesting, market, monitoring, portfolio, subscriptions, trading, users
from api.websocket import setup_websocket
from config import ConfigManager

app = FastAPI(title="Neural-net Trading API")

# CORS configuration
CORS(app, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Session configuration
app.add_middleware(SessionMiddleware, secret_key=ConfigManager.get_config("session_secret", "default_secret"))

# Setup WebSocket
setup_websocket(app)

# Register routes
app.include_router(alerts.router)
app.include_router(auth.router)
app.include_router(backtesting.router)
app.include_router(market.router)
app.include_router(monitoring.router)
app.include_router(portfolio.router)
app.include_router(subscriptions.router)
app.include_router(trading.router)
app.include_router(users.router)

@app.on_event("startup")
async def startup_event():
    print("Neural-net API started")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
