# trading/realtime_optimizer.py
import numpy as np
from typing import Dict, List
from collections import deque

class RealtimeStrategyOptimizer:
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.performance_history = deque(maxlen=window_size)
        self.parameter_history = deque(maxlen=window_size)
        
    def update_performance(self, strategy: str, parameters: Dict, outcome: float):
        """Update strategy performance in real-time"""
        self.performance_history.append({
            'strategy': strategy,
            'parameters': parameters,
            'outcome': outcome,
            'timestamp': datetime.now()
        })
        
    def get_optimal_parameters(self, strategy: str) -> Dict:
        """Get current optimal parameters based on recent performance"""
        strategy_data = [p for p in self.performance_history if p['strategy'] == strategy]
        
        if len(strategy_data) < 10:
            return self._get_default_parameters(strategy)
        
        # Group by parameter combinations
        param_performance = {}
        for data in strategy_data:
            param_key = json.dumps(data['parameters'], sort_keys=True)
            if param_key not in param_performance:
                param_performance[param_key] = []
            param_performance[param_key].append(data['outcome'])
        
        # Find best performing parameters
        best_params = None
        best_score = -float('inf')
        
        for param_key, outcomes in param_performance.items():
            # Calculate risk-adjusted score
            avg_outcome = np.mean(outcomes)
            std_outcome = np.std(outcomes)
            sharpe = avg_outcome / (std_outcome + 1e-6)
            
            if sharpe > best_score:
                best_score = sharpe
                best_params = json.loads(param_key)
                
        return best_params
