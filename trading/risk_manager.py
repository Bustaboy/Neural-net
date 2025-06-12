# trading/risk_manager.py
from typing import Dict, List
import numpy as np

class RiskManager:
    def __init__(self, config: Dict):
        self.config = config
        self.max_position_size = config.get('trade.max_position_size', 0.1)

    def validate_trade(self, position: Dict, portfolio_value: float) -> bool:
        return position['value'] / portfolio_value <= self.max_position_size
