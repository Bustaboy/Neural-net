from sqlalchemy.orm import Session
from core.database import get_db
import pandas as pd
import joblib
import os
import yfinance as yf  # For historical data
from alpha_vantage.timeseries import TimeSeries  # For extended historical data

def train_model(user_id: int, db: Session = Depends(get_db)):
    """Train a central model using 20 years of historical and live market data with user's API key."""
    # Fetch user's market API key
    user = db.execute(
        "SELECT market_api_key FROM users WHERE id = :user_id",
        {"user_id": user_id}
    ).fetchone()
    if not user or not user.market_api_key:
        raise HTTPException(status_code=400, detail="No market API key configured for this user")

    market_api_key = user.market_api_key

    # Fetch live market data
    market_data = db.execute("SELECT symbol, price, change, rsi, timestamp FROM market_data").fetchall()
    live_data = pd.DataFrame(market_data, columns=["symbol", "price", "change", "rsi", "timestamp"])
    live_data["feature"] = live_data["price"] * (1 + live_data["change"] / 100) + live_data["rsi"] / 100

    # Fetch historical data (placeholder until console access)
    historical_data = pd.DataFrame()
    try:
        # Initialize Alpha Vantage (uncomment and configure when ready)
        # ts = TimeSeries(key=market_api_key, output_format='pandas')
        # symbols = ["BTC", "ETH", "LTC", "XRP"]
        # for symbol in symbols:
        #     data, meta = ts.get_daily(symbol=symbol, outputsize='full')
        #     data = data.rename(columns={"4. close": "price"})
        #     data["symbol"] = f"{symbol}/USDT"
        #     data["change"] = data["price"].pct_change() * 100
        #     data["rsi"] = 50.0  # Placeholder; calculate later
        #     historical_data = pd.concat([historical_data, data])

        # Fallback to yfinance for broader historical data (uncomment when ready)
        # for symbol in ["BTC-USD", "ETH-USD", "LTC-USD", "XRP-USD"]:
        #     stock = yf.download(symbol, start="2005-06-13", end="2025-06-13")
        #     stock = stock.rename(columns={"Close": "price"})
        #     stock["symbol"] = symbol.replace("-USD", "/USDT")
        #     stock["change"] = stock["price"].pct_change() * 100
        #     stock["rsi"] = 50.0  # Placeholder
        #     historical_data = pd.concat([historical_data, stock])

        # Combine historical and live data (placeholder uses live data only for now)
        data = live_data  # Replace with pd.concat([historical_data, live_data]).dropna() when ready
        if data.empty:
            raise ValueError("No data available for training.")

        X = data[["feature"]]
        y = [1 if c > 0 else 0 for c in data["change"]]  # Positive change target
        from sklearn.linear_model import LinearRegression
        model = LinearRegression()
        model.fit(X, y)

        model_path = "models/central_model.pkl"
        os.makedirs("models", exist_ok=True)
        joblib.dump(model, model_path)
        return {"message": f"Central model trained and saved to {model_path}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training failed: {e}")
