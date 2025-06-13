from sqlalchemy.orm import Session
from core.database import get_db
import pandas as pd
import joblib
import os
import yfinance as yf  # For historical data (install later)

def train_model(db: Session = Depends(get_db)):
    """Train a central model using 20 years of historical and live market data (placeholder)."""
    # Placeholder: Simulate data until console access
    market_data = db.execute("SELECT symbol, price, change, rsi, timestamp FROM market_data").fetchall()
    if not market_data:
        raise ValueError("No market data available for training.")

    data = pd.DataFrame(market_data, columns=["symbol", "price", "change", "rsi", "timestamp"])
    data["feature"] = data["price"] * (1 + data["change"] / 100) + data["rsi"] / 100  # Combined feature

    # Historical data placeholder (uncomment and configure when ready)
    # symbols = ["BTC-USD", "ETH-USD", "LTC-USD", "XRP-USD"]
    # historical_data = pd.DataFrame()
    # for symbol in symbols:
    #     stock = yf.download(symbol, start="2005-06-13", end="2025-06-13")
    #     stock = stock.rename(columns={"Close": "price"})
    #     stock["symbol"] = symbol.replace("-USD", "/USDT")
    #     stock["change"] = stock["price"].pct_change() * 100
    #     stock["rsi"] = 50.0  # Placeholder RSI; calculate later
    #     historical_data = pd.concat([historical_data, stock])

    # Combine historical and live data
    # data = pd.concat([historical_data, data]).dropna()

    X = data[["feature"]]
    y = [1 if c > 0 else 0 for c in data["change"]]  # Positive change target
    from sklearn.linear_model import LinearRegression
    model = LinearRegression()
    model.fit(X, y)

    model_path = "models/central_model.pkl"
    os.makedirs("models", exist_ok=True)
    joblib.dump(model, model_path)
    return {"message": f"Central model trained and saved to {model_path}"}
