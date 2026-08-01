'use client';

import { useEffect, useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { TrendingUp, TrendingDown, Search, RefreshCw, DollarSign, BarChart3, Activity, ChevronDown, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/services/api';

interface Ticker24h {
  symbol: string;
  lastPrice: string;
  priceChangePercent: string;
  quoteVolume: string;
  highPrice: string;
  lowPrice: string;
}

interface CoinMarketData {
  id: string;
  symbol: string;
  current_price: number;
  market_cap: number;
  market_cap_rank: number;
  total_volume: number;
  price_change_percentage_24h: number;
}

interface PortfolioSummary {
  total_value: string;
  total_investment: string;
  total_pnl: string;
  pnl_percentage: string;
}

interface PositionData {
  id: string;
  trading_instance_id: string;
  symbol: string;
  side: string;
  quantity: string;
  entry_price: string;
  current_price: string;
  value: string;
  unrealized_pnl: string;
  realized_pnl: string;
}

interface OrderHistoryItem {
  id: string;
  exchange_order_id: string;
  symbol: string;
  side: string;
  order_type: string;
  quantity: string;
  price: string | null;
  filled_quantity: string;
  average_fill_price: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

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

type SortKey = 'volume' | 'marketCap' | 'change';

function formatNumber(val: number): string {
  if (val >= 1e9) return (val / 1e9).toFixed(2) + 'B';
  if (val >= 1e6) return (val / 1e6).toFixed(2) + 'M';
  if (val >= 1e3) return (val / 1e3).toFixed(2) + 'K';
  return val.toFixed(2);
}

function formatPrice(val: string | number): string {
  const num = typeof val === 'string' ? parseFloat(val) : val;
  if (isNaN(num)) return 'â€”';
  if (num >= 1000) return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  if (num >= 1) return num.toFixed(4);
  if (num >= 0.01) return num.toFixed(6);
  return num.toFixed(8);
}

export default function PortfolioPage() {
  const [tickers, setTickers] = useState<Ticker24h[]>([]);
  const [coinData, setCoinData] = useState<Map<string, CoinMarketData>>(new Map());
  const [portfolio, setPortfolio] = useState<PortfolioSummary | null>(null);
  const [positions, setPositions] = useState<PositionData[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('volume');
  const [activeTab, setActiveTab] = useState<'markets' | 'positions'>('markets');
  const [expandedSymbol, setExpandedSymbol] = useState<string | null>(null);
  const [symbolOrders, setSymbolOrders] = useState<Record<string, OrderHistoryItem[]>>({});
  const [ordersLoading, setOrdersLoading] = useState<string | null>(null);
  const [symbolGridStates, setSymbolGridStates] = useState<Record<string, GridStateData[]>>({});
  const [gridLoading, setGridLoading] = useState<string | null>(null);

  async function toggleSymbolOrders(symbol: string, instanceIds: string[] = []) {
    if (expandedSymbol === symbol) {
      setExpandedSymbol(null);
      return;
    }
    setExpandedSymbol(symbol);
    // Load order history (deduped by symbol)
    if (!symbolOrders[symbol]) {
      setOrdersLoading(symbol);
      try {
        const data = await api.get(`/api/v1/orders?symbol=${encodeURIComponent(symbol)}&limit=50`);
        setSymbolOrders((prev) => ({ ...prev, [symbol]: (data as OrderHistoryItem[]) ?? [] }));
      } catch {
        setSymbolOrders((prev) => ({ ...prev, [symbol]: [] }));
      } finally {
        setOrdersLoading(null);
      }
    }
    // Load grid state per trading instance for this symbol
    if (instanceIds.length > 0 && !symbolGridStates[symbol]) {
      setGridLoading(symbol);
      try {
        const results = await Promise.all(
          instanceIds.map((id) =>
            api.getGridState(id).catch(() => null),
          ),
        );
        const valid = (results.filter(Boolean) as GridStateData[]);
        setSymbolGridStates((prev) => ({ ...prev, [symbol]: valid }));
      } catch {
        setSymbolGridStates((prev) => ({ ...prev, [symbol]: [] }));
      } finally {
        setGridLoading(null);
      }
    }
  }

  const loadData = useCallback(async () => {
    setRefreshing(true);
    try {
      // Fetch 24h tickers from backend (which proxies to Binance)
      let allTickers: Ticker24h[] = [];
      try {
        const data = await api.getMarketTickers('binance', 200);
        allTickers = data.map((d) => ({
          symbol: d.symbol,
          lastPrice: d.last_price,
          priceChangePercent: d.price_change_percent,
          quoteVolume: d.quote_volume,
          highPrice: d.high_price,
          lowPrice: d.low_price,
        }));
      } catch {
        // Fallback: direct Binance public API
        const tickerRes = await fetch('https://api.binance.com/api/v3/ticker/24hr');
        const raw: Ticker24h[] = await tickerRes.json();
        allTickers = raw;
      }

      const usdtTickers = allTickers
        .filter((t) => t.symbol.endsWith('USDT') && !t.symbol.includes('UP') && !t.symbol.includes('DOWN'))
        .sort((a, b) => parseFloat(b.quoteVolume) - parseFloat(a.quoteVolume))
        .slice(0, 200);

      // Fetch CoinGecko market data for market cap
      const coinMap = new Map<string, CoinMarketData>();
      try {
        const cgRes = await fetch(
          'https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=250&page=1&sparkline=false'
        );
        const cgData: CoinMarketData[] = await cgRes.json();
        for (const coin of cgData) {
          coinMap.set(coin.symbol.toUpperCase(), coin);
        }
      } catch {
        // CoinGecko not available â€” market cap will show as "â€”"
      }

      setTickers(usdtTickers);
      setCoinData(coinMap);

      // Fetch user portfolio from backend
      try {
        const pfData = await api.getPortfolio() as Record<string, unknown>;
        const summary = pfData.summary as Record<string, string>;
        setPortfolio({
          total_value: summary?.total_value ?? '0',
          total_investment: summary?.total_investment ?? '0',
          total_pnl: summary?.total_pnl ?? '0',
          pnl_percentage: summary?.pnl_percentage ?? '0',
        });
        const posList = (pfData.positions ?? []) as PositionData[];
        setPositions(posList);
      } catch {
        // Backend not available
      }
    } catch {
      // API not available
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Merge ticker data with coin market cap data
  const mergedData = tickers
    .map((t) => {
      const baseAsset = t.symbol.replace('USDT', '');
      const coin = coinData.get(baseAsset);
      return {
        symbol: t.symbol,
        baseAsset,
        price: parseFloat(t.lastPrice),
        change24h: parseFloat(t.priceChangePercent),
        volume24h: parseFloat(t.quoteVolume),
        high24h: parseFloat(t.highPrice),
        low24h: parseFloat(t.lowPrice),
        marketCap: coin?.market_cap ?? 0,
        marketCapRank: coin?.market_cap_rank ?? 999,
      };
    })
    .filter((d) => {
      if (searchQuery && !d.symbol.toLowerCase().includes(searchQuery.toLowerCase())) return false;
      return true;
    });

  // Sort by selected key
  const sortedData = [...mergedData].sort((a, b) => {
    if (sortKey === 'volume') return b.volume24h - a.volume24h;
    if (sortKey === 'marketCap') return b.marketCap - a.marketCap;
    if (sortKey === 'change') return b.change24h - a.change24h;
    return 0;
  }).slice(0, 100);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-violet-500 border-t-transparent" />
      </div>
    );
  }

  const pnlPositive = parseFloat(portfolio?.total_pnl ?? '0') >= 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-bold tracking-tight">Portfolio</h2>
          <p className="text-sm text-muted-foreground">Top 100 pairs by volume & market cap</p>
        </div>
        <button
          onClick={loadData}
          disabled={refreshing}
          className="flex items-center gap-1.5 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-violet-700 disabled:opacity-50"
        >
          <RefreshCw className={cn('h-4 w-4', refreshing && 'animate-spin')} />
          {refreshing ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {/* Portfolio Summary Cards (from backend) */}
      {portfolio && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Card glass>
            <CardContent className="p-4">
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <DollarSign className="h-3.5 w-3.5" />
                Total Value
              </div>
              <p className="mt-1 text-lg font-bold tabular-nums">${formatPrice(portfolio.total_value)}</p>
            </CardContent>
          </Card>
          <Card glass>
            <CardContent className="p-4">
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <DollarSign className="h-3.5 w-3.5" />
                Investment
              </div>
              <p className="mt-1 text-lg font-bold tabular-nums">${formatPrice(portfolio.total_investment)}</p>
            </CardContent>
          </Card>
          <Card glass>
            <CardContent className="p-4">
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Activity className="h-3.5 w-3.5" />
                PnL
              </div>
              <p className={cn(
                'mt-1 text-lg font-bold tabular-nums',
                pnlPositive ? 'text-emerald-500' : 'text-red-500',
              )}>
                {pnlPositive ? '+' : ''}${formatPrice(portfolio.total_pnl)}
              </p>
            </CardContent>
          </Card>
          <Card glass>
            <CardContent className="p-4">
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <BarChart3 className="h-3.5 w-3.5" />
                PnL %
              </div>
              <p className={cn(
                'mt-1 text-lg font-bold tabular-nums',
                pnlPositive ? 'text-emerald-500' : 'text-red-500',
              )}>
                {pnlPositive ? '+' : ''}{parseFloat(portfolio.pnl_percentage).toFixed(2)}%
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tab Switch: Markets vs My Positions */}
      <div className="flex gap-2">
        <button
          onClick={() => setActiveTab('markets')}
          className={cn(
            'rounded-lg px-4 py-2 text-sm font-medium transition',
            activeTab === 'markets' ? 'bg-violet-600 text-white' : 'bg-muted text-muted-foreground hover:bg-accent',
          )}
        >
          Top 100 Markets
        </button>
        <button
          onClick={() => setActiveTab('positions')}
          className={cn(
            'rounded-lg px-4 py-2 text-sm font-medium transition',
            activeTab === 'positions' ? 'bg-violet-600 text-white' : 'bg-muted text-muted-foreground hover:bg-accent',
          )}
        >
          My Positions ({positions.length})
        </button>
      </div>

      {activeTab === 'positions' ? (
        /* My Positions Table — grouped by symbol, click to expand order history + grid levels */
        <Card glass>
          <CardHeader>
            <CardTitle>My Open Positions</CardTitle>
            <p className="text-xs text-muted-foreground">Click a coin to view its grid levels & order history.</p>
          </CardHeader>
          <CardContent>
            {positions.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <Activity className="mb-2 h-8 w-8 text-muted-foreground/50" />
                <p className="text-sm text-muted-foreground">No open positions yet.</p>
              </div>
            ) : (
              (() => {
                // Group positions by symbol (a symbol may have multiple positions across bots)
                const bySymbol = positions.reduce<Record<string, PositionData[]>>((acc, p) => {
                  (acc[p.symbol] ??= []).push(p);
                  return acc;
                }, {});
                const symbols = Object.keys(bySymbol).sort();
                return (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-border text-left text-xs text-muted-foreground">
                          <th className="py-2 pr-4 w-8"></th>
                          <th className="py-2 pr-4">Symbol</th>
                          <th className="py-2 pr-4">Positions</th>
                          <th className="py-2 pr-4">Total Qty</th>
                          <th className="py-2 pr-4">Avg Entry</th>
                          <th className="py-2 pr-4">Current</th>
                          <th className="py-2 pr-4">Total Value</th>
                          <th className="py-2 pr-4 text-right">Total PnL</th>
                        </tr>
                      </thead>
                      <tbody>
                        {symbols.map((symbol) => {
                          const posList = bySymbol[symbol];
                          const totalQty = posList.reduce((s, p) => s + parseFloat(p.quantity), 0);
                          const totalValue = posList.reduce((s, p) => s + parseFloat(p.value), 0);
                          const totalPnl = posList.reduce(
                            (s, p) => s + parseFloat(p.unrealized_pnl) + parseFloat(p.realized_pnl),
                            0,
                          );
                          const avgEntry =
                            posList.reduce((s, p) => s + parseFloat(p.entry_price) * parseFloat(p.quantity), 0) /
                            (totalQty || 1);
                          const currentPrice = posList[0]?.current_price ?? '0';
                          const isProfit = totalPnl >= 0;
                          const isExpanded = expandedSymbol === symbol;
                          const orders = symbolOrders[symbol];
                          const gridStates = symbolGridStates[symbol];
                          const instanceIds = posList.map((p) => p.trading_instance_id);
                          return (
                            <SymbolRow
                              key={symbol}
                              symbol={symbol}
                              posCount={posList.length}
                              totalQty={totalQty}
                              avgEntry={avgEntry}
                              currentPrice={currentPrice}
                              totalValue={totalValue}
                              totalPnl={totalPnl}
                              isProfit={isProfit}
                              isExpanded={isExpanded}
                              onToggle={() => toggleSymbolOrders(symbol, instanceIds)}
                              orders={orders}
                              ordersLoading={ordersLoading === symbol}
                              gridStates={gridStates}
                              gridLoading={gridLoading === symbol}
                            />
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                );
              })()
            )}
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Search + Sort Controls */}
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search pair (e.g. BTC, ETH, SOL)..."
                className="w-full rounded-lg border border-border bg-background py-2 pl-9 pr-3 text-sm focus:border-violet-500 focus:outline-none"
              />
            </div>
            <div className="flex gap-1">
              {(['volume', 'marketCap', 'change'] as SortKey[]).map((key) => (
                <button
                  key={key}
                  onClick={() => setSortKey(key)}
                  className={cn(
                    'rounded-lg px-3 py-2 text-xs font-medium transition',
                    sortKey === key ? 'bg-violet-600 text-white' : 'bg-muted text-muted-foreground hover:bg-accent',
                  )}
                >
                  {key === 'volume' ? 'Volume' : key === 'marketCap' ? 'Market Cap' : 'Change %'}
                </button>
              ))}
            </div>
          </div>

          {/* Top 100 Table */}
          <Card glass>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>Top 100 USDT Pairs</span>
                <span className="text-xs font-normal text-muted-foreground">
                  Sorted by {sortKey === 'volume' ? '24h Volume' : sortKey === 'marketCap' ? 'Market Cap' : '24h Change'}
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {sortedData.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <BarChart3 className="mb-2 h-8 w-8 text-muted-foreground/50" />
                  <p className="text-sm text-muted-foreground">
                    {tickers.length === 0 ? 'Failed to load market data. Try refreshing.' : 'No results match your search.'}
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border text-left text-xs text-muted-foreground">
                        <th className="py-2 pr-2 w-8">#</th>
                        <th className="py-2 pr-4">Pair</th>
                        <th className="py-2 pr-4 text-right">Price</th>
                        <th className="py-2 pr-4 text-right">24h Change</th>
                        <th className="py-2 pr-4 text-right">24h Volume</th>
                        <th className="py-2 pr-4 text-right">Market Cap</th>
                        <th className="py-2 pr-4 text-right hidden lg:table-cell">24h High</th>
                        <th className="py-2 pr-4 text-right hidden lg:table-cell">24h Low</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sortedData.map((d, idx) => {
                        const isPositive = d.change24h >= 0;
                        return (
                          <tr
                            key={d.symbol}
                            className="border-b border-border/30 transition hover:bg-muted/30"
                          >
                            <td className="py-2 pr-2 text-xs text-muted-foreground tabular-nums">{idx + 1}</td>
                            <td className="py-2 pr-4">
                              <div className="flex items-center gap-2">
                                <span className="font-medium">{d.baseAsset}</span>
                                <span className="text-xs text-muted-foreground">/USDT</span>
                                {d.marketCapRank <= 10 && (
                                  <Badge variant="warning" className="text-[9px] px-1.5 py-0">#{d.marketCapRank}</Badge>
                                )}
                              </div>
                            </td>
                            <td className="py-2 pr-4 text-right font-medium tabular-nums">
                              ${formatPrice(d.price)}
                            </td>
                            <td className={cn(
                              'py-2 pr-4 text-right tabular-nums font-medium',
                              isPositive ? 'text-emerald-500' : 'text-red-500',
                            )}>
                              <span className="inline-flex items-center gap-0.5">
                                {isPositive ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                                {isPositive ? '+' : ''}{d.change24h.toFixed(2)}%
                              </span>
                            </td>
                            <td className="py-2 pr-4 text-right tabular-nums text-muted-foreground">
                              ${formatNumber(d.volume24h)}
                            </td>
                            <td className="py-2 pr-4 text-right tabular-nums text-muted-foreground">
                              {d.marketCap > 0 ? `$${formatNumber(d.marketCap)}` : 'â€”'}
                            </td>
                            <td className="py-2 pr-4 text-right tabular-nums text-muted-foreground hidden lg:table-cell">
                              ${formatPrice(d.high24h)}
                            </td>
                            <td className="py-2 pr-4 text-right tabular-nums text-muted-foreground hidden lg:table-cell">
                              ${formatPrice(d.low24h)}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

interface SymbolRowProps {
  symbol: string;
  posCount: number;
  totalQty: number;
  avgEntry: number;
  currentPrice: string;
  totalValue: number;
  totalPnl: number;
  isProfit: boolean;
  isExpanded: boolean;
  onToggle: () => void;
  orders: OrderHistoryItem[] | undefined;
  ordersLoading: boolean;
  gridStates: GridStateData[] | undefined;
  gridLoading: boolean;
}

function SymbolRow({
  symbol,
  posCount,
  totalQty,
  avgEntry,
  currentPrice,
  totalValue,
  totalPnl,
  isProfit,
  isExpanded,
  onToggle,
  orders,
  ordersLoading,
  gridStates,
  gridLoading,
}: SymbolRowProps) {
  return (
    <>
      <tr
        className="border-b border-border/50 cursor-pointer hover:bg-muted/30 transition"
        onClick={onToggle}
      >
        <td className="py-2 pr-4 text-muted-foreground">
          {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </td>
        <td className="py-2 pr-4 font-medium">{symbol}</td>
        <td className="py-2 pr-4 tabular-nums text-muted-foreground">{posCount}</td>
        <td className="py-2 pr-4 tabular-nums">{totalQty.toFixed(6)}</td>
        <td className="py-2 pr-4 tabular-nums">${formatPrice(avgEntry)}</td>
        <td className="py-2 pr-4 tabular-nums">${formatPrice(currentPrice)}</td>
        <td className="py-2 pr-4 tabular-nums">${formatPrice(totalValue)}</td>
        <td className={cn('py-2 pr-4 text-right font-medium tabular-nums', isProfit ? 'text-emerald-500' : 'text-red-500')}>
          {isProfit ? '+' : ''}${totalPnl.toFixed(2)}
        </td>
      </tr>
      {isExpanded && (
        <tr className="border-b border-border/50 bg-muted/20">
          <td colSpan={8} className="p-4 space-y-4">
            {/* Grid levels per bot instance */}
            <div>
              <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Grid Levels — {symbol}
              </div>
              {gridLoading ? (
                <p className="text-sm text-muted-foreground">Loading grid levels…</p>
              ) : !gridStates || gridStates.length === 0 ? (
                <p className="text-sm text-muted-foreground">No active grid for this symbol.</p>
              ) : (
                <div className="space-y-3">
                  {gridStates.map((gs) => (
                    <div key={gs.instance_id} className="rounded-lg border border-border/50 p-3">
                      <div className="mb-2 flex flex-wrap items-center gap-2 text-xs">
                        <Badge variant={gs.status === 'running' ? 'success' : 'secondary'}>
                          {gs.status}
                        </Badge>
                        <span className="text-muted-foreground">
                          {gs.grid_count} levels · spacing {gs.grid_spacing?.toFixed(2)}% · cycles {gs.total_cycles} · profit ${gs.total_profit?.toFixed(2)}
                        </span>
                      </div>
                      <div className="overflow-x-auto">
                        <table className="w-full text-xs">
                          <thead>
                            <tr className="border-b border-border text-left text-muted-foreground">
                              <th className="py-1.5 pr-3">#</th>
                              <th className="py-1.5 pr-3">Side</th>
                              <th className="py-1.5 pr-3">Buy</th>
                              <th className="py-1.5 pr-3">Sell</th>
                              <th className="py-1.5 pr-3">Qty</th>
                              <th className="py-1.5 pr-3">Status</th>
                            </tr>
                          </thead>
                          <tbody>
                            {gs.levels.map((lvl) => (
                              <tr key={lvl.index} className="border-b border-border/30">
                                <td className="py-1.5 pr-3 tabular-nums">{lvl.index}</td>
                                <td className="py-1.5 pr-3">{lvl.side}</td>
                                <td className="py-1.5 pr-3 tabular-nums">${formatPrice(lvl.buy_price)}</td>
                                <td className="py-1.5 pr-3 tabular-nums">${formatPrice(lvl.sell_price)}</td>
                                <td className="py-1.5 pr-3 tabular-nums">{lvl.quantity}</td>
                                <td className="py-1.5 pr-3">
                                  <Badge
                                    variant={
                                      lvl.status === 'filled' ? 'success' :
                                      lvl.status === 'tp_hit' ? 'warning' :
                                      lvl.status === 'cancelled' ? 'destructive' : 'secondary'
                                    }
                                  >
                                    {lvl.status.replace('_', ' ')}
                                  </Badge>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Order history */}
            <div>
              <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Order History — {symbol}
              </div>
              {ordersLoading ? (
                <p className="text-sm text-muted-foreground">Loading orders…</p>
              ) : !orders || orders.length === 0 ? (
                <p className="text-sm text-muted-foreground">No orders for this symbol yet.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-border text-left text-muted-foreground">
                        <th className="py-1.5 pr-3">Side</th>
                        <th className="py-1.5 pr-3">Type</th>
                        <th className="py-1.5 pr-3">Qty</th>
                        <th className="py-1.5 pr-3">Price</th>
                        <th className="py-1.5 pr-3">Status</th>
                        <th className="py-1.5 pr-3 text-right">Date</th>
                      </tr>
                    </thead>
                    <tbody>
                      {orders.map((o) => (
                        <tr key={o.id} className="border-b border-border/30">
                          <td className="py-1.5 pr-3">
                            <Badge variant={o.side === 'buy' ? 'success' : 'destructive'}>{o.side}</Badge>
                          </td>
                          <td className="py-1.5 pr-3">{o.order_type}</td>
                          <td className="py-1.5 pr-3 tabular-nums">{o.quantity}</td>
                          <td className="py-1.5 pr-3 tabular-nums">{o.price ? `$${formatPrice(o.price)}` : '—'}</td>
                          <td className="py-1.5 pr-3">{o.status.replace('_', ' ')}</td>
                          <td className="py-1.5 pr-3 text-right text-muted-foreground">
                            {new Date(o.created_at).toLocaleString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
