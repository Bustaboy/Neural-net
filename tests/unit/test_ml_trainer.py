# tests/unit/test_ml_trainer.py
import pytest
import numpy as np
from unittest.mock import Mock, patch
from ml.trainer import EnhancedModelTrainer

class TestModelTrainer:
    @pytest.fixture
    def trainer(self):
        db_manager = Mock()
        notification_manager = Mock()
        config = {
            'min_training_samples': 100,
            'lookback_days': 30,
            'max_memory_percent': 80
        }
        return EnhancedModelTrainer(db_manager, notification_manager, config)
    
    def test_prepare_data_read_only(self, trainer):
        """Test that prepare_data uses read-only connection"""
        with patch('sqlite3.connect') as mock_connect:
            trainer.prepare_data(lookback_days=30)
            
            # Verify read-only connection was used
            mock_connect.assert_called_with(
                f"file:{trainer.db_manager.db_path}?mode=ro",
                uri=True
            )
    
    def test_train_model_non_blocking(self, trainer):
        """Test that training runs in separate process"""
        with patch('multiprocessing.Process') as mock_process:
            trainer.train_model(lookback_days=30)
            
            # Verify process was started
            mock_process.assert_called_once()
            mock_process.return_value.start.assert_called_once()
    
    def test_atomic_model_swap(self, trainer, tmp_path):
        """Test atomic model swapping"""
        trainer.model_path = tmp_path / "model.pkl"
        trainer.temp_model_path = tmp_path / "temp_model.pkl"
        
        # Create temporary model file
        trainer.temp_model_path.write_text("temp_model")
        
        # Perform swap
        trainer._swap_models()
        
        # Verify atomic rename occurred
        assert trainer.model_path.exists()
        assert not trainer.temp_model_path.exists()
    
    @pytest.mark.parametrize("cpu,memory,expected", [
        (50, 60, True),   # Normal usage
        (95, 60, False),  # High CPU
        (50, 85, False),  # High memory
        (95, 85, False),  # Both high
    ])
    def test_resource_checking(self, trainer, cpu, memory, expected):
        """Test resource monitoring"""
        with patch('psutil.cpu_percent', return_value=cpu):
            with patch('psutil.virtual_memory') as mock_memory:
                mock_memory.return_value.percent = memory
                
                result = trainer._check_resources()
                assert result == expected
