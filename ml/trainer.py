from sqlalchemy.orm import Session
from core.database import get_db
import pandas as pd
import joblib
import os

def train_model(db: Session = Depends(get_db)):
    """Train a central model using shared market data."""
    # Fetch all market data
    market_data = db.execute(
        "SELECT symbol, price, change, timestamp FROM market_data"
    ).fetchall()
    if not market_data:
        raise ValueError("No market data available for training.")

    # Convert to DataFrame
    data = pd.DataFrame(market_data, columns=["symbol", "price", "change", "timestamp"])
    data["feature"] = data["price"] * (1 + data["change"] / 100)  # Example feature

    # Train a simple model (replace with ensemble.py logic)
    X = data[["feature"]]
    y = [1 if c > 0 else 0 for c in data["change"]]  # Dummy target: positive change
    from sklearn.linear_model import LinearRegression
    model = LinearRegression()
    model.fit(X, y)

    # Save central model
    model_path = "models/central_model.pkl"
    os.makedirs("models", exist_ok=True)
    joblib.dump(model, model_path)
    return {"message": f"Central model trained and saved to {model_path}"}
