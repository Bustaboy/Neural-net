#!/usr/bin/env python3
"""
Enhanced API Server with Full Authentication and WebSocket Support
Version: 3.0.0
"""

import os
import sys
import asyncio
import json
import logging
import time
import jwt
import bcrypt
import redis
import uuid
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, Optional, List, Any

from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.exceptions import HTTPException

import prometheus_client
from prometheus_client import Counter, Histogram, Gauge

# Import trading bot components
from enhanced_trading_bot import EnhancedTradingBot, config
from safe_trading_database import SafeTradingDatabase
from binance.client import Client
from binance.exceptions import BinanceAPIException

# Initialize Flask app
app = Flask(__name__, static_folder='web/static', template_folder='web/templates')

# Security headers middleware
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com;"
    return response

# Configure CORS with specific origins
CORS(app, origins=[
    "http://localhost:3000",
    "http://localhost:5000",
    "https://your-domain.com"
], supports_credentials=True)

# Configure rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["1000 per hour", "100 per minute"],
    storage_uri=f"redis://:{os.getenv('REDIS_PASSWORD', '')}@redis:6379"
)

# Configure SocketIO
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='eventlet',
    logger=True,
    engineio_logger=False
)

# Configure JWT
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'change-this-in-production')
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'change-this-too')
app.config['JWT_EXPIRATION_DELTA'] = timedelta(hours=24)
app.config['JWT_REFRESH_EXPIRATION_DELTA'] = timedelta(days=30)

