# trading/dead_letter_queue.py
import json
from datetime import datetime
from typing import Dict, Any

class DeadLetterQueue:
    def __init__(self, db_manager, notification_manager):
        self.db_manager = db_manager
        self.notification_manager = notification_manager
        
    def add_failed_trade(self, trade_data: Dict[str, Any], error: str, retry_count: int):
        """Add failed trade to DLQ for manual review"""
        self.db_manager.execute("""
            INSERT INTO dead_letter_queue 
            (trade_data, error_message, retry_count, status, created_at)
            VALUES (?, ?, ?, 'pending', ?)
        """, (json.dumps(trade_data), error, retry_count, datetime.now()))
        
        # Alert if critical
        if retry_count >= 3 or 'insufficient_balance' in error.lower():
            self.notification_manager.send_critical_alert(
                f"Trade failed after {retry_count} attempts: {error}",
                trade_data
            )
    
    def process_dlq(self):
        """Process items in dead letter queue"""
        pending_items = self.db_manager.fetch_all("""
            SELECT * FROM dead_letter_queue 
            WHERE status = 'pending' 
            AND created_at > datetime('now', '-24 hours')
            ORDER BY created_at ASC
        """)
        
        for item in pending_items:
            try:
                # Attempt to reprocess
                trade_data = json.loads(item['trade_data'])
                # Reprocess logic here
                
                # Mark as processed
                self.db_manager.execute(
                    "UPDATE dead_letter_queue SET status = 'processed' WHERE id = ?",
                    (item['id'],)
                )
            except Exception as e:
                # Mark as failed
                self.db_manager.execute(
                    "UPDATE dead_letter_queue SET status = 'failed', error_message = ? WHERE id = ?",
                    (str(e), item['id'])
                )
