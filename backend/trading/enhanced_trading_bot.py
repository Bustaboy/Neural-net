import asyncio
import logging
from typing import Dict, Optional, List
from datetime import datetime
import numpy as np
import json
import websocket

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
        self.api_request_count = 0
        self.api_request_limit = 10  # Binance limit: 10 requests/second
        self.last_request_time = datetime.utcnow()

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
                await self._detect_arbitrage(db)

                for symbol in self.symbols.copy():
                    if not await self._check_api_limit():
                        await asyncio.sleep(1)
                        continue

                    portfolio = db.execute("SELECT cash FROM portfolio WHERE user_id = :user_id", {"user_id": self.user_id}).fetchone()
                    if not portfolio:
                        amount = 0.01
                    else:
                        cash = portfolio[0] or 1000.0
                        amount = min(cash * 0.02, 100.0)  # 2% of cash, capped

                    predictions = await self._get_predictions(db)
                    if not predictions or not predictions["predictions"]:
                        await asyncio.sleep(60)
                        continue

                    trade_type = "buy" if predictions["predictions"][0] > 0.5 else "sell"
                    market_data = db.execute(
                        "SELECT price, change FROM market_data WHERE symbol = :symbol ORDER BY timestamp DESC LIMIT 1",
                        {"symbol": symbol}
                    ).fetchone()
                    if not market_data:
                        continue
                    entry_price = market_data[0]
                    predicted_change = market_data[1] / 100 if market_data[1] else 0.005
                    risk = amount * entry_price * 0.01
                    reward = amount * entry_price * abs(predicted_change)
                    if reward / risk < self.risk_reward_ratio:
                        logger.info(f"Skipping {symbol}: Risk-reward {reward/risk:.2f} < {self.risk_reward_ratio}")
                        continue

                    stop_loss = entry_price * (1 - 0.01) if trade_type == "buy" else entry_price * (1 + 0.01)  # 1% stop-loss
                    take_profit = entry_price * (1 + 0.03) if trade_type == "buy" else entry_price * (1 - 0.03)  # 3% take-profit
                    trade_result = await self._manage_trade(db, symbol, amount, trade_type, stop_loss, take_profit)
                    if trade_result["status"] == "success":
                        self.session_trades += 1
                        self.trade_counts[symbol] = self.trade_counts.get(symbol, 0) + 1
                        pnl = amount * entry_price * (predicted_change if trade_type == "buy" else -predicted_change)
                        self.session_pnl[symbol] = self.session_pnl.get(symbol, 0.0) + pnl
                        total_pnl = sum(self.session_pnl.values())
                        trade_message = f"{datetime.now()}: Netrun {trade_type.capitalize()} {amount} {symbol} - Trade ID {trade_result['trade_id']} - Eddies Earned: ${pnl:.2f} - Total Eddies: ${total_pnl:.2f}"
                        portfolio_message = f"{datetime.now()}: Portfolio Update - Total Eddies: ${total_pnl:.2f}"
                        if self.app_instance:
                            self.app_instance.trade_log.append(trade_message)
                            self.app_instance.trade_log.append(portfolio_message)
                            self.app_instance.update_trade_log("")
                        logger.info(f"Netrun Trade Complete for {symbol}, Eddies: {pnl}")
                        # Dynamic hedging: Short a correlated asset if volatility spikes
                        if abs(predicted_change) > 0.02:  # 2% volatility threshold
                            await self._hedge_trade(db, symbol, amount, trade_type)
                        update_position(self.user_id, symbol, amount, "sell" if trade_type == "buy" else "buy", db)
                        update_position(self.user_id, self.stablecoin, amount, "buy" if trade_type == "buy" else "sell", db)
                        if self.app_instance:
                            self.app_instance.trade_log.append(
                                f"{datetime.now()}: Safely Stashed {amount} {symbol} into {self.stablecoin}"
                            )
                            self.app_instance.update_trade_log("")

                error_count = 0
                await asyncio.sleep(1)

            except asyncio.CancelledError:
                logger.info(f"Netrun loop disconnected for user {self.user_id}")
                break
            except Exception as e:
                error_count += 1
                logger.error(f"Netrun error for {self.user_id}: {e}")
                if error_count >= max_errors:
                    logger.error(f"Max errors reached, shutting down netrun for {self.user_id}")
                    self.is_running = False
                    break
                await asyncio.sleep(60)

    async def _manage_trade(self, db, symbol, amount, trade_type, stop_loss, take_profit):
        """Manage trade with stop-loss and take-profit (placeholder)."""
        self.api_request_count += 1
        trade_result = await self._execute_trade(db, symbol, amount, trade_type)
        # Placeholder: Monitor price via WebSocket for exit
        return trade_result

    async def _detect_arbitrage(self, db: Session):
        """Detect arbitrage opportunities across pairs."""
        if not await self._check_api_limit():
            await asyncio.sleep(1)
            return
        market_data = db.execute("SELECT symbol, price FROM market_data ORDER BY timestamp DESC").fetchall()
        prices = {row[0]: row[1] for row in market_data}
        # Example: BTC/USDT vs. ETH/BTC via USDT
        if "BTC/USDT" in prices and "ETH/USDT" in prices and "ETH/BTC" in prices:
            btc_usdt = prices["BTC/USDT"]
            eth_usdt = prices["ETH/USDT"]
            eth_btc = prices.get("ETH/BTC", eth_usdt / btc_usdt)  # Assume direct pair if missing
            arbitrage_profit = (eth_usdt / (btc_usdt * eth_btc) - 1) * 100
            if arbitrage_profit > 0.1:  # 0.1% arbitrage opportunity
                logger.info(f"Arbitrage detected: {arbitrage_profit:.2f}%")
                # Placeholder: Execute arbitrage trade
                pass

    async def _hedge_trade(self, db, symbol, amount, trade_type):
        """Hedge trade by shorting a correlated asset (placeholder)."""
        if trade_type == "buy":
            hedge_symbol = "ETH/USDT" if symbol == "BTC/USDT" else "BTC/USDT"  # Correlated pair
            hedge_amount = amount * 0.5  # 50% hedge
            hedge_result = await self._execute_trade(db, hedge_symbol, hedge_amount, "sell")
            if hedge_result["status"] == "success":
                logger.info(f"Hedged {symbol} with {hedge_amount} {hedge_symbol}")
                update_position(self.user_id, hedge_symbol, hedge_amount, "sell", db)

    async def _evaluate_new_pairs(self, db: Session):
        """Evaluate and manage profitable/unprofitable pairs from market_data."""
        if not await self._check_api_limit():
            await asyncio.sleep(1)
            return
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
                        logger.info(f"Unlocked new target {symbol} for {self.user_id}, Avg Eddies: {avg_pnl}")
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
                        logger.info(f"Purged unprofitable target {symbol} for {self.user_id}, Avg Eddies: {avg_pnl}")

    async def _get_predictions(self, db: Session):
        """Get central model predictions from the grid."""
        if not await self._check_api_limit():
            await asyncio.sleep(1)
            return None
        return predict(db)

    async def _check_trading_conditions(self, db: Session) -> bool:
        """Basic netrun condition check with API limit consideration."""
        if not await self._check_api_limit():
            await asyncio.sleep(1)
            return False
        return True

    async def _check_api_limit(self):
        """Check and manage Binance API request limits (10 requests/second)."""
        current_time = datetime.utcnow()
        time_diff = (current_time - self.last_request_time).total_seconds()
        if time_diff > 1:
            self.api_request_count = 0
            self.last_request_time = current_time
        if self.api_request_count >= self.api_request_limit:
            logger.warning("API request limit reached, waiting...")
            return False
        return True

    async def cleanup(self):
        """Disconnect from the grid."""
        self.is_running = False
        logger.info(f"Netrunner disconnected for {self.user_id}")

    def stop(self):
        """Shut down the netrun."""
        self.is_running = False
