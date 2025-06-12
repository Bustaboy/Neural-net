// client/src/api/auth.js
export class AuthClient {
  async login(email, password) {
    const response = await fetch('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!response.ok) throw new Error('Login failed');
    const { access_token, refresh_token } = await response.json();
    localStorage.setItem('access_token', access_token);
    localStorage.setItem('refresh_token', refresh_token);
  }

  async refreshToken() {
    const refresh_token = localStorage.getItem('refresh_token');
    const response = await fetch('/api/v1/auth/refresh', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${refresh_token}` },
    });
    if (!response.ok) throw new Error('Refresh failed');
    const { access_token } = await response.json();
    localStorage.setItem('access_token', access_token);
  }

  getToken() {
    return localStorage.getItem('access_token');
  }
}
