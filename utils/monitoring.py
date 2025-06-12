# utils/monitoring.py
import psutil
import logging

class ResourceMonitor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def check_resources(self) -> Dict[str, float]:
        return {
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent
        }
