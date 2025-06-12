# utils/metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import time

# Define metrics
prediction_counter = Counter('ml_predictions_total', 'Total number of ML predictions')
prediction_latency = Histogram('ml_prediction_duration_seconds', 'ML prediction latency')
model_accuracy = Gauge('ml_model_accuracy', 'Current model accuracy')
active_positions = Gauge('trading_active_positions', 'Number of active positions')
total_pnl = Gauge('trading_total_pnl', 'Total profit/loss')

class MetricsCollector:
    def __init__(self):
        self.start_time = time.time()
        
    def record_prediction(self, duration: float):
        prediction_counter.inc()
        prediction_latency.observe(duration)
    
    def update_model_accuracy(self, accuracy: float):
        model_accuracy.set(accuracy)
    
    def update_trading_metrics(self, positions: int, pnl: float):
        active_positions.set(positions)
        total_pnl.set(pnl)
