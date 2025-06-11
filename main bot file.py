#!/usr/bin/env python3
"""
Enhanced Binance Trading Bot with Market Intelligence
Version: 3.0.0
Includes: Cycle Detection, Bitcoin Dominance Trading, Dynamic Profit Targets, Volatility Regime Trading
All security and performance issues fixed
"""

import logging
import os
import sys
import pandas as pd
import numpy as np
import time
import asyncio
import aiohttp
from datetime import datetime, date, timedelta
from binance.client import Client
from binance.websockets import BinanceSocketManager
from binance.exceptions import BinanceAPIException
from dotenv import load_dotenv
import json
from decimal import Decimal, ROUND_DOWN
import threading
import sqlite3
import yaml
from typing import Dict, List, Optional, Tuple, Any, Union
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from dataclasses import dataclass, asdict, field
import signal
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.exceptions import NotFittedError
import pickle
from collections import defaultdict, deque
import hashlib
import queue
from contextlib import contextmanager
import traceback
import psutil
import gc

# Try to import scipy, fallback to numpy implementation
try:
    from scipy.stats import pearsonr, spearmanr
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    logging.warning("scipy not available, using numpy-based correlation calculations")
    
    def pearsonr(x, y):
        """Numpy-based Pearson correlation coefficient"""
        x = np.array(x)
        y = np.array(y)
        
        if len(x) != len(y) or len(x) < 2:
            return 0.0, 1.0
            
        # Remove any NaN values
        mask = ~(np.isnan(x) | np.isnan(y))
        x = x[mask]
        y = y[mask]
        
        if len(x) < 2:
            return 0.0, 1.0
            
        x_mean = np.mean(x)
        y_mean = np.mean(y)
        
        num = np.sum((x - x_mean) * (y - y_mean))
        den_x = np.sum((x - x_mean)**2)
        den_y = np.sum((y - y_mean)**2)
        
        if den_x == 0 or den_y == 0:
            return 0.0, 1.0
            
        r = num / np.sqrt(den_x * den_y)
        return np.clip(r, -1.0, 1.0), 0.0  # Simplified p-value
    
    def spearmanr(x, y):
        """Numpy-based Spearman correlation coefficient"""
        x = np.array(x)
        y = np.array(y)
        
        if len(x) != len(y) or len(x) < 3:
            return 0.0, 1.0
            
        # Rank the data
        x_ranks = pd.Series(x).rank().values
        y_ranks = pd.Series(y).rank().values
        
        return pearsonr(x_ranks, y_ranks)

# Load environment variables
load_dotenv()

# Load configuration with validation
def load_config(config_path: str = 'enhanced_config.yaml') -> Dict[str, Any]:
    """Load and validate configuration"""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        # Validate required sections
        required_sections = ['trading', 'strategy', 'risk_management', 'market_intelligence']
        for section in required_sections:
            if section not in config:
                raise ValueError(f"Missing required config section: {section}")
                
        # Set defaults for optional values
        config.setdefault('system', {}).setdefault('timezone', 'UTC')
        config.setdefault('performance', {}).setdefault('track_metrics', True)
        
        return config
        
    except FileNotFoundError:
        logging.error(f"Configuration file not found: {config_path}")
        raise
    except yaml.YAMLError as e:
        logging.error(f"Invalid YAML in configuration: {e}")
        raise
    except Exception as e:
        logging.error(f"Error loading configuration: {e}")
        raise

# Initialize configuration
try:
    config = load_config()
except Exception:
    logging.critical("Failed to load configuration. Creating default config...")
    # Create minimal default config
    config = {
        'trading': {
            'symbols': ['BTCUSDT', 'ETHUSDT'],
            'initial_capital': 1000.0,
            'position_size_pct': 1.0,
            'min_trade_size': 10.0,
            'max_positions': 3
        },
        'strategy': {
            'base_profit_target': 0.03,
            'stop_loss': 0.02,
            'confidence_threshold': 0.7,
            'max_hold_time_hours': 24
        },
        'risk_management': {
            'max_drawdown_pct': 10.0,
            'daily_loss_limit_pct': 3.0,
            'max_consecutive_losses': 5,
            'emergency_fund_pct': 10.0
        },
        'market_intelligence': {
            'cycle_detection': {'enabled': True},
            'dominance_trading': {'enabled': True},
            'volatility_detection': {'enabled': True}
        }
    }

