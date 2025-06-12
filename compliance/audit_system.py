# compliance/audit_system.py
import hashlib
from datetime import datetime
from typing import Dict, Any

class ComplianceAuditSystem:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        
    def log_trading_decision(self, decision_data: Dict[str, Any]):
        """Log every trading decision for compliance"""
        # Create immutable hash of decision
        decision_hash = self._create_hash(decision_data)
        
        self.db_manager.execute("""
            INSERT INTO compliance_log 
            (timestamp, decision_hash, decision_type, symbol, 
             quantity, price, reason, model_version, features_used, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now(),
            decision_hash,
            decision_data['type'],
            decision_data['symbol'],
            decision_data['quantity'],
            decision_data['price'],
            decision_data['reason'],
            decision_data.get('model_version'),
            json.dumps(decision_data.get('features', {})),
            decision_data.get('confidence')
        ))
    
    def _create_hash(self, data: Dict[str, Any]) -> str:
        """Create tamper-proof hash of decision"""
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def generate_compliance_report(self, start_date: datetime, end_date: datetime):
        """Generate compliance report for regulators"""
        report = {
            'period': {'start': start_date, 'end': end_date},
            'total_trades': 0,
            'decision_accuracy': {},
            'model_versions_used': [],
            'anomalies_detected': []
        }
        
        # Aggregate compliance data
        # ... implementation ...
        
        return report
