# backend/trading/enhanced_trading_bot.py
from typing import Dict, Any, Optional
from nlp.natural_language_trading import SentimentAnalyzer
from trading.exchange_abstraction import ExchangeAbstraction
from trading.market.indicators import MarketIndicators
from trading.position_manager import PositionManager
from ml.ensemble import EnsembleModel
import logging
import asyncio
import numpy as np

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
        self.min_profit_threshold = 0.05
        self.max_daily_trades = self.calculate_max_trades()
        self.daily_trades = 0
        self.micro_trend_window = 5  # 5-minute trends
        logger.info(f"Initialized bot for user {user_id} with capital ${self.get_capital()}")

    def get_capital(self) -> float:
        return self.position_manager.get_portfolio_value(self.user_id) or 500.0

    def calculate_max_trades(self) -> int:
        capital = self.get_capital()
        base_trades = 3
        additional_trades = int(capital // 500)
        return min(base_trades + additional_trades, 15)

    def is_financially_sensible(self, trade: Dict[str, Any]) -> bool:
        trade_size = trade["quantity"] * trade["price"]
        fee = trade_size * 0.001
        expected_profit = trade_size * trade.get("expected_return", 0.02)
        return expected_profit > 2 * fee and expected_profit > self.min_profit_threshold

    async def micro_trend_scalping(self, symbol: str, price: float) -> Optional[Dict[str, Any]]:
        """Scalp 5-minute micro-trends."""
        candles = await self.exchange.fetch_ohlcv(symbol, timeframe="5m", limit=10)
        returns = np.diff([c[4] for c in candles]) / [c[4] for c in candles][:-1]
        trend = np.mean(returns[-3:])  # Last 3 periods
        if abs(trend) > 0.005:  # 0.5% trend
            side = "buy" if trend > 0 else "sell"
            capital = self.get_capital()
            return {
                "symbol": symbol,
                "side": side,
                "quantity": capital * 0.05 / price,
                "price": price,
                "expected_return": abs(trend) * 0.7
            }
        return None

    async def defi_yield_farming(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Farm yield on DeFi pools with high APY."""
        defi_data = await self.exchange.fetch_defi_metrics(symbol)  # Assumes ccxt extension
        apy = defi_data.get("apy", 0.0)
        if apy > 0.5:  # 50% APY
            capital = self.get_capital()
            return {
                "symbol": symbol,
                "side": "stake",
                "quantity": capital * 0.05,
                "price": 1.0,  # Normalized for staking
                "expected_return": apy / 365  # Daily return
            }
        return None

    async def predictive_arbitrage(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Predict arbitrage opportunities using RL."""
        prices = self.exchange.get_cross_exchange_prices(symbol)
        if not prices:
            return None
        price_data = {"prices": list(prices.values()), "timestamp": asyncio.get_event_loop().time()}
        prediction = self.model.predict(price_data)
        if prediction["side"] and prediction["confidence"] > 0.9:
            low_ex = min(prices, key=prices.get)
            high_ex = max(prices, key=prices.get)
            spread = prices[high_ex] - prices[low_ex]
            if spread / prices[low_ex] > 0.02:
                capital = self.get_capital()
                return {
                    "symbol": symbol,
                    "side": "buy",
                    "quantity": capital * 0.05 / prices[low_ex],
                    "price": prices[low_ex],
                    "sell_exchange": high_ex,
                    "sell_price": prices[high_ex],
                    "expected_return": spread / prices[low_ex]
                }
        return None

    async def social_sentiment_arbitrage(self, symbol: str) -> Optional[Dict[str, Any]]:
        sentiment_score = self.sentiment_analyzer.analyze(symbol)
        if abs(sentiment_score) > 0.85:
            market_data = await self.exchange.fetch_market_data(symbol)
            side = "buy" if sentiment_score > 0.85 else "sell"
            capital = self.get_capital()
            return {
                "symbol": symbol,
                "side": side,
                "quantity": capital * 0.05 / market_data["price"],
                "price": market_data["price"],
                "expected_return": 0.04
            }
        return None

    async def run(self):
        while True:
            try:
                capital = self.get_capital()
                if self.daily_trades >= self.max_daily_trades:
                    logger.info("Daily trade limit reached")
                    await asyncio.sleep(86400)
                    self.daily_trades = 0
                    continue

                volatility = self.indicators.calculate_volatility("BTC/USDT", timeframe="1d")
                if volatility < 0.02:
                    await asyncio.sleep(3600)
                    continue

                market_data = await self.exchange.fetch_market_data("BTC/USDT")
                price = market_data["price"]

                # Try strategies in order of expected return
                trade = await self.predictive_arbitrage("BTC/USDT")
                if not trade:
                    trade = await self.micro_trend_scalping("BTC/USDT", price)
                if not trade:
                    trade = await self.defi_yield_farming("BTC/USDT")
                if not trade:
                    trade = await self.social_sentiment_arbitrage("BTC/USDT")
                if not trade:
                    ml_signal = self.model.predict(market_data)
                    trade = {
                        "symbol": "BTC/USDT",
                        "side": ml_signal["side"],
                        "quantity": capital * 0.05 / price,
                        "price": price,
                        "expected_return": ml_signal["confidence"] * 0.05
                    }

                if trade["side"] and self.is_financially_sensible(trade):
                    trade["stop_loss"] = trade["price"] * 0.98
                    trade["take_profit"] = trade["price"] * 1.05
                    await self.execute_trade(trade)
                    self.daily_trades += 1
                    self.position_manager.update_portfolio(self.user_id, trade)

                await asyncio.sleep(120)  # 2 minutes
            except Exception as e:
                logger.error(f"Trading error: {e}")
                await asyncio.sleep(60)

    async def execute_trade(self, trade: Dict[str, Any]):
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
