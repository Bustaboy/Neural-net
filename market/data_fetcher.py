from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
import ccxt  # For Binance integration
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def fetch_market_data(user_id: int, db: Session = Depends(get_db)):
    """Fetch and store live market data using the user's API keys, respecting API limits."""
    global api_request_count, last_request_time
    api_request_count = getattr(fetch_market_data, 'api_request_count', 0)
    last_request_time = getattr(fetch_market_data, 'last_request_time', datetime.utcnow())

    try:
        # Check API limit (10 requests/second)
        current_time = datetime.utcnow()
        time_diff = (current_time - last_request_time).total_seconds()
        if time_diff > 1:
            api_request_count = 0
            last_request_time = current_time
        if api_request_count >= 10:  # Binance limit for ticker requests
            logger.warning("API request limit reached, waiting...")
            time.sleep(1)  # Wait 1 second to reset
            api_request_count = 0
        api_request_count += 1
        setattr(fetch_market_data, 'api_request_count', api_request_count)
        setattr(fetch_market_data, 'last_request_time', last_request_time)

        # Fetch user's API keys and testnet setting
        user = db.execute(
            "SELECT market_api_key, exchange_api_key, exchange_secret FROM users WHERE id = :user_id",
            {"user_id": user_id}
        ).fetchone()
        if not user or not user.market_api_key or not user.exchange_api_key or not user.exchange_secret:
            raise HTTPException(status_code=400, detail="No API keys configured for this user")

        market_api_key = user.market_api_key
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

        # Trading pairs to monitor
        symbols = ["BTC/USDT", "ETH/USDT", "LTC/USDT", "XRP/USDT"]
        for symbol in symbols:
            try:
                ticker = exchange.fetch_ticker(symbol)
                price = ticker['last']
                change = ticker['percentage'] if 'percentage' in ticker else 0.0
                rsi = 50.0  # Placeholder; replace with technical analysis
                db.execute(
                    "INSERT INTO market_data (symbol, price, change, rsi, timestamp) VALUES (:symbol, :price, :change, :rsi, :timestamp)",
                    {"symbol": symbol, "price": price, "change": change, "rsi": rsi, "timestamp": datetime.utcnow()}
                )
            except ccxt.ExchangeError as e:
                logger.error(f"Failed to fetch {symbol} data: {e}")
                continue
        db.commit()

        latest = db.execute(
            "SELECT symbol, price, change, rsi FROM market_data ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
        return {"symbol": latest[0], "price": latest[1], "change": latest[2], "rsi": latest[3]} if latest else {"symbol": "BTC/USDT", "price": 0.0, "change": 0.0, "rsi": 50.0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Market data fetch failed: {e}")
