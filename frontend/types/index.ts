export interface User {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_verified: boolean;
  role: string;
  subscription_tier: string;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface TradingInstance {
  id: string;
  user_id: string;
  exchange_account_id: string;
  symbol: string;
  status: string;
  strategy: string;
  created_at: string;
  updated_at: string;
}

export interface GridLevel {
  index: number;
  price: number;
  side: string;
  status: 'waiting' | 'open' | 'filled' | 'cancelled' | 'tp_hit';
  quantity: number;
  order_id: string | null;
}

export interface GridState {
  instance_id: string;
  status: string;
  upper_price: number;
  lower_price: number;
  grid_count: number;
  grid_spacing: number;
  investment_per_grid: number;
  current_price: number;
  levels: GridLevel[];
}

export interface Order {
  id: string;
  user_id: string;
  symbol: string;
  side: string;
  type: string;
  quantity: number;
  price: number;
  status: string;
  filled_quantity: number;
  avg_fill_price: number | null;
  created_at: string;
  updated_at: string;
}

export interface Position {
  id: string;
  instance_id: string;
  symbol: string;
  side: string;
  quantity: number;
  entry_price: number;
  current_price: number;
  unrealized_pnl: number;
  realized_pnl: number;
  status: string;
}

export interface PortfolioSummary {
  total_value: number;
  total_pnl: number;
  total_pnl_pct: number;
  total_exposure: number;
  open_positions: number;
  positions: Position[];
}

export interface RiskStatus {
  max_exposure_per_symbol: number;
  max_exposure_per_exchange: number;
  max_open_positions: number;
  max_position_size: number;
  current_exposure: number;
  open_positions: number;
  orders_checked: number;
  orders_allowed: number;
  orders_denied: number;
}

export interface WorkerHealth {
  id: string;
  name: string;
  status: 'running' | 'stopped' | 'paused' | 'error';
  last_heartbeat: string;
  error_count: number;
}

export interface EventBusEvent {
  event_type: string;
  event_id: string;
  timestamp: string;
  data: Record<string, unknown>;
  metadata: Record<string, unknown>;
}

export interface NotificationItem {
  id: string;
  user_id: string;
  channel: string;
  title: string;
  message: string;
  status: string;
  created_at: string;
}

export interface Subscription {
  id: string;
  user_id: string;
  tier: string;
  start_date: string;
  end_date: string;
  is_active: boolean;
  auto_renew: boolean;
}

export interface PlanLimits {
  tier: string;
  max_instances: number;
  max_exchange_accounts: number;
  max_symbols: number;
  max_workers: number;
  feature_flags: string[];
}

export interface Invoice {
  id: string;
  user_id: string;
  amount: number;
  currency: string;
  plan: string;
  status: 'pending' | 'paid' | 'failed' | 'cancelled';
  provider: string | null;
  created_at: string;
  paid_at: string | null;
}

export interface AffiliateStats {
  total_referrals: number;
  total_earnings: number;
  active_referrals: number;
  commission_rate: number;
}

export interface ExchangeAccount {
  id: string;
  user_id: string;
  exchange_name: string;
  is_active: boolean;
  is_testnet: boolean;
  created_at: string;
}

export interface RecoveryStatus {
  instance_id: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  layers: {
    connection: string;
    state: string;
    reconciliation: string;
    persistence: string;
  };
}
