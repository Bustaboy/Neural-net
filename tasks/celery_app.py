# tasks/celery_app.py
from celery import Celery
from config import ConfigManager

app = Celery(
    'trading_bot',
    broker=ConfigManager.get_config("redis_url"),
    backend=ConfigManager.get_config("redis_url")
)
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True
)
