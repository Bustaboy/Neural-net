# integrated_automl_trading_bot.py
# Complete integration of AutoML with trading bot

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import logging
import json
import asyncio
import websocket
from typing import Dict, List, Tuple, Optional
import ccxt  # For crypto exchange integration
from enhanced_trading_bot_complete import TradingBot, EnhancedMLPredictor
from advanced_hyperparameter_optimization import AdvancedHyperparameterOptimizer, AutoMLTradingBot

logging.basicConfig(level=logging.INFO)

class IntegratedAutoMLTradingSystem:
    """
    Complete trading system with AutoML, live trading, and risk management.
    """
    
    def __init__(self, exchange_name='binance', config_file='trading_config.json'):
        self.exchange_name = exchange_name
        self.config = self.load_config(config_file)
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.ml_predictor = EnhancedMLPredictor()
        self.optimizer = AdvancedHyperparameterOptimizer(
            n_trials=self.config.get('optimization_trials', 100)
        )
        self.automl_bot = AutoMLTradingBot(self.optimizer)
        self.trading_bot = TradingBot(self.ml_predictor, use_auto_optimization=True)
        
        # Trading state
        self.active_models = {}
        self.performance_tracker = {}
        self.last_optimization = {}
        
        # Risk management
        self.max_position_size = self.config.get('max_position_size', 0.1)
        self.stop_loss_pct = self.config.get('stop_loss_pct', 0.02)
        self.take_profit_pct = self.config.get('take_profit_pct', 0.05)
        
        # Initialize exchange
        self.exchange = self.init_exchange()
        
    def load_config(self, config_file):
        """Load configuration from file."""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except:
            # Default configuration
            return {
                'symbols': ['BTC/USDT', 'ETH/USDT'],
                'optimization_trials': 100,
                'reoptimize_days': 7,
                'min_confidence': 0.65,
                'max_position_size': 0.1,
                'stop_loss_pct': 0.02,
                'take_profit_pct': 0.05,
                'update_interval': 300  # 5 minutes
            }
    
    def init_exchange(self):
        """Initialize exchange connection."""
        try:
            exchange_class = getattr(ccxt, self.exchange_name)
            exchange = exchange_class({
                'apiKey': self.config.get('api_key'),
                'secret': self.config.get('api_secret'),
                'enableRateLimit': True,
                'options': {'defaultType': 'spot'}
            })
            return exchange
        except:
            self.logger.warning("Exchange initialization failed. Using simulation mode.")
            return None
    
    async def fetch_historical_data(self, symbol, timeframe='1h', limit=1000):
        """
        Fetch historical OHLCV data from exchange.
        
        Args:
            symbol: Trading pair
            timeframe: Candle timeframe
            limit: Number of candles to fetch
            
        Returns:
            DataFrame with OHLCV data
        """
        if self.exchange:
            try:
                ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                return df
            except Exception as e:
                self.logger.error(f"Error fetching data: {e}")
                
        # Fallback to simulated data
        return self.generate_simulated_data(symbol, limit)
    
    def generate_simulated_data(self, symbol, days=1000):
        """Generate simulated market data for testing."""
        dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
        price = 100 * (1 + np.random.randn(days).cumsum() * 0.02)
        
        df = pd.DataFrame({
            'timestamp': dates,
            'open': price * (1 + np.random.uniform(-0.01, 0.01, days)),
            'high': price * (1 + np.random.uniform(0, 0.02, days)),
            'low': price * (1 - np.random.uniform(0, 0.02, days)),
            'close': price,
            'volume': np.random.uniform(1000, 5000, days) * 1000
        })
        return df
    
    async def optimize_and_train(self, symbol):
        """
        Run full optimization and training pipeline for a symbol.
        
        Args:
            symbol: Trading pair to optimize
        """
        self.logger.info(f"Starting optimization for {symbol}")
        
        # Fetch historical data
        df = await self.fetch_historical_data(symbol)
        
        # Convert to format expected by trading bot
        historical_data = df.to_dict('records')
        
        # Prepare features and labels
        X, y = self.trading_bot.prepare_training_data(historical_data)
        
        if len(X) < 100:
            self.logger.warning(f"Insufficient data for {symbol}. Skipping optimization.")
            return
        
        # Split data for training and validation
        split_idx = int(len(X) * 0.8)
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        
        # Run AutoML optimization
        training_results = self.automl_bot.auto_train(
            X_train, y_train,
            optimize_models=['xgboost', 'lightgbm', 'random_forest'],
            use_ensemble=True
        )
        
        # Evaluate on validation set
        predictions, confidence = self.automl_bot.predict_with_confidence(X_val)
        
        # Calculate performance metrics
        from sklearn.metrics import accuracy_score, precision_score, recall_score
        
        metrics = {
            'accuracy': accuracy_score(y_val, predictions),
            'precision': precision_score(y_val, predictions, zero_division=0),
            'recall': recall_score(y_val, predictions, zero_division=0),
            'avg_confidence': np.mean(confidence)
        }
        
        # Store results
        self.active_models[symbol] = {
            'model': self.automl_bot,
            'metrics': metrics,
            'last_updated': datetime.now(),
            'training_results': training_results
        }
        
        self.last_optimization[symbol] = datetime.now()
        
        self.logger.info(f"Optimization complete for {symbol}. Metrics: {metrics}")
        
        # Save model
        self.save_model(symbol)
        
    def save_model(self, symbol):
        """Save trained model to disk."""
        filepath = f"models/{symbol.replace('/', '_')}_model_{datetime.now().strftime('%Y%m%d')}.pkl"
        
        # Save using joblib
        import joblib
        joblib.dump(self.active_models[symbol], filepath)
        
        self.logger.info(f"Model saved for {symbol}: {filepath}")
    
    async def generate_signals(self, symbol):
        """
        Generate trading signals for a symbol.
        
        Args:
            symbol: Trading pair
            
        Returns:
            Dict with signal information
        """
        if symbol not in self.active_models:
            await self.optimize_and_train(symbol)
            
        if symbol not in self.active_models:
            return None
            
        # Fetch current market data
        df = await self.fetch_historical_data(symbol, limit=100)
        
        # Prepare current features
        market_data = {
            'klines': df['close'].tolist(),
            'volume': df['volume'].tolist(),
            'depth': {
                'bid': df['close'].iloc[-1] * 0.999,
                'ask': df['close'].iloc[-1] * 1.001,
                'bid_volume': df['volume'].iloc[-1] * 0.4,
                'ask_volume': df['volume'].iloc[-1] * 0.6
            }
        }
        
        # Get market analysis
        analysis = self.trading_bot.analyze_market(symbol, market_data)
        
        # Get prediction from AutoML model
        features = analysis['features'].reshape(1, -1)
        prediction, confidence = self.active_models[symbol]['model'].predict_with_confidence(features)
        
        signal = {
            'symbol': symbol,
            'signal': 'BUY' if prediction[0] == 1 else 'SELL',
            'confidence': float(confidence[0]),
            'market_phase': analysis['market_phase'],
            'sentiment': analysis['sentiment'],
            'timestamp': datetime.now(),
            'current_price': float(df['close'].iloc[-1])
        }
        
        return signal
    
    async def execute_signal(self, signal):
        """
        Execute trading signal with risk management.
        
        Args:
            signal: Signal dictionary
        """
        symbol = signal['symbol']
        confidence = signal['confidence']
        
        # Check confidence threshold
        if confidence < self.config.get('min_confidence', 0.65):
            self.logger.info(f"Skipping {symbol} signal due to low confidence: {confidence:.2%}")
            return
            
        # Calculate position size
        position_size = self.calculate_position_size(signal)
        
        # Check existing positions
        if symbol in self.trading_bot.positions:
            current_position = self.trading_bot.positions[symbol]
            
            # Check stop loss / take profit
            current_price = signal['current_price']
            entry_price = current_position['entry_price']
            pnl_pct = (current_price - entry_price) / entry_price
            
            if pnl_pct <= -self.stop_loss_pct:
                self.logger.warning(f"Stop loss triggered for {symbol}")
                await self.close_position(symbol, 'STOP_LOSS')
            elif pnl_pct >= self.take_profit_pct:
                self.logger.info(f"Take profit triggered for {symbol}")
                await self.close_position(symbol, 'TAKE_PROFIT')
            elif signal['signal'] == 'SELL':
                await self.close_position(symbol, 'SIGNAL')
        else:
            # Open new position if signal is BUY
            if signal['signal'] == 'BUY':
                await self.open_position(symbol, position_size, signal)
    
    def calculate_position_size(self, signal):
        """
        Calculate position size based on Kelly Criterion and risk management.
        
        Args:
            signal: Trading signal
            
        Returns:
            Position size as fraction of portfolio
        """
        confidence = signal['confidence']
        symbol = signal['symbol']
        
        # Get model performance metrics
        if symbol in self.active_models:
            metrics = self.active_models[symbol]['metrics']
            win_rate = metrics.get('precision', 0.5)
        else:
            win_rate = 0.5
            
        # Kelly Criterion: f = (p*b - q) / b
        # where p = win probability, q = loss probability, b = win/loss ratio
        p = win_rate
        q = 1 - p
        b = self.take_profit_pct / self.stop_loss_pct  # Win/loss ratio
        
        kelly_fraction = (p * b - q) / b if b > 0 else 0
        
        # Apply confidence scaling and safety factor
        position_size = kelly_fraction * confidence * 0.25  # 25% of Kelly for safety
        
        # Cap at maximum position size
        position_size = min(position_size, self.max_position_size)
        
        return max(0, position_size)
    
    async def open_position(self, symbol, size, signal):
        """Open a new position."""
        if self.exchange:
            try:
                # Place market buy order
                order = self.exchange.create_market_buy_order(
                    symbol,
                    self.trading_bot.balance * size / signal['current_price']
                )
                
                self.logger.info(f"Opened position: {order}")
            except Exception as e:
                self.logger.error(f"Error opening position: {e}")
        
        # Update internal state
        self.trading_bot.execute_trade(
            symbol, 
            signal['signal'], 
            signal['confidence'], 
            self.trading_bot.balance * size
        )
        
        # Track performance
        self.performance_tracker[symbol] = {
            'entry_signal': signal,
            'entry_time': datetime.now(),
            'position_size': size
        }
    
    async def close_position(self, symbol, reason):
        """Close an existing position."""
        if symbol not in self.trading_bot.positions:
            return
            
        position = self.trading_bot.positions[symbol]
        
        if self.exchange:
            try:
                # Place market sell order
                order = self.exchange.create_market_sell_order(
                    symbol,
                    position['amount'] / position['entry_price']
                )
                
                self.logger.info(f"Closed position: {order}, reason: {reason}")
            except Exception as e:
                self.logger.error(f"Error closing position: {e}")
        
        # Update performance tracking
        if symbol in self.performance_tracker:
            entry_data = self.performance_tracker[symbol]
            exit_price = await self.get_current_price(symbol)
            
            pnl = (exit_price - position['entry_price']) / position['entry_price']
            
            # Log trade for analysis
            self.log_trade({
                'symbol': symbol,
                'entry': entry_data,
                'exit_time': datetime.now(),
                'exit_price': exit_price,
                'exit_reason': reason,
                'pnl': pnl
            })
        
        # Execute internal close
        self.trading_bot.execute_trade(symbol, 'SELL', 1.0)
    
    async def get_current_price(self, symbol):
        """Get current price for a symbol."""
        if self.exchange:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker['last']
        else:
            # Simulated price
            return 100 * (1 + np.random.uniform(-0.01, 0.01))
    
    def log_trade(self, trade_data):
        """Log completed trade for analysis."""
        with open('trade_log.json', 'a') as f:
            f.write(json.dumps(trade_data, default=str) + '\n')
    
    async def check_reoptimization(self):
        """Check if any models need reoptimization."""
        reoptimize_days = self.config.get('reoptimize_days', 7)
        
        for symbol in self.config['symbols']:
            last_opt = self.last_optimization.get(symbol)
            
            if not last_opt or (datetime.now() - last_opt).days >= reoptimize_days:
                self.logger.info(f"Reoptimizing {symbol}")
                await self.optimize_and_train(symbol)
    
    async def run_trading_loop(self):
        """Main trading loop."""
        self.logger.info("Starting automated trading system...")
        
        # Initial optimization
        for symbol in self.config['symbols']:
            await self.optimize_and_train(symbol)
        
        # Trading loop
        while True:
            try:
                # Check for reoptimization
                await self.check_reoptimization()
                
                # Generate and execute signals
                for symbol in self.config['symbols']:
                    signal = await self.generate_signals(symbol)
                    
                    if signal:
                        self.logger.info(f"Signal generated: {signal}")
                        await self.execute_signal(signal)
                
                # Wait for next update
                await asyncio.sleep(self.config.get('update_interval', 300))
                
            except Exception as e:
                self.logger.error(f"Error in trading loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    def generate_performance_report(self):
        """Generate comprehensive performance report."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'balance': self.trading_bot.balance,
            'positions': self.trading_bot.positions,
            'models': {}
        }
        
        # Model performance
        for symbol, model_data in self.active_models.items():
            report['models'][symbol] = {
                'metrics': model_data['metrics'],
                'last_updated': model_data['last_updated'].isoformat(),
                'optimization_results': {
                    k: v['best_value'] 
                    for k, v in model_data['training_results']['optimization_results'].items()
                }
            }
        
        # Trade statistics
        trades = []
        with open('trade_log.json', 'r') as f:
            for line in f:
                trades.append(json.loads(line))
        
        if trades:
            pnls = [t['pnl'] for t in trades]
            report['trade_statistics'] = {
                'total_trades': len(trades),
                'win_rate': sum(1 for p in pnls if p > 0) / len(pnls),
                'avg_pnl': np.mean(pnls),
                'sharpe_ratio': np.mean(pnls) / (np.std(pnls) + 1e-8) * np.sqrt(252),
                'max_drawdown': min(pnls),
                'total_return': sum(pnls)
            }
        
        return report


# Configuration file example
def create_default_config():
    """Create default configuration file."""
    config = {
        "exchange": "binance",
        "symbols": ["BTC/USDT", "ETH/USDT", "BNB/USDT"],
        "optimization_trials": 100,
        "reoptimize_days": 7,
        "min_confidence": 0.65,
        "max_position_size": 0.1,
        "stop_loss_pct": 0.02,
        "take_profit_pct": 0.05,
        "update_interval": 300,
        "api_key": "your_api_key_here",
        "api_secret": "your_api_secret_here"
    }
    
    with open('trading_config.json', 'w') as f:
        json.dump(config, f, indent=4)
    
    print("Default configuration created: trading_config.json")


# Main execution
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--create-config':
        create_default_config()
        sys.exit(0)
    
    # Create and run trading system
    trading_system = IntegratedAutoMLTradingSystem()
    
    # Run in async event loop
    try:
        asyncio.run(trading_system.run_trading_loop())
    except KeyboardInterrupt:
        # Generate final report
        report = trading_system.generate_performance_report()
        
        with open(f'performance_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
            json.dump(report, f, indent=4)
        
        print("\nTrading stopped. Performance report saved.")
