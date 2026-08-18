const API_BASE_URL = 'http://localhost:8000/api';

interface SignInRequest {
  email: string;
  callback_url: string;
}

interface SignInResponse {
  connection_url: string;
}

export const apiService = {
  async createSignInLink(
    data: SignInRequest
  ): Promise<SignInResponse> {
    const response = await fetch(`${API_BASE_URL}/auth/signin`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(
        error.detail || 'Failed to create sign-in link'
      );
    }

    return response.json();
  },

  async getUserConnectionStatus(email: string) {
    const response = await fetch(
      `${API_BASE_URL}/auth/status/${encodeURIComponent(email)}`
    );

    if (!response.ok) {
      throw new Error('Failed to get connection status');
    }

    return response.json();
  },
};
