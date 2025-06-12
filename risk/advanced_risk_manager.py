# risk/advanced_risk_manager.py
from typing import Dict, List, Tuple
import numpy as np

class AdvancedRiskManager:
    def __init__(self, config: Dict):
        self.config = config
        self.var_confidence = config.get('var_confidence', 0.95)
        self.max_correlation = config.get('max_correlation', 0.7)
        
    def calculate_portfolio_var(self, positions: List[Dict], 
                               historical_returns: np.ndarray) -> float:
        """Calculate Value at Risk for portfolio"""
        weights = np.array([p['value'] for p in positions])
        weights = weights / np.sum(weights)
        
        # Calculate portfolio returns
        portfolio_returns = historical_returns @ weights
        
        # Calculate VaR
        var_percentile = (1 - self.var_confidence) * 100
        var = np.percentile(portfolio_returns, var_percentile)
        
        return abs(var)
    
    def check_correlation_risk(self, positions: List[Dict], 
                              correlation_matrix: np.ndarray) -> List[Tuple[str, str, float]]:
        """Check for highly correlated positions"""
        high_correlations = []
        
        for i in range(len(positions)):
            for j in range(i + 1, len(positions)):
                correlation = correlation_matrix[i, j]
                if abs(correlation) > self.max_correlation:
                    high_correlations.append((
                        positions[i]['symbol'],
                        positions[j]['symbol'],
                        correlation
                    ))
                    
        return high_correlations
    
    def calculate_stress_test_scenarios(self, positions: List[Dict]) -> Dict[str, float]:
        """Run stress test scenarios"""
        scenarios = {
            'market_crash': -0.20,  # 20% market drop
            'flash_crash': -0.10,   # 10% instant drop
            'black_swan': -0.50,    # 50% catastrophic event
            'sector_collapse': -0.30 # 30% sector-specific drop
        }
        
        results = {}
        for scenario_name, impact in scenarios.items():
            portfolio_value = sum(p['value'] for p in positions)
            loss = portfolio_value * impact
            results[scenario_name] = {
                'potential_loss': loss,
                'remaining_capital': portfolio_value + loss,
                'survival_probability': self._calculate_survival_probability(loss)
            }
            
        return results
