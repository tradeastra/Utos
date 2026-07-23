'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowLeft, Pause, Play, TrendingUp, TrendingDown, Activity, Settings, Zap } from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/services/api';
import { MetricCard } from '@/components/trade/metric-card';
import { ForceActions } from '@/components/trade/force-actions';

interface CoinDetail {
  id: string;
  symbol: string;
  status: string;
  exchange: string;
  currentPrice: number;
  startPrice: number | null;
  totalInvestment: number;
  qty: number;
  avgPrice: number | null;
  step: number | null;
  totalSteps: number | null;
  profit: number | null;
  profitPct: number | null;
  change24h: number;
}

interface GridMetrics {
  nextStepPrice: number | null;
  dropRate: number | null;
  tpPrice: number | null;
  tpPct: number | null;
  buyAmount: number | null;
  averagingLimit: number | null;
}

const STATUS_COLORS: Record<string, string> = {
  running: 'bg-emerald-500',
  paused: 'bg-amber-500',
  stopped: 'bg-red-500',
  error: 'bg-red-500',
  created: 'bg-blue-500',
  ready: 'bg-cyan-500',
};

function formatPrice(price: number): string {
  if (price >= 1000) return price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  if (price >= 1) return price.toFixed(4);
  if (price >= 0.01) return price.toFixed(6);
  return price.toFixed(8);
}

