from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
import random
from datetime import datetime

def fetch_market_data(user_id: int, db: Session = Depends(get_db)):
    """Fetch and store simulated market data for all users with technical indicators."""
    symbols = ["BTC", "ETH", "LTC", "XRP"]  # Diversified symbols
    for symbol in symbols:
        change = random.uniform(-2.0, 2.0)  # Random change between -2% and +2%
        price = 60000.75 if symbol == "BTC" else 3000.50 if symbol == "ETH" else 150.25 if symbol == "LTC" else 0.50  # Dummy prices
        # Simulate RSI (14-period, dummy value between 30-70)
        rsi = random.uniform(30.0, 70.0)
        db.execute(
            "INSERT INTO market_data (symbol, price, change, rsi) VALUES (:symbol, :price, :change, :rsi)",
            {"symbol": symbol, "price": price, "change": change, "rsi": rsi}
        )
    db.commit()
    # Return latest data for the user (all users share the same data)
    latest = db.execute(
        "SELECT symbol, price, change, rsi FROM market_data ORDER BY timestamp DESC LIMIT 1"
    ).fetchone()
    return {"symbol": latest[0], "price": latest[1], "change": latest[2], "rsi": latest[3]} if latest else {"symbol": "BTC", "price": 60000.75, "change": 0.0, "rsi": 50.0}
