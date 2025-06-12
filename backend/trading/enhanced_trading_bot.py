# backend/trading/enhanced_trading_bot.py
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from uuid import UUID
import pandas as pd
import numpy as np

from binance.client import AsyncClient
from binance.enums import *
from binance.exceptions import BinanceAPIException

from ..database.connection import DatabaseManager
from ..database.models.user import Portfolio, Position, Trade
from ..core.cache_manager import CacheManager
from .market_analyzer import MarketAnalyzer
from .ml_predictor import MLPredictor
from .risk_manager import RiskManager

logger = logging.getLogger(__name__)

class EnhancedTradingBot:
    """Multi-user enhanced trading bot with ML capabilities"""
    
    def __init__(self):
        # User-specific attributes
        self.user_id: Optional[UUID] = None
        self.portfolio_id: Optional[UUID] = None
        self.bot_instance_id: Optional[UUID] = None
        
        # Core components
        self.client: Optional[AsyncClient] = None
        self.db_manager = DatabaseManager()
        self.cache_manager = CacheManager()
        
        # Trading components
        self.market_analyzer: Optional[MarketAnalyzer] = None
        self.ml_predictor: Optional[MLPredictor] = None
        self.risk_manager: Optional[RiskManager] = None
        
        # Configuration
        self.config: Dict[str, Any] = {}
        self.symbols: List[str] = []
        self.is_running = False
        self.last_activity = datetime.utcnow()
        
        # Performance tracking
        self.session_trades = 0
        self.session_pnl = 0.0
        
    async def initialize(self, config: Dict[str, Any]):
        """Initialize bot with user-specific configuration"""
        self.config = config
        self.symbols = [s['symbol'] for s in config.get('trading', {}).get('symbols', [])]
        
        # Initialize Binance client
        api_key = config.get('api_key')
        api_secret = config.get('api_secret')
        testnet = config.get('testnet', True)
        
        if testnet:
            self.client = await AsyncClient.create(
                api_key=api_key,
                api_secret=api_secret,
                testnet=True
            )
        else:
            self.client = await AsyncClient.create(
                api_key=api_key,
                api_secret=api_secret
            )
        
        # Initialize components
        self.market_analyzer = MarketAnalyzer(self.client)
        self.ml_predictor = MLPredictor(
            user_id=self.user_id,
            model_path=f"models/user_{self.user_id}"
        )
        self.risk_manager = RiskManager(
            user_id=self.user_id,
            config=config.get('risk_management', {})
        )
        
        # Load ML models
        await self.ml_predictor.load_models()
        
        logger.info(f"Bot initialized for user {self.user_id}")
    
    async def run_trading_loop(self):
        """Main trading loop"""
        self.is_running = True
        error_count = 0
        max_errors = 5
        
        while self.is_running:
            try:
                # Update last activity
                self.last_activity = datetime.utcnow()
                
                # Check if trading is allowed
                if not await self._check_trading_conditions():
                    await asyncio.sleep(60)
                    continue
                
                # Analyze market for each symbol
                for symbol in self.symbols:
                    await self._process_symbol(symbol)
                
                # Update portfolio metrics
                await self._update_portfolio_metrics()
                
                # Reset error count on successful iteration
                error_count = 0
                
                # Sleep based on config
                sleep_time = self.config.get('loop_interval', 30)
                await asyncio.sleep(sleep_time)
                
            except asyncio.CancelledError:
                logger.info(f"Trading loop cancelled for user {self.user_id}")
                break
            except Exception as e:
                error_count += 1
                logger.error(f"Trading loop error for user {self.user_id}: {e}")
                
                if error_count >= max_errors:
                    logger.error(f"Max errors reached for user {self.user_id}, stopping bot")
                    self.is_running = False
                    break
                
                await asyncio.sleep(60)  # Wait before retry
        
        # Cleanup
        await self.cleanup()
    
    async def _process_symbol(self, symbol: str):
        """Process trading logic for a symbol"""
        try:
            # Get market data
            market_data = await self.market_analyzer.get_market_data(symbol)
            if not market_data:
                return
            
            # Check existing position
            position = await self._get_position(symbol)
            
            if position:
                # Manage existing position
                await self._manage_position(position, market_data)
            else:
                # Look for new opportunities
                await self._find_entry_opportunity(symbol, market_data)
                
        except Exception as e:
            logger.error(f"Error processing {symbol} for user {self.user_id}: {e}")
    
    async def _find_entry_opportunity(self, symbol: str, market_data: Dict[str, Any]):
        """Find entry opportunities using ML and technical analysis"""
        # Get ML prediction
        features = self._prepare_features(market_data)
        prediction = await self.ml_predictor.predict(symbol, features)
        
        if not prediction or prediction['confidence'] < self.config.get('min_confidence', 0.7):
            return
        
        # Check risk limits
        if not await self.risk_manager.can_open_position(self.portfolio_id):
            logger.info(f"Risk limits reached for user {self.user_id}")
            return
        
        # Calculate position size
        position_size = await self.risk_manager.calculate_position_size(
            self.portfolio_id,
            symbol,
            market_data['price']
        )
        
        if position_size <= 0:
            return
        
        # Place order
        side = 'BUY' if prediction['direction'] == 'up' else 'SELL'
        order = await self._place_order(
            symbol=symbol,
            side=side,
            quantity=position_size,
            price=market_data['price']
        )
        
        if order:
            # Create position record
            await self._create_position(
                symbol=symbol,
                side='long' if side == 'BUY' else 'short',
                quantity=position_size,
                entry_price=order['price'],
                stop_loss=prediction.get('stop_loss'),
                take_profit=prediction.get('take_profit')
            )
            
            logger.info(f"Opened {side} position for {symbol} - User: {self.user_id}")
    
    async def _manage_position(self, position: Position, market_data: Dict[str, Any]):
        """Manage existing position"""
        current_price = market_data['price']
        
        # Calculate P&L
        if position.side == 'long':
            pnl = (current_price - position.entry_price) * position.quantity
            pnl_pct = ((current_price - position.entry_price) / position.entry_price) * 100
        else:
            pnl = (position.entry_price - current_price) * position.quantity
            pnl_pct = ((position.entry_price - current_price) / position.entry_price) * 100
        
        # Check stop loss
        if position.stop_loss and (
            (position.side == 'long' and current_price <= position.stop_loss) or
            (position.side == 'short' and current_price >= position.stop_loss)
        ):
            await self._close_position(position, current_price, "Stop loss hit")
            return
        
        # Check take profit
        if position.take_profit and (
            (position.side == 'long' and current_price >= position.take_profit) or
            (position.side == 'short' and current_price <= position.take_profit)
        ):
            await self._close_position(position, current_price, "Take profit hit")
            return
        
        # Dynamic exit based on ML
        exit_signal = await self.ml_predictor.should_exit(
            position.symbol,
            position.side,
            pnl_pct,
            market_data
        )
        
        if exit_signal:
            await self._close_position(position, current_price, "ML exit signal")
            return
        
        # Update trailing stop if profitable
        if pnl_pct > 2.0:  # 2% profit
            await self._update_trailing_stop(position, current_price)
    
    async def _place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        order_type: str = 'MARKET'
    ) -> Optional[Dict[str, Any]]:
        """Place order on exchange"""
        try:
            if order_type == 'MARKET':
                if side == 'BUY':
                    order = await self.client.order_market_buy(
                        symbol=symbol,
                        quantity=quantity
                    )
                else:
                    order = await self.client.order_market_sell(
                        symbol=symbol,
                        quantity=quantity
                    )
            else:
                order = await self.client.create_order(
                    symbol=symbol,
                    side=side,
                    type=order_type,
                    quantity=quantity,
                    price=price,
                    timeInForce='GTC'
                )
            
            # Log trade
            await self._log_trade(order)
            
            return order
            
        except BinanceAPIException as e:
            logger.error(f"Order placement failed for user {self.user_id}: {e}")
            return None
    
    async def _close_position(self, position: Position, current_price: float, reason: str):
        """Close an existing position"""
        try:
            # Place closing order
            side = 'SELL' if position.side == 'long' else 'BUY'
            order = await self._place_order(
                symbol=position.symbol,
                side=side,
                quantity=position.quantity,
                price=current_price
            )
            
            if order:
                # Calculate final P&L
                if position.side == 'long':
                    pnl = (current_price - position.entry_price) * position.quantity
                else:
                    pnl = (position.entry_price - current_price) * position.quantity
                
                # Update position status
                with self.db_manager.get_db() as db:
                    db_position = db.query(Position).filter(
                        Position.id == position.id
                    ).first()
                    
                    db_position.status = 'closed'
                    db_position.closed_at = datetime.utcnow()
                    db_position.exit_price = current_price
                    db_position.realized_pnl = pnl
                    db_position.exit_reason = reason
                    
                    db.commit()
                
                # Update session metrics
                self.session_trades += 1
                self.session_pnl += pnl
                
                logger.info(
                    f"Closed {position.side} position for {position.symbol} "
                    f"- P&L: ${pnl:.2f} - Reason: {reason} - User: {self.user_id}"
                )
                
        except Exception as e:
            logger.error(f"Failed to close position for user {self.user_id}: {e}")
    
    async def _check_trading_conditions(self) -> bool:
        """Check if trading conditions are met"""
        # Check market hours
        if not self._is_market_open():
            return False
        
        # Check daily loss limit
        if await self.risk_manager.daily_loss_limit_reached(self.portfolio_id):
            logger.warning(f"Daily loss limit reached for user {self.user_id}")
            return False
        
        # Check consecutive losses
        if await self.risk_manager.max_consecutive_losses_reached(self.portfolio_id):
            logger.warning(f"Max consecutive losses reached for user {self.user_id}")
            return False
        
        return True
    
    async def update_config(self, new_config: Dict[str, Any]):
        """Update bot configuration dynamically"""
        self.config.update(new_config)
        
        # Update components
        if self.risk_manager:
            self.risk_manager.update_config(
                new_config.get('risk_management', {})
            )
        
        logger.info(f"Configuration updated for user {self.user_id}")
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.client:
            await self.client.close_connection()
        
        logger.info(f"Bot cleaned up for user {self.user_id}")
