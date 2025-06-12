# api/app.py
from flask import Flask
from flask_cors import CORS
from flask_limiter import Limiter
from api.auth import AuthManager
from config import ConfigManager

def create_app():
    app = Flask(__name__)
    CORS(app)
    Limiter(app, default_limits=["60 per minute"])
    AuthManager(app)
    return app
