# trading/risk_manager.py
from typing import Dict, Any
from core.database import EnhancedDatabaseManager
import logging

logger = logging.getLogger(__name__)

class RiskManager:
    def __init__(self, db_manager: EnhancedDatabaseManager):
        self.db_manager = db_manager
        self.max_daily_loss = 0.05  # 5% of capital
        self.max_position_size = 0.05  # 5% of capital
        self.stop_loss = 0.02  # 2% stop-loss
        self.take_profit = 0.05  # 5% take-profit

    def validate_trade(self, user_id: int, trade: Dict[str, Any]) -> bool:
        """Validate trade against risk parameters."""
        capital = self.get_capital(user_id)
        trade_value = trade["quantity"] * trade["price"]

        # Check position size
        if trade_value > capital * self.max_position_size:
            logger.warning(f"Trade exceeds position size: {trade_value} > {capital * self.max_position_size}")
            return False

        # Check daily loss
        daily_loss = self.calculate_daily_loss(user_id)
        if daily_loss >= capital * self.max_daily_loss:
            logger.warning(f"Daily loss limit reached: {daily_loss} >= {capital * self.max_daily_loss}")
            return False

        # Apply stop-loss and take-profit
        trade["stop_loss"] = trade["price"] * (1 - self.stop_loss)
        trade["take_profit"] = trade["price"] * (1 + self.take_profit)
        return True

    def get_capital(self, user_id: int) -> float:
        """Get user's current capital from database."""
        user = self.db_manager.fetch_one(
            "SELECT capital FROM users WHERE id = ?", (user_id,)
        )
        return user["capital"] if user and user["capital"] else 500.0  # Default $500

    def calculate_daily_loss(self, user_id: int) -> float:
        """Calculate total loss for today."""
        result = self.db_manager.fetch_one(
            """
            SELECT SUM(pnl) as total_loss
            FROM trades
            WHERE user_id = ? AND timestamp >= CURRENT_DATE AND pnl < 0
            """,
            (user_id,)
        )
        return abs(result["total_loss"]) if result["total_loss"] else 0.0
