# market/data_fetcher.py
import ccxt.async_support as ccxt
import asyncio
import logging
from config import ConfigManager

class MarketDataFetcher:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.exchange = ccxt.binance({
            'apiKey': ConfigManager.get_config("custom.binance.api_key"),
            'secret': ConfigManager.get_config("custom.binance.secret_key")
        })

    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 100):
        try:
            await self.exchange.enableRateLimit()
            data = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            await self.exchange.close()
            return data
        except Exception as e:
            self.logger.error(f"Failed to fetch OHLCV: {e}")
            raise

    async def fetch_ticker(self, symbol: str):
        try:
            await self.exchange.enableRateLimit()
            ticker = await self.exchange.fetch_ticker(symbol)
            await self.exchange.close()
            return {"price": ticker['last']}
        except Exception as e:
            self.logger.error(f"Failed to fetch ticker: {e}")
            raise
