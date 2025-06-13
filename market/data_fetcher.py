from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
import ccxt
import time
import logging
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)

class MarketDataCache:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MarketDataCache, cls).__new__(cls)
            cls._instance.cache = defaultdict(dict)
            cls._instance.last_update = datetime.utcnow()
        return cls._instance

    def get(self, symbol):
        if (datetime.utcnow() - self.last_update).total_seconds() > 60:  # Cache for 1 minute
            self.cache.clear()
            self.last_update = datetime.utcnow()
        return self.cache.get(symbol)

    def set(self, symbol, data):
        self.cache[symbol] = data
        self.last_update = datetime.utcnow()

cache = MarketDataCache()

def fetch_market_data(user_id: int, db: Session = Depends(get_db)):
    global api_request_count, last_request_time
    api_request_count = getattr(fetch_market_data, 'api_request_count', 0)
    last_request_time = getattr(fetch_market_data, 'last_request_time', datetime.utcnow())

    try:
        current_time = datetime.utcnow()
        time_diff = (current_time - last_request_time).total_seconds()
        if time_diff > 1:
            api_request_count = 0
            last_request_time = current_time
        if api_request_count >= 10:
            logger.warning("API request limit reached, waiting...")
            time.sleep(1)
            api_request_count = 0
        api_request_count += 1
        setattr(fetch_market_data, 'api_request_count', api_request_count)
        setattr(fetch_market_data, 'last_request_time', last_request_time)

        user = db.execute(
            "SELECT market_api_key, exchange_api_key, exchange_secret FROM users WHERE id = :user_id",
            {"user_id": user_id}
        ).fetchone()
        if not user or not user.market_api_key or not user.exchange_api_key or not user.exchange_secret:
            raise HTTPException(status_code=400, detail="No API keys configured")

        market_api_key = user.market_api_key
        exchange_api_key = user.exchange_api_key
        exchange_secret = user.exchange_secret

        testnet = False  # Placeholder; fetch from users table later

        exchange = ccxt.binance({
            'apiKey': exchange_api_key,
            'secret': exchange_secret,
            'enableRateLimit': True,
            'test': testnet
        })

        symbols = ["BTC/USDT", "ETH/USDT", "LTC/USDT", "XRP/USDT"]
        for symbol in symbols:
            cached_data = cache.get(symbol)
            if cached_data and (datetime.utcnow() - cached_data.get("timestamp", datetime.utcnow())).total_seconds() < 60:
                price, change = cached_data["price"], cached_data["change"]
            else:
                try:
                    ticker = exchange.fetch_ticker(symbol)
                    price = ticker['last']
                    change = ticker['percentage'] if 'percentage' in ticker else 0.0
                    cache.set(symbol, {"price": price, "change": change, "timestamp": datetime.utcnow()})
                except ccxt.ExchangeError as e:
                    logger.error(f"Failed to fetch {symbol} data: {e}")
                    continue
            rsi = 50.0  # Placeholder
            db.execute(
                "INSERT INTO market_data (symbol, price, change, rsi, timestamp) VALUES (:symbol, :price, :change, :rsi, :timestamp)",
                {"symbol": symbol, "price": price, "change": change, "rsi": rsi, "timestamp": datetime.utcnow()}
            )
        db.commit()

        latest = db.execute("SELECT symbol, price, change, rsi FROM market_data ORDER BY timestamp DESC LIMIT 1").fetchone()
        return {"symbol": latest[0], "price": latest[1], "change": latest[2], "rsi": latest[3]} if latest else {"symbol": "BTC/USDT", "price": 0.0, "change": 0.0, "rsi": 50.0}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Market data fetch failed: {e}")
