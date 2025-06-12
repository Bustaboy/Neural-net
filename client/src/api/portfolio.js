// client/src/api/portfolio.js
import { AuthClient } from './auth';

const authClient = new AuthClient();

export async function fetchPortfolio() {
    try {
        const token = authClient.getToken();
        if (!token) throw new Error('Not authenticated. Please log in.');
        const response = await fetch('/api/v1/portfolio', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
            },
        });
        if (!response.ok) {
            if (response.status === 401) {
                await authClient.refreshToken();
                return fetchPortfolio();
            }
            const error = await response.json();
            throw new Error(error.detail || 'Failed to fetch portfolio');
        }
        return await response.json();
    } catch (error) {
        console.error('Fetch portfolio error:', error);
        throw error;
    }
}
