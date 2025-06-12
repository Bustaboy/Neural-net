"""
Application settings module.

This module contains Python-based configuration settings that complement
the YAML configuration. Use this for settings that require Python objects,
computed values, or environment-specific logic.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import timedelta

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Environment detection
ENVIRONMENT = os.getenv('APP_ENV', 'development').lower()
IS_PRODUCTION = ENVIRONMENT == 'production'
IS_DEVELOPMENT = ENVIRONMENT == 'development'
IS_TESTING = ENVIRONMENT == 'testing'

# Debug mode - Never set to True in production!
DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes') and not IS_PRODUCTION

# Security settings from environment variables
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
if IS_PRODUCTION and SECRET_KEY == 'dev-secret-key-change-in-production':
    raise ValueError("SECRET_KEY must be set in production environment!")

# Allowed hosts
ALLOWED_HOSTS: List[str] = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Database configuration from environment
DATABASE_URL = os.getenv('DATABASE_URL', '')
if DATABASE_URL:
    # Parse database URL if provided
    import urllib.parse
    url = urllib.parse.urlparse(DATABASE_URL)
    DATABASE_CONFIG = {
        'engine': url.scheme,
        'host': url.hostname,
        'port': url.port,
        'name': url.path[1:],
        'user': url.username,
        'password': url.password,
    }
else:
    # Default database configuration
    DATABASE_CONFIG = {
        'engine': os.getenv('DB_ENGINE', 'postgresql'),
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', '5432')),
        'name': os.getenv('DB_NAME', 'myapp_db'),
        'user': os.getenv('DB_USER', 'myapp_user'),
        'password': os.getenv('DB_PASSWORD', 'secure_password'),
    }

# Redis configuration
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Logging configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO' if IS_PRODUCTION else 'DEBUG')
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'console': {
            'level': LOG_LEVEL,
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'level': LOG_LEVEL,
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'app.log',
            'maxBytes': 10 * 1024 * 1024,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': LOG_LEVEL,
    },
    'loggers': {
        'app': {
            'handlers': ['console', 'file'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
    },
}

# CORS settings
CORS_ALLOWED_ORIGINS = os.getenv('CORS_ALLOWED_ORIGINS', '').split(',') if os.getenv('CORS_ALLOWED_ORIGINS') else [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# JWT settings
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', SECRET_KEY)
JWT_ALGORITHM = 'HS256'
JWT_ACCESS_TOKEN_EXPIRE = timedelta(minutes=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRE_MINUTES', '30')))
JWT_REFRESH_TOKEN_EXPIRE = timedelta(days=int(os.getenv('JWT_REFRESH_TOKEN_EXPIRE_DAYS', '7')))

# Email settings
EMAIL_BACKEND = 'smtp' if os.getenv('EMAIL_ENABLED', 'false').lower() == 'true' else 'console'
EMAIL_CONFIG = {
    'host': os.getenv('SMTP_HOST', 'smtp.gmail.com'),
    'port': int(os.getenv('SMTP_PORT', '587')),
    'username': os.getenv('SMTP_USERNAME', ''),
    'password': os.getenv('SMTP_PASSWORD', ''),
    'use_tls': os.getenv('SMTP_USE_TLS', 'true').lower() == 'true',
    'from_email': os.getenv('DEFAULT_FROM_EMAIL', 'noreply@example.com'),
}

# File upload settings
UPLOAD_DIR = BASE_DIR / 'uploads'
UPLOAD_DIR.mkdir(exist_ok=True)

MAX_UPLOAD_SIZE = int(os.getenv('MAX_UPLOAD_SIZE', str(5 * 1024 * 1024)))  # 5MB default
ALLOWED_UPLOAD_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.pdf', '.doc', '.docx', '.txt'}

# Cache settings
CACHE_TYPE = os.getenv('CACHE_TYPE', 'redis' if IS_PRODUCTION else 'simple')
CACHE_CONFIG = {
    'redis': {
        'backend': 'redis',
        'location': REDIS_URL,
        'options': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'MAX_CONNECTIONS': 50,
        },
        'KEY_PREFIX': f'myapp_{ENVIRONMENT}',
        'TIMEOUT': 300,  # 5 minutes default
    },
    'simple': {
        'backend': 'simple',
        'location': 'unique-snowflake',
    }
}

# Celery settings (if using task queue)
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', REDIS_URL)
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TIMEZONE = 'UTC'
CELERY_ENABLE_UTC = True

# API Rate limiting
RATE_LIMIT_ENABLED = os.getenv('RATE_LIMIT_ENABLED', 'true').lower() == 'true'
RATE_LIMIT_CONFIG = {
    'default': '60/minute',
    'auth': '5/minute',
    'api': '1000/hour',
}

# Feature flags
FEATURES = {
    'REGISTRATION_ENABLED': os.getenv('FEATURE_REGISTRATION', 'true').lower() == 'true',
    'SOCIAL_AUTH_ENABLED': os.getenv('FEATURE_SOCIAL_AUTH', 'false').lower() == 'true',
    'TWO_FACTOR_AUTH': os.getenv('FEATURE_2FA', 'false').lower() == 'true',
    'API_DOCUMENTATION': os.getenv('FEATURE_API_DOCS', 'true').lower() == 'true',
    'MAINTENANCE_MODE': os.getenv('MAINTENANCE_MODE', 'false').lower() == 'true',
}

# Third-party service configurations
SENTRY_DSN = os.getenv('SENTRY_DSN', '')
if SENTRY_DSN and IS_PRODUCTION:
    import sentry_sdk
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=ENVIRONMENT,
        traces_sample_rate=0.1,
    )

# Stripe configuration
STRIPE_PUBLIC_KEY = os.getenv('STRIPE_PUBLIC_KEY', '')
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')

# AWS S3 configuration (if using S3 for storage)
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', '')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', '')
AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME', '')
AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', 'us-east-1')
AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com' if AWS_STORAGE_BUCKET_NAME else None

# Application-specific settings
APP_NAME = os.getenv('APP_NAME', 'MyApplication')
APP_VERSION = os.getenv('APP_VERSION', '1.0.0')
APP_DESCRIPTION = os.getenv('APP_DESCRIPTION', 'A powerful application built with Python')

# Timezone settings
USE_TZ = True
TIMEZONE = os.getenv('TIMEZONE', 'UTC')

# Pagination defaults
DEFAULT_PAGE_SIZE = int(os.getenv('DEFAULT_PAGE_SIZE', '20'))
MAX_PAGE_SIZE = int(os.getenv('MAX_PAGE_SIZE', '100'))

# Security headers
SECURITY_HEADERS = {
    'X-Frame-Options': 'DENY',
    'X-Content-Type-Options': 'nosniff',
    'X-XSS-Protection': '1; mode=block',
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains' if IS_PRODUCTION else None,
    'Content-Security-Policy': "default-src 'self'",
}

# Custom middleware settings
MIDDLEWARE_CLASSES = [
    'middleware.security.SecurityHeadersMiddleware',
    'middleware.logging.RequestLoggingMiddleware',
    'middleware.auth.AuthenticationMiddleware',
]

# Development-specific settings
if IS_DEVELOPMENT:
    # Enable all debug toolbars and development aids
    DEBUG_TOOLBAR_ENABLED = True
    PROFILING_ENABLED = True
    
    # Use console email backend in development
    EMAIL_BACKEND = 'console'
    
    # Disable rate limiting in development
    RATE_LIMIT_ENABLED = False

# Testing-specific settings
if IS_TESTING:
    # Use in-memory database for tests
    DATABASE_CONFIG['engine'] = 'sqlite'
    DATABASE_CONFIG['name'] = ':memory:'
    
    # Disable external services in tests
    EMAIL_BACKEND = 'test'
    CELERY_TASK_ALWAYS_EAGER = True
    SENTRY_DSN = ''

# Helper functions
def get_env_bool(key: str, default: bool = False) -> bool:
    """Get boolean value from environment variable."""
    value = os.getenv(key, str(default)).lower()
    return value in ('true', '1', 'yes', 'on')

def get_env_list(key: str, default: Optional[List[str]] = None) -> List[str]:
    """Get list value from environment variable (comma-separated)."""
    value = os.getenv(key, '')
    if not value:
        return default or []
    return [item.strip() for item in value.split(',') if item.strip()]

def get_env_int(key: str, default: int = 0) -> int:
    """Get integer value from environment variable."""
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default

# Export commonly used settings
__all__ = [
    'BASE_DIR',
    'ENVIRONMENT',
    'IS_PRODUCTION',
    'IS_DEVELOPMENT',
    'IS_TESTING',
    'DEBUG',
    'SECRET_KEY',
    'DATABASE_CONFIG',
    'REDIS_URL',
    'LOGGING_CONFIG',
    'FEATURES',
    'get_env_bool',
    'get_env_list',
    'get_env_int',
]