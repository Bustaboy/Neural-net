from sqlalchemy.orm import Session
from core.database import get_db
import joblib
import numpy as np

def predict(db: Session = Depends(get_db)):
    """Make predictions using the central ensemble model."""
    model_path = "models/central_model.pkl"
    if not os.path.exists(model_path):
        raise ValueError(f"Central model not found at {model_path}. Train a model first.")

    model = joblib.load(model_path)
    # Fetch latest market data (simplified)
    market_data = db.execute(
        "SELECT price FROM market_data ORDER BY timestamp DESC LIMIT 1"
    ).fetchone()
    if not market_data:
        raise ValueError("No market data available for prediction.")

    X = np.array([[market_data[0]]])  # Use latest price as feature
    predictions = model.predict(X)
    return {"predictions": predictions.tolist()}
