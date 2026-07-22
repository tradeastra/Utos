'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CandlestickChart, Coins, Check, Lock, Trash2, Wallet, Calculator, TrendingDown, Zap, Activity, Search, Layers } from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/services/api';
import type { AveragingTemplateSummary, CoinGroup, CoinSelectionLimit, ForceBuyResult, ForceSellResult, MMCalculationResult, MMPreset, StrategyMode, TAConfig, TAIndicatorDescription } from '@/types';
import { FilterChips, type FilterType } from '@/components/trade/filter-chips';
import { CoinRow, type CoinRowData } from '@/components/trade/coin-row';
import { useRouter } from 'next/navigation';

const strategyModes: { mode: StrategyMode; label: string; dailyRange: string; riskLevel: string; color: string }[] = [
  { mode: 'A', label: 'Super Bearish', dailyRange: '0.5% – 1.5%', riskLevel: 'Low', color: 'bg-blue-500/10 border-blue-500/30 text-blue-600 dark:text-blue-400' },
  { mode: 'B', label: 'Conventional', dailyRange: '1.0% – 3.0%', riskLevel: 'Medium', color: 'bg-green-500/10 border-green-500/30 text-green-600 dark:text-green-400' },
  { mode: 'C', label: 'Aggressive', dailyRange: '2.0% – 5.0%', riskLevel: 'High', color: 'bg-amber-500/10 border-amber-500/30 text-amber-600 dark:text-amber-400' },
  { mode: 'D', label: 'Very Aggressive', dailyRange: '3.0% – 8.0%', riskLevel: 'Very High', color: 'bg-orange-500/10 border-orange-500/30 text-orange-600 dark:text-orange-400' },
  { mode: 'U', label: 'Ultimate', dailyRange: '5.0% – 15.0%', riskLevel: 'Extreme', color: 'bg-violet-500/10 border-violet-500/30 text-violet-600 dark:text-violet-400' },
];

