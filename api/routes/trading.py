# api/routes/trading.py
from fastapi import APIRouter, Depends
from trading.order_executor import OrderExecutor
router = APIRouter(prefix="/trading")

@router.post("/execute")
async def execute_trade(trade: TradeRequest, executor: OrderExecutor = Depends()):
    return executor.execute_trade(trade.symbol, trade.side, trade.amount)
