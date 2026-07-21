'use client';

import { useEffect, useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Coins, Wallet, CandlestickChart, Trash2, Power } from 'lucide-react';
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
  mode: string; label: string; daily_range_min: number; daily_range_max: number; risk_level: string;
}

type Tab = 'coin-groups' | 'mm-presets' | 'strategy-modes';

export default function AdminSettingsPage() {
  const [tab, setTab] = useState<Tab>('coin-groups');
  const [coinGroups, setCoinGroups] = useState<AdminCoinGroup[]>([]);
  const [mmPresets, setMMPresets] = useState<AdminMMPreset[]>([]);
  const [strategyModes, setStrategyModes] = useState<AdminStrategyMode[]>([]);
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

  useEffect(() => { loadAll(); }, [loadAll]);

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

  const updateStrategyMode = async (mode: string, field: keyof AdminStrategyMode, value: string | number) => {
    try {
      const data: Record<string, string | number> = { [field]: value };
      await api.adminUpdateStrategyMode(mode, data);
      setStrategyModes(strategyModes.map(s => s.mode === mode ? { ...s, [field]: value } : s));
    } catch {}
  };

  const tabs: { id: Tab; label: string; icon: typeof Coins }[] = [
    { id: 'coin-groups', label: 'Coin Groups', icon: Coins },
    { id: 'mm-presets', label: 'MM Presets', icon: Wallet },
    { id: 'strategy-modes', label: 'Strategy Modes', icon: CandlestickChart },
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
                  <div key={g.id} className="flex items-center justify-between rounded-xl border border-border bg-card p-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{g.name}</span>
                        {g.is_builtin && <Badge variant="secondary">Built-in</Badge>}
                        {!g.is_active && <Badge variant="destructive">Inactive</Badge>}
                      </div>
                      <p className="mt-0.5 text-xs text-muted-foreground">
                        {g.max_coins >= 999 ? 'All' : g.max_coins} coins
                        {g.coins.length > 0 && ` · ${g.coins.join(', ')}`}
                      </p>
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
                  <div key={p.id} className="flex items-center justify-between rounded-xl border border-border bg-card p-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{p.name}</span>
                        <Badge variant="default">{p.preset_type}</Badge>
                        {p.is_builtin && <Badge variant="secondary">Built-in</Badge>}
                        {!p.is_active && <Badge variant="destructive">Inactive</Badge>}
                      </div>
                      <p className="mt-0.5 text-xs text-muted-foreground">
                        {p.steps} steps · Min: ${Number(p.min_capital).toLocaleString()}
                        {p.allowed_coin_groups.length > 0 && ` · ${p.allowed_coin_groups.join(', ')}`}
                      </p>
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
                          onChange={(e) => updateStrategyMode(sm.mode, 'label', e.target.value)}
                          className="w-full rounded-lg border border-border bg-background px-2 py-1 text-sm focus:border-violet-500 focus:outline-none"
                        />
                      </div>
                      <div>
                        <label className="mb-1 block text-xs text-muted-foreground">Daily Range Min (%)</label>
                        <input
                          type="number"
                          step="0.1"
                          value={sm.daily_range_min}
                          onChange={(e) => updateStrategyMode(sm.mode, 'daily_range_min', Number(e.target.value))}
                          className="w-full rounded-lg border border-border bg-background px-2 py-1 text-sm focus:border-violet-500 focus:outline-none"
                        />
                      </div>
                      <div>
                        <label className="mb-1 block text-xs text-muted-foreground">Daily Range Max (%)</label>
                        <input
                          type="number"
                          step="0.1"
                          value={sm.daily_range_max}
                          onChange={(e) => updateStrategyMode(sm.mode, 'daily_range_max', Number(e.target.value))}
                          className="w-full rounded-lg border border-border bg-background px-2 py-1 text-sm focus:border-violet-500 focus:outline-none"
                        />
                      </div>
                      <div>
                        <label className="mb-1 block text-xs text-muted-foreground">Risk Level</label>
                        <input
                          type="text"
                          value={sm.risk_level}
                          onChange={(e) => updateStrategyMode(sm.mode, 'risk_level', e.target.value)}
                          className="w-full rounded-lg border border-border bg-background px-2 py-1 text-sm focus:border-violet-500 focus:outline-none"
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