export default function CoinDetailPage() {
  const params = useParams();
  const router = useRouter();
  const symbol = decodeURIComponent(params.symbol as string);

  const [detail, setDetail] = useState<CoinDetail | null>(null);
  const [gridMetrics, setGridMetrics] = useState<GridMetrics | null>(null);
  const [avgEnabled, setAvgEnabled] = useState(true);
  const [nonStop, setNonStop] = useState(false);
  const [partial, setPartial] = useState(false);
  const [formula, setFormula] = useState('default');
  const [settingsSaving, setSettingsSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [pausing, setPausing] = useState(false);

  useEffect(() => {
    async function loadData() {
      try {
        const instances = await api.getTradingInstances().catch(() => [] as Record<string, unknown>[]);
        const instList = instances as Record<string, unknown>[];
        const found = instList.find((i) => String(i.symbol).toUpperCase() === symbol.toUpperCase());
        if (found) {
          const currentPrice = Number(found.current_price) || 0;
          const startPrice = found.start_price ? Number(found.start_price) : null;
          const totalInvestment = Number(found.total_investment) || 0;
          setDetail({
            id: String(found.id),
            symbol: String(found.symbol),
            status: String(found.status),
            exchange: String(found.exchange_name || '—'),
            currentPrice,
            startPrice,
            totalInvestment,
            qty: 0,
            avgPrice: startPrice,
            step: null,
            totalSteps: null,
            profit: null,
            profitPct: null,
            change24h: 0,
          });

          // Load per-coin settings from backend
          setAvgEnabled(found.avg_enabled !== false);
          setNonStop(found.non_stop === true);
          setPartial(found.partial_sell === true);
          setFormula(String(found.formula_mode || 'default'));

          // Try to load grid state for metrics
          try {
            const grid = await api.getGridState(String(found.id));
            const gridData = grid as Record<string, unknown>;
            const levels = gridData.levels as Record<string, unknown>[] | undefined;
            if (levels && levels.length > 0) {
              const nextLevel = levels.find((l) => l.status === 'waiting');
              setGridMetrics({
                nextStepPrice: nextLevel ? Number(nextLevel.buy_price) : null,
                dropRate: null,
                tpPrice: nextLevel ? Number(nextLevel.sell_price) : null,
                tpPct: null,
                buyAmount: Number(gridData.investment_per_grid) || null,
                averagingLimit: levels.length,
              });
            }
          } catch {
            // Grid state not available
          }
        }
      } catch {
        // API not available
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [symbol]);

  async function handleSettingChange(field: 'avg_enabled' | 'non_stop' | 'partial_sell' | 'formula_mode', value: boolean | string) {
    if (!detail) return;
    setSettingsSaving(true);
    try {
      await api.updateCoinSettings(detail.id, { [field]: value });
      if (field === 'avg_enabled') setAvgEnabled(value as boolean);
      if (field === 'non_stop') setNonStop(value as boolean);
      if (field === 'partial_sell') setPartial(value as boolean);
      if (field === 'formula_mode') setFormula(value as string);
    } catch {
      // Revert on error — state already updated optimistically
    } finally {
      setSettingsSaving(false);
    }
  }

  async function handlePauseResume() {
    if (!detail) return;
    setPausing(true);
    try {
      if (detail.status === 'running') {
        await api.pauseTradingInstance(detail.id);
        setDetail({ ...detail, status: 'paused' });
      } else if (detail.status === 'paused') {
        await api.resumeTradingInstance(detail.id);
        setDetail({ ...detail, status: 'running' });
      }
    } catch {
      // Ignore errors
    } finally {
      setPausing(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-violet-500 border-t-transparent" />
      </div>
    );
  }

  if (!detail) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <p className="text-sm text-muted-foreground">No trading instance found for {symbol}</p>
        <button
          onClick={() => router.push('/dashboard/trade')}
          className="mt-4 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-700"
        >
          Back to Trade
        </button>
      </div>
    );
  }

  const isRunning = detail.status === 'running';
  const isProfit = (detail.profit ?? 0) >= 0;

  return (
    <div className="space-y-6">
      {/* Back button + header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push('/dashboard/trade')}
            className="rounded-lg p-2 hover:bg-muted"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-bold tracking-tight">{detail.symbol}</h2>
              <span className={cn('h-2 w-2 rounded-full', STATUS_COLORS[detail.status] ?? 'bg-muted')} />
              <span className="text-xs capitalize text-muted-foreground">{detail.status}</span>
            </div>
            <p className="text-xs text-muted-foreground">{detail.exchange}</p>
          </div>
        </div>
        <button
          disabled={pausing || (detail.status !== 'running' && detail.status !== 'paused')}
          onClick={handlePauseResume}
          className={cn(
            'flex items-center justify-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium text-white transition disabled:opacity-50',
            isRunning ? 'bg-amber-600 hover:bg-amber-700' : 'bg-emerald-600 hover:bg-emerald-700',
          )}
        >
          {isRunning ? <><Pause className="h-4 w-4" /> Pause</> : <><Play className="h-4 w-4" /> Resume</>}
        </button>
      </div>

      {/* Price Card */}
      <Card glass>
        <CardContent className="p-5">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div>
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Current Price</div>
              <div className="mt-1 text-2xl font-bold tabular-nums">${formatPrice(detail.currentPrice)}</div>
              <div className={cn(
                'flex items-center gap-0.5 text-xs',
                detail.change24h > 0 ? 'text-emerald-500' : detail.change24h < 0 ? 'text-red-500' : 'text-muted-foreground',
              )}>
                {detail.change24h > 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                {Math.abs(detail.change24h).toFixed(2)}%
              </div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Avg Price</div>
              <div className="mt-1 text-lg font-semibold tabular-nums">
                {detail.avgPrice ? `$${formatPrice(detail.avgPrice)}` : '—'}
              </div>
              <div className="text-xs text-muted-foreground">
                Step {detail.step ?? '—'}/{detail.totalSteps ?? '—'}
              </div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Quantity</div>
              <div className="mt-1 text-lg font-semibold tabular-nums">
                {detail.qty > 0 ? detail.qty.toFixed(6) : '—'}
              </div>
              <div className="text-xs text-muted-foreground">Holdings</div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Profit / Floating</div>
              <div className={cn(
                'mt-1 text-lg font-bold tabular-nums',
                detail.profit === null ? 'text-muted-foreground' : isProfit ? 'text-emerald-500' : 'text-red-500',
              )}>
                {detail.profit !== null ? `${isProfit ? '+' : ''}$${detail.profit.toFixed(2)}` : '—'}
              </div>
              {detail.profitPct !== null && (
                <div className={cn('text-xs', isProfit ? 'text-emerald-500' : 'text-red-500')}>
                  {isProfit ? '+' : ''}{detail.profitPct.toFixed(2)}%
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Grid Metrics */}
      <Card glass>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-violet-500" />
            Grid Metrics
          </CardTitle>
        </CardHeader>
        <CardContent>
          {gridMetrics ? (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
              <MetricCard
                label="Next Step Price"
                value={gridMetrics.nextStepPrice ? `$${formatPrice(gridMetrics.nextStepPrice)}` : '—'}
                sublabel="Next buy target"
                variant="violet"
              />
              <MetricCard
                label="Drop Rate"
                value={gridMetrics.dropRate !== null ? `${gridMetrics.dropRate.toFixed(2)}%` : '—'}
                sublabel="Per step drop"
              />
              <MetricCard
                label="TP Price"
                value={gridMetrics.tpPrice ? `$${formatPrice(gridMetrics.tpPrice)}` : '—'}
                sublabel="Take profit target"
                variant="profit"
              />
              <MetricCard
                label="TP %"
                value={gridMetrics.tpPct !== null ? `${gridMetrics.tpPct.toFixed(2)}%` : '—'}
                sublabel="Take profit %"
                variant="profit"
              />
              <MetricCard
                label="Buy Amount"
                value={gridMetrics.buyAmount !== null ? `$${gridMetrics.buyAmount.toFixed(2)}` : '—'}
                sublabel="Per grid investment"
              />
              <MetricCard
                label="Avg Limit"
                value={gridMetrics.averagingLimit ?? '—'}
                sublabel="Max steps"
                variant="warning"
              />
            </div>
          ) : (
            <div className="py-8 text-center text-sm text-muted-foreground">
              Grid metrics not available. Initialize the grid to see metrics.
            </div>
          )}
        </CardContent>
      </Card>

      {/* Force Actions */}
      <Card glass>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Zap className="h-5 w-5 text-amber-500" />
            Force Buy / Force Sell
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ForceActions instanceId={detail.id} />
        </CardContent>
      </Card>

      {/* Per-Coin Settings */}
      <Card glass>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5 text-violet-500" />
            Per-Coin Settings
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Avg Toggle */}
          <div className="flex items-center justify-between rounded-lg border border-border/50 bg-card p-3">
            <div>
              <div className="text-sm font-medium">Averaging</div>
              <div className="text-xs text-muted-foreground">Enable/disable averaging for this coin</div>
            </div>
            <button
              onClick={() => {
                const newVal = !avgEnabled;
                setAvgEnabled(newVal);
                handleSettingChange('avg_enabled', newVal);
              }}
              disabled={settingsSaving}
              className={cn(
                'relative h-6 w-11 rounded-full transition-colors disabled:opacity-50',
                avgEnabled ? 'bg-violet-600' : 'bg-muted',
              )}
            >
              <span className={cn(
                'absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform',
                avgEnabled ? 'translate-x-5' : 'translate-x-0.5',
              )} />
            </button>
          </div>

          {/* Formula */}
          <div className="flex items-center justify-between rounded-lg border border-border/50 bg-card p-3">
            <div>
              <div className="text-sm font-medium">Formula</div>
              <div className="text-xs text-muted-foreground">Averaging formula mode</div>
            </div>
            <select
              value={formula}
              onChange={(e) => {
                const newVal = e.target.value;
                setFormula(newVal);
                handleSettingChange('formula_mode', newVal);
              }}
              disabled={settingsSaving}
              className="rounded-lg border border-border bg-background px-3 py-1.5 text-sm focus:border-violet-500 focus:outline-none disabled:opacity-50"
            >
              <option value="default">Default</option>
              <option value="aggressive">Aggressive</option>
              <option value="conservative">Conservative</option>
            </select>
          </div>

          {/* Non-Stop */}
          <div className="flex items-center justify-between rounded-lg border border-border/50 bg-card p-3">
            <div>
              <div className="text-sm font-medium">Non-Stop</div>
              <div className="text-xs text-muted-foreground">Continue averaging without stopping at limit</div>
            </div>
            <button
              onClick={() => {
                const newVal = !nonStop;
                setNonStop(newVal);
                handleSettingChange('non_stop', newVal);
              }}
              disabled={settingsSaving}
              className={cn(
                'relative h-6 w-11 rounded-full transition-colors disabled:opacity-50',
                nonStop ? 'bg-violet-600' : 'bg-muted',
              )}
            >
              <span className={cn(
                'absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform',
                nonStop ? 'translate-x-5' : 'translate-x-0.5',
              )} />
            </button>
          </div>

          {/* Partial */}
          <div className="flex items-center justify-between rounded-lg border border-border/50 bg-card p-3">
            <div>
              <div className="text-sm font-medium">Partial Sell</div>
              <div className="text-xs text-muted-foreground">Allow partial selling instead of full position</div>
            </div>
            <button
              onClick={() => {
                const newVal = !partial;
                setPartial(newVal);
                handleSettingChange('partial_sell', newVal);
              }}
              disabled={settingsSaving}
              className={cn(
                'relative h-6 w-11 rounded-full transition-colors disabled:opacity-50',
                partial ? 'bg-violet-600' : 'bg-muted',
              )}
            >
              <span className={cn(
                'absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform',
                partial ? 'translate-x-5' : 'translate-x-0.5',
              )} />
            </button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
