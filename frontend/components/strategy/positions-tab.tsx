'use client';

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Layers, Search, ChevronDown, ChevronRight, RefreshCw } from 'lucide-react';
import { cn, formatNumber } from '@/lib/utils';
import { api } from '@/services/api';
import { FilterChips, type FilterType } from '@/components/trade/filter-chips';
import { CoinRow, type CoinRowData } from '@/components/trade/coin-row';
import { useRouter } from 'next/navigation';

interface GridLevelData {
  index: number;
  price: number;
  buy_price: number;
  sell_price: number;
  side: string;
  status: string;
  quantity: number;
  order_id: string | null;
}

interface GridStateData {
  instance_id: string;
  status: string;
  symbol: string;
  current_price: number | null;
  upper_price: number;
  lower_price: number;
  grid_count: number;
  grid_spacing: number;
  investment_per_grid: number;
  total_cycles: number;
  total_profit: number;
  levels: GridLevelData[];
}

const gridStatusColors: Record<string, 'default' | 'secondary' | 'success' | 'destructive' | 'warning'> = {
  waiting: 'secondary',
  open: 'default',
  filled: 'success',
  cancelled: 'destructive',
  tp_hit: 'warning',
};

export function PositionsTab() {
  const router = useRouter();
  const [tradingInstances, setTradingInstances] = useState<CoinRowData[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [filter, setFilter] = useState<FilterType>('all');
  const [selectedExchange, setSelectedExchange] = useState<string>('all');
  const [exchanges, setExchanges] = useState<string[]>([]);

  // Grid levels inline expandable state (replaces separate Grid Levels tab)
  const [expandedInstanceId, setExpandedInstanceId] = useState<string | null>(null);
  const [gridState, setGridState] = useState<GridStateData | null>(null);
  const [gridLoading, setGridLoading] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const instances = await api.getTradingInstances().catch(() => [] as Record<string, unknown>[]);
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
      // ignore
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, [loadData]);

  // Load grid state for expanded instance
  const loadGridState = useCallback(async () => {
    if (!expandedInstanceId) {
      setGridState(null);
      return;
    }
    setGridLoading(true);
    try {
      const state = await api.getGridState(expandedInstanceId);
      setGridState(state as GridStateData);
    } catch {
      setGridState(null);
    } finally {
      setGridLoading(false);
    }
  }, [expandedInstanceId]);

  useEffect(() => {
    loadGridState();
    // Refresh grid state every 3s while expanded
    if (!expandedInstanceId) return;
    const interval = setInterval(loadGridState, 3000);
    return () => clearInterval(interval);
  }, [loadGridState, expandedInstanceId]);

  function toggleExpand(instanceId: string) {
    setExpandedInstanceId((prev) => (prev === instanceId ? null : instanceId));
  }

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
      {activeCount > 0 && (
        <Badge variant="success" className="text-sm">
          {activeCount} Active
        </Badge>
      )}

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

          <FilterChips active={filter} onChange={setFilter} counts={filterCounts} />

          {/* Table Header — desktop only */}
          <div className="hidden grid-cols-12 gap-2 border-b border-border/50 px-3 pb-2 text-[10px] font-medium uppercase tracking-wider text-muted-foreground md:grid">
            <div className="col-span-3">Pair</div>
            <div className="col-span-2">Qty</div>
            <div className="col-span-2">Price / 24h</div>
            <div className="col-span-2">Avg / Step</div>
            <div className="col-span-3 text-right">Profit / Floating</div>
          </div>

          {/* Rows with expandable grid levels */}
          {filteredInstances.length > 0 ? (
            <div className="space-y-1.5">
              {filteredInstances.map((inst) => {
                const isExpanded = expandedInstanceId === inst.id;
                return (
                  <div key={inst.id} className="rounded-lg border border-border/50">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => toggleExpand(inst.id)}
                        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:bg-muted"
                        aria-label={isExpanded ? 'Collapse grid levels' : 'Expand grid levels'}
                      >
                        {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                      </button>
                      <div className="flex-1 cursor-pointer" onClick={() => router.push(`/dashboard/strategy-setting/${inst.symbol}`)}>
                        <CoinRow data={inst} />
                      </div>
                    </div>

                    {isExpanded && (
                      <div className="border-t border-border/50 bg-muted/20 p-3">
                        <div className="mb-3 flex items-center justify-between">
                          <div className="text-sm font-medium">
                            Grid Levels
                            {gridState && (
                              <span className="ml-2 text-xs text-muted-foreground">
                                {gridState.grid_count} levels
                                {gridState.total_cycles > 0 && (
                                  <> | {gridState.total_cycles} cycles | {gridState.total_profit.toFixed(2)} profit</>
                                )}
                              </span>
                            )}
                          </div>
                          <Button size="sm" variant="outline" onClick={loadGridState} disabled={gridLoading}>
                            <RefreshCw className={cn('h-3 w-3', gridLoading && 'animate-spin')} />
                            <span className="ml-1">Refresh</span>
                          </Button>
                        </div>

                        {!gridState || gridState.levels.length === 0 ? (
                          <p className="py-4 text-center text-sm text-muted-foreground">
                            {gridState?.status === 'no_grid'
                              ? 'Grid has not been initialized yet. Start the bot to begin grid trading.'
                              : 'No grid levels found. The bot may not be running.'}
                          </p>
                        ) : (
                          <div className="max-h-80 space-y-1.5 overflow-y-auto">
                            {gridState.levels.map((level) => (
                              <div
                                key={level.index}
                                className="flex flex-col gap-2 rounded-md border border-border/40 bg-background p-2 text-xs sm:flex-row sm:items-center sm:justify-between"
                              >
                                <div className="flex items-center gap-2">
                                  <span className="text-muted-foreground">#{level.index}</span>
                                  <Badge variant={level.side === 'buy' ? 'success' : 'destructive'}>
                                    {level.side.toUpperCase()}
                                  </Badge>
                                  <div className="flex flex-col">
                                    <span className="font-medium">${formatNumber(level.buy_price)}</span>
                                    {level.sell_price > 0 && (
                                      <span className="text-[10px] text-muted-foreground">
                                        sell: ${formatNumber(level.sell_price)}
                                      </span>
                                    )}
                                  </div>
                                </div>
                                <div className="flex items-center gap-2">
                                  <span className="text-muted-foreground">
                                    {level.quantity} {gridState.symbol.replace('USDT', '').replace('BUSD', '')}
                                  </span>
                                  <Badge variant={gridStatusColors[level.status] || 'secondary'}>
                                    {level.status}
                                  </Badge>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Layers className="mb-2 h-8 w-8 text-muted-foreground/50" />
              <p className="text-sm text-muted-foreground">
                {tradingInstances.length === 0
                  ? 'No trading instances yet. Create one from the Setup tab.'
                  : 'No results match your filters.'}
              </p>
            </div>
          )}

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

          <p className="text-xs text-muted-foreground">
            Tip: click <ChevronRight className="inline h-3 w-3" /> on a row to expand its grid levels.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
