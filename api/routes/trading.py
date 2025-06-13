# api/routes/trading.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from jose import jwt, JWTError
from core.database import EnhancedDatabaseManager
from trading.order_executor import OrderExecutor
from utils.audit import AuditLogger
from config import ConfigManager

router = APIRouter(prefix="/trading")
db_manager = EnhancedDatabaseManager()
order_executor = OrderExecutor(db_manager)

# JWT configuration
SECRET_KEY = ConfigManager.get_config("jwt_secret", "your_jwt_secret")
ALGORITHM = "HS256"

def get_current_user(token: str = Depends(lambda: Depends(lambda: None))):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return int(user_id)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.get("/history")
async def get_trade_history(user_id: int = Depends(get_current_user)):
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
async def execute_trade(trade: TradeRequest, user_id: int = Depends(get_current_user)):
    audit_logger = AuditLogger(db_manager)
    audit_logger.log_action(user_id, "trade", {"symbol": trade.symbol, "side": trade.side, "amount": trade.amount})
    
    try:
        trade_result = await order_executor.execute_trade(
            user_id=user_id,
            symbol=trade.symbol,
            side=trade.side,
            amount=trade.amount
        )
        return {"status": "trade_placed", "trade_id": trade_result["trade_id"]}
    except Exception as e:
        audit_logger.log_action(user_id, "trade_error", {"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Trade execution failed: {str(e)}")
