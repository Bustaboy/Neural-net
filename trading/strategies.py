from sqlalchemy.orm import Session
from core.database import get_db
from ml.ensemble import predict

def get_trading_strategy(user_id: int, db: Session = Depends(get_db)):
    """Determine trading strategy using the central model."""
    predictions = predict(db)
    if not predictions or not predictions["predictions"]:
        return None
    return {"symbol": "BTC", "amount": 0.01, "type": "buy" if predictions["predictions"][0] > 0.5 else "sell"}
