# trading/order_executor.py
from trading.exchange_abstraction import BinanceAdapter
from core.exceptions import ExchangeError

class OrderExecutor:
    def __init__(self, config: Dict):
        self.exchange = BinanceAdapter(
            config['binance']['api_key'],
            config['binance']['secret']
        )

    def execute_trade(self, symbol: str, side: str, amount: float, price: float = None):
        try:
            order = self.exchange.place_order(symbol, side, amount, price)
            return order
        except Exception as e:
            raise ExchangeError(f"Order execution failed: {e}")
