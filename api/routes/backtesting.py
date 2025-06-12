# api/routes/backtesting.py
from fastapi import APIRouter
router = APIRouter(prefix="/backtesting")

@router.post("/run")
async def run_backtest(symbol: str, start_date: str, end_date: str):
    # Placeholder: Use scripts/backtest.py
    return {"pnl": 1000, "trades": 50}
