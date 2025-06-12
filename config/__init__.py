"""
Configuration package for managing Binance trading bot settings.
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from threading import Lock

# Explicit settings import
from .settings import BASE_CONFIG  # Example, adjust to actual variables

CONFIG_DIR = Path(__file__).parent
CONFIG_FILE = CONFIG_DIR / "config.yaml"

class ConfigManager:
    """Manages configuration loading from YAML and environment variables."""
    _config_cache: Optional[Dict[str, Any]] = None
    _lock = Lock()
    
    @classmethod
    def load_config(cls, reload: bool = False) -> Dict[str, Any]:
        """Load configuration from config.yaml.
        
        Args:
            reload: Force reload of configuration even if cached
            
        Returns:
            Dictionary of configuration values
            
        Raises:
            FileNotFoundError: If config.yaml doesn't exist
            yaml.YAMLError: If config.yaml contains invalid YAML
            ValueError: If config.yaml is empty
        """
        with cls._lock:
            if cls._config_cache is not None and not reload:
                return cls._config_cache
            if not CONFIG_FILE.exists():
                if os.getenv("FLASK_ENV") == "development":
                    cls._config_cache = {"binance": {"api_key": "test_key", "secret": "test_secret"}}
                    return cls._config_cache
                raise FileNotFoundError(f"Configuration file not found: {CONFIG_FILE}")
            if not os.access(CONFIG_FILE, os.R_OK):
                raise PermissionError(f"No read permission for: {CONFIG_FILE}")
            with open(CONFIG_FILE, 'r', encoding='utf-8') as file:
                if not (cls._config_cache := yaml.safe_load(file)):
                    raise ValueError("Configuration file is empty")
            cls._config_cache.update(BASE_CONFIG)
            return cls._config_cache
    
    @classmethod
    def get_config(cls, key: str, default: Any = None) -> Any:
        """Get configuration value by key, with environment variable override.
        
        Args:
            key: Configuration key (supports dot notation)
            default: Default value if key not found
            
        Returns:
            Configuration value, environment variable, or default
        """
        env_key = f"TRADING_BOT_{key.upper().replace('.', '_')}"
        if env_value := os.getenv(env_key):
            return env_value
        config = cls.load_config()
        keys = key.split('.')
        value = config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    @classmethod
    def validate_config(cls) -> None:
        """Validate required configuration on startup."""
        required_keys = ['binance.api_key', 'binance.secret', 'trade.symbol']
        for key in required_keys:
            if cls.get_config(key) is None:
                raise ValueError(f"Missing required configuration: {key}")

__all__ = ['ConfigManager']
