# market/data_fetcher.py
import ccxt.async_support as ccxt
import asyncio
from config import ConfigManager

class MarketDataFetcher:
    def __init__(self):
        self.exchange = ccxt.binance({
            'apiKey': ConfigManager.get_config("binance.api_key"),
            'secret': ConfigManager.get_config("binance.secret")
        })

    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 100):
        await self.exchange.enableRateLimit()
        data = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        await self.exchange.close()
        return data