# Redis client for session management
try:
    redis_client = redis.Redis(
        host=os.getenv('REDIS_HOST', 'redis'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        password=os.getenv('REDIS_PASSWORD', ''),
        decode_responses=True,
        socket_connect_timeout=5,
        retry_on_timeout=True
    )
    redis_client.ping()
except redis.ConnectionError:
    logging.warning("Redis not available, using in-memory session storage")
    redis_client = None

# Prometheus metrics
request_count = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint', 'status'])
request_duration = Histogram('api_request_duration_seconds', 'API request duration', ['method', 'endpoint'])
active_connections = Gauge('websocket_connections_active', 'Active WebSocket connections')
trading_bot_status = Gauge('trading_bot_status', 'Trading bot status (1=running, 0=stopped)')

# Global state
bot_instance: Optional[EnhancedTradingBot] = None
bot_thread = None
connected_clients = {}
admin_users = {}

# Setup logging
def setup_logging():
    """Setup comprehensive logging"""
    from logging.handlers import RotatingFileHandler
    
    os.makedirs('logs', exist_ok=True)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    
    # API server log
    file_handler = RotatingFileHandler(
        'logs/api_server.log',
        maxBytes=10*1024*1024,
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    
    # Access log
    access_handler = RotatingFileHandler(
        'logs/access.log',
        maxBytes=10*1024*1024,
        backupCount=5
    )
    access_handler.setFormatter(formatter)
    
    # Configure loggers
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    
    # Werkzeug logger for access logs
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.addHandler(access_handler)
    
    return app.logger

logger = setup_logging()

# Database initialization
def init_database():
    """Initialize database and admin user"""
    try:
        db = SafeTradingDatabase()
        
        # Create admin user if not exists
        admin_username = os.getenv('ADMIN_USERNAME', 'admin')
        admin_password = os.getenv('ADMIN_PASSWORD', 'changeme')
        
        # Hash password
        password_hash = bcrypt.hashpw(
            admin_password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')
        
        admin_users[admin_username] = {
            'username': admin_username,
            'password_hash': password_hash,
            'created_at': datetime.utcnow(),
            'role': 'admin'
        }
        
        logger.info("Database and admin user initialized")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

# Authentication helpers
def generate_tokens(username: str) -> Dict[str, str]:
    """Generate access and refresh tokens"""
    now = datetime.utcnow()
    
    # Access token
    access_payload = {
        'username': username,
        'type': 'access',
        'iat': now,
        'exp': now + app.config['JWT_EXPIRATION_DELTA']
    }
    
    access_token = jwt.encode(
        access_payload,
        app.config['JWT_SECRET_KEY'],
        algorithm='HS256'
    )
    
    # Refresh token
    refresh_payload = {
        'username': username,
        'type': 'refresh',
        'iat': now,
        'exp': now + app.config['JWT_REFRESH_EXPIRATION_DELTA']
    }
    
    refresh_token = jwt.encode(
        refresh_payload,
        app.config['JWT_SECRET_KEY'],
        algorithm='HS256'
    )
    
    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'expires_in': int(app.config['JWT_EXPIRATION_DELTA'].total_seconds())
    }

def verify_token(token: str, token_type: str = 'access') -> Optional[Dict]:
    """Verify JWT token"""
    try:
        payload = jwt.decode(
            token,
            app.config['JWT_SECRET_KEY'],
            algorithms=['HS256']
        )
        
        if payload.get('type') != token_type:
            return None
            
        # Check if token is blacklisted
        if redis_client and redis_client.get(f"blacklist:{token}"):
            return None
            
        return payload
        
    except jwt.ExpiredSignatureError:
        logger.debug("Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.debug(f"Invalid token: {e}")
        return None

# Authentication decorator
def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'error': 'No authorization token provided'}), 401
            
        if token.startswith('Bearer '):
            token = token[7:]
        else:
            return jsonify({'error': 'Invalid token format'}), 401
            
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid or expired token'}), 401
            
        request.current_user = payload['username']
        return f(*args, **kwargs)
        
    return decorated_function

# Metrics decorator
def track_metrics(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        status_code = 200
        
        try:
            result = f(*args, **kwargs)
            if isinstance(result, tuple):
                status_code = result[1]
            return result
        except HTTPException as e:
            status_code = e.code
            raise
        except Exception:
            status_code = 500
            raise
        finally:
            duration = time.time() - start_time
            endpoint = request.endpoint or 'unknown'
            
            request_count.labels(
                method=request.method,
                endpoint=endpoint,
                status=status_code
            ).inc()
            
            request_duration.labels(
                method=request.method,
                endpoint=endpoint
            ).observe(duration)
    
    return decorated_function

# Error handlers
@app.errorhandler(HTTPException)
def handle_http_exception(e):
    response = e.get_response()
    response.data = json.dumps({
        'error': e.description,
        'code': e.code
    })
    response.content_type = "application/json"
    return response

@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled exception: {e}", exc_info=True)
    return jsonify({
        'error': 'Internal server error',
        'message': str(e) if app.debug else 'An error occurred'
    }), 500

# API Routes
@app.route('/')
def index():
    """Serve the main web interface"""
    return send_from_directory('web', 'index.html')

@app.route('/api/health')
@track_metrics
def health_check():
    """Health check endpoint"""
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '3.0.0',
        'components': {
            'api': 'healthy',
            'database': 'unknown',
            'redis': 'unknown',
            'trading_bot': 'unknown'
        }
    }
    
    # Check database
    try:
        db = SafeTradingDatabase()
        db.get_performance_stats(1)
        health_status['components']['database'] = 'healthy'
    except Exception as e:
        health_status['components']['database'] = 'unhealthy'
        health_status['status'] = 'degraded'
    
    # Check Redis
    if redis_client:
        try:
            redis_client.ping()
            health_status['components']['redis'] = 'healthy'
        except Exception:
            health_status['components']['redis'] = 'unhealthy'
            health_status['status'] = 'degraded'
    
    # Check trading bot
    if bot_instance and bot_instance.running:
        health_status['components']['trading_bot'] = 'healthy'
    else:
        health_status['components']['trading_bot'] = 'stopped'
    
    status_code = 200 if health_status['status'] == 'healthy' else 503
    return jsonify(health_status), status_code

@app.route('/api/login', methods=['POST'])
@track_metrics
@limiter.limit("5 per minute")
def login():
    """Authenticate user and return tokens"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if not username or not password:
            return jsonify({'error': 'Username and password required'}), 400
        
        # Verify credentials
        user = admin_users.get(username)
        if not user:
            logger.warning(f"Login attempt for unknown user: {username}")
            return jsonify({'error': 'Invalid credentials'}), 401
        
        if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            logger.warning(f"Failed login attempt for user: {username}")
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Generate tokens
        tokens = generate_tokens(username)
        
        # Store session in Redis
        if redis_client:
            session_id = str(uuid.uuid4())
            session_data = {
                'username': username,
                'login_time': datetime.utcnow().isoformat(),
                'ip_address': request.remote_addr,
                'user_agent': request.headers.get('User-Agent', '')
            }
            
            redis_client.setex(
                f"session:{session_id}",
                int(app.config['JWT_EXPIRATION_DELTA'].total_seconds()),
                json.dumps(session_data)
            )
            
            tokens['session_id'] = session_id
        
        logger.info(f"Successful login for user: {username}")
        
        return jsonify({
            'success': True,
            **tokens
        })
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'error': 'Login failed'}), 500

@app.route('/api/refresh', methods=['POST'])
@track_metrics
def refresh_token():
    """Refresh access token using refresh token"""
    try:
        data = request.get_json()
        refresh_token = data.get('refresh_token')
        
        if not refresh_token:
            return jsonify({'error': 'Refresh token required'}), 400
        
        payload = verify_token(refresh_token, token_type='refresh')
        if not payload:
            return jsonify({'error': 'Invalid refresh token'}), 401
        
        # Generate new tokens
        tokens = generate_tokens(payload['username'])
        
        return jsonify({
            'success': True,
            **tokens
        })
        
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        return jsonify({'error': 'Token refresh failed'}), 500

@app.route('/api/logout', methods=['POST'])
@require_auth
@track_metrics
def logout():
    """Logout user and invalidate tokens"""
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        # Add token to blacklist
        if redis_client and token:
            redis_client.setex(
                f"blacklist:{token}",
                int(app.config['JWT_EXPIRATION_DELTA'].total_seconds()),
                "true"
            )
        
        # Remove session
        session_id = request.get_json().get('session_id')
        if redis_client and session_id:
            redis_client.delete(f"session:{session_id}")
        
        logger.info(f"User {request.current_user} logged out")
        
        return jsonify({'success': True, 'message': 'Logged out successfully'})
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return jsonify({'error': 'Logout failed'}), 500

# Continue with more routes...
# (Due to length, I'll continue in the next response)