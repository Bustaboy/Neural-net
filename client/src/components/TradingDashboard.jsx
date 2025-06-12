// client/src/components/TradingDashboard.jsx
import React, { useState, useEffect } from 'react';
import { fetchMarketData, placeTrade } from '../api/trading';

const TradingDashboard = () => {
  const [marketData, setMarketData] = useState({});
  const [trade, setTrade] = useState({ symbol: 'BTC/USDT', side: 'buy', amount: 0 });

  useEffect(() => {
    const interval = setInterval(async () => {
      const data = await fetchMarketData('BTC/USDT');
      setMarketData(data);
    }, 60000); // Update every minute
    return () => clearInterval(interval);
  }, []);

  const handleTrade = async () => {
    await placeTrade(trade);
    alert('Trade placed!');
  };

  return (
    <div>
      <h1>Trading Dashboard</h1>
      <div>Price: {marketData.price || 'Loading...'}</div>
      <form onSubmit={handleTrade}>
        <input
          type="text"
          value={trade.symbol}
          onChange={(e) => setTrade({ ...trade, symbol: e.target.value })}
        />
        <select
          value={trade.side}
          onChange={(e) => setTrade({ ...trade, side: e.target.value })}
        >
          <option value="buy">Buy</option>
          <option value="sell">Sell</option>
        </select>
        <input
          type="number"
          value={trade.amount}
          onChange={(e) => setTrade({ ...trade, amount: parseFloat(e.target.value) })}
        />
        <button type="submit">Trade</button>
      </form>
    </div>
  );
};

export default TradingDashboard;
