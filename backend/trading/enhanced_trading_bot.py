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
        self.micro_trend_window = 5
        self.portfolio = ["BTC/USDT", "ETH/USDT"]
        self.last_training_time = asyncio.get_event_loop().time()
        logger.info(f"Initialized bot for user {user_id} with capital ${self.get_capital()}")

    def get_capital(self) -> float:
        return self.position_manager.get_portfolio_value(self.user_id) or 500.0

    def calculate_max_trades(self) -> int:
        capital = self.get_capital()
        base_trades = 3
        additional_trades = int(capital // 500)
        return min(base_trades + additional_trades, 20)

    def is_financially_sensible(self, trade: Dict[str, Any]) -> bool:
        trade_size = trade["quantity"] * trade["price"]
        fee = trade_size * 0.001
        expected_profit = trade_size * trade.get("expected_return", 0.02)
        return expected_profit > 2 * fee and expected_profit > self.min_profit_threshold

    async def micro_trend_scalping(self, symbol: str, price: float) -> Optional[Dict[str, Any]]:
        candles = await self.exchange.fetch_ohlcv(symbol, timeframe="5m", limit=10)
        returns = np.diff([c[4] for c in candles]) / [c[4] for c in candles][:-1]
        trend = np.mean(returns[-3:])
        if abs(trend) > 0.005:
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
        defi_data = await self.exchange.fetch_defi_metrics(symbol)
        apy = defi_data.get("apy", 0.0)
        if apy > 0.6:
            capital = self.get_capital()
            return {
                "symbol": symbol,
                "side": "stake",
                "quantity": capital * 0.05,
                "price": 1.0,
                "expected_return": apy / 365
            }
        return None

    async def cross_chain_arbitrage(self, symbol: str) -> Optional[Dict[str, Any]]:
        chains = ["ethereum", "solana"]
        prices = {}
        for chain in chains:
            chain_price = await self.exchange.get_cross_chain_price(symbol, chain)
            if chain_price:
                prices[chain] = chain_price
        if len(prices) < 2:
            return None
        max_spread = max(prices.values()) - min(prices.values())
        if max_spread / min(prices.values()) > 0.025:
            low_chain = min(prices, key=prices.get)
            high_chain = max(prices, key=prices.get)
            capital = self.get_capital()
            return {
                "symbol": symbol,
                "side": "buy",
                "quantity": capital * 0.05 / prices[low_chain],
                "price": prices[low_chain],
                "sell_chain": high_chain,
                "sell_price": prices[high_chain],
                "expected_return": max_spread / prices[low_chain]
            }
        return None

    async def social_sentiment_arbitrage(self, symbol: str) -> Optional[Dict[str, Any]]:
        sentiment_score = self.sentiment_analyzer.analyze(symbol)
        if abs(sentiment_score) > 0.9:
            market_data = await self.exchange.fetch_market_data(symbol)
            side = "buy" if sentiment_score > 0.9 else "sell"
            capital = self.get_capital()
            return {
                "symbol": symbol,
                "side": side,
                "quantity": capital * 0.05 / market_data["price"],
                "price": market_data["price"],
                "expected_return": 0.05
            }
        return None

    async def rebalance_portfolio(self, market_data: Dict[str, Any]) -> None:
        weights = self.model.rebalance_portfolio(market_data)
        current_positions = self.position_manager.get_open_positions(self.user_id)
        for i, symbol in enumerate(self.portfolio):
            target_value = self.get_capital() * weights[i]
            current_value = sum(p["value"] for p in current_positions if p["symbol"] == symbol)
            if abs(target_value - current_value) > self.get_capital() * 0.01:
                side = "buy" if target_value > current_value else "sell"
                quantity = abs(target_value - current_value) / market_data["prices"][symbol]
                trade = {
                    "symbol": symbol,
                    "side": side,
                    "quantity": quantity,
                    "price": market_data["prices"][symbol],
                    "expected_return": 0.02
                }
                if self.is_financially_sensible(trade):
                    await self.execute_trade(trade)

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

                market_data = {
                    "symbol": "BTC/USDT",
                    "prices": {},
                    "volatility": volatility,
                    "sentiment": self.sentiment_analyzer.analyze("BTC/USDT"),
                    "defi_apy": (await self.exchange.fetch_defi_metrics("BTC/USDT")).get("apy", 0.5),
                    "portfolio_weights": [0.5, 0.5]
                }
                for symbol in self.portfolio:
                    market_data["prices"][symbol] = (await self.exchange.fetch_market_data(symbol))["price"]

                # Incremental training every 10 minutes
                current_time = asyncio.get_event_loop().time()
                if current_time - self.last_training_time >= 600:  # 10 minutes
                    logger.info("Performing incremental training")
                    self.model.train(market_data, incremental=True)
                    self.last_training_time = current_time

                await self.rebalance_portfolio(market_data)

                for symbol in self.portfolio:
                    price = market_data["prices"][symbol]
                    trade = await self.cross_chain_arbitrage(symbol)
                    if not trade:
                        trade = await self.micro_trend_scalping(symbol, price)
                    if not trade:
                        trade = await self.defi_yield_farming(symbol)
                    if not trade:
                        trade = await self.social_sentiment_arbitrage(symbol)
                    if not trade:
                        ml_signal = self.model.predict(market_data)
                        trade = {
                            "symbol": symbol,
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

                await asyncio.sleep(60)
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
