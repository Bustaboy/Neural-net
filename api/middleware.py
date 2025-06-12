# api/middleware.py
from fastapi import FastAPI, HTTPException, Request
from flask_jwt_extended import get_jwt_identity
from config import ConfigManager
from core.database import EnhancedDatabaseManager

db_manager = EnhancedDatabaseManager()

def setup_middleware(app: FastAPI):
    async def subscription_middleware(request: Request):
        user_id = get_jwt_identity()
        user = db_manager.fetch_one(
            "SELECT subscription_tier FROM users WHERE id = ?", (user_id,)
        )
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        tier = user['subscription_tier']
        max_trades = ConfigManager.get_config(f"subscriptions.tiers.{tier}.max_trades_per_day")
        trades_today = db_manager.fetch_one(
            "SELECT COUNT(*) FROM trades WHERE user_id = ? AND timestamp >= CURRENT_DATE",
            (user_id,)
        )[0]
        if trades_today >= max_trades:
            raise HTTPException(status_code=403, detail="Trade limit exceeded for your subscription")
        return user_id

    app.dependency_overrides['subscription_middleware'] = subscription_middleware
