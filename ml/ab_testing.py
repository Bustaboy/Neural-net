# ml/ab_testing.py
import random
from typing import Dict, Any

class ABTestingFramework:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.experiments = {}
        
    def create_experiment(self, name: str, variants: Dict[str, Any], 
                         traffic_split: Dict[str, float]):
        """Create new A/B test experiment"""
        self.experiments[name] = {
            'variants': variants,
            'traffic_split': traffic_split,
            'metrics': {variant: [] for variant in variants}
        }
        
    def get_variant(self, experiment_name: str, user_id: str) -> str:
        """Deterministically assign user to variant"""
        experiment = self.experiments.get(experiment_name)
        if not experiment:
            return 'control'
        
        # Use hash for consistent assignment
        hash_value = hash(f"{experiment_name}:{user_id}") % 100
        
        cumulative = 0
        for variant, split in experiment['traffic_split'].items():
            cumulative += split * 100
            if hash_value < cumulative:
                return variant
                
        return 'control'
    
    def track_metric(self, experiment_name: str, variant: str, 
                    metric_name: str, value: float):
        """Track experiment metrics"""
        self.db_manager.execute("""
            INSERT INTO ab_test_metrics 
            (experiment_name, variant, metric_name, value, timestamp)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (experiment_name, variant, metric_name, value))
