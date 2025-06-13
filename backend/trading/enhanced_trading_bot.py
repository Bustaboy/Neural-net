import asyncio
import logging
from typing import Dict, Optional, List
from datetime import datetime
import numpy as np

from sqlalchemy.orm import Session
from core.database import get_db
from ml.ensemble import predict
from trading.exchange_abstraction import execute_trade
from trading.position_manager import update_position

logger = logging.getLogger(__name__)

class EnhancedTradingBot:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.is_running = False
        self.last_activity = datetime.utcnow()
        self.session_trades = 0
        self.session_pnl: Dict[str, float] = {}  # PNL per symbol
        self.symbols: List[str] = ["BTC", "ETH", "LTC"]  # Diversified initial pairs
        self.profit_threshold = 0.005  # 0.5% profitability threshold
        self.min_trades = 5  # Minimum trades to evaluate profitability
        self.risk_reward_ratio = 2.0  # Minimum 2:1 risk-reward ratio
        self.stablecoin = "USDT"  # Stablecoin for risk elimination

    async def initialize(self):
        logger.info(f"Bot initialized for user {self.user_id}")
        self.is_running = True

    async def run_trading_loop(self, db: Session = Depends(get_db)):
        error_count = 0
        max_errors = 5

        while self.is_running:
            try:
                self.last_activity = datetime.utcnow()
                if not await self._check_trading_conditions(db):
                    await asyncio.sleep(60)
                    continue

                # Evaluate and add new profitable pairs
                await self._evaluate_new_pairs(db)

                for symbol in self.symbols:
                    portfolio = db.execute(
                        "SELECT cash FROM portfolio WHERE user_id = :user_id",
                        {"user_id": self.user_id}
                    ).fetchone()
                    if not portfolio:
                        amount = 0.01  # Default if no portfolio
                    else:
                        cash = portfolio[0] or 1000.0
                        amount = cash * 0.01  # 1% of cash per trade

                    predictions = await self._get_predictions(db)
                    if not predictions or not predictions["predictions"]:
                        await asyncio.sleep(60)
                        continue

                    trade_type = "buy" if predictions["predictions"][0] > 0.5 else "sell"
                    # Simulate risk-reward: Only trade if predicted change supports 2:1 ratio
                    market_data = db.execute(
                        "SELECT change FROM market_data WHERE symbol = :symbol ORDER BY timestamp DESC LIMIT 1",
                        {"symbol": symbol}
                    ).fetchone()
                    predicted_change = market_data[0] / 100 if market_data else 0.005
                    risk = amount * 60000.75 * 0.01  # 1% risk
                    reward = amount * 60000.75 * abs(predicted_change)
                    if reward / risk < self.risk_reward_ratio:
                        logger.info(f"Skipping {symbol} for user {self.user_id}: Risk-reward ratio {reward/risk:.2f} < {self.risk_reward_ratio}")
                        continue

                    trade_result = await self._execute_trade(db, symbol, amount, trade_type)
                    if trade_result["status"] == "success":
                        update_position(self.user_id, symbol, amount, trade_type, db)
                        self.session_trades += 1
                        # Simulate PNL based on market_data change
                        pnl = amount * 60000.75 * (predicted_change if trade_type == "buy" else -predicted_change)
                        self.session_pnl[symbol] = self.session_pnl.get(symbol, 0.0) + pnl
                        logger.info(f"Trade executed for user {self.user_id} on {symbol}: {trade_result}, PNL: {pnl}")
                        # Revert to stablecoin after trade
                        update_position(self.user_id, symbol, amount, "sell" if trade_type == "buy" else "buy", db)
                        update_position(self.user_id, self.stablecoin, amount, "buy" if trade_type == "buy" else "sell", db)
                        logger.info(f"Reverted to {self.stablecoin} for user {self.user_id}")

                error_count = 0
                await asyncio.sleep(30)  # Configurable interval

            except asyncio.CancelledError:
                logger.info(f"Trading loop cancelled for user {self.user_id}")
                break
            except Exception as e:
                error_count += 1
                logger.error(f"Trading error for user {self.user_id}: {e}")
                if error_count >= max_errors:
                    logger.error(f"Max errors reached for user {self.user_id}, stopping bot")
                    self.is_running = False
                    break
                await asyncio.sleep(60)

    async def _evaluate_new_pairs(self, db: Session):
        """Evaluate and add new profitable pairs from market_data."""
        market_data = db.execute("SELECT symbol, change FROM market_data GROUP BY symbol").fetchall()
        for symbol_data in market_data:
            symbol, change = symbol_data[0], symbol_data[1]
            if symbol not in self.symbols:
                if symbol not in self.session_pnl:
                    self.session_pnl[symbol] = 0.0
                trade_count = sum(1 for _ in db.execute(
                    "SELECT 1 FROM trades WHERE user_id = :user_id AND symbol = :symbol",
                    {"user_id": self.user_id, "symbol": symbol}
                ))
                if trade_count >= self.min_trades:
                    avg_pnl = self.session_pnl[symbol] / trade_count if trade_count > 0 else 0.0
                    if avg_pnl > self.profit_threshold * 60000.75:  # Threshold in value
                        self.symbols.append(symbol)
                        logger.info(f"Added new profitable pair {symbol} for user {self.user_id}, Avg PNL: {avg_pnl}")

    async def _get_predictions(self, db: Session):
        """Get central model predictions."""
        return predict(db)

    async def _execute_trade(self, db: Session, symbol: str, amount: float, trade_type: str):
        """Execute a trade with user-specific keys."""
        return execute_trade(self.user_id, symbol, amount, trade_type, db)

    async def _check_trading_conditions(self, db: Session) -> bool:
        """Basic trading condition check."""
        return True  # Simplified; add market hours/risk checks later

    async def cleanup(self):
        """Cleanup resources."""
        self.is_running = False
        logger.info(f"Bot cleaned up for user {self.user_id}")

    def stop(self):
        """Stop the bot."""
        self.is_running = False
