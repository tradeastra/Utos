'use client';

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Sliders, Bitcoin, Wallet, Activity, ArrowRight, ShieldAlert } from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/services/api';
import { StrategyModeSelector } from '@/components/settings/strategy-mode';
import { CoinGroupsSelector } from '@/components/settings/coin-groups';
import { MoneyManagementSection } from '@/components/settings/money-management';
import { TechnicalAnalysisSettings } from '@/components/settings/technical-analysis';
import type {
  BreakerResumeMode,
  BreakerThreshold,
  CoinGroup,
  CoinSelectionLimit,
  ContinuationRate,
  MMCalculationResult,
  MMPreset,
  StrategyMode,
  TAConfig,
  TAIndicatorDescription,
} from '@/types';
import { BREAKER_RESUME_MODES } from '@/types';

// Persisted template — bridges Config tab to Bots creation flow.
// Backend persistence is not yet available; localStorage keeps the
// template so the wizard pre-fills from the user's last saved settings.
interface StrategyTemplate {
  mode: StrategyMode;
  coinGroupId: string;
  capital: number;
  presetType: string;
  taEnabled: boolean;
  taConfigs: TAConfig[];
  symbol: string;
  upperPrice: number;
  lowerPrice: number;
  gridCount: number;
  investmentPerGrid: number;
  // Circuit breaker: continuation rate the user wants to apply.
  // 0.90 = conservative (only break on drops that historically
  // continued 90% of the time). 0.70 = more sensitive.
  continuationRate: ContinuationRate;
  breakerEnabled: boolean;
  // Resume behavior after the breaker triggers.
  resumeMode: BreakerResumeMode;
  recoveryPct: number;  // for trailing_buy mode (e.g. 5 = 5% recovery)
  widenMultiplier: number;  // for widen_step mode (e.g. 2 = 2× wider)
}

const STORAGE_KEY = 'utos.strategy-template.v1';

const DEFAULT_TEMPLATE: StrategyTemplate = {
  mode: 'B',
  coinGroupId: '',
  capital: 0,
  presetType: '',
  taEnabled: false,
  taConfigs: [],
  symbol: 'BTCUSDT',
  upperPrice: 50000,
  lowerPrice: 40000,
  gridCount: 10,
  investmentPerGrid: 10,
  continuationRate: 0.90,
  breakerEnabled: true,
  resumeMode: 'ta_confirm',
  recoveryPct: 5,
  widenMultiplier: 2,
};

function loadTemplate(): StrategyTemplate {
  if (typeof window === 'undefined') return DEFAULT_TEMPLATE;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_TEMPLATE;
    return { ...DEFAULT_TEMPLATE, ...JSON.parse(raw) };
  } catch {
    return DEFAULT_TEMPLATE;
  }
}

function saveTemplate(t: StrategyTemplate) {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(t));
  } catch {
    // ignore quota errors
  }
}

interface ExchangeAccount {
  id: string;
  exchange_name: string;
  is_testnet: boolean;
  is_active: boolean;
  connection_status: string;
}

interface Strategy {
  id: string;
  name: string;
  type: string;
  description: string | null;
}

interface TradingInstance {
  id: string;
  status: string;
  symbol: string;
  total_investment: number;
  start_price?: number | null;
  current_price?: number | null;
  started_at?: string | null;
  stopped_at?: string | null;
  error_message?: string | null;
}

const STEPS = [
  { key: 'mode', label: 'Strategy Mode', icon: Sliders },
  { key: 'coins', label: 'Coins Selection', icon: Bitcoin },
  { key: 'mm', label: 'Money Management', icon: Wallet },
  { key: 'breaker', label: 'Circuit Breaker', icon: ShieldAlert },
  { key: 'ta', label: 'Technical Analysis', icon: Activity },
  { key: 'launch', label: 'Launch Bot', icon: ArrowRight },
] as const;

const CONTINUATION_RATES: { value: ContinuationRate; label: string; desc: string }[] = [
  { value: 0.90, label: 'Fearless', desc: 'Bot tetap averaging selama mungkin. Baru berhenti beli kalau 90% data historis mengatakan harga akan terus jatuh. Paling berani, paling sedikit false alarm.' },
  { value: 0.80, label: 'Balanced', desc: 'Butuh 80% keyakinan dari data historis sebelum bot berhenti beli. Seimbang antara aman dan tetap averaging.' },
  { value: 0.70, label: 'Protective', desc: 'Cukup 70% yakin harga akan jatuh, bot sudah berhenti beli. Paling cepat keluar dari pasar — aman dari kerugian besar, tapi sering berhenti padahal harga cuma turun sebentar.' },
];

