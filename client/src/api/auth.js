// client/src/api/auth.js
export class AuthClient {
  async login(email, password) {
    const response = await fetch('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!response.ok) throw new Error('Login failed');
    const data = await response.json();
    if (data.status === '2fa_required') {
      return { status: '2fa_required', user_id: data.user_id };
    }
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
    return { status: 'success' };
  }

  async verify2FA(user_id, code) {
    const response = await fetch('/api/v1/auth/verify-2fa', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id, code }),
    });
    if (!response.ok) throw new Error('2FA verification failed');
    const data = await response.json();
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
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
