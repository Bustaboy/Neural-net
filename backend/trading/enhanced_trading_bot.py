# backend/trading/enhanced_trading_bot.py
from typing import Dict, Any, Optional
from nlp.natural_language_trading import SentimentAnalyzer
from trading.exchange_abstraction import ExchangeAbstraction
from trading.market.indicators import MarketIndicators
from trading.position_manager import PositionManager
from ml.ensemble import EnsembleModel
import logging

logger = logging.getLogger(__name__)

class EnhancedTradingBot:
    def __init__(self, user_id: int, config: Dict[str, Any], position_manager: PositionManager):
        self.user_id = user_id
        self.config = config
        self.position_manager = position_manager
        self.exchange = ExchangeAbstraction(config.get("exchange_api_key"), config.get("exchange_secret"))
        self.sentiment_analyzer = SentimentAnalyzer()
        self.indicators = MarketIndicators()
        self.model = EnsembleModel.load(config.get("model_path", "models/central_model.pkl"))
        self.min_profit_threshold = 0.05  # Minimum expected profit ($0.05 to cover $0.025 fee)
        self.max_daily_trades = self.calculate_max_trades()
        self.daily_trades = 0
        logger.info(f"Initialized bot for user {user_id} with capital ${self.get_capital()}")

    def get_capital(self) -> float:
        """Get current capital from position manager."""
        return self.position_manager.get_portfolio_value(self.user_id) or 500.0  # Default $500

    def calculate_max_trades(self) -> int:
        """Scale trades based on capital (3 trades/day for $500, +1 per $500)."""
        capital = self.get_capital()
        base_trades = 3
        additional_trades = int(capital // 500)
        return min(base_trades + additional_trades, 10)  # Cap at 10 trades/day

    def is_financially_sensible(self, trade: Dict[str, Any]) -> bool:
        """Check if trade's expected profit exceeds 2x fees."""
        trade_size = trade["quantity"] * trade["price"]
        fee = trade_size * 0.001  # 0.1% fee
        expected_profit = trade_size * trade.get("expected_return", 0.02)  # Assume 2% return
        return expected_profit > 2 * fee and expected_profit > self.min_profit_threshold

    async def run(self):
        """Main trading loop with sentiment, arbitrage, and volatility checks."""
        while True:
            try:
                capital = self.get_capital()
                if self.daily_trades >= self.max_daily_trades:
                    logger.info("Daily trade limit reached")
                    await asyncio.sleep(86400)  # Wait until next day
                    self.daily_trades = 0
                    continue

                # Check market volatility
                volatility = self.indicators.calculate_volatility("BTC/USDT", timeframe="1d")
                if volatility < 0.02:  # Skip if volatility < 2%
                    await asyncio.sleep(3600)  # Wait 1 hour
                    continue

                # Get sentiment signal
                sentiment_score = self.sentiment_analyzer.analyze("BTC/USDT")
                sentiment_signal = "buy" if sentiment_score > 0.7 else "sell" if sentiment_score < -0.7 else None

                # Get ML signal
                market_data = await self.exchange.fetch_market_data("BTC/USDT")
                ml_signal = self.model.predict(market_data)
                signal = sentiment_signal or ml_signal.get("side")

                # Check for arbitrage opportunities
                arbitrage_opp = self.find_arbitrage("BTC/USDT")
                if arbitrage_opp:
                    trade = arbitrage_opp
                else:
                    trade = {
                        "symbol": "BTC/USDT",
                        "side": signal,
                        "quantity": capital * 0.05 / market_data["price"],  # 5% of capital
                        "price": market_data["price"],
                        "expected_return": ml_signal.get("confidence", 0.02) * 0.05  # Scaled return
                    }

                # Validate trade
                if trade["side"] and self.is_financially_sensible(trade):
                    trade["stop_loss"] = trade["price"] * 0.98  # 2% stop-loss
                    trade["take_profit"] = trade["price"] * 1.05  # 5% take-profit
                    await self.execute_trade(trade)
                    self.daily_trades += 1
                    # Reinvest profits by updating capital
                    self.position_manager.update_portfolio(self.user_id, trade)

                await asyncio.sleep(300)  # Wait 5 minutes
            except Exception as e:
                logger.error(f"Trading error: {e}")
                await asyncio.sleep(60)

    async def execute_trade(self, trade: Dict[str, Any]):
        """Execute trade and log it."""
        order = await self.exchange.place_order(
            symbol=trade["symbol"],
            side=trade["side"],
            quantity=trade["quantity"],
            price=trade["price"],
            stop_loss=trade.get("stop_loss"),
            take_profit=trade.get("take_profit")
        )
        logger.info(f"Executed trade: {order}")
        self.position_manager.add_trade(self.user_id, order)

    def find_arbitrage(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Check for arbitrage opportunities across exchanges."""
        prices = self.exchange.get_cross_exchange_prices(symbol)
        if not prices:
            return None
        max_spread = max(prices.values()) - min(prices.values())
        if max_spread / min(prices.values()) > 0.015:  # 1.5% spread after fees
            low_ex = min(prices, key=prices.get)
            high_ex = max(prices, key=prices.get)
            capital = self.get_capital()
            return {
                "symbol": symbol,
                "side": "buy",
                "quantity": capital * 0.05 / prices[low_ex],  # 5% of capital
                "price": prices[low_ex],
                "sell_exchange": high_ex,
                "sell_price": prices[high_ex],
                "expected_return": max_spread / prices[low_ex]
            }
        return None
