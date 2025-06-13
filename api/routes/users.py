from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from core.database import get_db

router = APIRouter()

class ApiKeys(BaseModel):
    market_api_key: str
    exchange_api_key: str
    exchange_secret: str

def get_current_user(token: str):
    """Extract user_id from token (simplified; use JWT in production)."""
    try:
        user_id = int(token.replace("token_", ""))
        return user_id
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.post("/users/api-keys")
async def update_api_keys(keys: ApiKeys, user_id: int = Depends(get_current_user), db: Session = Depends(get_db)):
    """Save API keys for the current user."""
    db.execute(
        "UPDATE users SET market_api_key = :market, exchange_api_key = :exchange, exchange_secret = :secret WHERE id = :user_id",
        {
            "market": keys.market_api_key,
            "exchange": keys.exchange_api_key,
            "secret": keys.exchange_secret,
            "user_id": user_id
        }
    )
    db.commit()
    return {"message": "API keys updated"}

@router.get("/users/api-keys")
async def get_api_keys(user_id: int = Depends(get_current_user), db: Session = Depends(get_db)):
    """Retrieve API keys for the current user."""
    user = db.execute(
        "SELECT market_api_key, exchange_api_key, exchange_secret FROM users WHERE id = :user_id",
        {"user_id": user_id}
    ).fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "market_api_key": user.market_api_key or "",
        "exchange_api_key": user.exchange_api_key or "",
        "exchange_secret": user.exchange_secret or ""
    }
