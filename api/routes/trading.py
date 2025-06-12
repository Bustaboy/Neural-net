# api/routes/trading.py
from fastapi import APIRouter, Depends
from flask_jwt_extended import get_jwt_identity
from core.database import EnhancedDatabaseManager
from pydantic import BaseModel
from utils.audit import AuditLogger

router = APIRouter(prefix="/trading")
db_manager = EnhancedDatabaseManager()

@router.get("/history")
async def get_trade_history(user_id: int = Depends(get_jwt_identity)):
    trades = db_manager.execute(
        "SELECT * FROM trades WHERE user_id = ? ORDER BY timestamp DESC LIMIT 50",
        (user_id,)
    )
    return {"trades": trades}

class TradeRequest(BaseModel):
    symbol: str
    side: str
    amount: float

@router.post("/execute")
async def execute_trade(trade: TradeRequest, user_id: int = Depends(subscription_middleware)):
    # Placeholder: Use trading/order_executor.py
    return {"status": "trade_placed"}

@router.post("/execute")
async def execute_trade(trade: TradeRequest, user_id: int = Depends(subscription_middleware)):
    audit_logger = AuditLogger(db_manager)
    audit_logger.log_action(user_id, "trade", {"symbol": trade.symbol, "side": trade.side})
    # Execute trade
    return {"status": "trade_placed"}
