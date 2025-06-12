// client/src/api/trading.js
export async function fetchMarketData(symbol) {
  const response = await fetch(`/api/v1/market/data/${symbol}`, {
    headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` },
  });
  if (!response.ok) throw new Error('Failed to fetch market data');
  return response.json();
}

export async function placeTrade(trade) {
  const response = await fetch('/api/v1/trading/execute', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(trade),
  });
  if (!response.ok) throw new Error('Trade failed');
  return response.json();
}
