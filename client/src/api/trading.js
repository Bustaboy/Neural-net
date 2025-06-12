// client/src/api/trading.js
import { AuthClient } from './auth';

const authClient = new AuthClient();

/**
 * Fetches market data for a given symbol.
 * @param {string} symbol - Trading pair (e.g., 'BTC/USDT').
 * @returns {Promise<Object>} Market data (e.g., { price: number }).
 * @throws {Error} If the request fails (e.g., unauthorized, server error).
 */
export async function fetchMarketData(symbol) {
  try {
    const token = authClient.getToken();
    if (!token) {
      throw new Error('Not authenticated. Please log in.');
    }

    const response = await fetch(`/api/v1/market/data/${symbol}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      if (response.status === 401) {
        await authClient.refreshToken();
        return fetchMarketData(symbol); // Retry with new token
      }
      const error = await response.json();
      throw new Error(error.detail || 'Failed to fetch market data');
    }

    return await response.json();
  } catch (error) {
    console.error('Fetch market data error:', error);
    throw error;
  }
}

/**
 * Places a trade with the specified parameters.
 * @param {Object} trade - Trade details (e.g., { symbol: string, side: string, amount: number }).
 * @returns {Promise<Object>} Trade response (e.g., { status: string }).
 * @throws {Error} If the trade fails (e.g., subscription limit, insufficient balance).
 */
export async function placeTrade(trade) {
  try {
    const token = authClient.getToken();
    if (!token) {
      throw new Error('Not authenticated. Please log in.');
    }

    const response = await fetch('/api/v1/trading/execute', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(trade),
    });

    if (!response.ok) {
      if (response.status === 401) {
        await authClient.refreshToken();
        return placeTrade(trade); // Retry with new token
      }
      if (response.status === 403) {
        const error = await response.json();
        throw new Error(error.detail || 'Trade limit exceeded or unauthorized');
      }
      const error = await response.json();
      throw new Error(error.detail || 'Trade failed');
    }

    return await response.json();
  } catch (error) {
    console.error('Place trade error:', error);
    throw error;
  }
}

/**
 * Fetches the user’s trade history.
 * @returns {Promise<Array>} List of past trades (e.g., [{ id: number, symbol: string, ... }]).
 * @throws {Error} If the request fails (e.g., unauthorized, server error).
 */
export async function fetchTradeHistory() {
  try {
    const token = authClient.getToken();
    if (!token) {
      throw new Error('Not authenticated. Please log in.');
    }

    const response = await fetch('/api/v1/trading/history', {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      if (response.status === 401) {
        await authClient.refreshToken();
        return fetchTradeHistory(); // Retry with new token
      }
      const error = await response.json();
      throw new Error(error.detail || 'Failed to fetch trade history');
    }

    return await response.json();
  } catch (error) {
    console.error('Fetch trade history error:', error);
    throw error;
  }
}