# Setup enhanced logging
def setup_enhanced_logging():
    """Setup comprehensive logging with rotation"""
    from logging.handlers import RotatingFileHandler
    import colorlog
    
    os.makedirs('logs', exist_ok=True)
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s() - %(message)s'
    )
    
    # Console formatter with colors
    console_formatter = colorlog.ColoredFormatter(
        '%(log_color)s%(asctime)s - %(levelname)s - %(message)s',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    
    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        'logs/enhanced_trading_bot.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Error file handler
    error_handler = RotatingFileHandler(
        'logs/errors.log',
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    logger.addHandler(error_handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # Set specific logger levels
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('binance').setLevel(logging.WARNING)
    
    return logger

# Initialize logger
logger = setup_enhanced_logging()

# Enhanced Data Classes with validation
@dataclass
class MarketSignal:
    """Enhanced market signal with validation"""
    symbol: str
    signal_type: str  # 'buy', 'sell', 'hold'
    confidence: float
    strategy: str
    price: float
    timestamp: datetime
    features: Dict[str, Any] = field(default_factory=dict)
    cycle_phase: Optional[str] = None
    dominance_phase: Optional[str] = None
    volatility_regime: Optional[str] = None
    
    def __post_init__(self):
        # Validate signal type
        if self.signal_type not in ['buy', 'sell', 'hold']:
            raise ValueError(f"Invalid signal type: {self.signal_type}")
        
        # Validate confidence
        if not 0 <= self.confidence <= 1:
            raise ValueError(f"Confidence must be between 0 and 1: {self.confidence}")
        
        # Validate price
        if self.price < 0:
            raise ValueError(f"Price cannot be negative: {self.price}")

@dataclass
class TradeRecord:
    """Trade record with enhanced tracking"""
    symbol: str
    side: str
    quantity: float
    price: float
    timestamp: datetime
    order_id: str
    trade_type: str
    strategy: str
    confidence: float
    profit_loss: Optional[float] = None
    profit_pct: Optional[float] = None
    reason: Optional[str] = None
    cycle_phase: Optional[str] = None
    dominance_phase: Optional[str] = None
    volatility_regime: Optional[str] = None
    fees: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

# Database connection pool
class DatabasePool:
    """Thread-safe database connection pool"""
    
    def __init__(self, db_path: str, pool_size: int = 5):
        self.db_path = db_path
        self.pool = queue.Queue(maxsize=pool_size)
        self._lock = threading.Lock()
        
        # Initialize pool
        for _ in range(pool_size):
            conn = sqlite3.connect(db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            self.pool.put(conn)
    
    @contextmanager
    def get_connection(self):
        """Get connection from pool"""
        conn = self.pool.get()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self.pool.put(conn)
    
    def close_all(self):
        """Close all connections"""
        while not self.pool.empty():
            try:
                conn = self.pool.get_nowait()
                conn.close()
            except queue.Empty:
                break

# Enhanced Database Manager
class EnhancedDatabaseManager:
    """Database manager with connection pooling and better error handling"""
    
    def __init__(self, db_path: str = "enhanced_trading_bot.db"):
        self.db_path = db_path
        self.pool = DatabasePool(db_path)
        self._init_database()
    
    def _init_database(self):
        """Initialize database with enhanced schema"""
        with self.pool.get_connection() as conn:
            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Create tables with proper indexes
            conn.executescript('''
                -- Trades table with enhanced fields
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL CHECK(side IN ('BUY', 'SELL')),
                    quantity REAL NOT NULL CHECK(quantity > 0),
                    price REAL NOT NULL CHECK(price > 0),
                    timestamp TEXT NOT NULL,
                    order_id TEXT UNIQUE,
                    trade_type TEXT,
                    strategy TEXT,
                    confidence REAL CHECK(confidence BETWEEN 0 AND 1),
                    profit_loss REAL,
                    profit_pct REAL,
                    reason TEXT,
                    cycle_phase TEXT,
                    dominance_phase TEXT,
                    volatility_regime TEXT,
                    fees REAL DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_symbol_timestamp (symbol, timestamp),
                    INDEX idx_strategy (strategy),
                    INDEX idx_profit (profit_loss)
                );
                
                -- Performance metrics table
                CREATE TABLE IF NOT EXISTS daily_performance (
                    date TEXT PRIMARY KEY,
                    total_trades INTEGER DEFAULT 0,
                    winning_trades INTEGER DEFAULT 0,
                    losing_trades INTEGER DEFAULT 0,
                    total_profit REAL DEFAULT 0,
                    total_loss REAL DEFAULT 0,
                    net_profit REAL DEFAULT 0,
                    portfolio_value REAL DEFAULT 0,
                    max_drawdown REAL DEFAULT 0,
                    sharpe_ratio REAL,
                    win_rate REAL,
                    profit_factor REAL,
                    cycle_phase TEXT,
                    dominance_phase TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                
                -- System events table
                CREATE TABLE IF NOT EXISTS system_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    severity TEXT DEFAULT 'INFO',
                    component TEXT,
                    message TEXT,
                    details TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_timestamp_severity (timestamp, severity)
                );
                
                -- Market conditions table
                CREATE TABLE IF NOT EXISTS market_conditions (
                    timestamp TEXT PRIMARY KEY,
                    btc_price REAL,
                    btc_dominance REAL,
                    total_market_cap REAL,
                    fear_greed_index INTEGER,
                    volatility_index REAL,
                    cycle_phase TEXT,
                    dominance_phase TEXT,
                    volatility_regime TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                
                -- Strategy performance table
                CREATE TABLE IF NOT EXISTS strategy_performance (
                    strategy TEXT PRIMARY KEY,
                    total_trades INTEGER DEFAULT 0,
                    winning_trades INTEGER DEFAULT 0,
                    total_profit REAL DEFAULT 0,
                    avg_profit REAL DEFAULT 0,
                    max_profit REAL DEFAULT 0,
                    max_loss REAL DEFAULT 0,
                    win_rate REAL DEFAULT 0,
                    profit_factor REAL DEFAULT 0,
                    sharpe_ratio REAL DEFAULT 0,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            
            logger.info("Database initialized successfully")
    
    def save_trade(self, trade: TradeRecord) -> bool:
        """Save trade record with error handling"""
        try:
            with self.pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO trades (
                        symbol, side, quantity, price, timestamp, order_id,
                        trade_type, strategy, confidence, profit_loss, profit_pct,
                        reason, cycle_phase, dominance_phase, volatility_regime, fees
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    trade.symbol, trade.side, trade.quantity, trade.price,
                    trade.timestamp.isoformat(), trade.order_id, trade.trade_type,
                    trade.strategy, trade.confidence, trade.profit_loss,
                    trade.profit_pct, trade.reason, trade.cycle_phase,
                    trade.dominance_phase, trade.volatility_regime, trade.fees
                ))
                
                # Update strategy performance
                self._update_strategy_performance(conn, trade)
                
                logger.debug(f"Trade saved: {trade.order_id}")
                return True
                
        except sqlite3.IntegrityError as e:
            logger.warning(f"Trade already exists: {trade.order_id}")
            return False
        except Exception as e:
            logger.error(f"Error saving trade: {e}")
            return False
    
    def _update_strategy_performance(self, conn: sqlite3.Connection, trade: TradeRecord):
        """Update strategy performance metrics"""
        if not trade.strategy or trade.profit_loss is None:
            return
            
        cursor = conn.cursor()
        
        # Get current stats
        cursor.execute(
            "SELECT * FROM strategy_performance WHERE strategy = ?",
            (trade.strategy,)
        )
        row = cursor.fetchone()
        
        if row:
            # Update existing record
            total_trades = row['total_trades'] + 1
            winning_trades = row['winning_trades'] + (1 if trade.profit_loss > 0 else 0)
            total_profit = row['total_profit'] + trade.profit_loss
            
            cursor.execute('''
                UPDATE strategy_performance
                SET total_trades = ?,
                    winning_trades = ?,
                    total_profit = ?,
                    avg_profit = ?,
                    max_profit = MAX(max_profit, ?),
                    max_loss = MIN(max_loss, ?),
                    win_rate = ?,
                    last_updated = CURRENT_TIMESTAMP
                WHERE strategy = ?
            ''', (
                total_trades,
                winning_trades,
                total_profit,
                total_profit / total_trades,
                trade.profit_loss,
                trade.profit_loss,
                winning_trades / total_trades,
                trade.strategy
            ))
        else:
            # Insert new record
            cursor.execute('''
                INSERT INTO strategy_performance (
                    strategy, total_trades, winning_trades, total_profit,
                    avg_profit, max_profit, max_loss, win_rate
                ) VALUES (?, 1, ?, ?, ?, ?, ?, ?)
            ''', (
                trade.strategy,
                1 if trade.profit_loss > 0 else 0,
                trade.profit_loss,
                trade.profit_loss,
                max(0, trade.profit_loss),
                min(0, trade.profit_loss),
                1.0 if trade.profit_loss > 0 else 0.0
            ))
    
    def get_recent_trades(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent trades with proper error handling"""
        try:
            with self.pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM trades
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (limit,))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error fetching recent trades: {e}")
            return []
    
    def get_performance_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get performance statistics"""
        try:
            with self.pool.get_connection() as conn:
                cursor = conn.cursor()
                
                # Calculate date range
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                
                # Get trade statistics
                cursor.execute('''
                    SELECT
                        COUNT(*) as total_trades,
                        SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
                        SUM(CASE WHEN profit_loss < 0 THEN 1 ELSE 0 END) as losing_trades,
                        SUM(CASE WHEN profit_loss > 0 THEN profit_loss ELSE 0 END) as total_profit,
                        SUM(CASE WHEN profit_loss < 0 THEN ABS(profit_loss) ELSE 0 END) as total_loss,
                        SUM(profit_loss) as net_profit,
                        AVG(profit_loss) as avg_profit,
                        AVG(profit_pct) as avg_profit_pct,
                        MAX(profit_loss) as max_profit,
                        MIN(profit_loss) as max_loss,
                        AVG(confidence) as avg_confidence
                    FROM trades
                    WHERE timestamp >= ? AND timestamp <= ?
                ''', (start_date.isoformat(), end_date.isoformat()))
                
                stats = dict(cursor.fetchone() or {})
                
                # Calculate additional metrics
                if stats.get('total_trades', 0) > 0:
                    stats['win_rate'] = (stats.get('winning_trades', 0) / stats['total_trades']) * 100
                    
                    if stats.get('total_loss', 0) > 0:
                        stats['profit_factor'] = stats.get('total_profit', 0) / stats['total_loss']
                    else:
                        stats['profit_factor'] = float('inf') if stats.get('total_profit', 0) > 0 else 0
                    
                    # Calculate Sharpe ratio (simplified)
                    cursor.execute('''
                        SELECT 
                            AVG(profit_pct) as mean_return,
                            SQRT(AVG(profit_pct * profit_pct) - AVG(profit_pct) * AVG(profit_pct)) as std_return
                        FROM trades
                        WHERE timestamp >= ? AND timestamp <= ?
                        AND profit_pct IS NOT NULL
                    ''', (start_date.isoformat(), end_date.isoformat()))
                    
                    returns_data = cursor.fetchone()
                    if returns_data and returns_data['std_return'] and returns_data['std_return'] > 0:
                        # Annualized Sharpe ratio (assuming 365 trading days)
                        stats['sharpe_ratio'] = (returns_data['mean_return'] * np.sqrt(365)) / returns_data['std_return']
                    else:
                        stats['sharpe_ratio'] = 0
                    
                    # Get strategy breakdown
                    cursor.execute('''
                        SELECT 
                            strategy,
                            COUNT(*) as trades,
                            SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as wins,
                            SUM(profit_loss) as total_pnl
                        FROM trades
                        WHERE timestamp >= ? AND timestamp <= ?
                        GROUP BY strategy
                        ORDER BY total_pnl DESC
                    ''', (start_date.isoformat(), end_date.isoformat()))
                    
                    stats['strategy_breakdown'] = [dict(row) for row in cursor.fetchall()]
                else:
                    # Default values
                    stats.update({
                        'win_rate': 0,
                        'profit_factor': 0,
                        'sharpe_ratio': 0,
                        'strategy_breakdown': []
                    })
                
                return stats
                
        except Exception as e:
            logger.error(f"Error calculating performance stats: {e}")
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'total_profit': 0,
                'total_loss': 0,
                'net_profit': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'sharpe_ratio': 0,
                'strategy_breakdown': []
            }
    
    def log_system_event(self, event_type: str, message: str, severity: str = 'INFO',
                        component: str = None, details: str = None):
        """Log system event with detailed information"""
        try:
            with self.pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO system_events (timestamp, event_type, severity, component, message, details)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    datetime.now().isoformat(),
                    event_type,
                    severity,
                    component or 'SYSTEM',
                    message,
                    details
                ))
                
        except Exception as e:
            logger.error(f"Error logging system event: {e}")
    
    def save_market_conditions(self, conditions: Dict[str, Any]):
        """Save current market conditions"""
        try:
            with self.pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO market_conditions (
                        timestamp, btc_price, btc_dominance, total_market_cap,
                        fear_greed_index, volatility_index, cycle_phase,
                        dominance_phase, volatility_regime
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    conditions.get('timestamp', datetime.now().isoformat()),
                    conditions.get('btc_price'),
                    conditions.get('btc_dominance'),
                    conditions.get('total_market_cap'),
                    conditions.get('fear_greed_index'),
                    conditions.get('volatility_index'),
                    conditions.get('cycle_phase'),
                    conditions.get('dominance_phase'),
                    conditions.get('volatility_regime')
                ))
                
        except Exception as e:
            logger.error(f"Error saving market conditions: {e}")
    
    def cleanup_old_data(self, days_to_keep: int = 90):
        """Clean up old data to prevent database bloat"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).isoformat()
            
            with self.pool.get_connection() as conn:
                cursor = conn.cursor()
                
                # Clean up old trades
                cursor.execute(
                    "DELETE FROM trades WHERE timestamp < ?",
                    (cutoff_date,)
                )
                trades_deleted = cursor.rowcount
                
                # Clean up old system events
                cursor.execute(
                    "DELETE FROM system_events WHERE timestamp < ?",
                    (cutoff_date,)
                )
                events_deleted = cursor.rowcount
                
                # Clean up old market conditions
                cursor.execute(
                    "DELETE FROM market_conditions WHERE timestamp < ?",
                    (cutoff_date,)
                )
                conditions_deleted = cursor.rowcount
                
                # Vacuum database to reclaim space
                conn.execute("VACUUM")
                
                logger.info(f"Cleanup complete - Deleted: {trades_deleted} trades, "
                          f"{events_deleted} events, {conditions_deleted} market conditions")
                
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
    
    def close(self):
        """Close database connections"""
        self.pool.close_all()

# Enhanced Notification Manager
class EnhancedNotificationManager:
    """Notification manager with multiple channels and rate limiting"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config.get('notifications', {})
        self.email_config = self.config.get('email', {})
        self.email_enabled = self.email_config.get('enabled', False)
        self.alerts_config = self.config.get('alerts', {})
        
        # Rate limiting
        self.notification_history = deque(maxlen=100)
        self.rate_limit_window = 3600  # 1 hour
        self.max_notifications_per_window = 20
        
    def should_send_notification(self, notification_type: str) -> bool:
        """Check if notification should be sent based on rate limits"""
        now = time.time()
        
        # Remove old entries
        while self.notification_history and self.notification_history[0][0] < now - self.rate_limit_window:
            self.notification_history.popleft()
        
        # Check rate limit
        recent_count = sum(1 for t, n_type in self.notification_history if n_type == notification_type)
        
        if recent_count >= self.max_notifications_per_window:
            logger.warning(f"Rate limit exceeded for {notification_type} notifications")
            return False
        
        # Add to history
        self.notification_history.append((now, notification_type))
        return True
    
    def send_email(self, subject: str, body: str, priority: str = 'normal') -> bool:
        """Send email notification with error handling"""
        if not self.email_enabled:
            return False
            
        if not self.should_send_notification('email'):
            return False
            
        try:
            sender_email = self.email_config.get('sender')
            sender_password = os.getenv('EMAIL_PASSWORD')
            recipients = self.email_config.get('recipients', [])
            
            if not sender_email or not sender_password or not recipients:
                logger.error("Email configuration incomplete")
                return False
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = sender_email
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = f"[Trading Bot] {subject}"
            msg['X-Priority'] = '1' if priority == 'high' else '3'
            
            # Create HTML body
            html_body = f"""
            <html>
                <body style="font-family: Arial, sans-serif;">
                    <h2 style="color: #2e6da4;">{subject}</h2>
                    <pre style="background-color: #f4f4f4; padding: 10px; border-radius: 5px;">
{body}
                    </pre>
                    <hr>
                    <p style="color: #666; font-size: 12px;">
                        Sent by Enhanced Trading Bot at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                    </p>
                </body>
            </html>
            """
            
            # Attach parts
            msg.attach(MIMEText(body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))
            
            # Send email
            with smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port']) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(msg)
            
            logger.info(f"Email sent: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def notify_trade(self, trade: TradeRecord):
        """Send trade notification"""
        if trade.profit_loss is None:
            return
            
        # Check thresholds
        profit_threshold = self.alerts_config.get('profit_threshold', 100.0)
        loss_threshold = self.alerts_config.get('loss_threshold', 50.0)
        
        if abs(trade.profit_loss) < min(profit_threshold, loss_threshold):
            return
            
        subject = f"Trade Alert: {trade.symbol} {trade.side}"
        
        body = f"""
Trade Executed:
===============
Symbol: {trade.symbol}
Side: {trade.side}
Quantity: {trade.quantity:.6f}
Price: ${trade.price:.2f}
Strategy: {trade.strategy}
Confidence: {trade.confidence:.2%}

Results:
--------
P&L: ${trade.profit_loss:.2f} ({trade.profit_pct:.2f}%)
Reason: {trade.reason}

Market Conditions:
-----------------
Cycle Phase: {trade.cycle_phase}
Dominance Phase: {trade.dominance_phase}
Volatility Regime: {trade.volatility_regime}
"""
        
        priority = 'high' if abs(trade.profit_loss) > profit_threshold * 2 else 'normal'
        self.send_email(subject, body, priority)
    
    def notify_risk_alert(self, alert_type: str, details: Dict[str, Any]):
        """Send risk management alert"""
        subject = f"Risk Alert: {alert_type}"
        
        body = f"""
Risk Alert Triggered:
====================
Type: {alert_type}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Details:
--------
"""
        for key, value in details.items():
            body += f"{key}: {value}\n"
        
        self.send_email(subject, body, priority='high')
    
    def send_daily_report(self, performance: Dict[str, Any], market_conditions: Dict[str, Any]):
        """Send daily performance report"""
        subject = f"Daily Report - {datetime.now().strftime('%Y-%m-%d')}"
        
        net_pnl = performance.get('net_profit', 0)
        pnl_emoji = "🟢" if net_pnl >= 0 else "🔴"
        
        body = f"""
Daily Trading Report
===================

Performance Summary {pnl_emoji}
------------------
Total Trades: {performance.get('total_trades', 0)}
Winning Trades: {performance.get('winning_trades', 0)}
Win Rate: {performance.get('win_rate', 0):.1f}%
Net P&L: ${net_pnl:.2f}
Profit Factor: {performance.get('profit_factor', 0):.2f}
Sharpe Ratio: {performance.get('sharpe_ratio', 0):.2f}

Market Conditions
----------------
BTC Price: ${market_conditions.get('btc_price', 0):,.2f}
BTC Dominance: {market_conditions.get('btc_dominance', 0):.1f}%
Market Cap: ${market_conditions.get('total_market_cap', 0)/1e9:.1f}B
Fear & Greed: {market_conditions.get('fear_greed_index', 0)}
Cycle Phase: {market_conditions.get('cycle_phase', 'Unknown')}
Volatility: {market_conditions.get('volatility_regime', 'Unknown')}

Top Performing Strategies
------------------------
"""
        
        for strategy in performance.get('strategy_breakdown', [])[:5]:
            body += f"{strategy['strategy']}: {strategy['trades']} trades, ${strategy['total_pnl']:.2f}\n"
        
        self.send_email(subject, body)

# Enhanced API Call Manager with caching
class EnhancedAPICallManager:
    """API call manager with rate limiting and intelligent caching"""
    
    def __init__(self):
        # Rate limiting configuration
        self.request_limit_per_minute = 800  # Conservative limit
        self.order_limit_per_second = 8
        self.weight_limit_per_minute = 1000
        
        # Request tracking
        self.request_timestamps = deque(maxlen=self.request_limit_per_minute)
        self.order_timestamps = deque(maxlen=self.order_limit_per_second * 10)
        self.weight_usage = deque(maxlen=self.weight_limit_per_minute)
        
        # Enhanced caching
        self.cache = {}
        self.cache_ttl = {}
        self.cache_stats = defaultdict(lambda: {'hits': 0, 'misses': 0, 'lookups': 0})
        
        # Locks for thread safety
        self.request_lock = asyncio.Lock()
        self.order_lock = asyncio.Lock()
        self.cache_lock = threading.RLock()
        
    async def wait_for_request_slot(self, weight: int = 1):
        """Wait for available API request slot with weight consideration"""
        async with self.request_lock:
            now = time.time()
            
            # Clean old timestamps
            while self.request_timestamps and now - self.request_timestamps[0] > 60:
                self.request_timestamps.popleft()
            
            while self.weight_usage and now - self.weight_usage[0][0] > 60:
                self.weight_usage.popleft()
            
            # Calculate current weight usage
            current_weight = sum(w for t, w in self.weight_usage)
            
            # Wait if limits exceeded
            if len(self.request_timestamps) >= self.request_limit_per_minute - 10:  # Buffer
                wait_time = 61 - (now - self.request_timestamps[0])
                if wait_time > 0:
                    logger.warning(f"Rate limit approaching, waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
            
            if current_weight + weight > self.weight_limit_per_minute - 100:  # Buffer
                wait_time = 61 - (now - self.weight_usage[0][0])
                if wait_time > 0:
                    logger.warning(f"Weight limit approaching, waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
    
    async def wait_for_order_slot(self):
        """Wait for available order execution slot"""
        async with self.order_lock:
            now = time.time()
            
            # Clean old timestamps
            while self.order_timestamps and now - self.order_timestamps[0] > 1:
                self.order_timestamps.popleft()
            
            # Wait if limit exceeded
            if len(self.order_timestamps) >= self.order_limit_per_second:
                wait_time = 1.01 - (now - self.order_timestamps[0])
                if wait_time > 0:
                    logger.warning(f"Order rate limit hit, waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
    
    def record_request(self, endpoint: str, weight: int = 1):
        """Record API request with weight"""
        now = time.time()
        self.request_timestamps.append(now)
        self.weight_usage.append((now, weight))
        
        # Log API usage periodically
        if len(self.request_timestamps) % 100 == 0:
            logger.debug(f"API usage: {len(self.request_timestamps)}/min requests, "
                        f"{sum(w for t, w in self.weight_usage)}/min weight")
    
    def record_order(self):
        """Record order execution"""
        self.order_timestamps.append(time.time())
    
    def get_cached_response(self, cache_key: str) -> Optional[Any]:
        """Get cached response with statistics"""
        with self.cache_lock:
            self.cache_stats[cache_key]['lookups'] += 1
            
            if cache_key in self.cache:
                if time.time() < self.cache_ttl[cache_key]:
                    self.cache_stats[cache_key]['hits'] += 1
                    return self.cache[cache_key]
                else:
                    # Expired
                    del self.cache[cache_key]
                    del self.cache_ttl[cache_key]
            
            self.cache_stats[cache_key]['misses'] += 1
            return None
    
    def cache_response(self, cache_key: str, response: Any, ttl_seconds: int = 30):
        """Cache API response with TTL"""
        with self.cache_lock:
            self.cache[cache_key] = response
            self.cache_ttl[cache_key] = time.time() + ttl_seconds
            
            # Limit cache size
            if len(self.cache) > 1000:
                self._evict_expired_cache()
    
    def _evict_expired_cache(self):
        """Remove expired cache entries"""
        now = time.time()
        expired_keys = [k for k, ttl in self.cache_ttl.items() if ttl < now]
        
        for key in expired_keys:
            del self.cache[key]
            del self.cache_ttl[key]
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        with self.cache_lock:
            total_lookups = sum(stats['lookups'] for stats in self.cache_stats.values())
            total_hits = sum(stats['hits'] for stats in self.cache_stats.values())
            
            return {
                'cache_size': len(self.cache),
                'total_lookups': total_lookups,
                'total_hits': total_hits,
                'hit_rate': (total_hits / total_lookups * 100) if total_lookups > 0 else 0,
                'top_cached_keys': sorted(
                    self.cache_stats.items(),
                    key=lambda x: x[1]['hits'],
                    reverse=True
                )[:10]
            }

# Continue with the rest of the enhanced components...
# (Due to length limits, I'll continue in the next message)