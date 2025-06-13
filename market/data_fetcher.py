from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db

def fetch_market_data(user_id: int, db: Session = Depends(get_db)):
    """Fetch market data using the user's API key."""
    user = db.execute(
        "SELECT market_api_key FROM users WHERE id = :user_id",
        {"user_id": user_id}
    ).fetchone()
    if not user or not user.market_api_key:
        raise HTTPException(status_code=400, detail="No market API key configured")
    api_key = user.market_api_key
    # Example: Fetch data from Alpha Vantage (uncomment and configure for real use)
    # try:
    #     response = requests.get(
    #         f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=BTC&interval=5min&apikey={api_key}",
    #         timeout=10
    #     )
    #     response.raise_for_status()
    #     data = response.json()
    #     # Process data...
    # except requests.RequestException:
    #     raise HTTPException(status_code=500, detail="Failed to fetch market data")
    # Dummy data for testing
    return {"symbol": "BTC", "price": 60000.75, "change": 2.5}
