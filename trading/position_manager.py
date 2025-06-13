from sqlalchemy.orm import Session
from core.database import get_db

def update_position(user_id: int, symbol: str, amount: float, trade_type: str, db: Session = Depends(get_db)):
    """Update user position based on trade."""
    portfolio = db.execute(
        "SELECT id FROM portfolio WHERE user_id = :user_id",
        {"user_id": user_id}
    ).fetchone()
    if not portfolio:
        db.execute(
            "INSERT INTO portfolio (user_id, cash) VALUES (:user_id, 1000.0)",
            {"user_id": user_id}
        )
        db.commit()
        portfolio = db.execute("SELECT id FROM portfolio WHERE user_id = :user_id", {"user_id": user_id}).fetchone()

    asset = db.execute(
        "SELECT id, value FROM assets WHERE portfolio_id = :portfolio_id AND name = :symbol",
        {"portfolio_id": portfolio.id, "symbol": symbol}
    ).fetchone()
    price = 60000.75  # Dummy price; replace with market data later
    if trade_type == "buy":
        if not asset:
            db.execute(
                "INSERT INTO assets (portfolio_id, name, value) VALUES (:portfolio_id, :symbol, :amount)",
                {"portfolio_id": portfolio.id, "symbol": symbol, "amount": amount * price}
            )
        else:
            new_value = asset.value + (amount * price)
            db.execute(
                "UPDATE assets SET value = :value WHERE id = :id",
                {"value": new_value, "id": asset.id}
            )
    elif trade_type == "sell":
        if asset and asset.value >= (amount * price):
            new_value = asset.value - (amount * price)
            if new_value <= 0:
                db.execute("DELETE FROM assets WHERE id = :id", {"id": asset.id})
            else:
                db.execute(
                    "UPDATE assets SET value = :value WHERE id = :id",
                    {"value": new_value, "id": asset.id}
                )
    db.commit()
