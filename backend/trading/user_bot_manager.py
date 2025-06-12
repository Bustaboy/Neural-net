# backend/trading/user_bot_manager.py
import asyncio
from typing import Dict, Optional, List, Any
from uuid import UUID
from datetime import datetime, timedelta
import logging
from collections import defaultdict

from ..database.connection import DatabaseManager
from ..database.models.user import User, Portfolio, BotInstance, Trade, Position
from ..core.notification_service import NotificationService
from .enhanced_trading_bot import EnhancedTradingBot
from .config_manager import UserConfigManager

logger = logging.getLogger(__name__)

class UserBotManager:
    """Manages multiple trading bot instances for different users"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.notification_service = NotificationService()
        self.active_bots: Dict[UUID, EnhancedTradingBot] = {}
        self.bot_tasks: Dict[UUID, asyncio.Task] = {}
        self.bot_status: Dict[UUID, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        
    async def create_bot_instance(
        self,
        user_id: UUID,
        portfolio_id: UUID,
        name: str,
        strategy: str,
        config: Dict[str, Any]
    ) -> BotInstance:
        """Create a new bot instance for a user"""
        with self.db_manager.get_db() as db:
            # Check if user already has an active bot
            existing_bot = db.query(BotInstance).filter(
                BotInstance.user_id == user_id,
                BotInstance.status.in_(["running", "starting"])
            ).first()
            
            if existing_bot:
                raise ValueError("User already has an active bot")
            
            # Create new bot instance
            bot_instance = BotInstance(
                user_id=user_id,
                portfolio_id=portfolio_id,
                name=name,
                strategy=strategy,
                config=config,
                status="created",
                created_at=datetime.utcnow()
            )
            
            db.add(bot_instance)
            db.commit()
            db.refresh(bot_instance)
            
            return bot_instance
    
    async def start_bot(self, user_id: UUID, bot_instance_id: UUID) -> bool:
        """Start a bot instance for a user"""
        async with self._lock:
            try:
                with self.db_manager.get_db() as db:
                    # Get bot instance
                    bot_instance = db.query(BotInstance).filter(
                        BotInstance.id == bot_instance_id,
                        BotInstance.user_id == user_id
                    ).first()
                    
                    if not bot_instance:
                        raise ValueError("Bot instance not found")
                    
                    if bot_instance.status == "running":
                        return False  # Already running
                    
                    # Get user's API keys
                    portfolio = db.query(Portfolio).filter(
                        Portfolio.id == bot_instance.portfolio_id
                    ).first()
                    
                    if not portfolio:
                        raise ValueError("Portfolio not found")
                    
                    # Create config manager
                    config_manager = UserConfigManager(user_id)
                    user_config = await config_manager.get_user_config(bot_instance.config)
                    
                    # Create bot instance
                    bot = EnhancedTradingBot()
                    bot.user_id = user_id
                    bot.portfolio_id = bot_instance.portfolio_id
                    bot.bot_instance_id = bot_instance.id
                    
                    # Initialize bot with user config
                    await bot.initialize(user_config)
                    
                    # Update status
                    bot_instance.status = "starting"
                    bot_instance.started_at = datetime.utcnow()
                    db.commit()
                    
                    # Start bot in background
                    task = asyncio.create_task(
                        self._run_bot(user_id, bot_instance.id, bot)
                    )
                    
                    self.active_bots[user_id] = bot
                    self.bot_tasks[user_id] = task
                    self.bot_status[user_id] = {
                        "status": "running",
                        "started_at": datetime.utcnow(),
                        "errors": []
                    }
                    
                    # Send notification
                    await self.notification_service.send_notification(
                        user_id,
                        "bot_started",
                        {
                            "bot_name": bot_instance.name,
                            "strategy": bot_instance.strategy
                        }
                    )
                    
                    logger.info(f"Bot started for user {user_id}")
                    return True
                    
            except Exception as e:
                logger.error(f"Failed to start bot for user {user_id}: {e}")
                await self._update_bot_error(user_id, str(e))
                raise
    
    async def _run_bot(self, user_id: UUID, bot_instance_id: UUID, bot: EnhancedTradingBot):
        """Run bot with error handling and monitoring"""
        try:
            with self.db_manager.get_db() as db:
                bot_instance = db.query(BotInstance).filter(
                    BotInstance.id == bot_instance_id
                ).first()
                bot_instance.status = "running"
                db.commit()
            
            # Run the bot
            await bot.run_trading_loop()
            
        except asyncio.CancelledError:
            logger.info(f"Bot cancelled for user {user_id}")
            raise
        except Exception as e:
            logger.error(f"Bot error for user {user_id}: {e}")
            await self._update_bot_error(user_id, str(e))
            
            # Send error notification
            await self.notification_service.send_notification(
                user_id,
                "bot_error",
                {"error": str(e)}
            )
        finally:
            # Cleanup
            async with self._lock:
                self.active_bots.pop(user_id, None)
                self.bot_tasks.pop(user_id, None)
                self.bot_status.pop(user_id, None)
                
                # Update database status
                with self.db_manager.get_db() as db:
                    bot_instance = db.query(BotInstance).filter(
                        BotInstance.id == bot_instance_id
                    ).first()
                    if bot_instance:
                        bot_instance.status = "stopped"
                        bot_instance.stopped_at = datetime.utcnow()
                        db.commit()
    
    async def stop_user_bot(self, user_id: UUID) -> bool:
        """Stop a user's bot"""
        async with self._lock:
            task = self.bot_tasks.get(user_id)
            if not task:
                return False
            
            # Cancel the task
            task.cancel()
            
            # Wait for cleanup
            try:
                await task
            except asyncio.CancelledError:
                pass
            
            # Send notification
            await self.notification_service.send_notification(
                user_id,
                "bot_stopped",
                {"stopped_at": datetime.utcnow().isoformat()}
            )
            
            logger.info(f"Bot stopped for user {user_id}")
            return True
    
    async def stop_all_bots(self):
        """Stop all active bots (for shutdown)"""
        tasks = []
        for user_id in list(self.bot_tasks.keys()):
            tasks.append(self.stop_user_bot(user_id))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def get_user_bot(self, user_id: UUID) -> Optional[BotInstance]:
        """Get user's bot instance"""
        with self.db_manager.get_db() as db:
            return db.query(BotInstance).filter(
                BotInstance.user_id == user_id,
                BotInstance.status.in_(["running", "starting", "paused"])
            ).first()
    
    async def get_user_bot_status(self, user_id: UUID) -> Optional[BotInstance]:
        """Get detailed bot status"""
        with self.db_manager.get_db() as db:
            bot_instance = db.query(BotInstance).filter(
                BotInstance.user_id == user_id
            ).order_by(BotInstance.created_at.desc()).first()
            
            if bot_instance and user_id in self.active_bots:
                # Update real-time metrics
                bot = self.active_bots[user_id]
                bot_instance.last_activity_at = bot.last_activity
                
            return bot_instance
    
    async def update_bot_config(self, user_id: UUID, config: Dict[str, Any]) -> bool:
        """Update bot configuration"""
        with self.db_manager.get_db() as db:
            bot_instance = db.query(BotInstance).filter(
                BotInstance.user_id == user_id,
                BotInstance.status.in_(["running", "paused"])
            ).first()
            
            if not bot_instance:
                return False
            
            # Update config
            bot_instance.config = {**bot_instance.config, **config}
            db.commit()
            
            # Update running bot if exists
            if user_id in self.active_bots:
                bot = self.active_bots[user_id]
                await bot.update_config(config)
            
            return True
    
    async def validate_portfolio_ownership(
        self,
        user_id: UUID,
        portfolio_id: str
    ) -> Optional[Portfolio]:
        """Validate that user owns the portfolio"""
        with self.db_manager.get_db() as db:
            return db.query(Portfolio).filter(
                Portfolio.id == portfolio_id,
                Portfolio.user_id == user_id
            ).first()
    
    async def get_user_portfolio(self, user_id: UUID) -> Optional[Portfolio]:
        """Get user's active portfolio"""
        with self.db_manager.get_db() as db:
            return db.query(Portfolio).filter(
                Portfolio.user_id == user_id,
                Portfolio.is_active == True
            ).first()
    
    async def get_user_positions(self, user_id: UUID) -> List[Position]:
        """Get all open positions for a user"""
        with self.db_manager.get_db() as db:
            portfolios = db.query(Portfolio).filter(
                Portfolio.user_id == user_id
            ).all()
            
            portfolio_ids = [p.id for p in portfolios]
            
            return db.query(Position).filter(
                Position.portfolio_id.in_(portfolio_ids),
                Position.status == "open"
            ).all()
    
    async def get_user_position(
        self,
        user_id: UUID,
        position_id: str
    ) -> Optional[Position]:
        """Get specific position for a user"""
        with self.db_manager.get_db() as db:
            position = db.query(Position).filter(
                Position.id == position_id
            ).first()
            
            if position:
                # Verify ownership
                portfolio = db.query(Portfolio).filter(
                    Portfolio.id == position.portfolio_id,
                    Portfolio.user_id == user_id
                ).first()
                
                if portfolio:
                    return position
            
            return None
    
    async def save_trade(self, trade: Trade):
        """Save trade to database"""
        with self.db_manager.get_db() as db:
            db.add(trade)
            db.commit()
            
            # Update bot statistics
            bot_instance = db.query(BotInstance).filter(
                BotInstance.user_id == trade.user_id,
                BotInstance.status == "running"
            ).first()
            
            if bot_instance:
                bot_instance.total_trades += 1
                if trade.realized_pnl:
                    if trade.realized_pnl > 0:
                        bot_instance.winning_trades += 1
                    else:
                        bot_instance.losing_trades += 1
                    bot_instance.total_pnl += trade.realized_pnl
                bot_instance.last_activity_at = datetime.utcnow()
                db.commit()
    
    async def get_trade_history(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
        symbol: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Trade]:
        """Get trade history for a user"""
        with self.db_manager.get_db() as db:
            query = db.query(Trade).filter(Trade.user_id == user_id)
            
            if symbol:
                query = query.filter(Trade.symbol == symbol)
            if start_date:
                query = query.filter(Trade.executed_at >= start_date)
            if end_date:
                query = query.filter(Trade.executed_at <= end_date)
            
            return query.order_by(
                Trade.executed_at.desc()
            ).limit(limit).offset(offset).all()
    
    async def calculate_performance_metrics(
        self,
        user_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Calculate performance metrics for a user"""
        with self.db_manager.get_db() as db:
            # Get portfolios
            portfolios = db.query(Portfolio).filter(
                Portfolio.user_id == user_id
            ).all()
            
            # Aggregate metrics
            total_balance = sum(p.total_balance_usd for p in portfolios)
            total_pnl = sum(p.total_pnl for p in portfolios)
            
            # Get trades for period
            query = db.query(Trade).filter(Trade.user_id == user_id)
            if start_date:
                query = query.filter(Trade.executed_at >= start_date)
            if end_date:
                query = query.filter(Trade.executed_at <= end_date)
            
            trades = query.all()
            
            # Calculate metrics
            winning_trades = [t for t in trades if t.realized_pnl and t.realized_pnl > 0]
            losing_trades = [t for t in trades if t.realized_pnl and t.realized_pnl < 0]
            
            win_rate = (len(winning_trades) / len(trades) * 100) if trades else 0
            
            avg_win = (sum(t.realized_pnl for t in winning_trades) / len(winning_trades)) if winning_trades else 0
            avg_loss = (sum(abs(t.realized_pnl) for t in losing_trades) / len(losing_trades)) if losing_trades else 0
            
            profit_factor = (sum(t.realized_pnl for t in winning_trades) / 
                           sum(abs(t.realized_pnl) for t in losing_trades)) if losing_trades else 0
            
            # Calculate drawdown
            equity_curve = self._calculate_equity_curve(trades)
            max_drawdown = self._calculate_max_drawdown(equity_curve)
            
            return {
                "total_balance": total_balance,
                "total_pnl": total_pnl,
                "total_pnl_percentage": (total_pnl / total_balance * 100) if total_balance else 0,
                "total_trades": len(trades),
                "winning_trades": len(winning_trades),
                "losing_trades": len(losing_trades),
                "win_rate": win_rate,
                "average_win": avg_win,
                "average_loss": avg_loss,
                "profit_factor": profit_factor,
                "max_drawdown": max_drawdown,
                "sharpe_ratio": self._calculate_sharpe_ratio(trades),
                "daily_pnl": self._calculate_daily_pnl(trades),
                "best_trade": max((t.realized_pnl for t in trades if t.realized_pnl), default=0),
                "worst_trade": min((t.realized_pnl for t in trades if t.realized_pnl), default=0),
            }
    
    async def get_current_price(self, symbol: str) -> float:
        """Get current price for a symbol"""
        # This would connect to your price feed service
        # For now, returning a mock price
        return 50000.0  # Mock BTC price
    
    async def send_notification(
        self,
        user_id: UUID,
        event_type: str,
        data: Dict[str, Any]
    ):
        """Send notification to user"""
        await self.notification_service.send_notification(
            user_id,
            event_type,
            data
        )
    
    async def _update_bot_error(self, user_id: UUID, error_message: str):
        """Update bot error status"""
        with self.db_manager.get_db() as db:
            bot_instance = db.query(BotInstance).filter(
                BotInstance.user_id == user_id,
                BotInstance.status == "running"
            ).first()
            
            if bot_instance:
                bot_instance.status = "error"
                bot_instance.error_message = error_message
                bot_instance.stopped_at = datetime.utcnow()
                db.commit()
    
    def _calculate_equity_curve(self, trades: List[Trade]) -> List[float]:
        """Calculate equity curve from trades"""
        equity_curve = [0.0]
        current_equity = 0.0
        
        for trade in sorted(trades, key=lambda t: t.executed_at):
            if trade.realized_pnl:
                current_equity += trade.realized_pnl
                equity_curve.append(current_equity)
        
        return equity_curve
    
    def _calculate_max_drawdown(self, equity_curve: List[float]) -> float:
        """Calculate maximum drawdown"""
        if len(equity_curve) < 2:
            return 0.0
        
        peak = equity_curve[0]
        max_drawdown = 0.0
        
        for value in equity_curve[1:]:
            if value > peak:
                peak = value
            else:
                drawdown = (peak - value) / peak * 100 if peak > 0 else 0
                max_drawdown = max(max_drawdown, drawdown)
        
        return max_drawdown
    
    def _calculate_sharpe_ratio(
        self,
        trades: List[Trade],
        risk_free_rate: float = 0.02
    ) -> float:
        """Calculate Sharpe ratio"""
        if not trades:
            return 0.0
        
        returns = [t.realized_pnl_percentage for t in trades if t.realized_pnl_percentage]
        if len(returns) < 2:
            return 0.0
        
        import numpy as np
        returns_array = np.array(returns)
        
        avg_return = np.mean(returns_array)
        std_return = np.std(returns_array)
        
        if std_return == 0:
            return 0.0
        
        # Annualized Sharpe ratio (assuming daily returns)
        sharpe = (avg_return - risk_free_rate/252) / std_return * np.sqrt(252)
        return float(sharpe)
    
    def _calculate_daily_pnl(self, trades: List[Trade]) -> float:
        """Calculate today's P&L"""
        today = datetime.utcnow().date()
        daily_trades = [
            t for t in trades 
            if t.executed_at.date() == today and t.realized_pnl
        ]
        
        return sum(t.realized_pnl for t in daily_trades)
