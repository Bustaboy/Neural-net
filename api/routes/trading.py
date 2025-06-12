# api/routes/trading.py
from fastapi import APIRouter, Depends
from flask_jwt_extended import get_jwt_identity
from core.database import EnhancedDatabaseManager

router = APIRouter(prefix="/trading")
db_manager = EnhancedDatabaseManager()

@router.get("/history")
async def get_trade_history(user_id: int = Depends(get_jwt_identity)):
    trades = db_manager.execute(
        "SELECT * FROM trades WHERE user_id = ? ORDER BY timestamp DESC LIMIT 50",
        (user_id,)
    )
    return {"trades": trades}