export default function TradePage() {
  const [selectedMode, setSelectedMode] = useState<StrategyMode>('B');
  const [coinGroups, setCoinGroups] = useState<CoinGroup[]>([]);
  const [selectedGroup, setSelectedGroup] = useState<string | null>(null);
  const [limits, setLimits] = useState<CoinSelectionLimit | null>(null);
  const [mmPresets, setMMPresets] = useState<MMPreset[]>([]);
  const [selectedPreset, setSelectedPreset] = useState<string | null>(null);
  const [capital, setCapital] = useState<string>('');
  const [calcResult, setCalcResult] = useState<MMCalculationResult | null>(null);
  const [calculating, setCalculating] = useState(false);
  const [avgTemplate, setAvgTemplate] = useState<AveragingTemplateSummary | null>(null);
  const [showAvgConfig, setShowAvgConfig] = useState(false);
  const [forceInstanceId, setForceInstanceId] = useState<string>('');
  const [forceLevel, setForceLevel] = useState<string>('');
  const [forcePrice, setForcePrice] = useState<string>('');
  const [forceQty, setForceQty] = useState<string>('');
  const [forceResult, setForceResult] = useState<ForceBuyResult | ForceSellResult | null>(null);
  const [forceLoading, setForceLoading] = useState(false);
  const [taIndicators, setTAIndicators] = useState<TAIndicatorDescription[]>([]);
  const [taConfigs, setTAConfigs] = useState<TAConfig[]>([]);
  const [taInstanceId, setTaInstanceId] = useState<string>('');
  const [taLoading, setTaLoading] = useState(false);
  const [tradingInstances, setTradingInstances] = useState<CoinRowData[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [filter, setFilter] = useState<FilterType>('all');
  const [selectedExchange, setSelectedExchange] = useState<string>('all');
  const [exchanges, setExchanges] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    async function loadData() {
      try {
        const [groups, lim, presets, template, indicators, instances] = await Promise.all([
          api.getCoinGroups(),
          api.getCoinSelectionLimits(),
          api.getMMPresets(),
          api.getAveragingTemplate(),
          api.getTAIndicators(),
          api.getTradingInstances().catch(() => [] as Record<string, unknown>[]),
        ]);
        setCoinGroups(groups);
        setLimits(lim);
        setMMPresets(presets);
        setAvgTemplate(template);
        setTAIndicators(indicators);
        const instList = instances as Record<string, unknown>[];
        setTradingInstances(instList.map((inst) => ({
          id: String(inst.id),
          symbol: String(inst.symbol),
          status: String(inst.status) as CoinRowData['status'],
          exchange: String(inst.exchange_name || '—'),
          qty: Number(inst.total_investment) || 0,
          currentPrice: Number(inst.current_price) || 0,
          change24h: 0,
          avgPrice: inst.start_price ? Number(inst.start_price) : null,
          step: null,
          totalSteps: null,
          profit: null,
          profitPct: null,
          isAveraging: false,
        })));
        setExchanges(Array.from(new Set(instList.map((i) => String(i.exchange_name)).filter(Boolean))));
      } catch {
        setCoinGroups([]);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const selectedGroupData = coinGroups.find((g) => g.id === selectedGroup);

  const filteredInstances = tradingInstances.filter((inst) => {
    if (searchQuery && !inst.symbol.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    if (selectedExchange !== 'all' && inst.exchange !== selectedExchange) return false;
    if (filter === 'active' && inst.status !== 'running') return false;
    if (filter === 'paused' && inst.status !== 'paused') return false;
    if (filter === 'profit' && (inst.profit === null || inst.profit < 0)) return false;
    if (filter === 'loss' && (inst.profit === null || inst.profit >= 0)) return false;
    return true;
  });

  const filterCounts = {
    all: tradingInstances.length,
    active: tradingInstances.filter(i => i.status === 'running').length,
    paused: tradingInstances.filter(i => i.status === 'paused').length,
    profit: tradingInstances.filter(i => i.profit !== null && i.profit >= 0).length,
    loss: tradingInstances.filter(i => i.profit !== null && i.profit < 0).length,
  };

  const activeCount = tradingInstances.filter(i => i.status === 'running').length;
  const openPositions = tradingInstances.filter(i => i.qty > 0).length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold tracking-tight">Trade</h2>
          <p className="text-sm text-muted-foreground">Strategy mode & coin selection</p>
        </div>
        {activeCount > 0 && (
          <Badge variant="success" className="text-sm">
            {activeCount} Active
          </Badge>
        )}
      </div>

      {/* Trading Table */}
      <Card glass>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Layers className="h-5 w-5 text-violet-500" />
            Active Positions
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {/* Search + Exchange Selector */}
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search pair..."
                className="w-full rounded-lg border border-border bg-background py-2 pl-9 pr-3 text-sm focus:border-violet-500 focus:outline-none"
              />
            </div>
            {exchanges.length > 0 && (
              <select
                value={selectedExchange}
                onChange={(e) => setSelectedExchange(e.target.value)}
                className="rounded-lg border border-border bg-background px-3 py-2 text-sm focus:border-violet-500 focus:outline-none"
              >
                <option value="all">All Exchanges</option>
                {exchanges.map((ex) => (
                  <option key={ex} value={ex}>{ex}</option>
                ))}
              </select>
            )}
          </div>

          {/* Filter Chips */}
          <FilterChips active={filter} onChange={setFilter} counts={filterCounts} />

          {/* Table Header — desktop only */}
          <div className="hidden grid-cols-12 gap-2 border-b border-border/50 px-3 pb-2 text-[10px] font-medium uppercase tracking-wider text-muted-foreground md:grid">
            <div className="col-span-3">Pair</div>
            <div className="col-span-2">Qty</div>
            <div className="col-span-2">Price / 24h</div>
            <div className="col-span-2">Avg / Step</div>
            <div className="col-span-3 text-right">Profit / Floating</div>
          </div>

          {/* Rows */}
          {filteredInstances.length > 0 ? (
            <div className="space-y-1.5">
              {filteredInstances.map((inst) => (
                <CoinRow
                  key={inst.id}
                  data={inst}
                  onClick={(symbol) => router.push(`/dashboard/trade/${symbol}`)}
                />
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Layers className="mb-2 h-8 w-8 text-muted-foreground/50" />
              <p className="text-sm text-muted-foreground">
                {tradingInstances.length === 0
                  ? 'No trading instances yet. Create one to get started.'
                  : 'No results match your filters.'}
              </p>
            </div>
          )}

          {/* Bottom Sheet — Open Position Counter */}
          {openPositions > 0 && (
            <div className="sticky bottom-0 mt-2 flex items-center justify-between rounded-xl border border-violet-500/20 bg-violet-500/10 px-4 py-2.5 backdrop-blur-md">
              <span className="text-sm font-medium text-violet-600 dark:text-violet-400">
                {openPositions} Open Position{openPositions !== 1 ? 's' : ''}
              </span>
              <span className="text-xs text-muted-foreground">
                {filteredInstances.length} of {tradingInstances.length} shown
              </span>
            </div>
          )}
        </CardContent>
      </Card>

      <Card glass>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CandlestickChart className="h-5 w-5 text-violet-500" />
            Strategy Mode
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-5">
            {strategyModes.map((sm) => (
              <button
                key={sm.mode}
                onClick={() => setSelectedMode(sm.mode)}
                className={cn(
                  'rounded-2xl border p-4 text-left transition-all active:scale-[0.98]',
                  selectedMode === sm.mode
                    ? sm.color + ' border-2'
                    : 'border-border bg-card hover:bg-accent',
                )}
              >
                <div className="flex items-center justify-between">
                  <span className="text-lg font-bold">{sm.mode}</span>
                  {selectedMode === sm.mode && <Check className="h-4 w-4" />}
                </div>
                <p className="mt-1 text-sm font-medium">{sm.label}</p>
                <p className="mt-1 text-xs text-muted-foreground">{sm.dailyRange}</p>
                <div className="mt-2">
                  <span className="text-xs font-medium opacity-80">Risk: {sm.riskLevel}</span>
                </div>
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card glass>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span className="flex items-center gap-2">
              <Coins className="h-5 w-5 text-violet-500" />
              Coin Selection
            </span>
            {limits && (
              <Badge variant="new">
                {limits.tier}: {limits.max_coin_selection >= 999 ? 'Unlimited' : `${limits.max_coin_selection} coins`}
              </Badge>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-violet-500 border-t-transparent" />
            </div>
          ) : coinGroups.length === 0 ? (
            <div className="rounded-xl bg-amber-500/10 p-4 text-sm text-amber-600 dark:text-amber-400">
              Backend not connected. Coin groups will appear here when the API is available.
            </div>
          ) : (
            <>
              <div className="grid gap-2 grid-cols-2 sm:grid-cols-3 lg:grid-cols-6">
                {coinGroups.map((group) => (
                  <button
                    key={group.id}
                    onClick={() => setSelectedGroup(group.id)}
                    className={cn(
                      'rounded-xl border p-3 text-left transition-all active:scale-[0.98]',
                      selectedGroup === group.id
                        ? 'border-violet-500 bg-violet-500/10'
                        : 'border-border bg-card hover:bg-accent',
                    )}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-semibold">{group.name}</span>
                      {selectedGroup === group.id && <Check className="h-3.5 w-3.5 text-violet-500" />}
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {group.max_coins >= 999 ? 'All' : group.max_coins} coins
                    </span>
                  </button>
                ))}
              </div>

              {selectedGroupData && (
                <div className="rounded-xl border border-border bg-card p-4">
                  <div className="mb-2 flex items-center justify-between">
                    <h4 className="text-sm font-semibold">{selectedGroupData.name}</h4>
                    {selectedGroupData.is_builtin ? (
                      <Badge variant="secondary">Built-in</Badge>
                    ) : (
                      <button
                        onClick={async () => {
                          try {
                            await api.deleteCoinGroup(selectedGroupData.id);
                            setCoinGroups(coinGroups.filter((g) => g.id !== selectedGroupData.id));
                            setSelectedGroup(null);
                          } catch {}
                        }}
                        className="text-muted-foreground hover:text-red-500"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                  {selectedGroupData.coins.length > 0 ? (
                    <div className="flex flex-wrap gap-1.5">
                      {selectedGroupData.coins.map((coin) => (
                        <Badge key={coin} variant="default">{coin}</Badge>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      Dynamic list — coins fetched from market data based on volume ranking.
                    </p>
                  )}
                </div>
              )}

              {limits && limits.max_coin_selection < 999 && (
                <div className="flex items-center gap-2 rounded-xl bg-violet-500/5 p-3 text-sm">
                  <Lock className="h-4 w-4 text-violet-500" />
                  <span className="text-muted-foreground">
                    Your <span className="font-medium text-violet-500">{limits.tier}</span> plan allows selecting up to{' '}
                    <span className="font-medium">{limits.max_coin_selection}</span> coins.
                    Upgrade to select more.
                  </span>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      <Card glass>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Wallet className="h-5 w-5 text-violet-500" />
            Money Management
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-violet-500 border-t-transparent" />
            </div>
          ) : mmPresets.length === 0 ? (
            <div className="rounded-xl bg-amber-500/10 p-4 text-sm text-amber-600 dark:text-amber-400">
              Backend not connected. MM presets will appear here when the API is available.
            </div>
          ) : (
            <>
              <div className="grid gap-2 grid-cols-2 sm:grid-cols-4">
                {mmPresets.map((preset) => (
                  <button
                    key={preset.id}
                    onClick={() => {
                      setSelectedPreset(preset.id);
                      setCalcResult(null);
                    }}
                    className={cn(
                      'rounded-xl border p-3 text-left transition-all active:scale-[0.98]',
                      selectedPreset === preset.id
                        ? 'border-violet-500 bg-violet-500/10'
                        : 'border-border bg-card hover:bg-accent',
                    )}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-semibold">{preset.name}</span>
                      {selectedPreset === preset.id && <Check className="h-3.5 w-3.5 text-violet-500" />}
                    </div>
                    <span className="text-xs text-muted-foreground">{preset.steps} steps</span>
                    <span className="mt-0.5 block text-xs text-muted-foreground">
                      Min: ${Number(preset.min_capital).toLocaleString()}
                    </span>
                  </button>
                ))}
              </div>

              {selectedPreset && (
                <div className="space-y-3 rounded-xl border border-border bg-card p-4">
                  <div className="flex items-center gap-2">
                    <Calculator className="h-4 w-4 text-violet-500" />
                    <h4 className="text-sm font-semibold">Capital Calculator</h4>
                  </div>
                  <div className="flex gap-2">
                    <div className="flex-1">
                      <label className="mb-1 block text-xs text-muted-foreground">Total Capital (USDT)</label>
                      <input
                        type="number"
                        value={capital}
                        onChange={(e) => {
                          setCapital(e.target.value);
                          setCalcResult(null);
                        }}
                        placeholder="e.g. 500"
                        className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:border-violet-500 focus:outline-none"
                      />
                    </div>
                    <button
                      disabled={!capital || calculating}
                      onClick={async () => {
                        const preset = mmPresets.find((p) => p.id === selectedPreset);
                        if (!preset || !capital) return;
                        setCalculating(true);
                        try {
                          const result = await api.calculateMM(
                            preset.preset_type,
                            Number(capital),
                            selectedGroupData?.name,
                          );
                          setCalcResult(result);
                        } catch {
                          setCalcResult(null);
                        } finally {
                          setCalculating(false);
                        }
                      }}
                      className="mt-5 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-violet-700 disabled:opacity-50"
                    >
                      {calculating ? 'Calculating...' : 'Calculate'}
                    </button>
                  </div>

                  {calcResult && (
                    <div className="grid grid-cols-2 gap-3 rounded-lg bg-violet-500/5 p-3 sm:grid-cols-4">
                      <div>
                        <p className="text-xs text-muted-foreground">Buy Amount</p>
                        <p className="text-sm font-bold text-violet-600 dark:text-violet-400">
                          ${Number(calcResult.buy_amount).toFixed(2)}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Max Coins</p>
                        <p className="text-sm font-bold">{calcResult.max_coins}</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Steps</p>
                        <p className="text-sm font-bold">{calcResult.steps}</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Min Volume</p>
                        <p className="text-sm font-bold">
                          ${Number(calcResult.min_volume_filter).toFixed(2)}
                        </p>
                      </div>
                    </div>
                  )}

                  {(() => {
                    const preset = mmPresets.find((p) => p.id === selectedPreset);
                    if (!preset) return null;
                    if (preset.allowed_coin_groups.length > 0 && selectedGroupData) {
                      const compatible = preset.allowed_coin_groups.includes(selectedGroupData.name);
                      if (!compatible) {
                        return (
                          <div className="rounded-lg bg-red-500/10 p-3 text-sm text-red-600 dark:text-red-400">
                            <strong>{preset.name}</strong> is only compatible with: {preset.allowed_coin_groups.join(', ')}.
                            Current selection: {selectedGroupData.name}.
                          </div>
                        );
                      }
                    }
                    return null;
                  })()}
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      <Card glass>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span className="flex items-center gap-2">
              <TrendingDown className="h-5 w-5 text-violet-500" />
              Averaging Configuration
            </span>
            <button
              onClick={() => setShowAvgConfig(!showAvgConfig)}
              className="text-sm text-violet-500 hover:underline"
            >
              {showAvgConfig ? 'Hide' : 'Show'} Details
            </button>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {avgTemplate ? (
            <>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <div className="rounded-xl border border-border bg-card p-3">
                  <p className="text-xs text-muted-foreground">Total Steps</p>
                  <p className="text-lg font-bold">{avgTemplate.total_steps}</p>
                </div>
                <div className="rounded-xl border border-border bg-card p-3">
                  <p className="text-xs text-muted-foreground">Avg Drop Rate</p>
                  <p className="text-lg font-bold text-blue-500">{avgTemplate.avg_drop_rate.toFixed(2)}%</p>
                </div>
                <div className="rounded-xl border border-border bg-card p-3">
                  <p className="text-xs text-muted-foreground">Avg Take Profit</p>
                  <p className="text-lg font-bold text-green-500">{avgTemplate.avg_take_profit.toFixed(2)}%</p>
                </div>
                <div className="rounded-xl border border-border bg-card p-3">
                  <p className="text-xs text-muted-foreground">Max Multiplier</p>
                  <p className="text-lg font-bold text-amber-500">{avgTemplate.max_multiplier}x</p>
                </div>
              </div>

              {showAvgConfig && (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border text-left text-xs text-muted-foreground">
                        <th className="py-2 pr-4">Step</th>
                        <th className="py-2 pr-4">Drop Rate</th>
                        <th className="py-2 pr-4">Multiplier</th>
                        <th className="py-2 pr-4">Take Profit</th>
                      </tr>
                    </thead>
                    <tbody>
                      {avgTemplate.drop_rates.map((dr, i) => (
                        <tr key={i} className="border-b border-border/50">
                          <td className="py-1.5 pr-4 font-medium">{i}</td>
                          <td className="py-1.5 pr-4 text-blue-500">{dr}%</td>
                          <td className="py-1.5 pr-4 text-amber-500">{avgTemplate.multipliers[i]}x</td>
                          <td className="py-1.5 pr-4 text-green-500">{avgTemplate.take_profits[i]}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          ) : (
            <div className="rounded-xl bg-amber-500/10 p-4 text-sm text-amber-600 dark:text-amber-400">
              Backend not connected. Averaging template will appear here when the API is available.
            </div>
          )}
        </CardContent>
      </Card>

      <Card glass>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Zap className="h-5 w-5 text-amber-500" />
            Force Buy / Force Sell
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-xl bg-blue-500/10 p-3 text-xs text-blue-600 dark:text-blue-400">
            <strong>Force Buy</strong> — Manually initiate a buy at a specific level, bypassing market signals.
            After the buy fills, averaging continues automatically for subsequent levels.
            <br />
            <strong>Force Sell</strong> — Close an existing position (spot market: can only sell coins you hold).
            Sells all filled positions if no level is specified.
          </div>

          <div className="space-y-3">
            <div>
              <label className="mb-1 block text-xs text-muted-foreground">Trading Instance ID</label>
              <input
                type="text"
                value={forceInstanceId}
                onChange={(e) => setForceInstanceId(e.target.value)}
                placeholder="e.g. 550e8400-e29b-41d4-a716-446655440000"
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:border-amber-500 focus:outline-none"
              />
            </div>
            <div className="grid grid-cols-3 gap-2">
              <div>
                <label className="mb-1 block text-xs text-muted-foreground">Level (optional)</label>
                <input
                  type="number"
                  value={forceLevel}
                  onChange={(e) => setForceLevel(e.target.value)}
                  placeholder="Auto"
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:border-amber-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs text-muted-foreground">Price (optional)</label>
                <input
                  type="number"
                  step="0.01"
                  value={forcePrice}
                  onChange={(e) => setForcePrice(e.target.value)}
                  placeholder="Market"
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:border-amber-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs text-muted-foreground">Qty (optional)</label>
                <input
                  type="number"
                  step="0.001"
                  value={forceQty}
                  onChange={(e) => setForceQty(e.target.value)}
                  placeholder="Default"
                  className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:border-amber-500 focus:outline-none"
                />
              </div>
            </div>
            <div className="flex gap-2">
              <button
                disabled={!forceInstanceId || forceLoading}
                onClick={async () => {
                  setForceLoading(true);
                  setForceResult(null);
                  try {
                    const result = await api.forceBuy(forceInstanceId, {
                      level: forceLevel ? Number(forceLevel) : undefined,
                      price: forcePrice ? Number(forcePrice) : undefined,
                      quantity: forceQty ? Number(forceQty) : undefined,
                    });
                    setForceResult(result as ForceBuyResult);
                  } catch {
                    setForceResult(null);
                  } finally {
                    setForceLoading(false);
                  }
                }}
                className="flex-1 rounded-lg bg-green-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-green-700 disabled:opacity-50"
              >
                Force Buy
              </button>
              <button
                disabled={!forceInstanceId || forceLoading}
                onClick={async () => {
                  setForceLoading(true);
                  setForceResult(null);
                  try {
                    const result = await api.forceSell(forceInstanceId, {
                      level: forceLevel ? Number(forceLevel) : undefined,
                      price: forcePrice ? Number(forcePrice) : undefined,
                      quantity: forceQty ? Number(forceQty) : undefined,
                    });
                    setForceResult(result as ForceSellResult);
                  } catch {
                    setForceResult(null);
                  } finally {
                    setForceLoading(false);
                  }
                }}
                className="flex-1 rounded-lg bg-red-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-red-700 disabled:opacity-50"
              >
                Force Sell
              </button>
            </div>

            {forceLoading && (
              <div className="flex items-center justify-center py-4">
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-amber-500 border-t-transparent" />
              </div>
            )}

            {forceResult && (
              <div className="rounded-lg bg-amber-500/5 p-4 text-sm">
                {'order_id' in forceResult ? (
                  <>
                    <p className="font-semibold text-green-600 dark:text-green-400">Buy Order Placed</p>
                    <p className="mt-1 text-muted-foreground">
                      Level: {forceResult.level} · Price: ${forceResult.price} · Qty: {forceResult.quantity}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">{forceResult.message}</p>
                  </>
                ) : (
                  <>
                    <p className="font-semibold text-red-600 dark:text-red-400">Sell Order Placed</p>
                    <p className="mt-1 text-muted-foreground">
                      Levels: {forceResult.levels_sold.join(', ')} · Total Qty: {forceResult.total_quantity} · Value: ${forceResult.total_value}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">{forceResult.message}</p>
                  </>
                )}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      <Card glass>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-cyan-500" />
            Technical Analysis Gate
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-xl bg-cyan-500/10 p-3 text-xs text-cyan-600 dark:text-cyan-400">
            Configure TA indicators as a gate before buy orders. When enabled, the grid engine
            will skip buy orders if the TA gate fails. Sell orders are never blocked.
            Multiple indicators are combined with AND/OR logic.
          </div>

          <div>
            <label className="mb-1 block text-xs text-muted-foreground">Trading Instance ID</label>
            <div className="flex gap-2">
              <input
                type="text"
                value={taInstanceId}
                onChange={(e) => setTaInstanceId(e.target.value)}
                placeholder="Instance ID to load/save TA configs"
                className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none"
              />
              <button
                disabled={!taInstanceId || taLoading}
                onClick={async () => {
                  setTaLoading(true);
                  try {
                    const configs = await api.getTAConfigs(taInstanceId);
                    setTAConfigs(configs);
                  } catch {
                    setTAConfigs([]);
                  } finally {
                    setTaLoading(false);
                  }
                }}
                className="rounded-lg bg-cyan-600 px-4 py-2 text-sm font-medium text-white hover:bg-cyan-700 disabled:opacity-50"
              >
                Load
              </button>
            </div>
          </div>

          {taIndicators.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Indicators ({taConfigs.length})</span>
                <button
                  onClick={() => {
                    setTAConfigs([...taConfigs, {
                      indicator: 'rsi',
                      time_frame: '1h',
                      operator: 'and',
                      params: taIndicators.find(i => i.indicator === 'rsi')?.default_params || null,
                      enabled: true,
                      priority: taConfigs.length,
                      description: null,
                    }]);
                  }}
                  className="text-xs text-cyan-500 hover:underline"
                >
                  + Add Indicator
                </button>
              </div>

              {taConfigs.map((cfg, idx) => (
                <div key={idx} className="rounded-lg border border-border bg-card p-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <select
                      value={cfg.indicator}
                      onChange={(e) => {
                        const newParams = taIndicators.find(i => i.indicator === e.target.value)?.default_params || null;
                        setTAConfigs(taConfigs.map((c, i) => i === idx ? { ...c, indicator: e.target.value, params: newParams as Record<string, number | string> | null } : c));
                      }}
                      className="rounded border border-border bg-background px-2 py-1 text-sm"
                    >
                      {taIndicators.map(ind => (
                        <option key={ind.indicator} value={ind.indicator}>{ind.label}</option>
                      ))}
                    </select>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setTAConfigs(taConfigs.map((c, i) => i === idx ? { ...c, enabled: !c.enabled } : c))}
                        className={cn('rounded px-2 py-0.5 text-xs', cfg.enabled ? 'bg-green-600 text-white' : 'bg-muted text-muted-foreground')}
                      >
                        {cfg.enabled ? 'ON' : 'OFF'}
                      </button>
                      <button
                        onClick={() => setTAConfigs(taConfigs.filter((_, i) => i !== idx))}
                        className="text-red-500 hover:text-red-600"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="text-xs text-muted-foreground">Time Frame</label>
                      <select
                        value={cfg.time_frame}
                        onChange={(e) => setTAConfigs(taConfigs.map((c, i) => i === idx ? { ...c, time_frame: e.target.value } : c))}
                        className="w-full rounded border border-border bg-background px-2 py-1 text-sm"
                      >
                        {['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w'].map(tf => (
                          <option key={tf} value={tf}>{tf}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="text-xs text-muted-foreground">Operator</label>
                      <select
                        value={cfg.operator}
                        onChange={(e) => setTAConfigs(taConfigs.map((c, i) => i === idx ? { ...c, operator: e.target.value } : c))}
                        className="w-full rounded border border-border bg-background px-2 py-1 text-sm"
                      >
                        <option value="and">AND</option>
                        <option value="or">OR</option>
                      </select>
                    </div>
                  </div>
                  {cfg.params && (
                    <div className="text-xs text-muted-foreground">
                      Params: {Object.entries(cfg.params).map(([k, v]) => `${k}=${v}`).join(', ')}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {taConfigs.length > 0 && taInstanceId && (
            <button
              disabled={taLoading}
              onClick={async () => {
                setTaLoading(true);
                try {
                  await api.updateTAConfigs(taInstanceId, taConfigs.map(c => ({
                    indicator: c.indicator,
                    time_frame: c.time_frame,
                    operator: c.operator,
                    params: c.params,
                    enabled: c.enabled,
                    priority: c.priority,
                    description: c.description ?? undefined,
                  })));
                } finally {
                  setTaLoading(false);
                }
              }}
              className="w-full rounded-lg bg-cyan-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-cyan-700 disabled:opacity-50"
            >
              {taLoading ? 'Saving...' : 'Save TA Configs'}
            </button>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
