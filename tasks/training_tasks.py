# tasks/training_tasks.py
from tasks.celery_app import app
from ml.trainer import EnhancedModelTrainer

@app.task
def train_model_task(lookback_days: int, reason: str):
    trainer = EnhancedModelTrainer(db_manager, config)
    return trainer.train_model(lookback_days, reason)
