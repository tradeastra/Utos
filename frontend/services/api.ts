import type { BreakerThreshold } from '@/types';

function resolveApiBase(): string {
  const raw = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  if (typeof window !== 'undefined' && window.location.protocol === 'https:') {
    return raw.replace(/^http:\/\//, 'https://');
  }
  return raw;
}

class ApiClient {
  private baseUrl: string;
  private token: string | null = null;
  private refreshPromise: Promise<string | null> | null = null;

  constructor(baseUrl?: string) {
    // Lazy evaluation â€” resolveApiBase() runs at runtime (in the browser),
    // NOT at build time. This ensures the httpâ†’https upgrade works even
    // if the bundler pre-evaluates module-level constants.
    this.baseUrl = baseUrl ?? resolveApiBase();
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

  setRefreshToken(token: string | null) {
    if (typeof window !== 'undefined') {
      if (token) {
        localStorage.setItem('refresh_token', token);
      } else {
        localStorage.removeItem('refresh_token');
      }
    }
  }

  getRefreshToken(): string | null {
    return typeof window !== 'undefined' ? localStorage.getItem('refresh_token') : null;
  }

  getToken(): string | null {
    return this.token;
  }

  private clearAuthAndRedirect() {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      this.token = null;
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
  }

  private async tryRefresh(): Promise<string | null> {
    if (this.refreshPromise) return this.refreshPromise;

    const refreshToken = this.getRefreshToken();
    if (!refreshToken) return null;

    this.refreshPromise = (async () => {
      try {
        const res = await fetch(`${this.baseUrl}/api/v1/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
        if (!res.ok) return null;
        const json = await res.json();
        const newToken = json.data?.access_token ?? json.access_token;
        if (newToken) {
          this.setToken(newToken);
          return newToken;
        }
        return null;
      } catch {
        return null;
      } finally {
        this.refreshPromise = null;
      }
    })();

    return this.refreshPromise;
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

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000);

    let res = await fetch(`${this.baseUrl}${path}`, {
      ...options,
      headers,
      signal: options.signal ?? controller.signal,
    });

    clearTimeout(timeoutId);

    // On 401, try to refresh the token and retry once
    if (res.status === 401 && typeof window !== 'undefined' && !path.includes('/auth/')) {
      const newToken = await this.tryRefresh();
      if (newToken) {
        headers['Authorization'] = `Bearer ${newToken}`;
        const retryController = new AbortController();
        const retryTimeoutId = setTimeout(() => retryController.abort(), 10000);
        res = await fetch(`${this.baseUrl}${path}`, {
          ...options,
          headers,
          signal: options.signal ?? retryController.signal,
        });
        clearTimeout(retryTimeoutId);
      } else {
        this.clearAuthAndRedirect();
        throw new Error('Session expired. Please log in again.');
      }
    }

    if (!res.ok) {
      if (res.status === 401 && typeof window !== 'undefined') {
        this.clearAuthAndRedirect();
      }
      const error = await res.json().catch(() => ({ message: res.statusText }));
      throw new Error(error?.error?.message || error?.message || error?.detail || `HTTP ${res.status}`);
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

  async patch<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>(path, {
      method: 'PATCH',
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
    this.setRefreshToken(data.refresh_token);
    return data;
  }

  async register(email: string, password: string, full_name?: string) {
    return this.post('/api/v1/auth/register', { email, password, full_name });
  }

  async logout() {
    this.setToken(null);
    this.setRefreshToken(null);
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

  async getMarketTickers(exchange: string, limit: number = 200) {
    return this.get<Array<{
      symbol: string;
      last_price: string;
      price_change_percent: string;
      quote_volume: string;
      high_price: string;
      low_price: string;
    }>>(`/api/v1/market/tickers/${exchange}?limit=${limit}`);
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
  async getSupportedExchanges() {
    return this.get<Array<{
      id: string;
      name: string;
      testnet_url: string;
      has_testnet: boolean;
      status: string;
      requires_passphrase: boolean;
    }>>('/api/v1/exchange-accounts/supported');
  }

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

  async listStrategyModes() {
    return this.get<Array<{
      mode: string;
      label: string;
      tp_range_min: number;
      tp_range_max: number;
      risk_level: string;
      description: string | null;
      is_active: boolean;
      sort_order: number;
    }>>('/api/v1/strategies/modes');
  }

  async getGridSpacing(symbol: string, mode: string, exchange?: string) {
    const qs = new URLSearchParams({ mode });
    if (exchange) qs.set('exchange', exchange);
    return this.get<{
      symbol: string; exchange: string; mode: string;
      tp_range_pct: number; atr_pct: number; avg_atr_pct: number;
      adaptive_factor: number; spacing_pct: number;
      used_fallback: boolean; candle_count: number;
    }>(`/api/v1/strategies/grid-spacing/${symbol.toUpperCase()}?${qs.toString()}`);
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
    strategy_mode?: string;
    selected_coins?: string[];
    continuation_rate?: number;
    breaker_enabled?: boolean;
    auto_start?: boolean;
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

  async deleteTradingInstance(id: string) {
    return this.delete<void>(`/api/v1/trading-instances/${id}`);
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

  async getCoinGroups() {
    return this.get<{
      id: string;
      name: string;
      description: string | null;
      max_coins: number;
      coins: string[];
      is_builtin: boolean;
      is_active: boolean;
    }[]>('/api/v1/coin-groups');
  }

  async createCoinGroup(name: string, coins: string[], description?: string) {
    return this.post<{
      id: string;
      name: string;
      max_coins: number;
      coins: string[];
      is_builtin: boolean;
    }>('/api/v1/coin-groups', { name, coins, description });
  }

  async deleteCoinGroup(groupId: string) {
    return this.delete(`/api/v1/coin-groups/${groupId}`);
  }

  async getCoinSelectionLimits() {
    return this.get<{
      tier: string;
      max_coin_selection: number;
      current_selection: number;
    }>('/api/v1/coin-groups/limits');
  }

  async getMMPresets() {
    return this.get<{
      id: string;
      name: string;
      preset_type: string;
      steps: number;
      min_capital: string;
      max_capital: string | null;
      description: string | null;
      allowed_coin_groups: string[];
      is_builtin: boolean;
      is_active: boolean;
    }[]>('/api/v1/mm-presets');
  }

  async calculateMM(presetType: string, capital: number, coinGroupName: string, customSteps?: number, numCoins?: number) {
    return this.post<{
      buy_amount: string;
      max_coins: number;
      steps: number;
      capital: string;
      preset_type: string;
      min_volume_filter: string;
    }>('/api/v1/mm-presets/calculate', {
      preset_type: presetType,
      capital,
      coin_group_name: coinGroupName,
      custom_steps: customSteps,
      num_coins: numCoins,
    });
  }

  async createMMPreset(name: string, steps: number, minCapital: number, description?: string) {
    return this.post<{
      id: string;
      name: string;
      preset_type: string;
      steps: number;
    }>('/api/v1/mm-presets', { name, steps, min_capital: minCapital, description });
  }

  async deleteMMPreset(presetId: string) {
    return this.delete(`/api/v1/mm-presets/${presetId}`);
  }

  // â”€â”€â”€ Admin endpoints â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

  async adminListCoinGroups() {
    return this.get<{
      id: string; name: string; description: string | null; max_coins: number;
      coins: string[]; is_builtin: boolean; is_active: boolean; user_id: string | null;
    }[]>('/api/v1/admin/coin-groups');
  }

  async adminCreateCoinGroup(data: { name: string; description?: string; max_coins: number; coins: string[]; is_builtin?: boolean }) {
    return this.post<{
      id: string; name: string; max_coins: number; coins: string[]; is_builtin: boolean; is_active: boolean;
    }>('/api/v1/admin/coin-groups', data);
  }

  async adminUpdateCoinGroup(groupId: string, data: {
    name?: string; description?: string; max_coins?: number; coins?: string[]; is_active?: boolean;
  }) {
    return this.put<{
      id: string; name: string; description: string | null; max_coins: number;
      coins: string[]; is_builtin: boolean; is_active: boolean;
    }>(`/api/v1/admin/coin-groups/${groupId}`, data);
  }

  async adminDeleteCoinGroup(groupId: string) {
    return this.delete(`/api/v1/admin/coin-groups/${groupId}`);
  }

  async adminListMMPresets() {
    return this.get<{
      id: string; name: string; preset_type: string; steps: number; min_capital: string;
      max_capital: string | null; description: string | null; allowed_coin_groups: string[];
      is_builtin: boolean; is_active: boolean; user_id: string | null;
    }[]>('/api/v1/admin/mm-presets');
  }

  async adminCreateMMPreset(data: {
    name: string; preset_type: string; steps: number; min_capital: number;
    max_capital?: number; description?: string; allowed_coin_groups?: string[]; is_builtin?: boolean;
  }) {
    return this.post<{
      id: string; name: string; preset_type: string; steps: number;
    }>('/api/v1/admin/mm-presets', data);
  }

  async adminUpdateMMPreset(presetId: string, data: {
    name?: string; steps?: number; min_capital?: number; max_capital?: number;
    description?: string; allowed_coin_groups?: string[]; is_active?: boolean;
  }) {
    return this.put<{
      id: string; name: string; preset_type: string; steps: number;
    }>(`/api/v1/admin/mm-presets/${presetId}`, data);
  }

  async adminDeleteMMPreset(presetId: string) {
    return this.delete(`/api/v1/admin/mm-presets/${presetId}`);
  }

  async adminListStrategyModes() {
    return this.get<{
      mode: string; label: string; tp_range_min: number; tp_range_max: number; risk_level: string; description: string | null;
    }[]>('/api/v1/admin/strategy-modes');
  }

  async adminUpdateStrategyMode(mode: string, data: {
    label?: string; tp_range_min?: number; tp_range_max?: number; risk_level?: string; description?: string;
  }) {
    return this.put<{
      mode: string; label: string; tp_range_min: number; tp_range_max: number; risk_level: string; description: string | null;
    }>(`/api/v1/admin/strategy-modes/${mode}`, data);
  }

  // â”€â”€â”€ Admin: Circuit Breaker Thresholds â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

  async adminListBreakerThresholds(params?: { rate?: number; exchange?: string }) {
    const qs = new URLSearchParams();
    if (params?.rate !== undefined) qs.set('rate', String(params.rate));
    if (params?.exchange) qs.set('exchange', params.exchange);
    const q = qs.toString();
    return this.get<{
      id: string; exchange: string; symbol: string; min_continuation_rate: number;
      threshold_pct: number; continuation_window: number; min_future_drop_pct: number;
      lookback_days: number; candle_count: number; used_fallback: boolean;
      note: string | null; screened_at: string | null; created_at: string | null;
      updated_at: string | null;
    }[]>(`/api/v1/admin/breaker-thresholds${q ? `?${q}` : ''}`);
  }

  async adminGetBreakerThreshold(symbol: string, params?: { rate?: number; exchange?: string }) {
    const qs = new URLSearchParams();
    if (params?.rate !== undefined) qs.set('rate', String(params.rate));
    if (params?.exchange) qs.set('exchange', params.exchange);
    const q = qs.toString();
    return this.get<any>(`/api/v1/admin/breaker-thresholds/${symbol.toUpperCase()}${q ? `?${q}` : ''}`);
  }

  async adminBreakerHealthSummary() {
    return this.get<{
      total_rows: number; distinct_symbols: number;
      per_rate: Record<string, { count: number; fallback_count: number }>;
      oldest_screened_at: string | null; newest_screened_at: string | null;
      fallback_total: number;
    }>('/api/v1/admin/breaker-thresholds/health/summary');
  }

  async adminRescreenBreakerThresholds(data: {
    symbols?: string[];
    rates?: number[];
    lookback_days?: number;
    continuation_window?: number;
    min_future_drop_pct?: number;
  }) {
    return this.post<{
      screened_symbols: number; rates: number[];
      results: Record<string, {
        symbol_count: number; fallback_count: number; data_driven_count: number; symbols: string[];
      }>;
    }>('/api/v1/admin/breaker-thresholds/rescreen', data);
  }

  async adminUpdateBreakerResumeConfig(
    symbol: string,
    params: { rate: number; exchange?: string },
    data: {
      resume_mode?: 'ta_confirm' | 'widen_step' | 'trailing_buy';
      recovery_pct?: number;
      widen_multiplier?: number;
    },
  ) {
    const qs = new URLSearchParams();
    qs.set('rate', String(params.rate));
    if (params.exchange) qs.set('exchange', params.exchange);
    return this.patch<BreakerThreshold>(
      `/api/v1/admin/breaker-thresholds/${symbol.toUpperCase()}/resume-config?${qs.toString()}`,
      data,
    );
  }

  // â”€â”€â”€ User-facing: Circuit Breaker Thresholds (read-only) â”€â”€â”€â”€

  async getBreakerThresholds(symbol: string, params?: { rate?: number; exchange?: string }) {
    const qs = new URLSearchParams();
    if (params?.rate !== undefined) qs.set('rate', String(params.rate));
    if (params?.exchange) qs.set('exchange', params.exchange);
    const q = qs.toString();
    return this.get<BreakerThreshold[]>(`/api/v1/breaker-thresholds/${symbol.toUpperCase()}${q ? `?${q}` : ''}`);
  }

  // â”€â”€â”€ Averaging Config â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

  async getAveragingConfig(instanceId: string) {
    return this.get<{
      step_number: number; drop_rate: string; multiple_buy_amount: string;
      take_profit: string; description: string | null;
    }[]>(`/api/v1/trading-instances/${instanceId}/averaging-config`);
  }

  async updateAveragingConfig(instanceId: string, steps: {
    step_number: number; drop_rate: number; multiple_buy_amount?: number;
    take_profit: number; description?: string;
  }[]) {
    return this.put<{
      step_number: number; drop_rate: string; multiple_buy_amount: string;
      take_profit: string; description: string | null;
    }[]>(`/api/v1/trading-instances/${instanceId}/averaging-config`, { steps });
  }

  async resetAveragingConfig(instanceId: string) {
    return this.post<{
      step_number: number; drop_rate: string; multiple_buy_amount: string;
      take_profit: string; description: string | null;
    }[]>(`/api/v1/trading-instances/${instanceId}/averaging-config/reset`, {});
  }

  async getAveragingTemplate() {
    return this.get<{
      total_steps: number; avg_drop_rate: number; max_drop_rate: number;
      min_drop_rate: number; avg_take_profit: number; max_multiplier: number;
      drop_rates: number[]; take_profits: number[]; multipliers: number[];
    }>('/api/v1/trading-instances/averaging-config/template');
  }

  async adminGetAveragingTemplate() {
    return this.get<{
      summary: {
        total_steps: number; avg_drop_rate: number; max_drop_rate: number;
        min_drop_rate: number; avg_take_profit: number; max_multiplier: number;
        drop_rates: number[]; take_profits: number[]; multipliers: number[];
      };
      steps: {
        step_number: number; drop_rate: string; multiple_buy_amount: string; take_profit: string;
      }[];
    }>('/api/v1/admin/averaging-config/template');
  }

  async adminUpdateAveragingTemplate(steps: {
    step_number: number; drop_rate: number; multiple_buy_amount?: number; take_profit: number;
  }[]) {
    return this.put<{
      total_steps: number; drop_rates: number[]; take_profits: number[]; multipliers: number[];
    }>('/api/v1/admin/averaging-config/template', { steps });
  }

  // â”€â”€â”€ Force Buy / Force Sell â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

  async forceBuy(instanceId: string, data: {
    level?: number; price?: number; quantity?: number;
  }) {
    return this.post<{
      order_id: string; level: number; price: string; quantity: string;
      side: string; message: string;
    }>(`/api/v1/trading-instances/${instanceId}/force-buy`, data);
  }

  async forceSell(instanceId: string, data: {
    level?: number; price?: number; quantity?: number;
  }) {
    return this.post<{
      order_ids: string[]; levels_sold: number[]; price: string;
      total_quantity: string; total_value: string; side: string; message: string;
    }>(`/api/v1/trading-instances/${instanceId}/force-sell`, data);
  }

  // â”€â”€â”€ Per-Coin Settings â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

  async updateCoinSettings(instanceId: string, data: {
    avg_enabled?: boolean; non_stop?: boolean; partial_sell?: boolean; formula_mode?: string;
  }) {
    return this.patch<{
      instance_id: string; avg_enabled: boolean; non_stop: boolean;
      partial_sell: boolean; formula_mode: string; updated: boolean;
    }>(`/api/v1/trading-instances/${instanceId}/coin-settings`, data);
  }

  // â”€â”€â”€ Technical Analysis â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

  async getTAConfigs(instanceId: string) {
    return this.get<{
      id: string; indicator: string; time_frame: string; operator: string;
      params: Record<string, number | string> | null; enabled: boolean;
      priority: number; description: string | null;
    }[]>(`/api/v1/trading-instances/${instanceId}/technical-analysis`);
  }

  async updateTAConfigs(instanceId: string, configs: {
    indicator: string; time_frame: string; operator: string;
    params?: Record<string, number | string> | null; enabled: boolean;
    priority: number; description?: string;
  }[]) {
    return this.put<{
      id: string; indicator: string; time_frame: string; operator: string;
      params: Record<string, number | string> | null; enabled: boolean;
      priority: number; description: string | null;
    }[]>(`/api/v1/trading-instances/${instanceId}/technical-analysis`, { configs });
  }

  async toggleTA(instanceId: string, enabled: boolean) {
    return this.post<{
      instance_id: string; ta_enabled: boolean; config_count: number;
    }>(`/api/v1/trading-instances/${instanceId}/technical-analysis/toggle?enabled=${enabled}`, {});
  }

  async getTAIndicators() {
    return this.get<{
      indicator: string; label: string; description: string;
      default_params: Record<string, number>;
    }[]>('/api/v1/trading-instances/technical-analysis/indicators');
  }

  async adminListTATemplates() {
    return this.get<{
      name: string; description: string;
      configs: { indicator: string; time_frame: string; operator: string; params: Record<string, number>; enabled: boolean; priority: number; }[];
    }[]>('/api/v1/admin/technical-analysis/templates');
  }
}

// Lazy singleton â€” the ApiClient (and thus resolveApiBase()) is only
// instantiated on first property access, which happens in the browser
// at runtime where window.location.protocol is available for the
// httpâ†’https upgrade. This avoids the bundler pre-evaluating the
// singleton at build time where window is undefined.
let _apiInstance: ApiClient | null = null;

export const api = new Proxy({} as ApiClient, {
  get(_target, prop, receiver) {
    if (!_apiInstance) {
      _apiInstance = new ApiClient();
    }
    return Reflect.get(_apiInstance, prop, receiver);
  },
  set(_target, prop, value, receiver) {
    if (!_apiInstance) {
      _apiInstance = new ApiClient();
    }
    return Reflect.set(_apiInstance, prop, value, receiver);
  },
});
