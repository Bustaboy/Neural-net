# trading/order_executor.py
import ccxt.async_support as ccxt
from core.database import EnhancedDatabaseManager
from typing import Dict, Any
from fastapi import HTTPException
import uuid
import time

class OrderExecutor:
    def __init__(self, db_manager: EnhancedDatabaseManager):
        self.db_manager = db_manager
        self.exchanges = {}

    async def initialize_exchange(self, user_id: int) -> ccxt.binance:
        user = self.db_manager.fetch_one(
            "SELECT exchange_api_key, exchange_secret FROM users WHERE id = ?",
            (user_id,)
        )
        if not user or not user['exchange_api_key'] or not user['exchange_secret']:
            raise HTTPException(status_code=400, detail="Exchange API keys not configured")
        
        exchange = ccxt.binance({
            'apiKey': user['exchange_api_key'],
            'secret': user['exchange_secret'],
            'enableRateLimit': True,
        })
        self.exchanges[user_id] = exchange
        return exchange

    async def execute_trade(self, user_id: int, symbol: str, side: str, amount: float) -> Dict[str, Any]:
        if side not in ["buy", "sell"]:
            raise HTTPException(status_code=400, detail="Invalid trade side")
        
        exchange = self.exchanges.get(user_id)
        if not exchange:
            exchange = await self.initialize_exchange(user_id)
        
        try:
            symbol = symbol.replace("/", "")  # e.g., BTC/USDT -> BTCUSDT
            order_type = "market"
            order = await exchange.create_order(symbol, order_type, side, amount)
            
            # Log trade to database
            trade_id = str(uuid.uuid4())
            self.db_manager.execute(
                """
                INSERT INTO trades (id, user_id, symbol, side, amount, price, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trade_id,
                    user_id,
                    symbol,
                    side,
                    amount,
                    order['price'] or 0.0,
                    int(time.time())
                )
            )
            
            return {"trade_id": trade_id, "order": order}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Trade execution failed: {str(e)}")
        finally:
            if exchange:
                await exchange.close()
