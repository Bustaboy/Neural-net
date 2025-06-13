from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
import ccxt  # For Binance integration
import time
import logging

logger = logging.getLogger(__name__)

def execute_trade(user_id: int, symbol: str, amount: float, trade_type: str, db: Session = Depends(get_db)):
    """Execute a trade on Binance testnet or live with API limit respect."""
    global api_request_count, last_request_time
    api_request_count = getattr(execute_trade, 'api_request_count', 0)
    last_request_time = getattr(execute_trade, 'last_request_time', datetime.utcnow())

    try:
        # Check API limit (10 requests/second)
        current_time = datetime.utcnow()
        time_diff = (current_time - last_request_time).total_seconds()
        if time_diff > 1:
            api_request_count = 0
            last_request_time = current_time
        if api_request_count >= 10:  # Binance limit for some endpoints
            logger.warning("API request limit reached, waiting...")
            time.sleep(1)  # Wait 1 second to reset
            api_request_count = 0
        api_request_count += 1
        setattr(execute_trade, 'api_request_count', api_request_count)
        setattr(execute_trade, 'last_request_time', last_request_time)

        # Fetch user's API keys and testnet setting
        user = db.execute(
            "SELECT exchange_api_key, exchange_secret FROM users WHERE id = :user_id",
            {"user_id": user_id}
        ).fetchone()
        if not user or not user.exchange_api_key or not user.exchange_secret:
            raise HTTPException(status_code=400, detail="No exchange API keys configured")

        exchange_api_key = user.exchange_api_key
        exchange_secret = user.exchange_secret

        # Fetch testnet setting (placeholder; update schema if needed)
        testnet = False  # Default to live; fetch from users table later
        # testnet = db.execute("SELECT testnet FROM users WHERE id = :user_id", {"user_id": user_id}).fetchone()[0]

        # Initialize Binance client
        exchange = ccxt.binance({
            'apiKey': exchange_api_key,
            'secret': exchange_secret,
            'enableRateLimit': True,
            'test': testnet
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
