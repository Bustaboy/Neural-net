from sqlalchemy.orm import Session
from core.database import get_db
import joblib
import numpy as np
from fastapi import Depends

def predict(user_id: int, db: Session = Depends(get_db)):
    """Make predictions using the user-specific ensemble model."""
    model_path = f"models/user_{user_id}_model.pkl"
    if not os.path.exists(model_path):
        raise ValueError(f"Model not found at {model_path}. Train a model first.")

    model = joblib.load(model_path)
    # Fetch user-specific data (simplified)
    trades = db.execute(
        "SELECT amount FROM trades WHERE user_id = :user_id",
        {"user_id": user_id}
    ).fetchall()
    if not trades:
        raise ValueError("No trade data available for prediction.")

    X = np.array([[trade[0]] for trade in trades])  # Use amount as feature
    predictions = model.predict(X)
    return {"predictions": predictions.tolist(), "user_id": user_id}
