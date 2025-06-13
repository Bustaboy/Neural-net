from sqlalchemy.orm import Session
from core.database import get_db

def update_position(user_id: int, symbol: str, amount: float, trade_type: str, db: Session = Depends(get_db)):
    """Update user position with dynamic hedging support."""
    portfolio = db.execute("SELECT id, cash FROM portfolio WHERE user_id = :user_id", {"user_id": user_id}).fetchone()
    if not portfolio:
        db.execute("INSERT INTO portfolio (user_id, cash) VALUES (:user_id, 1000.0)", {"user_id": user_id})
        db.commit()
        portfolio = db.execute("SELECT id, cash FROM portfolio WHERE user_id = :user_id", {"user_id": user_id}).fetchone()

    portfolio_id, cash = portfolio
    usdt_asset = db.execute("SELECT id, value FROM assets WHERE portfolio_id = :portfolio_id AND name = 'USDT'", {"portfolio_id": portfolio_id}).fetchone()
    if not usdt_asset:
        db.execute("INSERT INTO assets (portfolio_id, name, value) VALUES (:portfolio_id, 'USDT', 0.0)", {"portfolio_id": portfolio_id})
        db.commit()
        usdt_asset = db.execute("SELECT id, value FROM assets WHERE portfolio_id = :portfolio_id AND name = 'USDT'", {"portfolio_id": portfolio_id}).fetchone()

    usdt_id, usdt_value = usdt_asset
    traded_asset = db.execute("SELECT id, value FROM assets WHERE portfolio_id = :portfolio_id AND name = :symbol", {"portfolio_id": portfolio_id, "symbol": symbol}).fetchone()
    market_data = db.execute("SELECT price FROM market_data WHERE symbol = :symbol ORDER BY timestamp DESC LIMIT 1", {"symbol": symbol}).fetchone()
    price = market_data[0] if market_data else 60000.75
    value = amount * price

    if trade_type == "buy":
        if not traded_asset or traded_asset[1] < value:
            if cash < value:
                raise ValueError("Insufficient eddies for netrun.")
            db.execute("UPDATE portfolio SET cash = cash - :value WHERE id = :id", {"value": value, "id": portfolio_id})
        if not traded_asset:
            db.execute("INSERT INTO assets (portfolio_id, name, value) VALUES (:portfolio_id, :symbol, :value)", {"portfolio_id": portfolio_id, "symbol": symbol, "value": value})
        else:
            new_value = traded_asset[1] + value
            db.execute("UPDATE assets SET value = :value WHERE id = :id", {"value": new_value, "id": traded_asset[0]})
        # Revert to USDT
        if traded_asset:
            db.execute("DELETE FROM assets WHERE id = :id", {"id": traded_asset[0]})
        else:
            db.execute("UPDATE assets SET value = value - :value WHERE id = :id", {"value": value, "id": usdt_id})
        new_usdt_value = usdt_value + value
        db.execute("UPDATE assets SET value = :value WHERE id = :id", {"value": new_usdt_value, "id": usdt_id})
    elif trade_type == "sell":
        if traded_asset and traded_asset[1] >= value:
            new_value = traded_asset[1] - value
            if new_value <= 0:
                db.execute("DELETE FROM assets WHERE id = :id", {"id": traded_asset[0]})
            else:
                db.execute("UPDATE assets SET value = :value WHERE id = :id", {"value": new_value, "id": traded_asset[0]})
        # Revert to USDT
        if traded_asset:
            db.execute("UPDATE assets SET value = value + :value WHERE id = :id", {"value": value, "id": usdt_id})
        else:
            db.execute("UPDATE assets SET value = value + :value WHERE id = :id", {"value": value, "id": usdt_id})
        # Hedging adjustment (placeholder)
        if trade_type == "sell" and "USDT" not in symbol:
            hedge_symbol = "ETH/USDT" if "BTC" in symbol else "BTC/USDT"
            hedge_value = value * 0.5  # 50% hedge
            db.execute("INSERT INTO assets (portfolio_id, name, value) VALUES (:portfolio_id, :symbol, :value)", {"portfolio_id": portfolio_id, "symbol": hedge_symbol, "value": -hedge_value})
    db.commit()
