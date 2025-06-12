# backend/api/routes/trading_routes.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import uuid

from ..auth.jwt_handler import get_current_user
from ..auth.permissions import PermissionChecker, Permission
from ...database.models.user import User, Trade, Position, BotInstance
from ...trading.user_bot_manager import UserBotManager
from ...trading.strategy_executor import StrategyExecutor
from ...core.cache_manager import CacheManager

router = APIRouter()
permission_checker = PermissionChecker()
bot_manager = UserBotManager()
cache_manager = CacheManager()

# Request/Response models
class BotConfigRequest(BaseModel):
    name: str
    strategy: str = "enhanced_ml"
    config: Dict[str, Any]
    portfolio_id: str

class BotStatusResponse(BaseModel):
    bot_id: str
    status: str
    started_at: Optional[datetime]
    last_activity: Optional[datetime]
    total_trades: int
    active_positions: int
    total_pnl: float
    error_message: Optional[str]

class OrderRequest(BaseModel):
    symbol: str
    side: str  # buy/sell
    order_type: str = "market"  # market/limit
    quantity: float
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

class PositionResponse(BaseModel):
    id: str
    symbol: str
    side: str
    quantity: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_percentage: float
    opened_at: datetime
    stop_loss: Optional[float]
    take_profit: Optional[float]

