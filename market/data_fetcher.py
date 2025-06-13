from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
import ccxt  # For Binance live data
import time
import logging

logger = logging.getLogger(__name__)

def fetch_market_data(user_id: int, db: Session = Depends(get_db)):
    """Fetch and store live market data using the user's API keys, with support for historical ingestion."""
    try:
        # Fetch user's API keys
        user = db.execute(
            "SELECT market_api_key, exchange_api_key, exchange_secret FROM users WHERE id = :user_id",
            {"user_id": user_id}
        ).fetchone()
        if not user or not user.market_api_key or not user.exchange_api_key or not user.exchange_secret:
            raise HTTPException(status_code=400, detail="No API keys configured for this user")

        market_api_key = user.market_api_key  # For Alpha Vantage or yfinance
        exchange_api_key = user.exchange_api_key  # For Binance
        exchange_secret = user.exchange_secret  # For Binance

        # Initialize Binance client
        exchange = ccxt.binance({
            'apiKey': exchange_api_key,
            'secret': exchange_secret,
            'enableRateLimit': True,
        })

        # Trading pairs to monitor
        symbols = ["BTC/USDT", "ETH/USDT", "LTC/USDT", "XRP/USDT"]
        for symbol in symbols:
            try:
                # Fetch live ticker data from Binance
                ticker = exchange.fetch_ticker(symbol)
                price = ticker['last']
                change = ticker['percentage'] if 'percentage' in ticker else 0.0
                # Placeholder RSI (to be calculated later with real data)
                rsi = 50.0  # Dummy value; replace with technical analysis
                db.execute(
                    "INSERT INTO market_data (symbol, price, change, rsi, timestamp) VALUES (:symbol, :price, :change, :rsi, :timestamp)",
                    {"symbol": symbol, "price": price, "change": change, "rsi": rsi, "timestamp": datetime.utcnow()}
                )
            except ccxt.ExchangeError as e:
                logger.error(f"Failed to fetch {symbol} data: {e}")
                continue
        db.commit()

        # Return latest data for the user
        latest = db.execute(
            "SELECT symbol, price, change, rsi FROM market_data ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
        return {"symbol": latest[0], "price": latest[1], "change": latest[2], "rsi": latest[3]} if latest else {"symbol": "BTC/USDT", "price": 0.0, "change": 0.0, "rsi": 50.0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Market data fetch failed: {e}")
