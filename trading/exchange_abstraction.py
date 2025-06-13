from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
import ccxt  # For Binance integration

def execute_trade(user_id: int, symbol: str, amount: float, trade_type: str, db: Session = Depends(get_db)):
    """Execute a trade on Binance testnet or live based on user configuration."""
    try:
        # Fetch user's API keys and testnet setting
        user = db.execute(
            "SELECT exchange_api_key, exchange_secret FROM users WHERE id = :user_id",
            {"user_id": user_id}
        ).fetchone()
        if not user or not user.exchange_api_key or not user.exchange_secret:
            raise HTTPException(status_code=400, detail="No exchange API keys configured")

        exchange_api_key = user.exchange_api_key
        exchange_secret = user.exchange_secret

        # Fetch testnet setting (placeholder; to be saved in users table or config)
        testnet = False  # Default to live; update via GUI/config later
        # Example: Fetch from users table if added (e.g., "SELECT testnet FROM users WHERE id = :user_id")
        # testnet = db.execute("SELECT testnet FROM users WHERE id = :user_id", {"user_id": user_id}).fetchone()[0]

        # Initialize Binance client
        exchange = ccxt.binance({
            'apiKey': exchange_api_key,
            'secret': exchange_secret,
            'enableRateLimit': True,
            'test': testnet  # True for testnet, False for live
        })

        # Execute trade
        side = 'buy' if trade_type.lower() == 'buy' else 'sell'
        try:
            order = exchange.create_order(symbol, side.upper(), 'market', amount)
            return {"trade_id": order['id'], "status": "success"}
        except ccxt.ExchangeError as e:
            raise HTTPException(status_code=500, detail=f"Trade failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Trade execution failed: {e}")
