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
import gui.main  # Import to access shared trade_log

logger = logging.getLogger(__name__)

class EnhancedTradingBot:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.is_running = False
        self.last_activity = datetime.utcnow()
        self.session_trades = 0
        self.session_pnl: Dict[str, float] = {}  # Eddies per symbol
        self.trade_counts: Dict[str, int] = {}  # Trade count per symbol
        self.symbols: List[str] = ["BTC/USDT", "ETH/USDT", "LTC/USDT", "XRP/USDT"]  # Netrun targets
        self.profit_threshold = 0.005  # 0.5% eddie threshold
        self.loss_threshold = -0.005  # -0.5% eddie threshold for removal
        self.min_trades = 5  # Minimum netruns to evaluate addition
        self.min_removal_trades = 10  # Minimum netruns to evaluate removal
        self.risk_reward_ratio = 2.0  # Minimum 2:1 risk-reward ratio
        self.stablecoin = "USDT"  # Safe haven
        self.app_instance = None  # Cyberdeck link

    async def initialize(self, app_instance):
        """Jack into the grid with cyberdeck link."""
        self.app_instance = app_instance
        logger.info(f"Netrunner jacked in for user {self.user_id}")
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

                await self._evaluate_new_pairs(db)

                for symbol in self.symbols.copy():  # Copy to allow modification
                    portfolio = db.execute(
                        "SELECT cash FROM portfolio WHERE user_id = :user_id",
                        {"user_id": self.user_id}
                    ).fetchone()
                    if not portfolio:
                        amount = 0.01
                    else:
                        cash = portfolio[0] or 1000.0
                        amount = cash * 0.01  # 1% of eddies per netrun

                    predictions = await self._get_predictions(db)
                    if not predictions or not predictions["predictions"]:
                        await asyncio.sleep(60)
                        continue

                    trade_type = "buy" if predictions["predictions"][0] > 0.5 else "sell"
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
                        self.trade_counts[symbol] = self.trade_counts.get(symbol, 0) + 1
                        pnl = amount * 60000.75 * (predicted_change if trade_type == "buy" else -predicted_change)
                        self.session_pnl[symbol] = self.session_pnl.get(symbol, 0.0) + pnl
                        total_pnl = sum(self.session_pnl.values())
                        # Report to cyberdeck
                        if self.app_instance:
                            self.app_instance.trade_log.append(
                                f"{datetime.now()}: Netrun {trade_type.capitalize()} {amount} {symbol} - Trade ID {trade_result['trade_id']} - Eddies Earned: ${pnl:.2f} - Total Eddies: ${total_pnl:.2f}"
                            )
                            self.app_instance.update_trade_log("")
                        logger.info(f"Netrun Trade Complete for user {self.user_id} on {symbol}: {trade_result}, Eddies: {pnl}")
                        update_position(self.user_id, symbol, amount, "sell" if trade_type == "buy" else "buy", db)
                        update_position(self.user_id, self.stablecoin, amount, "buy" if trade_type == "buy" else "sell", db)
                        if self.app_instance:
                            self.app_instance.trade_log.append(
                                f"{datetime.now()}: Safely Stashed {amount} {symbol} into {self.stablecoin}"
                            )
                            self.app_instance.update_trade_log("")

                error_count = 0
                await asyncio.sleep(30)  # Configurable netrun interval

            except asyncio.CancelledError:
                logger.info(f"Netrun loop disconnected for user {self.user_id}")
                break
            except Exception as e:
                error_count += 1
                logger.error(f"Netrun error for user {self.user_id}: {e}")
                if error_count >= max_errors:
                    logger.error(f"Max errors reached for user {self.user_id}, shutting down netrun")
                    self.is_running = False
                    break
                await asyncio.sleep(60)

    async def _evaluate_new_pairs(self, db: Session):
        """Evaluate and manage profitable/unprofitable pairs from market_data."""
        market_data = db.execute("SELECT symbol, change FROM market_data GROUP BY symbol").fetchall()
        for symbol_data in market_data:
            symbol, change = symbol_data[0], symbol_data[1]
            if symbol not in self.symbols:
                if symbol not in self.session_pnl:
                    self.session_pnl[symbol] = 0.0
                    self.trade_counts[symbol] = 0
                trade_count = self.trade_counts.get(symbol, 0)
                if trade_count >= self.min_trades:
                    avg_pnl = self.session_pnl[symbol] / trade_count if trade_count > 0 else 0.0
                    if avg_pnl > self.profit_threshold * 60000.75:
                        self.symbols.append(symbol)
                        if self.app_instance:
                            self.app_instance.trade_log.append(
                                f"{datetime.now()}: Unlocked new target {symbol} - Avg Eddies: ${avg_pnl:.2f}"
                            )
                            self.app_instance.update_trade_log("")
                        logger.info(f"Unlocked new target {symbol} for user {self.user_id}, Avg Eddies: {avg_pnl}")
            elif symbol in self.symbols:
                trade_count = self.trade_counts.get(symbol, 0)
                if trade_count >= self.min_removal_trades:
                    avg_pnl = self.session_pnl[symbol] / trade_count if trade_count > 0 else 0.0
                    if avg_pnl < self.loss_threshold * 60000.75:
                        self.symbols.remove(symbol)
                        if self.app_instance:
                            self.app_instance.trade_log.append(
                                f"{datetime.now()}: Purged unprofitable target {symbol} - Avg Eddies: ${avg_pnl:.2f}"
                            )
                            self.app_instance.update_trade_log("")
                        logger.info(f"Purged unprofitable target {symbol} for user {self.user_id}, Avg Eddies: {avg_pnl}")

    async def _get_predictions(self, db: Session):
        """Get central model predictions from the grid."""
        return predict(db)

    async def _execute_trade(self, db: Session, symbol: str, amount: float, trade_type: str):
        """Execute a trade with user-specific keys, breaching corpo servers."""
        return execute_trade(self.user_id, symbol, amount, trade_type, db)

    async def _check_trading_conditions(self, db: Session) -> bool:
        """Basic netrun condition check."""
        return True  # Simplified; add market hours/risk checks later

    async def cleanup(self):
        """Disconnect from the grid."""
        self.is_running = False
        logger.info(f"Netrunner disconnected for user {self.user_id}")

    def stop(self):
        """Shut down the netrun."""
        self.is_running = False
