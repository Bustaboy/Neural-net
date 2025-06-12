# trading/exchange_abstraction.py
from abc import ABC, abstractmethod
import ccxt

class ExchangeInterface(ABC):
    @abstractmethod
    def get_balance(self, asset: str) -> float:
        pass
    
    @abstractmethod
    def place_order(self, symbol: str, side: str, amount: float, price: float = None):
        pass
    
    @abstractmethod
    def get_order_status(self, order_id: str):
        pass

class BinanceAdapter(ExchangeInterface):
    def __init__(self, api_key: str, api_secret: str):
        self.exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret
        })
    
    def get_balance(self, asset: str) -> float:
        balance = self.exchange.fetch_balance()
        return balance[asset]['free']
    
    def place_order(self, symbol: str, side: str, amount: float, price: float = None):
        if price:
            return self.exchange.create_limit_order(symbol, side, amount, price)
        else:
            return self.exchange.create_market_order(symbol, side, amount)

class MultiExchangeManager:
    def __init__(self):
        self.exchanges = {}
        
    def add_exchange(self, name: str, adapter: ExchangeInterface):
        self.exchanges[name] = adapter
        
    def execute_best_price(self, symbol: str, side: str, amount: float):
        """Execute order on exchange with best price"""
        best_price = None
        best_exchange = None
        
        for name, exchange in self.exchanges.items():
            try:
                orderbook = exchange.get_orderbook(symbol)
                price = orderbook['bids'][0][0] if side == 'sell' else orderbook['asks'][0][0]
                
                if best_price is None or (side == 'buy' and price < best_price) or (side == 'sell' and price > best_price):
                    best_price = price
                    best_exchange = name
            except:
                continue
                
        if best_exchange:
            return self.exchanges[best_exchange].place_order(symbol, side, amount)