interface SetupWizardProps {
  onInstanceCreated?: (instance: TradingInstance) => void;
}

export function SetupWizard({ onInstanceCreated }: SetupWizardProps) {
  const [template, setTemplate] = useState<StrategyTemplate>(DEFAULT_TEMPLATE);
  const [hydrated, setHydrated] = useState(false);

  const [limits, setLimits] = useState<CoinSelectionLimit | null>(null);
  const [coinGroups, setCoinGroups] = useState<CoinGroup[]>([]);
  const [presets, setPresets] = useState<MMPreset[]>([]);
  const [indicators, setIndicators] = useState<TAIndicatorDescription[]>([]);
  const [mmResult, setMMResult] = useState<MMCalculationResult | null>(null);
  const [selectedCoins, setSelectedCoins] = useState<string[]>([]);

  const [accounts, setAccounts] = useState<ExchangeAccount[]>([]);
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [selectedAccount, setSelectedAccount] = useState('');
  const [selectedStrategy, setSelectedStrategy] = useState('');

  // Circuit breaker thresholds for the selected symbol (all rates).
  const [breakerThresholds, setBreakerThresholds] = useState<BreakerThreshold[]>([]);
  const [breakerLoading, setBreakerLoading] = useState(false);
  const [breakerError, setBreakerError] = useState<string | null>(null);

  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);

  // Hydrate template from localStorage on mount
  useEffect(() => {
    setTemplate(loadTemplate());
    setHydrated(true);
  }, []);

  // Persist template whenever it changes (after hydration)
  useEffect(() => {
    if (hydrated) saveTemplate(template);
  }, [template, hydrated]);

  // Load reference data
  const loadReference = useCallback(async () => {
    try {
      const [lim, groups, prs, inds, accs, strat] = await Promise.all([
        api.getCoinSelectionLimits().catch(() => null),
        api.getCoinGroups().catch(() => [] as CoinGroup[]),
        api.getMMPresets().catch(() => [] as MMPreset[]),
        api.getTAIndicators().catch(() => [] as TAIndicatorDescription[]),
        api.listExchangeAccounts().catch(() => [] as ExchangeAccount[]),
        api.listStrategies().catch(() => [] as Strategy[]),
      ]);
      setLimits(lim);
      setCoinGroups(groups || []);
      setPresets(prs || []);
      setIndicators(inds || []);
      setAccounts(accs || []);
      setStrategies(strat || []);

      // Auto-select first preset if template has none
      setTemplate((t) => {
        if (t.presetType && prs?.some((p) => p.preset_type === t.presetType)) return t;
        const first = prs?.[0];
        return first ? { ...t, presetType: first.preset_type } : t;
      });

      // Auto-select first coin group if template has none
      setTemplate((t) => {
        if (t.coinGroupId && groups?.some((g) => g.id === t.coinGroupId)) return t;
        const first = groups?.[0];
        return first ? { ...t, coinGroupId: first.id } : t;
      });
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    loadReference();
  }, [loadReference]);

  // Load breaker thresholds for the first selected coin (all rates).
  // This lets the user see the pre-computed threshold before launching
  // and pick the continuation rate that matches their risk appetite.
  const breakerSymbol = selectedCoins[0] ?? '';
  useEffect(() => {
    if (!breakerSymbol) {
      setBreakerThresholds([]);
      return;
    }
    let cancelled = false;
    (async () => {
      setBreakerLoading(true);
      setBreakerError(null);
      try {
        const rows = await api.getBreakerThresholds(breakerSymbol);
        if (!cancelled) setBreakerThresholds(rows);
      } catch (e: unknown) {
        if (!cancelled) {
          setBreakerThresholds([]);
          setBreakerError(e instanceof Error ? e.message : 'No pre-computed threshold yet');
        }
      } finally {
        if (!cancelled) setBreakerLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [breakerSymbol]);

  // NOTE: Grid spacing auto-calc (ATR-based) was removed — in averaging
  // mode, grid levels are derived from market price + per-step drop rates
  // at runtime (see process_manager._wire_grid_and_market). The frontend
  // no longer needs to compute grid_count or spacing.

  // When coin group changes, reset selected coins
  useEffect(() => {
    setSelectedCoins([]);
  }, [template.coinGroupId]);

  // Recompute MM when relevant inputs change (lazy — only if user already calculated once)
  async function recalculateMM() {
    const selected = presets.find((p) => p.preset_type === template.presetType);
    if (!selected || !template.capital) return;
    const group = coinGroups.find((g) => g.id === template.coinGroupId);
    if (!group?.name) {
      setMMResult(null);
      return;
    }
    try {
      // Pass num_coins = number of coins the user actually selected, so
      // capital is allocated across only the chosen coins (e.g. 1 coin
      // from Top 3 → larger per-layer buy amount, not split across 3).
      const result = await api.calculateMM(
        selected.preset_type,
        template.capital,
        group.name,
        undefined,
        selectedCoins.length > 0 ? selectedCoins.length : undefined,
      );
      setMMResult(result);
      // Sync investment_per_grid from MM result — used when auto-creating
      // the grid profile (averaging mode ignores upper/lower/grid_count).
      if (result.buy_amount) {
        patchTemplate({ investmentPerGrid: Number(result.buy_amount) });
      }
    } catch {
      setMMResult(null);
    }
  }

  // Auto-recompute MM when capital, preset, coin group, or selected coins change
  useEffect(() => {
    if (mmResult || template.capital > 0) recalculateMM();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [template.capital, template.presetType, template.coinGroupId, selectedCoins]);

  function patchTemplate(p: Partial<StrategyTemplate>) {
    setTemplate((t) => ({ ...t, ...p }));
  }

  async function handleCreateGridProfile(coin: string): Promise<string | null> {
    try {
      // Auto-trading mode: grid levels are generated from the market price
      // + averaging steps at runtime (see process_manager._wire_grid_and_market).
      // The grid profile here only stores investment_per_grid; upper/lower/
      // grid_count are placeholders that are IGNORED in averaging mode.
      const steps = mmResult?.steps ?? template.gridCount;
      const profile = await api.createGridProfile({
        name: `${coin} auto (avg ${steps} steps)`,
        upper_price: 100000,  // placeholder — ignored in averaging mode
        lower_price: 1,       // placeholder — ignored in averaging mode
        grid_count: steps,
        investment_per_grid: template.investmentPerGrid,
      });
      return profile.id;
    } catch (err) {
      setMsg({ type: 'error', text: err instanceof Error ? err.message : 'Failed to create grid profile' });
      return null;
    }
  }

  async function handleLaunch() {
    if (!selectedAccount) {
      setMsg({ type: 'error', text: 'Select an exchange account in the Launch section below.' });
      if (typeof window !== 'undefined') {
        document.getElementById('setup-launch')?.scrollIntoView({ behavior: 'smooth' });
      }
      return;
    }
    if (!selectedStrategy) {
      setMsg({ type: 'error', text: 'Select a strategy in the Launch section below.' });
      if (typeof window !== 'undefined') {
        document.getElementById('setup-launch')?.scrollIntoView({ behavior: 'smooth' });
      }
      return;
    }
    if (selectedCoins.length === 0) {
      setMsg({ type: 'error', text: 'Select at least one coin in the Coins Selection section.' });
      if (typeof window !== 'undefined') {
        document.getElementById('setup-coins')?.scrollIntoView({ behavior: 'smooth' });
      }
      return;
    }
    setBusy(true);
    setMsg(null);
    try {
      // Create one bot per selected coin. Each coin gets its own grid profile
      // (investment_per_grid from MM calculation; upper/lower are placeholders
      // ignored in averaging mode — grid levels are derived from market price).
      const created: string[] = [];
      const failed: string[] = [];
      for (const coin of selectedCoins) {
        try {
          const gridProfileId = await handleCreateGridProfile(coin);
          if (!gridProfileId) {
            failed.push(coin.toUpperCase());
            continue;
          }

          const instance = await api.createTradingInstance({
            exchange_account_id: selectedAccount,
            strategy_id: selectedStrategy,
            grid_profile_id: gridProfileId,
            symbol: coin.toUpperCase(),
            strategy_mode: template.mode,
            selected_coins: selectedCoins,
            continuation_rate: template.breakerEnabled ? template.continuationRate : undefined,
            breaker_enabled: template.breakerEnabled,
            auto_start: true,
          });

          // Push TA configs to the new instance if enabled
          if (template.taEnabled && template.taConfigs.length > 0) {
            try {
              await api.updateTAConfigs(instance.id, template.taConfigs.map((c) => ({
                indicator: c.indicator,
                time_frame: c.time_frame,
                operator: c.operator,
                params: c.params,
                enabled: c.enabled && template.taEnabled,
                priority: c.priority,
                description: c.description ?? undefined,
              })));
            } catch {
              // Non-fatal — bot can still run without TA gate
            }
          }
          created.push(coin.toUpperCase());
        } catch (err) {
          failed.push(coin.toUpperCase());
          console.error(`Failed to create bot for ${coin}:`, err);
        }
      }

      if (created.length > 0 && failed.length === 0) {
        setMsg({
          type: 'success',
          text: `Created ${created.length} bot${created.length > 1 ? 's' : ''}: ${created.join(', ')}. Go to the Bots list to Prepare & Start.`,
        });
      } else if (created.length > 0 && failed.length > 0) {
        setMsg({
          type: 'info',
          text: `Created ${created.length} bots (${created.join(', ')}). Failed: ${failed.join(', ')}.`,
        });
      } else {
        setMsg({ type: 'error', text: `Failed to create all ${failed.length} bots: ${failed.join(', ')}` });
      }
      if (created.length > 0) onInstanceCreated?.({} as TradingInstance);
    } catch (err) {
      setMsg({ type: 'error', text: err instanceof Error ? err.message : 'Failed to create bot' });
    } finally {
      setBusy(false);
    }
  }

  const filteredPresets = presets.filter((p) => {
    // MM30 only allowed for Top 3 / Top 5 (per business rule in INTERFACE_REFERENCE)
    if (p.preset_type === 'mm30') {
      const group = coinGroups.find((g) => g.id === template.coinGroupId);
      if (!group) return true;
      const name = group.name.toLowerCase();
      return name.includes('top 3') || name.includes('top 5') || group.max_coins <= 5;
    }
    return true;
  });

  const selectedCoinGroup = coinGroups.find((g) => g.id === template.coinGroupId);
  const selectedCoinGroupName = selectedCoinGroup?.name;

  if (!hydrated) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-violet-500 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Section quick-nav (anchor scroll, not page switch) */}
      <div className="sticky top-0 z-10 -mx-4 flex items-center gap-1 overflow-x-auto bg-background/80 px-4 py-2 backdrop-blur md:mx-0 md:rounded-lg md:border md:border-border">
        {STEPS.map((s) => {
          const Icon = s.icon;
          return (
            <a
              key={s.key}
              href={`#setup-${s.key}`}
              className="flex shrink-0 items-center gap-2 rounded-full bg-slate-100 px-3 py-1.5 text-xs font-medium text-muted-foreground transition hover:bg-violet-500/10 hover:text-violet-600 dark:bg-muted"
            >
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-muted-foreground/20">
                <Icon className="h-3 w-3" />
              </span>
              <span className="hidden sm:inline">{s.label}</span>
            </a>
          );
        })}
      </div>

      {msg && (
        <div className={cn(
          'rounded-lg p-3 text-sm',
          msg.type === 'success' ? 'bg-green-500/10 text-green-600 dark:text-green-400'
            : msg.type === 'error' ? 'bg-red-500/10 text-red-600 dark:text-red-400'
              : 'bg-amber-500/10 text-amber-600 dark:text-amber-400',
        )}>
          {msg.text}
        </div>
      )}

      {/* Section 1: Strategy Mode */}
      <Card glass id="setup-mode" className="scroll-mt-20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sliders className="h-5 w-5 text-violet-500" />
            Strategy Mode
          </CardTitle>
          <CardDescription>Risk profile & daily range for the bot</CardDescription>
        </CardHeader>
        <CardContent>
          <StrategyModeSelector
            value={template.mode}
            onChange={(mode) => patchTemplate({ mode })}
          />
          <p className="mt-3 text-xs text-muted-foreground">
            *Result may vary due to market fluctuations.
          </p>
        </CardContent>
      </Card>

      {/* Section 2: Coins Selection — pick a group then select specific coins */}
      <Card glass id="setup-coins" className="scroll-mt-20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bitcoin className="h-5 w-5 text-violet-500" />
            Coins Selection
          </CardTitle>
          <CardDescription>
            {limits
              ? `${limits.max_coin_selection >= 999 ? 'Unlimited' : limits.max_coin_selection} coins max — ${limits.tier} tier. Pick a group, then select which coins to trade.`
              : 'Pick a group, then select which coins to trade'}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {coinGroups.length === 0 ? (
            <p className="text-sm text-muted-foreground">No coin groups available. Contact admin or check backend connection.</p>
          ) : (
            <>
              {/* Step 2a: Pick a coin group */}
              <CoinGroupsSelector
                groups={coinGroups.map((g) => ({
                  id: g.id,
                  name: g.name,
                  description: g.description,
                  count: g.coins.length,
                }))}
                selected={template.coinGroupId}
                onChange={(id) => {
                  patchTemplate({ coinGroupId: id });
                  setSelectedCoins([]);  // reset selection when group changes
                }}
                limit={limits?.max_coin_selection}
              />

              {/* Step 2b: Select specific coins from the group */}
              {template.coinGroupId && (() => {
                const group = coinGroups.find((g) => g.id === template.coinGroupId);
                if (!group || group.coins.length === 0) {
                  return (
                    <div className="rounded-md bg-muted/40 p-3 text-xs text-muted-foreground">
                      This group has no pre-defined coins. Coins will be resolved at runtime.
                    </div>
                  );
                }
                const maxSelect = limits?.max_coin_selection ?? group.coins.length;
                const toggleCoin = (coin: string) => {
                  setSelectedCoins((prev) => {
                    if (prev.includes(coin)) return prev.filter((c) => c !== coin);
                    if (prev.length >= maxSelect) return prev;
                    return [...prev, coin];
                  });
                };
                return (
                  <div>
                    <label className="text-sm font-medium">
                      Select Coins ({selectedCoins.length}/{Math.min(maxSelect, group.coins.length)})
                    </label>
                    <p className="text-xs text-muted-foreground mb-2">
                      One bot will be created per selected coin. Max {maxSelect >= 999 ? 'unlimited' : maxSelect} coins.
                      Fewer coins = larger buy amount per layer.
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {group.coins.map((coin) => {
                        const selected = selectedCoins.includes(coin);
                        return (
                          <button
                            key={coin}
                            onClick={() => toggleCoin(coin)}
                            className={cn(
                              'rounded-lg border px-3 py-1.5 text-sm font-medium transition',
                              selected
                                ? 'border-violet-500 bg-violet-500/10 text-violet-600 dark:text-violet-400'
                                : 'border-border bg-card hover:bg-accent',
                            )}
                          >
                            {coin}
                          </button>
                        );
                      })}
                    </div>
                    {selectedCoins.length > 0 && (
                      <button
                        onClick={() => setSelectedCoins([])}
                        className="mt-2 text-xs text-muted-foreground hover:text-foreground"
                      >
                        Clear selection
                      </button>
                    )}
                  </div>
                );
              })()}
            </>
          )}
        </CardContent>
      </Card>

      {/* Section 3: Money Management */}
      <Card glass id="setup-mm" className="scroll-mt-20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Wallet className="h-5 w-5 text-violet-500" />
            Money Management
          </CardTitle>
          <CardDescription>Capital allocation & buy amount per grid</CardDescription>
        </CardHeader>
        <CardContent>
          <MoneyManagementSection
            presets={filteredPresets}
            capital={template.capital}
            selectedPreset={template.presetType}
            coinGroupName={selectedCoinGroupName}
            onCapitalChange={(c) => patchTemplate({ capital: c > 0 ? c : 0 })}
            onPresetChange={(presetType) => patchTemplate({ presetType })}
            onCalculation={(result) => setMMResult(result)}
          />
          {mmResult && (
            <div className="mt-4 rounded-lg bg-blue-500/10 p-3 text-xs text-blue-600 dark:text-blue-400">
              <strong>Allocation preview:</strong> {mmResult.max_coins} coins × {mmResult.steps} layers × ${Number(mmResult.buy_amount).toFixed(2)}/layer
              {' → '}≈ ${(mmResult.max_coins * mmResult.steps * Number(mmResult.buy_amount)).toFixed(2)} max deployed.
              {' '}Min 24h volume filter: ${Number(mmResult.min_volume_filter).toLocaleString()}.
            </div>
          )}
          <p className="mt-3 text-xs text-muted-foreground">
            Tip: MM30 is restricted to small coin groups (Top 3 / Top 5). Each coin receives {`steps`} DCA layers, so capital must cover coins × layers × $15 min per layer.
          </p>
        </CardContent>
      </Card>

      {/* Section 4: Circuit Breaker (grid levels auto-generated from market price) */}
      <Card glass id="setup-breaker" className="scroll-mt-20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ShieldAlert className="h-5 w-5 text-violet-500" />
            Daily Drop Circuit Breaker
          </CardTitle>
          <CardDescription>
            Pause buy orders if a critical daily drop is reached, then resume only on a 15m TA reversal signal.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={template.breakerEnabled}
              onChange={(e) => patchTemplate({ breakerEnabled: e.target.checked })}
              className="h-4 w-4"
            />
            <span className="text-sm font-medium">Enable circuit breaker for this bot</span>
          </label>

          {template.breakerEnabled && (
            <>
              <div>
                <label className="text-sm font-medium">Continuation Rate</label>
                <p className="text-xs text-muted-foreground mb-2">
                  Bot menghitung dari data historis: berapa persen drop yang berlanjut turun. Pilih persentase yang lebih tinggi = bot lebih yakin dulu sebelum berhenti beli.
                </p>
                <div className="grid gap-2">
                  {CONTINUATION_RATES.map((r) => (
                    <label
                      key={r.value}
                      className={cn(
                        'flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition-colors',
                        template.continuationRate === r.value
                          ? 'border-violet-500 bg-violet-500/10'
                          : 'border-border hover:bg-muted/40',
                      )}
                    >
                      <input
                        type="radio"
                        name="continuationRate"
                        value={r.value}
                        checked={template.continuationRate === r.value}
                        onChange={() => patchTemplate({ continuationRate: r.value })}
                        className="mt-1"
                      />
                      <div>
                        <div className="text-sm font-medium">{r.label}</div>
                        <div className="text-xs text-muted-foreground">{r.desc}</div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              {/* Threshold preview table for the selected symbol */}
              <div className="rounded-lg border border-border p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium">
                    Pre-computed thresholds for {breakerSymbol.toUpperCase()}
                  </span>
                  {breakerLoading && <span className="text-xs text-muted-foreground">Loading…</span>}
                </div>
                {breakerError ? (
                  <div className="rounded-md bg-amber-500/10 p-2 text-xs text-amber-700 dark:text-amber-400">
                    {breakerError}. The bot will use a conservative fallback threshold until screening runs.
                  </div>
                ) : breakerThresholds.length === 0 ? (
                  <div className="text-xs text-muted-foreground">No thresholds available yet.</div>
                ) : (
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-left text-muted-foreground">
                        <th className="pb-1 font-medium">Rate</th>
                        <th className="pb-1 font-medium">Threshold</th>
                        <th className="pb-1 font-medium">Source</th>
                        <th className="pb-1 font-medium">Candles</th>
                        <th className="pb-1 font-medium">Screened</th>
                      </tr>
                    </thead>
                    <tbody>
                      {breakerThresholds.map((t) => (
                        <tr
                          key={t.id}
                          className={cn(
                            'border-t border-border',
                            template.continuationRate === t.min_continuation_rate && 'bg-violet-500/5',
                          )}
                        >
                          <td className="py-1.5">{(t.min_continuation_rate * 100).toFixed(0)}%</td>
                          <td className="py-1.5 font-semibold">{t.threshold_pct.toFixed(2)}%</td>
                          <td className="py-1.5">
                            {t.used_fallback ? (
                              <span className="text-amber-600 dark:text-amber-400">fallback</span>
                            ) : (
                              <span className="text-green-600 dark:text-green-400">data-driven</span>
                            )}
                          </td>
                          <td className="py-1.5">{t.candle_count}</td>
                          <td className="py-1.5 text-muted-foreground">
                            {t.screened_at ? new Date(t.screened_at).toLocaleDateString() : '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
                {(() => {
                  const selected = breakerThresholds.find(
                    (t) => t.min_continuation_rate === template.continuationRate,
                  );
                  if (!selected) return null;
                  return (
                    <div className="mt-3 rounded-md bg-blue-500/10 p-2 text-xs text-blue-700 dark:text-blue-300">
                      <strong>Selected:</strong> {template.continuationRate * 100}% rate → buys pause if {breakerSymbol.toUpperCase()} drops <strong>{selected.threshold_pct.toFixed(2)}%</strong> intraday from the day&apos;s open. {selected.used_fallback ? '(Fallback value — ask admin to run screening.)' : `(From ${selected.candle_count} daily candles, screened ${selected.screened_at ? new Date(selected.screened_at).toLocaleDateString() : 'recently'}.)`}
                    </div>
                  );
                })()}

                {/* Resume mode — what happens AFTER the breaker triggers */}
                <div className="mt-4">
                  <label className="text-sm font-medium">Resume Mode</label>
                  <p className="text-xs text-muted-foreground mb-2">
                    What should the bot do <em>after</em> the breaker triggers?
                    This controls when buying resumes.
                  </p>
                  <div className="grid gap-2">
                    {BREAKER_RESUME_MODES.map((m) => (
                      <label
                        key={m.value}
                        className={cn(
                          'flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition-colors',
                          template.resumeMode === m.value
                            ? 'border-violet-500 bg-violet-500/10'
                            : 'border-border hover:bg-muted/40',
                        )}
                      >
                        <input
                          type="radio"
                          name="resumeMode"
                          value={m.value}
                          checked={template.resumeMode === m.value}
                          onChange={() => patchTemplate({ resumeMode: m.value })}
                          className="mt-1"
                        />
                        <div>
                          <div className="text-sm font-medium">{m.label}</div>
                          <div className="text-xs text-muted-foreground">{m.desc}</div>
                        </div>
                      </label>
                    ))}
                  </div>

                  {/* Conditional parameter for trailing_buy mode */}
                  {template.resumeMode === 'trailing_buy' && (
                    <div className="mt-3 rounded-lg border border-border p-3">
                      <label className="text-sm font-medium">Recovery %</label>
                      <p className="text-xs text-muted-foreground mb-2">
                        Resume buying when price recovers this percentage from
                        the intraday low. Lower = resume sooner (more
                        aggressive). Higher = wait for a stronger bounce.
                      </p>
                      <div className="flex items-center gap-3">
                        <input
                          type="range"
                          min={1}
                          max={20}
                          step={0.5}
                          value={template.recoveryPct}
                          onChange={(e) =>
                            patchTemplate({ recoveryPct: parseFloat(e.target.value) })
                          }
                          className="flex-1"
                        />
                        <span className="w-16 text-right text-sm font-semibold">
                          {template.recoveryPct.toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Conditional parameter for widen_step mode */}
                  {template.resumeMode === 'widen_step' && (
                    <div className="mt-3 rounded-lg border border-border p-3">
                      <label className="text-sm font-medium">Widen Multiplier</label>
                      <p className="text-xs text-muted-foreground mb-2">
                        Multiply the grid spacing by this factor while the
                        breaker is active. 2 = buy at every 2nd level (2×
                        wider). 3 = every 3rd level. Higher = slower
                        accumulation.
                      </p>
                      <div className="flex items-center gap-3">
                        <input
                          type="range"
                          min={1}
                          max={5}
                          step={0.5}
                          value={template.widenMultiplier}
                          onChange={(e) =>
                            patchTemplate({
                              widenMultiplier: parseFloat(e.target.value),
                            })
                          }
                          className="flex-1"
                        />
                        <span className="w-16 text-right text-sm font-semibold">
                          {template.widenMultiplier.toFixed(1)}×
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Section 6: Technical Analysis */}
      <Card glass id="setup-ta" className="scroll-mt-20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-violet-500" />
            Technical Analysis (Optional)
          </CardTitle>
          <CardDescription>Gate buy orders with indicator conditions</CardDescription>
        </CardHeader>
        <CardContent>
          <TechnicalAnalysisSettings
            indicators={indicators}
            configs={template.taConfigs}
            enabled={template.taEnabled}
            onEnabledChange={(taEnabled) => patchTemplate({ taEnabled })}
            onConfigsChange={(taConfigs) => patchTemplate({ taConfigs })}
          />
          <p className="mt-3 text-xs text-muted-foreground">
            When enabled, TA configs will be pushed to the bot automatically on launch.
          </p>
        </CardContent>
      </Card>

      {/* Section 7: Launch — Exchange + Strategy + Create */}
      <div id="setup-launch" className="scroll-mt-20 space-y-6">
        <Card glass>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ArrowRight className="h-5 w-5 text-violet-500" />
              Select Exchange Account
            </CardTitle>
            <CardDescription>Choose your saved exchange account</CardDescription>
          </CardHeader>
          <CardContent>
            {accounts.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No exchange accounts found. Add one in Settings → Exchanges first.
              </p>
            ) : (
              <div className="space-y-2">
                {accounts.map((acc) => (
                  <label key={acc.id} className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="radio"
                      name="account"
                      value={acc.id}
                      checked={selectedAccount === acc.id}
                      onChange={(e) => setSelectedAccount(e.target.value)}
                    />
                    <span className="font-medium capitalize">{acc.exchange_name}</span>
                    {acc.is_testnet && <Badge variant="warning">testnet</Badge>}
                    <Badge variant={acc.is_active ? 'success' : 'secondary'}>{acc.connection_status}</Badge>
                  </label>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card glass>
          <CardHeader>
            <CardTitle>Select Strategy Algorithm</CardTitle>
            <CardDescription>Trading strategy implementation</CardDescription>
          </CardHeader>
          <CardContent>
            {strategies.length === 0 ? (
              <p className="text-sm text-muted-foreground">Loading strategies...</p>
            ) : (
              <div className="space-y-2">
                {strategies.map((s) => (
                  <label key={s.id} className="flex items-start gap-3 cursor-pointer">
                    <input
                      type="radio"
                      name="strategy"
                      value={s.id}
                      checked={selectedStrategy === s.id}
                      onChange={(e) => setSelectedStrategy(e.target.value)}
                    />
                    <div>
                      <span className="font-medium">{s.name}</span>
                      {s.description && <p className="text-sm text-muted-foreground">{s.description}</p>}
                    </div>
                  </label>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card glass>
          <CardHeader>
            <CardTitle>Launch Summary</CardTitle>
            <CardDescription>Review before creating the bot</CardDescription>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-1 gap-2 text-sm sm:grid-cols-2">
              <div className="flex justify-between rounded-md bg-muted/40 px-3 py-2">
                <dt className="text-muted-foreground">Strategy Mode</dt>
                <dd className="font-medium">{template.mode}</dd>
              </div>
              <div className="flex justify-between rounded-md bg-muted/40 px-3 py-2">
                <dt className="text-muted-foreground">Coin Group</dt>
                <dd className="font-medium">
                  {coinGroups.find((g) => g.id === template.coinGroupId)?.name ?? '—'}
                </dd>
              </div>
              <div className="flex justify-between rounded-md bg-muted/40 px-3 py-2">
                <dt className="text-muted-foreground">Capital</dt>
                <dd className="font-medium">${template.capital || '—'}</dd>
              </div>
              <div className="flex justify-between rounded-md bg-muted/40 px-3 py-2">
                <dt className="text-muted-foreground">MM Preset</dt>
                <dd className="font-medium">
                  {presets.find((p) => p.preset_type === template.presetType)?.name ?? '—'}
                </dd>
              </div>
              <div className="flex justify-between rounded-md bg-muted/40 px-3 py-2">
                <dt className="text-muted-foreground">Selected Coins</dt>
                <dd className="font-medium">
                  {selectedCoins.length > 0
                    ? `${selectedCoins.length} coin${selectedCoins.length > 1 ? 's' : ''}: ${selectedCoins.join(', ')}`
                    : '— (select in Coins Selection)'}
                </dd>
              </div>
              <div className="flex justify-between rounded-md bg-muted/40 px-3 py-2">
                <dt className="text-muted-foreground">Averaging Steps</dt>
                <dd className="font-medium">
                  {mmResult ? `${mmResult.steps} steps` : '— (calculate MM first)'}
                </dd>
              </div>
              <div className="flex justify-between rounded-md bg-muted/40 px-3 py-2">
                <dt className="text-muted-foreground">Buy Amount/Layer</dt>
                <dd className="font-medium">
                  {mmResult ? `$${Number(mmResult.buy_amount).toFixed(2)}` : '— (calculate MM first)'}
                </dd>
              </div>
              <div className="flex justify-between rounded-md bg-muted/40 px-3 py-2">
                <dt className="text-muted-foreground">Entry Mode</dt>
                <dd className="font-medium">Auto (market price + averaging)</dd>
              </div>
              <div className="flex justify-between rounded-md bg-muted/40 px-3 py-2">
                <dt className="text-muted-foreground">TA Gate</dt>
                <dd className="font-medium">
                  {template.taEnabled ? `On (${template.taConfigs.length} rule${template.taConfigs.length !== 1 ? 's' : ''})` : 'Off'}
                </dd>
              </div>
            </dl>
            <Button
              onClick={handleLaunch}
              disabled={busy || !selectedAccount || !selectedStrategy || selectedCoins.length === 0}
              className="mt-4 w-full"
            >
              {busy ? 'Creating...' : 'Create Trading Bot'}
            </Button>
            <p className="mt-2 text-center text-xs text-muted-foreground">
              Bot enters at current market price and averages down automatically.
              {' '}Status: <Badge variant="secondary">created</Badge> → auto prepare → <Badge variant="success">running</Badge>.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
