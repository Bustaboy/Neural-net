# api/middleware.py
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

def setup_rate_limiting(app):
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="redis://localhost:6379"
    )
    
    # Specific limits for sensitive endpoints
    @limiter.limit("5 per hour")
    @app.route("/api/ml/force_retrain", methods=["POST"])
    def limited_retrain():
        pass
    
    @limiter.limit("10 per minute")
    @app.route("/api/trading/execute", methods=["POST"])
    def limited_trading():
        pass
    
    return limiter
