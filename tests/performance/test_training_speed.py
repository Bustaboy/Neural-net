# tests/performance/test_training_speed.py
import time
import pytest
from ml.trainer import EnhancedModelTrainer

class TestTrainingPerformance:
    @pytest.mark.performance
    def test_training_time_small_dataset(self, trainer, small_dataset):
        """Test training time with 1,000 samples"""
        start_time = time.time()
        
        success = trainer.train_model(lookback_days=30)
        
        duration = time.time() - start_time
        assert success
        assert duration < 30  # Should complete within 30 seconds
    
    @pytest.mark.performance
    def test_training_time_large_dataset(self, trainer, large_dataset):
        """Test training time with 10,000 samples"""
        start_time = time.time()
        
        success = trainer.train_model(lookback_days=90)
        
        duration = time.time() - start_time
        assert success
        assert duration < 300  # Should complete within 5 minutes
    
    @pytest.mark.performance
    def test_prediction_latency(self, trainer):
        """Test prediction latency"""
        trainer.load_model()
        features = np.random.rand(100)  # 100 features
        
        latencies = []
        for _ in range(100):
            start = time.time()
            trainer.predict(features)
            latencies.append(time.time() - start)
        
        avg_latency = np.mean(latencies) * 1000  # Convert to ms
        assert avg_latency < 10  # Should be under 10ms