# Bot Management Endpoints
@router.post("/bot/start", response_model=BotStatusResponse)
@permission_checker.require_permission(Permission.START_BOT)
async def start_bot(
    config: BotConfigRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Start trading bot for user"""
    try:
        # Check if bot already running
        existing_bot = await bot_manager.get_user_bot(current_user.id)
        if existing_bot and existing_bot.status == "running":
            raise HTTPException(
                status_code=400,
                detail="Bot is already running. Stop it first."
            )
        
        # Validate portfolio ownership
        portfolio = await bot_manager.validate_portfolio_ownership(
            current_user.id,
            config.portfolio_id
        )
        if not portfolio:
            raise HTTPException(
                status_code=403,
                detail="Portfolio not found or access denied"
            )
        
        # Create bot instance
        bot_instance = await bot_manager.create_bot_instance(
            user_id=current_user.id,
            portfolio_id=config.portfolio_id,
            name=config.name,
            strategy=config.strategy,
            config=config.config
        )
        
        # Start bot in background
        background_tasks.add_task(
            bot_manager.start_bot,
            current_user.id,
            bot_instance.id
        )
        
        return BotStatusResponse(
            bot_id=str(bot_instance.id),
            status="starting",
            started_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
            total_trades=0,
            active_positions=0,
            total_pnl=0.0,
            error_message=None
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/bot/stop")
@permission_checker.require_permission(Permission.STOP_BOT)
async def stop_bot(current_user: User = Depends(get_current_user)):
    """Stop trading bot for user"""
    try:
        success = await bot_manager.stop_user_bot(current_user.id)
        if not success:
            raise HTTPException(
                status_code=404,
                detail="No active bot found"
            )
        
        return {"message": "Bot stopped successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/bot/status", response_model=BotStatusResponse)
@permission_checker.require_permission(Permission.VIEW_BOT_STATUS)
async def get_bot_status(current_user: User = Depends(get_current_user)):
    """Get bot status for user"""
    bot_instance = await bot_manager.get_user_bot_status(current_user.id)
    
    if not bot_instance:
        raise HTTPException(
            status_code=404,
            detail="No bot instance found"
        )
    
    return BotStatusResponse(
        bot_id=str(bot_instance.id),
        status=bot_instance.status,
        started_at=bot_instance.started_at,
        last_activity=bot_instance.last_activity_at,
        total_trades=bot_instance.total_trades,
        active_positions=len(bot_instance.portfolio.positions),
        total_pnl=bot_instance.total_pnl,
        error_message=bot_instance.error_message
    )

@router.put("/bot/config")
@permission_checker.require_permission(Permission.CONFIGURE_BOT)
async def update_bot_config(
    config: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Update bot configuration"""
    try:
        success = await bot_manager.update_bot_config(current_user.id, config)
        if not success:
            raise HTTPException(
                status_code=404,
                detail="No bot instance found"
            )
        
        # Clear cache for this user
        await cache_manager.delete(f"bot_config:{current_user.id}")
        
        return {"message": "Configuration updated successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Trading Operations
@router.post("/orders")
@permission_checker.require_permission(Permission.CREATE_ORDER)
async def place_order(
    order: OrderRequest,
    current_user: User = Depends(get_current_user)
):
    """Place a manual order"""
    try:
        # Get user's active portfolio
        portfolio = await bot_manager.get_user_portfolio(current_user.id)
        if not portfolio:
            raise HTTPException(
                status_code=404,
                detail="No active portfolio found"
            )
        
        # Execute order
        strategy_executor = StrategyExecutor(portfolio.id)
        order_result = await strategy_executor.place_order(
            symbol=order.symbol,
            side=order.side,
            order_type=order.order_type,
            quantity=order.quantity,
            price=order.price,
            stop_loss=order.stop_loss,
            take_profit=order.take_profit
        )
        
        # Log trade
        trade = Trade(
            user_id=current_user.id,
            portfolio_id=portfolio.id,
            order_id=order_result['order_id'],
            symbol=order.symbol,
            side=order.side,
            order_type=order.order_type,
            quantity=order.quantity,
            price=order_result['price'],
            total_value=order_result['total_value'],
            fee=order_result['fee'],
            fee_currency=order_result['fee_currency'],
            status=order_result['status'],
            executed_at=datetime.utcnow()
        )
        
        await bot_manager.save_trade(trade)
        
        # Send WebSocket notification
        await bot_manager.send_notification(
            current_user.id,
            "order_placed",
            order_result
        )
        
        return order_result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/orders/{order_id}")
@permission_checker.require_permission(Permission.CANCEL_ORDER)
async def cancel_order(
    order_id: str,
    current_user: User = Depends(get_current_user)
):
    """Cancel an open order"""
    try:
        # Verify order ownership
        order = await bot_manager.get_user_order(current_user.id, order_id)
        if not order:
            raise HTTPException(
                status_code=404,
                detail="Order not found"
            )
        
        # Cancel order
        strategy_executor = StrategyExecutor(order.portfolio_id)
        result = await strategy_executor.cancel_order(order_id)
        
        # Update order status
        await bot_manager.update_order_status(order_id, "cancelled")
        
        return {"message": "Order cancelled successfully", "result": result}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/positions", response_model=List[PositionResponse])
@permission_checker.require_permission(Permission.VIEW_ORDERS)
async def get_positions(current_user: User = Depends(get_current_user)):
    """Get all open positions"""
    # Try to get from cache first
    cache_key = f"positions:{current_user.id}"
    cached_positions = await cache_manager.get(cache_key)
    
    if cached_positions:
        return cached_positions
    
    # Get from database
    positions = await bot_manager.get_user_positions(current_user.id)
    
    position_responses = []
    for position in positions:
        # Get current price
        current_price = await bot_manager.get_current_price(position.symbol)
        
        # Calculate P&L
        if position.side == "long":
            pnl = (current_price - position.entry_price) * position.quantity
            pnl_percentage = ((current_price - position.entry_price) / position.entry_price) * 100
        else:
            pnl = (position.entry_price - current_price) * position.quantity
            pnl_percentage = ((position.entry_price - current_price) / position.entry_price) * 100
        
        position_responses.append(PositionResponse(
            id=str(position.id),
            symbol=position.symbol,
            side=position.side,
            quantity=position.quantity,
            entry_price=position.entry_price,
            current_price=current_price,
            unrealized_pnl=pnl,
            unrealized_pnl_percentage=pnl_percentage,
            opened_at=position.opened_at,
            stop_loss=position.stop_loss,
            take_profit=position.take_profit
        ))
    
    # Cache for 30 seconds
    await cache_manager.set(cache_key, position_responses, 30)
    
    return position_responses

@router.get("/trades")
@permission_checker.require_permission(Permission.VIEW_ORDERS)
async def get_trade_history(
    limit: int = 50,
    offset: int = 0,
    symbol: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user)
):
    """Get trade history"""
    filters = {
        "user_id": current_user.id,
        "limit": limit,
        "offset": offset
    }
    
    if symbol:
        filters["symbol"] = symbol
    if start_date:
        filters["start_date"] = start_date
    if end_date:
        filters["end_date"] = end_date
    
    trades = await bot_manager.get_trade_history(**filters)
    
    return {
        "trades": trades,
        "total": len(trades),
        "limit": limit,
        "offset": offset
    }

@router.post("/positions/{position_id}/close")
@permission_checker.require_permission(Permission.CREATE_ORDER)
async def close_position(
    position_id: str,
    current_user: User = Depends(get_current_user)
):
    """Close an open position"""
    try:
        # Verify position ownership
        position = await bot_manager.get_user_position(current_user.id, position_id)
        if not position:
            raise HTTPException(
                status_code=404,
                detail="Position not found"
            )
        
        # Close position
        strategy_executor = StrategyExecutor(position.portfolio_id)
        result = await strategy_executor.close_position(position)
        
        # Update position status
        await bot_manager.update_position_status(position_id, "closed")
        
        # Send notification
        await bot_manager.send_notification(
            current_user.id,
            "position_closed",
            result
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance")
async def get_performance_metrics(
    timeframe: str = "1d",  # 1d, 7d, 30d, all
    current_user: User = Depends(get_current_user)
):
    """Get trading performance metrics"""
    # Calculate date range
    end_date = datetime.utcnow()
    if timeframe == "1d":
        start_date = end_date - timedelta(days=1)
    elif timeframe == "7d":
        start_date = end_date - timedelta(days=7)
    elif timeframe == "30d":
        start_date = end_date - timedelta(days=30)
    else:
        start_date = None
    
    metrics = await bot_manager.calculate_performance_metrics(
        current_user.id,
        start_date,
        end_date
    )
    
    return metrics
