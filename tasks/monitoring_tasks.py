# tasks/monitoring_tasks.py
from tasks.celery_app import app
from utils.health_check import HealthCheckSystem

@app.task
def run_health_checks():
    health_system = HealthCheckSystem()
    return health_system.run_checks()
