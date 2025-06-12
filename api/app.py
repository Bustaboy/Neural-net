# api/app.py
from flask import Flask
from flask_session import Session
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from api.auth import AuthManager
from config import ConfigManager
from api.middleware import setup_middleware, setup_rate_limiter
from api.routes import auth, portfolio, trading, subscriptions, users

def create_app():
    app = Flask(__name__)
    CORS(app)
    
    # Session configuration
    app.config['SESSION_TYPE'] = 'redis'
    app.config['SESSION_REDIS'] = ConfigManager.get_config("redis_url")
    Session(app)
    
    # Setup middleware
    setup_middleware(app)
    setup_rate_limiter(app)
    
    # Initialize auth
    AuthManager(app)
    
    # Register routes (convert FastAPI routers to Flask)
    # Note: In production, consider fully migrating to FastAPI or Flask
    app.register_blueprint(auth.to_flask_blueprint())
    app.register_blueprint(portfolio.to_flask_blueprint())
    app.register_blueprint(trading.to_flask_blueprint())
    app.register_blueprint(subscriptions.to_flask_blueprint())
    app.register_blueprint(users.to_flask_blueprint())
    
    return app
