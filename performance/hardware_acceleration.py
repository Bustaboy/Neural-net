# performance/hardware_acceleration.py
import cupy as cp  # GPU acceleration
import numpy as np
from numba import cuda

class GPUAcceleratedTrading:
    """Use GPU for parallel computation"""
    
    @cuda.jit
    def calculate_indicators_gpu(prices, indicators_out):
        """Calculate technical indicators on GPU"""
        idx = cuda.grid(1)
        if idx < prices.shape[0]:
            # Simple moving average example
            if idx >= 20:
                sma = 0.0
                for i in range(20):
                    sma += prices[idx - i]
                indicators_out[idx, 0] = sma / 20.0
    
    def batch_predict_gpu(self, features: np.ndarray) -> np.ndarray:
        """Run ML predictions on GPU"""
        # Transfer to GPU
        features_gpu = cp.asarray(features)
        
        # Run predictions in parallel
        predictions_gpu = self.gpu_model.predict(features_gpu)
        
        # Transfer back to CPU
        return cp.asnumpy(predictions_gpu)
