# trading/position_manager.py
from typing import Dict, List
from core.database import EnhancedDatabaseManager

class PositionManager:
    def __init__(self, db_manager: EnhancedDatabaseManager):
        self.db_manager = db_manager

    def get_open_positions(self, user_id: int) -> List[Dict]:
        return self.db_manager.execute(
            "SELECT * FROM positions WHERE user_id = ? AND status = 'open'",
            (user_id,)
        )

    def close_position(self, position_id: int):
        self.db_manager.execute(
            "UPDATE positions SET status = 'closed' WHERE id = ?",
            (position_id,)
        )
