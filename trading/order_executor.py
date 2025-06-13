from trading.exchange_abstraction import execute_trade
from fastapi import Depends

def execute_order(user_id: int, symbol: str, amount: float, trade_type: str, db: Session = Depends(get_db)):
    """Execute a trading order for the user."""
    return execute_trade(user_id, symbol, amount, trade_type, db)
