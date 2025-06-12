# tests/unit/test_strategies.py
import unittest
from trading.strategies import TradingStrategy
import numpy as np

class TestStrategies(unittest.TestCase):
    def test_momentum_strategy(self):
        config = {'trade.threshold': 0.1}
        strategy = TradingStrategy(config)
        features = np.array([0.2])
        self.assertEqual(strategy.momentum_strategy(features), 'buy')
