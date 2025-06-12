# tests/unit/test_ensemble.py
import unittest
from ml.ensemble import create_ensemble_model

class TestEnsemble(unittest.TestCase):
    def test_ensemble_creation(self):
        model = create_ensemble_model()
        self.assertIsNotNone(model)
        self.assertTrue(hasattr(model, 'fit'))
