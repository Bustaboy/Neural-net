# trading/strategies.py
from typing import Dict
import numpy as np

class TradingStrategy:
    def __init__(self, config: Dict):
        self.config = config

    def momentum_strategy(self, features: np.ndarray) -> str:
        threshold = self.config.get('trade.threshold', 0.1)
        prediction = features[-1]  # Assume last feature is prediction
        return "buy" if prediction > threshold else "sell" if prediction < -threshold else "hold"
