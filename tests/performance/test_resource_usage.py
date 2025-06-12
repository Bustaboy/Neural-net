# tests/performance/test_resource_usage.py
import pytest
import psutil
from ml.trainer import EnhancedModelTrainer

def test_memory_usage(trainer):
    process = psutil.Process()
    initial_memory = process.memory_info().rss
    trainer.train_model(lookback_days=30)
    final_memory = process.memory_info().rss
    assert (final_memory - initial_memory) / 1024 / 1024 < 1000  # Less than 1GB
