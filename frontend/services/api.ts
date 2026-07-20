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

    // Always read token directly from localStorage (this.token may be null from SSR)
    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const res = await fetch(`${this.baseUrl}${path}`, {
      ...options,
      headers,
    });

    if (!res.ok) {
      if (res.status === 401 && typeof window !== 'undefined') {
        const isAuthEndpoint = path.includes('/auth/');
        if (isAuthEndpoint && window.location.pathname !== '/login') {
          localStorage.removeItem('access_token');
          window.location.href = '/login';
        }
      }
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

  // Market data
  async getMarketPrice(exchange: string, symbol: string) {
    return this.get<{ exchange: string; symbol: string; price: string }>(
      `/api/v1/market/price/${exchange}/${symbol}`,
    );
  }

  async getMarketTicker(exchange: string, symbol: string) {
    return this.get<{
      symbol: string;
      bid: string;
      ask: string;
      last: string;
      volume: string;
      timestamp: string;
    }>(`/api/v1/market/ticker/${exchange}/${symbol}`);
  }

  async getMarketSnapshot() {
    return this.get<{
      running: boolean;
      active_logical_subscriptions: number;
      active_websocket_subscriptions: number;
      consumer_subscriptions: number;
      cache_entries: number;
      exchanges: string[];
      avg_latency_ms: number;
    }>('/api/v1/market/snapshot');
  }

  async testExchangeConnection(exchange: string) {
    return this.get<{
      exchange: string;
      is_testnet: boolean;
      connected: boolean;
      server_time: string | null;
      latency_ms: number | null;
      price_symbol: string | null;
      price: string | null;
      error: string | null;
    }>(`/api/v1/market/test-connection/${exchange}`);
  }

  // Exchange accounts
  async saveExchangeAccount(data: {
    exchange_name: string;
    api_key: string;
    api_secret: string;
    is_testnet: boolean;
  }) {
    return this.post<{
      id: string;
      user_id: string;
      exchange_name: string;
      is_testnet: boolean;
      is_active: boolean;
      connection_status: string;
      created_at: string;
      updated_at: string;
    }>('/api/v1/exchange-accounts/', data);
  }

  async listExchangeAccounts() {
    return this.get<Array<{
      id: string;
      user_id: string;
      exchange_name: string;
      is_testnet: boolean;
      is_active: boolean;
      connection_status: string;
      created_at: string;
      updated_at: string;
    }>>('/api/v1/exchange-accounts/');
  }

  async deleteExchangeAccount(accountId: string) {
    return this.delete<{ message: string }>(`/api/v1/exchange-accounts/${accountId}`);
  }

  async getExchangeAccountBalance(accountId: string) {
    return this.get<{
      balances: Array<{
        currency: string;
        available: string;
        locked: string;
        total: string;
      }>;
    }>(`/api/v1/exchange-accounts/${accountId}/balance`);
  }

  async getExchangeAccountOrders(accountId: string) {
    return this.get<{
      open_orders: Array<{
        order_id: string;
        symbol: string;
        side: string;
        order_type: string;
        quantity: string;
        price: string | null;
        status: string;
        created_at: string | null;
      }>;
    }>(`/api/v1/exchange-accounts/${accountId}/orders`);
  }

  // Strategies
  async listStrategies() {
    return this.get<Array<{
      id: string;
      name: string;
      type: string;
      description: string | null;
      min_investment: number;
      max_investment: number | null;
    }>>('/api/v1/strategies/');
  }

  // Grid Profiles
  async listGridProfiles() {
    return this.get<Array<{
      id: string;
      user_id: string;
      name: string;
      strategy_type: string;
      upper_price: number;
      lower_price: number;
      grid_count: number;
      grid_spacing: number | null;
      investment_per_grid: number;
      take_profit_enabled: boolean;
      take_profit_percentage: number | null;
      stop_loss_enabled: boolean;
      stop_loss_percentage: number | null;
      is_default: boolean;
      created_at: string;
    }>>('/api/v1/grid-profiles/');
  }

  async createGridProfile(data: {
    name: string;
    upper_price: number;
    lower_price: number;
    grid_count: number;
    investment_per_grid: number;
    take_profit_enabled?: boolean;
    take_profit_percentage?: number | null;
    stop_loss_enabled?: boolean;
    stop_loss_percentage?: number | null;
  }) {
    return this.post<{
      id: string;
      name: string;
      upper_price: number;
      lower_price: number;
      grid_count: number;
      investment_per_grid: number;
    }>('/api/v1/grid-profiles/', data);
  }

  async deleteGridProfile(profileId: string) {
    return this.delete<{ message: string }>(`/api/v1/grid-profiles/${profileId}`);
  }

  // Trading Instances
  async createTradingInstance(data: {
    exchange_account_id: string;
    strategy_id: string;
    grid_profile_id: string;
    symbol: string;
    total_investment?: number;
    start_price?: number | null;
    base_currency?: string;
    quote_currency?: string;
  }) {
    return this.post<{
      id: string;
      status: string;
      symbol: string;
      total_investment: number;
    }>('/api/v1/trading-instances', data);
  }

  async listTradingInstances() {
    return this.get<Array<{
      id: string;
      status: string;
      symbol: string;
      total_investment: number;
      start_price: number | null;
      current_price: number | null;
      started_at: string | null;
      stopped_at: string | null;
      error_message: string | null;
    }>>('/api/v1/trading-instances');
  }

  async getTradingInstance(id: string) {
    return this.get<{
      id: string;
      status: string;
      symbol: string;
      total_investment: number;
      start_price: number | null;
      current_price: number | null;
      started_at: string | null;
      stopped_at: string | null;
      error_message: string | null;
    }>(`/api/v1/trading-instances/${id}`);
  }

  async prepareTradingInstance(id: string) {
    return this.post<{
      id: string;
      status: string;
    }>(`/api/v1/trading-instances/${id}/prepare`);
  }

  async startTradingInstance(id: string) {
    return this.post<{
      id: string;
      status: string;
    }>(`/api/v1/trading-instances/${id}/start`);
  }

  async pauseTradingInstance(id: string) {
    return this.post<{
      id: string;
      status: string;
    }>(`/api/v1/trading-instances/${id}/pause`);
  }

  async resumeTradingInstance(id: string) {
    return this.post<{
      id: string;
      status: string;
    }>(`/api/v1/trading-instances/${id}/resume`);
  }

  async stopTradingInstance(id: string) {
    return this.post<{
      id: string;
      status: string;
    }>(`/api/v1/trading-instances/${id}/stop`);
  }

  async configureTrailingProfit(instanceId: string, triggerPercentage: number, trailPercentage: number, maxProfitPercentage: number = 0) {
    return this.post<{
      instance_id: string;
      trigger_percentage: number;
      trail_percentage: number;
      max_profit_percentage: number;
      status: string;
    }>(`/api/v1/trading-instances/${instanceId}/trailing-profit`, {
      trigger_percentage: triggerPercentage,
      trail_percentage: trailPercentage,
      max_profit_percentage: maxProfitPercentage,
    });
  }

  // Add-ons
  async listAddons() {
    return this.get<Array<{
      key: string;
      name: string;
      description: string;
      price: number;
      is_purchased: boolean;
      is_active: boolean;
    }>>('/api/v1/addons/');
  }

  async checkAddonAccess(addonKey: string) {
    return this.get<{
      addon_key: string;
      has_access: boolean;
      via_tier: boolean;
      via_addon: boolean;
      tier: string;
    }>(`/api/v1/addons/check/${addonKey}`);
  }

  async purchaseAddon(addonKey: string, durationDays: number = 30) {
    return this.post<{
      addon_key: string;
      is_active: boolean;
      purchased_at: string;
      expires_at: string | null;
    }>('/api/v1/addons/purchase', {
      addon_key: addonKey,
      duration_days: durationDays,
    });
  }
}

export const api = new ApiClient();
