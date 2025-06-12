# utils/audit.py
from core.database import EnhancedDatabaseManager
import json
from datetime import datetime

class AuditLogger:
    def __init__(self, db_manager: EnhancedDatabaseManager):
        self.db_manager = db_manager

    def log_action(self, user_id: int, action: str, details: Dict):
        self.db_manager.execute(
            "INSERT INTO audit_logs (user_id, action, details, timestamp) VALUES (?, ?, ?, ?)",
            (user_id, action, json.dumps(details), datetime.utcnow())
        )
