# utils/advanced_logger.py
import logging
import json
from pythonjsonlogger import jsonlogger
from elasticsearch import Elasticsearch

class AdvancedLogger:
    def __init__(self, name: str, es_host: str = None):
        self.logger = logging.getLogger(name)
        self.setup_handlers()
        self.es_client = Elasticsearch(es_host) if es_host else None
        
    def setup_handlers(self):
        # JSON formatter for structured logging
        json_formatter = jsonlogger.JsonFormatter()
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(json_formatter)
        self.logger.addHandler(console_handler)
        
        # File handler with rotation
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            'logs/trading_bot.log',
            maxBytes=100*1024*1024,  # 100MB
            backupCount=10
        )
        file_handler.setFormatter(json_formatter)
        self.logger.addHandler(file_handler)
        
    def log_with_context(self, level: str, message: str, **context):
        """Log with additional context"""
        log_data = {
            'message': message,
            'timestamp': datetime.utcnow().isoformat(),
            **context
        }
        
        # Log locally
        getattr(self.logger, level)(json.dumps(log_data))
        
        # Send to Elasticsearch if configured
        if self.es_client:
            self.es_client.index(
                index=f"trading-logs-{datetime.utcnow().strftime('%Y.%m.%d')}",
                body=log_data
            )
