# api/middleware.py
from flask import request
from flask_limiter import Limiter
import logging

def setup_middleware(app):
    limiter = Limiter(app, default_limits=["60 per minute"])
    logger = logging.getLogger(__name__)

    @app.before_request
    def log_request():
        logger.info(f"Request: {request.method} {request.path}")
