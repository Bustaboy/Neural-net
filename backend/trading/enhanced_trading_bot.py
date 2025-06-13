import asyncio
import logging
from typing import Dict, Optional
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
        self.session_pnl = 0.0

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

                predictions = await self._get_predictions(db)
                if not predictions or not predictions["predictions"]:
                    await asyncio.sleep(60)
                    continue

                symbol = "BTC"
                amount = 0.01
                trade_type = "buy" if predictions["predictions"][0] > 0.5 else "sell"
                trade_result = await self._execute_trade(db, symbol, amount, trade_type)
                if trade_result["status"] == "success":
                    update_position(self.user_id, symbol, amount, trade_type, db)
                    self.session_trades += 1
                    logger.info(f"Trade executed for user {self.user_id}: {trade_result}")

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
