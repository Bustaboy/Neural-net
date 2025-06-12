# utils/alert_manager.py
import json
from typing import Dict, List
from datetime import datetime

class AlertManager:
    def __init__(self, db_manager, notification_manager):
        self.db_manager = db_manager
        self.notification_manager = notification_manager
        self.active_alerts = {}
        
    def create_alert_rule(self, user_id: int, alert_config: Dict):
        """Create a new alert rule"""
        self.db_manager.execute("""
            INSERT INTO alert_rules 
            (user_id, name, condition_type, operator, threshold, symbol, enabled)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            alert_config['name'],
            alert_config['condition_type'],
            alert_config['operator'],
            alert_config['threshold'],
            alert_config.get('symbol'),
            True
        ))
        
    def check_alerts(self, market_data: Dict):
        """Check all active alerts against current market data"""
        active_rules = self.db_manager.fetch_all("""
            SELECT * FROM alert_rules WHERE enabled = 1
        """)
        
        for rule in active_rules:
            if self._evaluate_rule(rule, market_data):
                self._trigger_alert(rule, market_data)
                
    def _evaluate_rule(self, rule: Dict, market_data: Dict) -> bool:
        """Evaluate if alert condition is met"""
        value = None
        
        # Get the value to check based on condition type
        if rule['condition_type'] == 'btc_dominance':
            value = market_data.get('btc_dominance', 0)
        elif rule['condition_type'] == 'volatility':
            value = market_data.get('volatility_index', 0)
        elif rule['condition_type'] == 'price' and rule['symbol']:
            value = market_data.get('prices', {}).get(rule['symbol'], 0)
        elif rule['condition_type'] == 'win_rate':
            value = self._calculate_win_rate()
            
        if value is None:
            return False
            
        # Evaluate operator
        operator = rule['operator']
        threshold = rule['threshold']
        
        if operator == '>':
            return value > threshold
        elif operator == '<':
            return value < threshold
        elif operator == '>=':
            return value >= threshold
        elif operator == '<=':
            return value <= threshold
        elif operator == '=':
            return abs(value - threshold) < 0.0001
            
        return False
