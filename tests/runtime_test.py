# tests/runtime_test.py
import pytest
import asyncio
from ml.ensemble import EnsembleModel
from backend.trading.enhanced_trading_bot import EnhancedTradingBot
from core.database import EnhancedDatabaseManager
from utils.notifications import NotificationManager
import logging

logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_runtime_components():
    """Test critical runtime components."""
    try:
        # Test database
        db_manager = EnhancedDatabaseManager()
        assert db_manager.test_connection(), "Database connection failed"

        # Test model initialization
        model = EnsembleModel("models/test_model.pkl")
        model.run_diagnostics()

        # Test bot initialization
        bot = EnhancedTradingBot(
            user_id=1,
            config={"exchange_api_key": "test_key", "exchange_secret": "test_secret"},
            position_manager=PositionManager(db_manager)
        )
        market_data = {
            "symbol": "BTC/USDT",
            "prices": {"BTC/USDT": 50000.0, "ETH/USDT": 3000.0, "MATIC/USDT": 1.0, "AVAX/USDT": 50.0},
            "volatility": 0.03,
            "sentiment": 0.9,
            "defi_apy": 0.8,
            "portfolio_weights": [0.25] * 4
        }
        await bot.model.fetch_server_model()

        # Test notifications
        notifier = NotificationManager()
        await notifier.send_notification(1, "Test notification")

        logger.info("Runtime test passed")
    except Exception as e:
        logger.error(f"Runtime test failed: {e}")
        raise
