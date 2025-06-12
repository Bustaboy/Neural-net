"""
Configuration package initialization file.

This module provides a clean interface for accessing configuration settings
from both YAML files and Python settings modules.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

# Get the directory where this file is located
CONFIG_DIR = Path(__file__).parent
CONFIG_FILE = CONFIG_DIR / "config.yaml"

# Import settings from settings.py
from .settings import *

# Cache for loaded configuration
_config_cache: Optional[Dict[str, Any]] = None


def load_config(reload: bool = False) -> Dict[str, Any]:
    """
    Load configuration from config.yaml file.
    
    Args:
        reload: Force reload of configuration even if cached
        
    Returns:
        Dictionary containing configuration values
        
    Raises:
        FileNotFoundError: If config.yaml doesn't exist
        yaml.YAMLError: If config.yaml contains invalid YAML
    """
    global _config_cache
    
    if _config_cache is not None and not reload:
        return _config_cache
    
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"Configuration file not found: {CONFIG_FILE}")
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as file:
            _config_cache = yaml.safe_load(file) or {}
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Error parsing configuration file: {e}")
    
    return _config_cache


def get_config(key: str, default: Any = None) -> Any:
    """
    Get a configuration value by key.
    
    Args:
        key: Configuration key (supports dot notation for nested values)
        default: Default value if key not found
        
    Returns:
        Configuration value or default
    """
    config = load_config()
    
    # Support dot notation for nested values
    keys = key.split('.')
    value = config
    
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return default
    
    return value


# Make common functions available at package level
__all__ = ['load_config', 'get_config', 'CONFIG_DIR', 'CONFIG_FILE']


# Configuration Validation
def validate_config():
    """Validate configuration on startup."""
    config = load_config()
    required_keys = ['app.name', 'server.port', 'database.main.engine']
    for key in required_keys:
        if get_config(key) is None:
            raise ValueError(f"Missing required configuration: {key}")


# Environment Variable Override
def get_config(key: str, default: Any = None) -> Any:
    """Get configuration with environment variable override."""
    # Check environment first (MYAPP_DATABASE_HOST for database.host)
    env_key = f"MYAPP_{key.upper().replace('.', '_')}"
    env_value = os.getenv(env_key)
    if env_value is not None:
        return env_value
    
    # Then check YAML config
    # ... (existing code)
