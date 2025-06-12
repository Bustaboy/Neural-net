# trading/position_manager.py
from typing import Dict, List
from core.database import EnhancedDatabaseManager
import logging

class PositionManager:
    def __init__(self, db_manager: EnhancedDatabaseManager):
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)

    def get_open_positions(self, user_id: int) -> List[Dict]:
        try:
            positions = self.db_manager.execute(
                "SELECT id, symbol, amount, value FROM positions WHERE user_id = ? AND status = 'open'",
                (user_id,)
            )
            return [
                {"id": p[0], "symbol": p[1], "amount": p[2], "value": p[3]}
                for p in positions
            ]
        except Exception as e:
            self.logger.error(f"Failed to fetch positions: {e}")
            raise

    def close_position(self, position_id: int):
        try:
            self.db_manager.execute(
                "UPDATE positions SET status = 'closed' WHERE id = ?",
                (position_id,)
            )
        except Exception as e:
            self.logger.error(f"Failed to close position: {e}")
            raise
