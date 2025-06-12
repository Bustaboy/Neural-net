# tests/unit/test_optimizer.py
import unittest
from ml.optimizer import BayesianOptimizer
import numpy as np

class TestOptimizer(unittest.TestCase):
    def test_optimize(self):
        optimizer = BayesianOptimizer()
        X = np.random.rand(100, 10)
        y = np.random.randint(0, 2, 100)
        params = optimizer.optimize(X, y, n_trials=5)
        self.assertIsInstance(params, dict)
