from sqlalchemy.orm import Session
from core.database import get_db
import pandas as pd
import joblib
import os
import yfinance as yf
from alpha_vantage.timeseries import TimeSeries
import logging
from fastapi import Depends, HTTPException
from stable_baselines3 import DQN  # For RL

logger = logging.getLogger(__name__)

def train_model(user_id: int, db: Session = Depends(get_db)):
    """Train an adaptive central model with collaborative learning."""
    user = db.execute("SELECT market_api_key FROM users WHERE id = :user_id", {"user_id": user_id}).fetchone()
    if not user or not user.market_api_key:
        raise HTTPException(status_code=400, detail="No market API key configured")

    market_api_key = user.market_api_key

    # Fetch live and historical data from all users
    market_data = db.execute("SELECT symbol, price, change, rsi, timestamp FROM market_data").fetchall()
    live_data = pd.DataFrame(market_data, columns=["symbol", "price", "change", "rsi", "timestamp"])
    live_data["feature"] = live_data["price"] * (1 + live_data["change"] / 100) + live_data["rsi"] / 100

    historical_data = pd.DataFrame()
    try:
        ts = TimeSeries(key=market_api_key, output_format='pandas')
        symbols = ["BTC", "ETH", "LTC", "XRP"]
        for symbol in symbols:
            logger.info(f"Fetching historical data for {symbol}")
            data, meta = ts.get_daily(symbol=symbol, outputsize='full')
            data = data.rename(columns={"4. close": "price"})
            data["symbol"] = f"{symbol}/USDT"
            data["change"] = data["price"].pct_change() * 100
            data["rsi"] = 50.0
            historical_data = pd.concat([historical_data, data])

        for symbol in ["BTC-USD", "ETH-USD", "LTC-USD", "XRP-USD"]:
            logger.info(f"Supplementing historical data for {symbol}")
            stock = yf.download(symbol, start="2005-06-13", end="2025-06-13")
            stock = stock.rename(columns={"Close": "price"})
            stock["symbol"] = symbol.replace("-USD", "/USDT")
            stock["change"] = stock["price"].pct_change() * 100
            stock["rsi"] = 50.0
            historical_data = pd.concat([historical_data, stock])

        data = pd.concat([historical_data, live_data]).dropna()
        if data.empty:
            raise ValueError("No data available")
    except Exception as e:
        logger.error(f"Historical data fetch failed: {e}")
        data = live_data
        if data.empty:
            raise ValueError("No data available")

    # Collaborative learning placeholder
    # Fetch aggregated user trade data
    # trade_data = db.execute("SELECT symbol, amount, type, timestamp FROM trades").fetchall()
    # data = pd.concat([data, pd.DataFrame(trade_data, columns=["symbol", "amount", "type", "timestamp"])])
    # env = CustomTradingEnv(data)  # Define with gym
    # model = DQN("MlpPolicy", env, verbose=1)
    # model.learn(total_timesteps=10000)

    X = data[["feature"]]
    y = [1 if c > 0 else 0 for c in data["change"]]
    from sklearn.linear_model import LinearRegression
    model = LinearRegression()
    model.fit(X, y)

    model_path = "models/central_model.pkl"
    os.makedirs("models", exist_ok=True)
    joblib.dump(model, model_path)
    return {"message": f"Central model trained with {len(data)} data points and saved to {model_path}"}
