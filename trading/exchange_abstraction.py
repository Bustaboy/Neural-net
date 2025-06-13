from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db

def execute_trade(user_id: int, symbol: str, amount: float, trade_type: str, db: Session = Depends(get_db)):
    """Execute a trade using the user's exchange API keys."""
    user = db.execute(
        "SELECT exchange_api_key, exchange_secret FROM users WHERE id = :user_id",
        {"user_id": user_id}
    ).fetchone()
    if not user or not user.exchange_api_key or not user.exchange_secret:
        raise HTTPException(status_code=400, detail="No exchange API keys configured")
    api_key = user.exchange_api_key
    secret = user.exchange_secret
    # Example: Execute trade on Binance (uncomment and configure for real use)
    # try:
    #     import ccxt
    #     exchange = ccxt.binance({"apiKey": api_key, "secret": secret})
    #     order = exchange.create_order(symbol, trade_type, "market", amount)
    #     return {"trade_id": order["id"], "status": "success"}
    # except Exception as e:
    #     raise HTTPException(status_code=500, detail=f"Trade failed: {str(e)}")
    # Dummy data for testing
    return {"trade_id": f"trade_{symbol}_{amount}", "status": "success"}
