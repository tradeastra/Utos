'use client';

import { useEffect, useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Coins, Wallet, CandlestickChart, Trash2, Power, ShieldAlert, RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/services/api';

interface AdminCoinGroup {
  id: string; name: string; description: string | null; max_coins: number;
  coins: string[]; is_builtin: boolean; is_active: boolean; user_id: string | null;
}

interface AdminMMPreset {
  id: string; name: string; preset_type: string; steps: number; min_capital: string;
  max_capital: string | null; description: string | null; allowed_coin_groups: string[];
  is_builtin: boolean; is_active: boolean; user_id: string | null;
}

interface AdminStrategyMode {
  mode: string; label: string; tp_range_min: number; tp_range_max: number; risk_level: string;
}

interface AdminBreakerThreshold {
  id: string; exchange: string; symbol: string; min_continuation_rate: number;
  threshold_pct: number; continuation_window: number; min_future_drop_pct: number;
  lookback_days: number; candle_count: number; used_fallback: boolean;
  resume_mode: 'ta_confirm' | 'widen_step' | 'trailing_buy';
  recovery_pct: number; widen_multiplier: number;
  note: string | null; screened_at: string | null; created_at: string | null;
  updated_at: string | null;
}

interface AdminBreakerHealth {
  total_rows: number; distinct_symbols: number;
  per_rate: Record<string, { count: number; fallback_count: number }>;
  oldest_screened_at: string | null; newest_screened_at: string | null;
  fallback_total: number;
}

type Tab = 'coin-groups' | 'mm-presets' | 'strategy-modes' | 'breaker-thresholds';

export default function AdminSettingsPage() {
  const [tab, setTab] = useState<Tab>('coin-groups');
  const [coinGroups, setCoinGroups] = useState<AdminCoinGroup[]>([]);
  const [mmPresets, setMMPresets] = useState<AdminMMPreset[]>([]);
  const [strategyModes, setStrategyModes] = useState<AdminStrategyMode[]>([]);
  const [strategyModeDrafts, setStrategyModeDrafts] = useState<Record<string, AdminStrategyMode>>({});
  const [strategyModeSaving, setStrategyModeSaving] = useState<Record<string, boolean>>({});
  const [strategyModeMsg, setStrategyModeMsg] = useState<Record<string, { type: 'success' | 'error'; text: string }>>({});
  const [breakerThresholds, setBreakerThresholds] = useState<AdminBreakerThreshold[]>([]);
  const [breakerHealth, setBreakerHealth] = useState<AdminBreakerHealth | null>(null);
  const [breakerRateFilter, setBreakerRateFilter] = useState<number | 'all'>('all');
  const [breakerRescreening, setBreakerRescreening] = useState(false);
  const [breakerMsg, setBreakerMsg] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [groups, presets, modes] = await Promise.all([
        api.adminListCoinGroups(),
        api.adminListMMPresets(),
        api.adminListStrategyModes(),
      ]);
      setCoinGroups(groups);
      setMMPresets(presets);
      setStrategyModes(modes);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load admin data');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadBreakerData = useCallback(async () => {
    try {
      const [thresholds, health] = await Promise.all([
        api.adminListBreakerThresholds(
          breakerRateFilter !== 'all' ? { rate: breakerRateFilter } : undefined,
        ),
        api.adminBreakerHealthSummary(),
      ]);
      setBreakerThresholds(thresholds as AdminBreakerThreshold[]);
      setBreakerHealth(health);
    } catch (e: unknown) {
      setBreakerMsg({
        type: 'error',
        text: e instanceof Error ? e.message : 'Failed to load breaker thresholds',
      });
    }
  }, [breakerRateFilter]);

  useEffect(() => { loadAll(); }, [loadAll]);

  useEffect(() => {
    if (tab === 'breaker-thresholds') loadBreakerData();
  }, [tab, loadBreakerData]);

  const handleRescreenBreakers = async () => {
    if (!confirm(
      'Re-screen all breaker thresholds? This fetches 365 daily candles for every symbol and may take 1-2 minutes. Existing thresholds will be updated.',
    )) return;
    setBreakerRescreening(true);
    setBreakerMsg({ type: 'info', text: 'Screening in progress… (this may take 1-2 minutes)' });
    try {
      const result = await api.adminRescreenBreakerThresholds({
        rates: [0.70, 0.80, 0.90],
      });
      const totalDataDriven = Object.values(result.results).reduce(
        (sum, r) => sum + r.data_driven_count, 0,
      );
      const totalFallback = Object.values(result.results).reduce(
        (sum, r) => sum + r.fallback_count, 0,
      );
      setBreakerMsg({
        type: 'success',
        text: `Re-screened ${result.screened_symbols} symbols × ${result.rates.length} rates. ${totalDataDriven} data-driven, ${totalFallback} fallback.`,
      });
      await loadBreakerData();
    } catch (e: unknown) {
      setBreakerMsg({
        type: 'error',
        text: e instanceof Error ? e.message : 'Re-screen failed',
      });
    } finally {
      setBreakerRescreening(false);
    }
  };

  const toggleCoinGroupActive = async (g: AdminCoinGroup) => {
    try {
      await api.adminUpdateCoinGroup(g.id, { is_active: !g.is_active });
      setCoinGroups(coinGroups.map(x => x.id === g.id ? { ...x, is_active: !x.is_active } : x));
    } catch {}
  };

  const deleteCoinGroup = async (g: AdminCoinGroup) => {
    if (!confirm(`Delete "${g.name}"? This cannot be undone.`)) return;
    try {
      await api.adminDeleteCoinGroup(g.id);
      setCoinGroups(coinGroups.filter(x => x.id !== g.id));
    } catch {}
  };

  const updateCoinGroup = async (id: string, field: keyof AdminCoinGroup, value: string | number | string[]) => {
    try {
      const data: Record<string, string | number | string[]> = { [field]: value };
      await api.adminUpdateCoinGroup(id, data);
      setCoinGroups(coinGroups.map(g => g.id === id ? { ...g, [field]: value } : g));
    } catch {}
  };

  const toggleMMPresetActive = async (p: AdminMMPreset) => {
    try {
      await api.adminUpdateMMPreset(p.id, { is_active: !p.is_active });
      setMMPresets(mmPresets.map(x => x.id === p.id ? { ...x, is_active: !x.is_active } : x));
    } catch {}
  };

  const deleteMMPreset = async (p: AdminMMPreset) => {
    if (!confirm(`Delete "${p.name}"? This cannot be undone.`)) return;
    try {
      await api.adminDeleteMMPreset(p.id);
      setMMPresets(mmPresets.filter(x => x.id !== p.id));
    } catch {}
  };

  const updateMMPreset = async (id: string, field: keyof AdminMMPreset, value: string | number) => {
    try {
      const data: Record<string, string | number> = { [field]: value };
      await api.adminUpdateMMPreset(id, data);
      setMMPresets(mmPresets.map(p => p.id === id ? { ...p, [field]: value } : p));
    } catch {}
  };

  const updateStrategyModeDraft = (mode: string, field: keyof AdminStrategyMode, value: string | number) => {
    setStrategyModeDrafts((prev) => {
      const original = strategyModes.find((s) => s.mode === mode);
      const base = prev[mode] ?? original!;
      return { ...prev, [mode]: { ...base, [field]: value } };
    });
    // Clear any previous error/success for this row when the user edits again.
    setStrategyModeMsg((prev) => (prev[mode] ? { ...prev, [mode]: undefined as never } : prev));
  };

  const saveStrategyMode = async (mode: string) => {
    const draft = strategyModeDrafts[mode];
    if (!draft) return;
    setStrategyModeSaving((prev) => ({ ...prev, [mode]: true }));
    try {
      const updated = await api.adminUpdateStrategyMode(mode, {
        label: draft.label,
        tp_range_min: draft.tp_range_min,
        tp_range_max: draft.tp_range_max,
        risk_level: draft.risk_level,
      });
      setStrategyModes((prev) => prev.map((s) => (s.mode === mode ? updated : s)));
      setStrategyModeDrafts((prev) => {
        const next = { ...prev };
        delete next[mode];
        return next;
      });
      setStrategyModeMsg((prev) => ({ ...prev, [mode]: { type: 'success', text: 'Saved' } }));
    } catch (e: unknown) {
      setStrategyModeMsg((prev) => ({
        ...prev,
        [mode]: { type: 'error', text: e instanceof Error ? e.message : 'Failed to save' },
      }));
    } finally {
      setStrategyModeSaving((prev) => ({ ...prev, [mode]: false }));
    }
  };

  const resetStrategyModeDraft = (mode: string) => {
    setStrategyModeDrafts((prev) => {
      const next = { ...prev };
      delete next[mode];
      return next;
    });
    setStrategyModeMsg((prev) => {
      const next = { ...prev };
      delete next[mode];
      return next;
    });
  };

  const tabs: { id: Tab; label: string; icon: typeof Coins }[] = [
    { id: 'coin-groups', label: 'Coin Groups', icon: Coins },
    { id: 'mm-presets', label: 'MM Presets', icon: Wallet },
    { id: 'strategy-modes', label: 'Strategy Modes', icon: CandlestickChart },
    { id: 'breaker-thresholds', label: 'Breaker Thresholds', icon: ShieldAlert },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold tracking-tight">Admin Settings</h2>
        <p className="text-sm text-muted-foreground">Manage coin groups, MM presets, and strategy modes</p>
      </div>

      {error && (
        <div className="rounded-xl bg-red-500/10 p-4 text-sm text-red-600 dark:text-red-400">
          {error}
        </div>
      )}

      {/* Tab selector */}
      <div className="flex gap-2 overflow-x-auto pb-1">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={cn(
              'flex items-center gap-2 rounded-xl border px-4 py-2 text-sm font-medium transition-all whitespace-nowrap',
              tab === t.id
                ? 'border-violet-500 bg-violet-500/10 text-violet-600 dark:text-violet-400'
                : 'border-border bg-card hover:bg-accent',
            )}
          >
            <t.icon className="h-4 w-4" />
            {t.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-violet-500 border-t-transparent" />
        </div>
      ) : (
        <>
          {/* Coin Groups Tab */}
          {tab === 'coin-groups' && (
            <Card glass>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span className="flex items-center gap-2">
                    <Coins className="h-5 w-5 text-violet-500" />
                    Coin Groups ({coinGroups.length})
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {coinGroups.map((g) => (
                  <div key={g.id} className="rounded-xl border border-border bg-card p-4">
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-4">
                      <div>
                        <label className="mb-1 block text-xs text-muted-foreground">Name</label>
                        <input
                          type="text"
                          value={g.name}
                          onChange={(e) => updateCoinGroup(g.id, 'name', e.target.value)}
                          className="w-full rounded-lg border border-border bg-background px-2 py-1 text-sm focus:border-violet-500 focus:outline-none"
                        />
                      </div>
                      <div>
                        <label className="mb-1 block text-xs text-muted-foreground">Max Coins</label>
                        <input
                          type="number"
                          value={g.max_coins >= 999 ? 999 : g.max_coins}
                          onChange={(e) => updateCoinGroup(g.id, 'max_coins', Number(e.target.value))}
                          className="w-full rounded-lg border border-border bg-background px-2 py-1 text-sm focus:border-violet-500 focus:outline-none"
                        />
                      </div>
                      <div className="sm:col-span-2">
                        <label className="mb-1 block text-xs text-muted-foreground">Description</label>
                        <input
                          type="text"
                          value={g.description ?? ''}
                          placeholder="—"
                          onChange={(e) => updateCoinGroup(g.id, 'description', e.target.value)}
                          className="w-full rounded-lg border border-border bg-background px-2 py-1 text-sm focus:border-violet-500 focus:outline-none"
                        />
                      </div>
                      <div className="sm:col-span-4">
                        <label className="mb-1 block text-xs text-muted-foreground">
                          Coins (comma-separated)
                        </label>
                        <input
                          type="text"
                          value={g.coins.join(', ')}
                          onChange={(e) => updateCoinGroup(g.id, 'coins', e.target.value.split(',').map(s => s.trim().toUpperCase()).filter(Boolean))}
                          className="w-full rounded-lg border border-border bg-background px-2 py-1 text-sm focus:border-violet-500 focus:outline-none"
                        />
                      </div>
                    </div>
                    <div className="mt-3 flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {g.is_builtin && <Badge variant="secondary">Built-in</Badge>}
                        {!g.is_active && <Badge variant="destructive">Inactive</Badge>}
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => toggleCoinGroupActive(g)}
                          className={cn(
                            'rounded-lg p-2 transition',
                            g.is_active ? 'text-green-500 hover:bg-green-500/10' : 'text-muted-foreground hover:bg-accent',
                          )}
                          title={g.is_active ? 'Deactivate' : 'Activate'}
                        >
                          <Power className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => deleteCoinGroup(g)}
                          className="rounded-lg p-2 text-muted-foreground transition hover:bg-red-500/10 hover:text-red-500"
                          title="Delete"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* MM Presets Tab */}
          {tab === 'mm-presets' && (
            <Card glass>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Wallet className="h-5 w-5 text-violet-500" />
                  MM Presets ({mmPresets.length})
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {mmPresets.map((p) => (
                  <div key={p.id} className="rounded-xl border border-border bg-card p-4">
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-4">
                      <div>
                        <label className="mb-1 block text-xs text-muted-foreground">Name</label>
                        <input
                          type="text"
                          value={p.name}
                          onChange={(e) => updateMMPreset(p.id, 'name', e.target.value)}
                          className="w-full rounded-lg border border-border bg-background px-2 py-1 text-sm focus:border-violet-500 focus:outline-none"
                        />
                      </div>
                      <div>
                        <label className="mb-1 block text-xs text-muted-foreground">Steps</label>
                        <input
                          type="number"
                          value={p.steps}
                          onChange={(e) => updateMMPreset(p.id, 'steps', Number(e.target.value))}
                          className="w-full rounded-lg border border-border bg-background px-2 py-1 text-sm focus:border-violet-500 focus:outline-none"
                        />
                      </div>
                      <div>
                        <label className="mb-1 block text-xs text-muted-foreground">Min Capital ($)</label>
                        <input
                          type="number"
                          step="0.01"
                          value={Number(p.min_capital)}
                          onChange={(e) => updateMMPreset(p.id, 'min_capital', Number(e.target.value))}
                          className="w-full rounded-lg border border-border bg-background px-2 py-1 text-sm focus:border-violet-500 focus:outline-none"
                        />
                      </div>
                      <div>
                        <label className="mb-1 block text-xs text-muted-foreground">Max Capital ($)</label>
                        <input
                          type="number"
                          step="0.01"
                          value={p.max_capital ? Number(p.max_capital) : ''}
                          placeholder="—"
                          onChange={(e) => updateMMPreset(p.id, 'max_capital', Number(e.target.value))}
                          className="w-full rounded-lg border border-border bg-background px-2 py-1 text-sm focus:border-violet-500 focus:outline-none"
                        />
                      </div>
                      <div className="sm:col-span-4">
                        <label className="mb-1 block text-xs text-muted-foreground">Description</label>
                        <input
                          type="text"
                          value={p.description ?? ''}
                          placeholder="—"
                          onChange={(e) => updateMMPreset(p.id, 'description', e.target.value)}
                          className="w-full rounded-lg border border-border bg-background px-2 py-1 text-sm focus:border-violet-500 focus:outline-none"
                        />
                      </div>
                    </div>
                    <div className="mt-3 flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Badge variant="default">{p.preset_type}</Badge>
                        {p.is_builtin && <Badge variant="secondary">Built-in</Badge>}
                        {!p.is_active && <Badge variant="destructive">Inactive</Badge>}
                        <span className="text-xs text-muted-foreground">
                          {p.allowed_coin_groups.length > 0 && `Groups: ${p.allowed_coin_groups.join(', ')}`}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => toggleMMPresetActive(p)}
                          className={cn(
                            'rounded-lg p-2 transition',
                            p.is_active ? 'text-green-500 hover:bg-green-500/10' : 'text-muted-foreground hover:bg-accent',
                          )}
                          title={p.is_active ? 'Deactivate' : 'Activate'}
                        >
                          <Power className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => deleteMMPreset(p)}
                          className="rounded-lg p-2 text-muted-foreground transition hover:bg-red-500/10 hover:text-red-500"
                          title="Delete"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Strategy Modes Tab */}
          {tab === 'strategy-modes' && (
            <Card glass>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <CandlestickChart className="h-5 w-5 text-violet-500" />
                  Strategy Modes ({strategyModes.length})
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {strategyModes.map((sm) => (
                  <div key={sm.mode} className="rounded-xl border border-border bg-card p-4">
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-5">
                      <div>
                        <label className="mb-1 block text-xs text-muted-foreground">Mode</label>
                        <span className="text-lg font-bold">{sm.mode}</span>
                      </div>
                      <div>
                        <label className="mb-1 block text-xs text-muted-foreground">Label</label>
                        <input
                          type="text"
                          value={sm.label}
                          onChange={(e) => updateStrategyModeDraft(sm.mode, 'label', e.target.value)}
                          className="w-full rounded-lg border border-border bg-background px-2 py-1 text-sm focus:border-violet-500 focus:outline-none"
                        />
                      </div>
                      <div>
                        <label className="mb-1 block text-xs text-muted-foreground">TP Range Min (%)</label>
                        <input
                          type="number"
                          step="0.1"
                          value={sm.tp_range_min}
                          onChange={(e) => updateStrategyModeDraft(sm.mode, 'tp_range_min', Number(e.target.value))}
                          className="w-full rounded-lg border border-border bg-background px-2 py-1 text-sm focus:border-violet-500 focus:outline-none"
                        />
                      </div>
                      <div>
                        <label className="mb-1 block text-xs text-muted-foreground">TP Range Max (%)</label>
                        <input
                          type="number"
                          step="0.1"
                          value={sm.tp_range_max}
                          onChange={(e) => updateStrategyModeDraft(sm.mode, 'tp_range_max', Number(e.target.value))}
                          className="w-full rounded-lg border border-border bg-background px-2 py-1 text-sm focus:border-violet-500 focus:outline-none"
                        />
                      </div>
                      <div>
                        <label className="mb-1 block text-xs text-muted-foreground">Risk Level</label>
                        <input
                          type="text"
                          value={sm.risk_level}
                          onChange={(e) => updateStrategyModeDraft(sm.mode, 'risk_level', e.target.value)}
                          className="w-full rounded-lg border border-border bg-background px-2 py-1 text-sm focus:border-violet-500 focus:outline-none"
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Breaker Thresholds Tab */}
          {tab === 'breaker-thresholds' && (
            <div className="space-y-4">
              {/* Health summary card */}
              <Card glass>
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <span className="flex items-center gap-2">
                      <ShieldAlert className="h-5 w-5 text-violet-500" />
                      Breaker Threshold Health
                    </span>
                    <button
                      onClick={handleRescreenBreakers}
                      disabled={breakerRescreening}
                      className={cn(
                        'flex items-center gap-2 rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-medium text-white transition',
                        breakerRescreening ? 'opacity-50 cursor-not-allowed' : 'hover:bg-violet-700',
                      )}
                    >
                      <RefreshCw className={cn('h-3.5 w-3.5', breakerRescreening && 'animate-spin')} />
                      {breakerRescreening ? 'Screening…' : 'Re-screen All'}
                    </button>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {breakerMsg && (
                    <div
                      className={cn(
                        'mb-3 rounded-lg p-3 text-xs',
                        breakerMsg.type === 'success' && 'bg-green-500/10 text-green-700 dark:text-green-400',
                        breakerMsg.type === 'error' && 'bg-red-500/10 text-red-600 dark:text-red-400',
                        breakerMsg.type === 'info' && 'bg-blue-500/10 text-blue-700 dark:text-blue-400',
                      )}
                    >
                      {breakerMsg.text}
                    </div>
                  )}
                  {breakerHealth ? (
                    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                      <div className="rounded-lg border border-border bg-card p-3">
                        <div className="text-xs text-muted-foreground">Total Rows</div>
                        <div className="text-xl font-bold">{breakerHealth.total_rows}</div>
                      </div>
                      <div className="rounded-lg border border-border bg-card p-3">
                        <div className="text-xs text-muted-foreground">Symbols Covered</div>
                        <div className="text-xl font-bold">{breakerHealth.distinct_symbols}</div>
                      </div>
                      <div className="rounded-lg border border-border bg-card p-3">
                        <div className="text-xs text-muted-foreground">Fallback Rows</div>
                        <div className={cn(
                          'text-xl font-bold',
                          breakerHealth.fallback_total > 0 ? 'text-amber-600 dark:text-amber-400' : 'text-green-600',
                        )}>
                          {breakerHealth.fallback_total}
                        </div>
                      </div>
                      <div className="rounded-lg border border-border bg-card p-3">
                        <div className="text-xs text-muted-foreground">Last Screened</div>
                        <div className="text-sm font-medium">
                          {breakerHealth.newest_screened_at
                            ? new Date(breakerHealth.newest_screened_at).toLocaleString()
                            : '—'}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">Loading health summary…</p>
                  )}
                  {breakerHealth && breakerHealth.fallback_total > 0 && (
                    <div className="mt-3 rounded-lg bg-amber-500/10 p-3 text-xs text-amber-700 dark:text-amber-400">
                      <strong>⚠ {breakerHealth.fallback_total} thresholds are using fallback values</strong> — these symbols have no real historical data. Run &quot;Re-screen All&quot; to fetch candles and compute data-driven thresholds.
                    </div>
                  )}
                  {breakerHealth && breakerHealth.oldest_screened_at && (
                    <div className="mt-2 text-xs text-muted-foreground">
                      Oldest screening: {new Date(breakerHealth.oldest_screened_at).toLocaleString()}
                      {' · '}
                      {(() => {
                        const ageMs = Date.now() - new Date(breakerHealth.oldest_screened_at).getTime();
                        const days = Math.floor(ageMs / (1000 * 60 * 60 * 24));
                        return days > 7
                          ? <span className="text-amber-600 dark:text-amber-400">({days} days ago — consider re-screening)</span>
                          : <span className="text-green-600">({days} days ago — fresh)</span>;
                      })()}
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Thresholds table */}
              <Card glass>
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <span className="flex items-center gap-2">
                      <CandlestickChart className="h-5 w-5 text-violet-500" />
                      Thresholds ({breakerThresholds.length})
                    </span>
                    <select
                      value={breakerRateFilter === 'all' ? 'all' : String(breakerRateFilter)}
                      onChange={(e) => setBreakerRateFilter(e.target.value === 'all' ? 'all' : Number(e.target.value))}
                      className="rounded-lg border border-border bg-background px-2 py-1 text-xs focus:border-violet-500 focus:outline-none"
                    >
                      <option value="all">All Tiers</option>
                      <option value="0.7">Protective (≥9% / 5d)</option>
                      <option value="0.8">Balanced (≥12% / 10d)</option>
                      <option value="0.9">Patient (≥15% / 30d)</option>
                    </select>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {breakerThresholds.length === 0 ? (
                    <p className="text-sm text-muted-foreground">
                      No thresholds stored yet. Click &quot;Re-screen All&quot; to compute them from historical data.
                    </p>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs">
                        <thead>
                          <tr className="text-left text-muted-foreground border-b border-border">
                            <th className="pb-2 font-medium">Symbol</th>
                            <th className="pb-2 font-medium">Tier</th>
                            <th className="pb-2 font-medium">Threshold</th>
                            <th className="pb-2 font-medium">Window</th>
                            <th className="pb-2 font-medium">Future Decline</th>
                            <th className="pb-2 font-medium">Resume</th>
                            <th className="pb-2 font-medium">Source</th>
                            <th className="pb-2 font-medium">Candles</th>
                            <th className="pb-2 font-medium">Screened</th>
                          </tr>
                        </thead>
                        <tbody>
                          {breakerThresholds
                            .slice()
                            .sort((a, b) =>
                              a.symbol === b.symbol
                                ? a.min_continuation_rate - b.min_continuation_rate
                                : a.symbol.localeCompare(b.symbol),
                            )
                            .map((t) => {
                              const tierLabel =
                                t.min_continuation_rate === 0.7 ? 'Protective' :
                                t.min_continuation_rate === 0.8 ? 'Balanced' :
                                t.min_continuation_rate === 0.9 ? 'Patient' :
                                `${(t.min_continuation_rate * 100).toFixed(0)}%`;
                              const resumeLabel =
                                t.resume_mode === 'ta_confirm' ? 'TA Confirm' :
                                t.resume_mode === 'widen_step' ? `Widen ${t.widen_multiplier}×` :
                                t.resume_mode === 'trailing_buy' ? `Trail ${t.recovery_pct}%` :
                                t.resume_mode;
                              return (
                              <tr key={t.id} className="border-b border-border/50">
                                <td className="py-2 font-medium">{t.symbol}</td>
                                <td className="py-2">{tierLabel}</td>
                                <td className="py-2 font-semibold">{t.threshold_pct.toFixed(2)}%</td>
                                <td className="py-2 text-muted-foreground">{t.continuation_window}d</td>
                                <td className="py-2 text-muted-foreground">≥{t.min_future_drop_pct.toFixed(0)}%</td>
                                <td className="py-2">
                                  <Badge variant="secondary">{resumeLabel}</Badge>
                                </td>
                                <td className="py-2">
                                  {t.used_fallback ? (
                                    <Badge variant="destructive">fallback</Badge>
                                  ) : (
                                    <Badge variant="default">data</Badge>
                                  )}
                                </td>
                                <td className="py-2 text-muted-foreground">{t.candle_count}</td>
                                <td className="py-2 text-muted-foreground">
                                  {t.screened_at ? new Date(t.screened_at).toLocaleDateString() : '—'}
                                </td>
                              </tr>
                            );})}
                        </tbody>
                      </table>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          )}
        </>
      )}
    </div>
  );
}
