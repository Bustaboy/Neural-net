// client/src/api/ml.js
import { AuthClient } from './auth';

const authClient = new AuthClient();

export async function fetchModelStatus() {
    try {
        const token = authClient.getToken();
        if (!token) throw new Error('Not authenticated. Please log in.');
        const response = await fetch('/api/v1/model_status', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
            },
        });
        if (!response.ok) {
            if (response.status === 401) {
                await authClient.refreshToken();
                return fetchModelStatus();
            }
            const error = await response.json();
            throw new Error(error.detail || 'Failed to fetch model status');
        }
        return await response.json();
    } catch (error) {
        console.error('Fetch model status error:', error);
        throw error;
    }
}
