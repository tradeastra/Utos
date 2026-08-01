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

export type StrategyMode = 'A' | 'B' | 'C' | 'D' | 'U';

export interface StrategyModeInfo {
  mode: StrategyMode;
  label: string;
  tpRange: string;
  riskLevel: string;
}

export interface CoinGroup {
  id: string;
  name: string;
  description: string | null;
  max_coins: number;
  coins: string[];
  is_builtin: boolean;
  is_active: boolean;
}

export interface TickerItem {
  symbol: string;
  last: string;
  volume: string;
  quote_volume: string | null;
}

export interface CoinSelectionLimit {
  tier: string;
  max_coin_selection: number;
  current_selection: number;
}

export type MMPresetType = 'mm30' | 'mm50' | 'mm70' | 'custom';

export interface MMPreset {
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
}

export interface MMCalculationResult {
  buy_amount: string;
  max_coins: number;
  steps: number;
  capital: string;
  preset_type: string;
  min_volume_filter: string;
}

export interface AveragingStep {
  step_number: number;
  drop_rate: string;
  multiple_buy_amount: string;
  take_profit: string;
  description: string | null;
}

export interface AveragingTemplateSummary {
  total_steps: number;
  avg_drop_rate: number;
  max_drop_rate: number;
  min_drop_rate: number;
  avg_take_profit: number;
  max_multiplier: number;
  drop_rates: number[];
  take_profits: number[];
  multipliers: number[];
}

export interface ForceBuyResult {
  order_id: string;
  level: number;
  price: string;
  quantity: string;
  side: 'buy';
  message: string;
}

export interface ForceSellResult {
  order_ids: string[];
  levels_sold: number[];
  price: string;
  total_quantity: string;
  total_value: string;
  side: 'sell';
  message: string;
}

export interface TAConfig {
  id?: string;
  indicator: string;
  time_frame: string;
  operator: string;
  params: Record<string, number | string> | null;
  enabled: boolean;
  priority: number;
  description: string | null;
}

export interface TAIndicatorDescription {
  indicator: string;
  label: string;
  description: string;
  default_params: Record<string, number>;
}

export interface TATemplate {
  name: string;
  description: string;
  configs: TAConfig[];
}

// ─── Circuit Breaker Thresholds ────────────────────────────────────

export interface BreakerThreshold {
  id: string;
  exchange: string;
  symbol: string;
  min_continuation_rate: number;
  threshold_pct: number;
  continuation_window: number;
  min_future_drop_pct: number;
  lookback_days: number;
  candle_count: number;
  used_fallback: boolean;
  // Resume behavior after the breaker triggers.
  resume_mode: 'ta_confirm' | 'widen_step' | 'trailing_buy';
  recovery_pct: number;  // for trailing_buy mode
  widen_multiplier: number;  // for widen_step mode
  note: string | null;
  screened_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

// Resume mode labels for UI display.
export type BreakerResumeMode = 'ta_confirm' | 'widen_step' | 'trailing_buy';

export const BREAKER_RESUME_MODES: {
  value: BreakerResumeMode;
  label: string;
  desc: string;
}[] = [
  {
    value: 'ta_confirm',
    label: 'TA Confirm — wait for reversal',
    desc: '',
  },
  {
    value: 'widen_step',
    label: 'Widen Step — keep buying, slower',
    desc: '',
  },
  {
    value: 'trailing_buy',
    label: 'Trailing Buy — resume on recovery',
    desc: '',
  },
];

// ─── Grid Spacing (ATR-based auto-calculation) ──────────────────────

export interface GridSpacingResult {
  symbol: string;
  exchange: string;
  mode: string;
  tp_range_pct: number;
  atr_pct: number;
  avg_atr_pct: number;
  adaptive_factor: number;
  spacing_pct: number;
  used_fallback: boolean;
  candle_count: number;
}

export interface BreakerHealthSummary {
  total_rows: number;
  distinct_symbols: number;
  per_rate: Record<string, { count: number; fallback_count: number }>;
  oldest_screened_at: string | null;
  newest_screened_at: string | null;
  fallback_total: number;
}

export interface BreakerRescreenResult {
  screened_symbols: number;
  rates: number[];
  results: Record<string, {
    symbol_count: number;
    fallback_count: number;
    data_driven_count: number;
    symbols: string[];
  }>;
}

export type ContinuationRate = 0.70 | 0.80 | 0.90;
