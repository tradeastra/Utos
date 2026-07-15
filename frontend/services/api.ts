const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class ApiClient {
  private baseUrl: string;
  private token: string | null = null;

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('access_token');
    }
  }

  setToken(token: string | null) {
    this.token = token;
    if (typeof window !== 'undefined') {
      if (token) {
        localStorage.setItem('access_token', token);
      } else {
        localStorage.removeItem('access_token');
      }
    }
  }

  getToken(): string | null {
    return this.token;
  }

  private async request<T>(
    path: string,
    options: RequestInit = {},
  ): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...options.headers as Record<string, string>,
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const res = await fetch(`${this.baseUrl}${path}`, {
      ...options,
      headers,
    });

    if (!res.ok) {
      const error = await res.json().catch(() => ({ message: res.statusText }));
      throw new Error(error?.error?.message || error?.message || `HTTP ${res.status}`);
    }

    const json = await res.json();
    return json.data ?? json;
  }

  async get<T>(path: string): Promise<T> {
    return this.request<T>(path, { method: 'GET' });
  }

  async post<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>(path, {
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  async put<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>(path, {
      method: 'PUT',
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  async delete<T>(path: string): Promise<T> {
    return this.request<T>(path, { method: 'DELETE' });
  }

  // Auth
  async login(email: string, password: string) {
    const data = await this.post<{
      access_token: string;
      refresh_token: string;
      token_type: string;
      expires_in: number;
    }>('/api/v1/auth/login', { email, password });
    this.setToken(data.access_token);
    return data;
  }

  async register(email: string, password: string, full_name?: string) {
    return this.post('/api/v1/auth/register', { email, password, full_name });
  }

  async logout() {
    this.setToken(null);
  }

  // Trading
  async getTradingInstances() {
    return this.get('/api/v1/trading-instances');
  }

  async getGridState(instanceId: string) {
    return this.get(`/api/v1/trading-instances/${instanceId}/grid`);
  }

  async getOrders() {
    return this.get('/api/v1/orders');
  }

  async getPortfolio() {
    return this.get('/api/v1/portfolio');
  }

  // SaaS
  async getSubscription() {
    return this.get('/api/v1/subscription');
  }

  async getInvoices() {
    return this.get('/api/v1/billing/invoices');
  }

  async getAffiliateStats() {
    return this.get('/api/v1/affiliate/stats');
  }
}

export const api = new ApiClient();
