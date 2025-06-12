# scripts/backtest.py
import pandas as pd
from trading.strategies import TradingStrategy

def run_backtest(symbol: str, data: pd.DataFrame, config: Dict):
    strategy = TradingStrategy(config)
    trades = []
    for _, row in data.iterrows():
        signal = strategy.momentum_strategy(row.values)
        if signal != "hold":
            trades.append({"symbol": symbol, "side": signal, "price": row['close']})
    return trades
