from sqlalchemy.orm import Session
from core.database import get_db

def update_position(user_id: int, symbol: str, amount: float, trade_type: str, db: Session = Depends(get_db)):
    """Update user position based on trade, reverting to USDT."""
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

    usdt_asset = db.execute(
        "SELECT id, value FROM assets WHERE portfolio_id = :portfolio_id AND name = 'USDT'",
        {"portfolio_id": portfolio.id}
    ).fetchone()
    if not usdt_asset:
        db.execute(
            "INSERT INTO assets (portfolio_id, name, value) VALUES (:portfolio_id, 'USDT', 0.0)",
            {"portfolio_id": portfolio.id}
        )
        db.commit()
        usdt_asset = db.execute("SELECT id, value FROM assets WHERE portfolio_id = :portfolio_id AND name = 'USDT'", {"portfolio_id": portfolio.id}).fetchone()

    traded_asset = db.execute(
        "SELECT id, value FROM assets WHERE portfolio_id = :portfolio_id AND name = :symbol",
        {"portfolio_id": portfolio.id, "symbol": symbol}
    ).fetchone()
    # Fetch latest price from market_data (dummy for now)
    market_data = db.execute(
        "SELECT price FROM market_data WHERE symbol = :symbol ORDER BY timestamp DESC LIMIT 1",
        {"symbol": symbol}
    ).fetchone()
    price = market_data[0] if market_data else 60000.75  # Default dummy price
    value = amount * price

    if trade_type == "buy":
        if not traded_asset:
            db.execute(
                "INSERT INTO assets (portfolio_id, name, value) VALUES (:portfolio_id, :symbol, :value)",
                {"portfolio_id": portfolio.id, "symbol": symbol, "value": value}
            )
        else:
            new_value = traded_asset.value + value
            db.execute(
                "UPDATE assets SET value = :value WHERE id = :id",
                {"value": new_value, "id": traded_asset.id}
            )
        # Revert to USDT immediately
        if traded_asset:
            db.execute("DELETE FROM assets WHERE id = :id", {"id": traded_asset.id})
        else:
            db.execute(
                "UPDATE assets SET value = value - :value WHERE id = :id",
                {"value": value, "id": usdt_asset.id}
            )
        new_usdt_value = usdt_asset.value + value
        db.execute(
            "UPDATE assets SET value = :value WHERE id = :id",
            {"value": new_usdt_value, "id": usdt_asset.id}
        )
    elif trade_type == "sell":
        if traded_asset and traded_asset.value >= value:
            new_value = traded_asset.value - value
            if new_value <= 0:
                db.execute("DELETE FROM assets WHERE id = :id", {"id": traded_asset.id})
            else:
                db.execute(
                    "UPDATE assets SET value = :value WHERE id = :id",
                    {"value": new_value, "id": traded_asset.id}
                )
        # Revert to USDT immediately
        if traded_asset:
            db.execute(
                "UPDATE assets SET value = value + :value WHERE id = :id",
                {"value": value, "id": usdt_asset.id}
            )
        else:
            db.execute(
                "UPDATE assets SET value = value + :value WHERE id = :id",
                {"value": value, "id": usdt_asset.id}
            )
    db.commit()
