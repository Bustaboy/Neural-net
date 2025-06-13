from sqlalchemy.orm import Session
from core.database import get_db
from fastapi import Depends
import pandas as pd
import joblib
import os

def train_model(user_id: int, db: Session = Depends(get_db)):
    """Train a model using user-specific market data."""
    # Fetch user-specific trades and market data
    trades = db.execute(
        "SELECT symbol, amount, type, timestamp FROM trades WHERE user_id = :user_id",
        {"user_id": user_id}
    ).fetchall()
    if not trades:
        raise ValueError("No trade data available for training.")

    # Convert to DataFrame (simplified; enhance with market data in production)
    data = pd.DataFrame(trades, columns=["symbol", "amount", "type", "timestamp"])
    # Placeholder: Add features (e.g., from market/data_fetcher.py)
    data["price"] = 60000.75  # Dummy price
    data["feature"] = data["amount"] * data["price"]  # Example feature

    # Train a simple model (replace with ensemble.py logic)
    X = data[["feature"]]
    y = [1 if t == "buy" else 0 for t in data["type"]]  # Dummy target
    from sklearn.linear_model import LinearRegression
    model = LinearRegression()
    model.fit(X, y)

    # Save model per user
    model_path = f"models/user_{user_id}_model.pkl"
    os.makedirs("models", exist_ok=True)
    joblib.dump(model, model_path)
    return {"message": f"Model trained and saved to {model_path}"}
