# api/middleware.py
from fastapi import FastAPI, HTTPException, Request, Depends
from jose import jwt, JWTError
from config import ConfigManager
from core.database import EnhancedDatabaseManager
from fastapi.security import OAuth2PasswordBearer

db_manager = EnhancedDatabaseManager()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
SECRET_KEY = ConfigManager.get_config("jwt_secret", "your_jwt_secret")
ALGORITHM = "HS256"

def setup_middleware(app: FastAPI):
    async def subscription_middleware(request: Request, token: str = Depends(oauth2_scheme)):
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id: str = payload.get("sub")
            if user_id is None:
                raise HTTPException(status_code=401, detail="Invalid token")
            user_id = int(user_id)
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = db_manager.fetch_one(
            "SELECT subscription_tier FROM users WHERE id = ?", (user_id,)
        )
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        tier = user['subscription_tier']
        max_trades = ConfigManager.get_config(f"subscriptions.tiers.{tier}.max_trades_per_day", 100)
        trades_today = db_manager.fetch_one(
            "SELECT COUNT(*) FROM trades WHERE user_id = ? AND timestamp >= CURRENT_DATE",
            (user_id,)
        )[0]
        if trades_today >= max_trades:
            raise HTTPException(status_code=403, detail="Trade limit exceeded for your subscription")
        return user_id

    app.dependency_overrides['subscription_middleware'] = subscription_middleware
