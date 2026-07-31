'use client';

<<<<<<< HEAD
import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatCurrency, formatNumber } from '@/lib/utils';
import { Wallet, TrendingUp, TrendingDown, ArrowUpRight, ArrowDownRight } from 'lucide-react';
import type { Position } from '@/types';

export default function PortfolioPage() {
  const [positions, setPositions] = useState<Position[]>([]);

  useEffect(() => {
    setPositions([
      { id: '1', instance_id: 'i1', symbol: 'BTC/USDT', side: 'long', quantity: 0.3, entry_price: 62000, current_price: 65000, unrealized_pnl: 900, realized_pnl: 200, status: 'open' },
      { id: '2', instance_id: 'i2', symbol: 'ETH/USDT', side: 'long', quantity: 5.0, entry_price: 3100, current_price: 3200, unrealized_pnl: 500, realized_pnl: 100, status: 'open' },
      { id: '3', instance_id: 'i3', symbol: 'SOL/USDT', side: 'long', quantity: 50, entry_price: 135, current_price: 140, unrealized_pnl: 250, realized_pnl: 0, status: 'open' },
    ]);
  }, []);

  const totalUnrealized = positions.reduce((sum, p) => sum + p.unrealized_pnl, 0);
  const totalRealized = positions.reduce((sum, p) => sum + p.realized_pnl, 0);
  const totalPnl = totalUnrealized + totalRealized;

  return (
    <>
      {/* Mobile */}
      <div className="min-h-full bg-slate-50 pb-24 dark:bg-background md:hidden">
        <section className="relative overflow-hidden rounded-b-[2rem] bg-gradient-to-br from-violet-700 via-purple-600 to-fuchsia-600 px-5 pb-24 pt-[max(1.25rem,env(safe-area-inset-top))] text-white">
          <div className="absolute -right-14 top-4 h-44 w-44 rounded-full bg-fuchsia-400/20 blur-2xl" />
          <div className="relative flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-white/15 backdrop-blur-sm">
              <Wallet className="h-5 w-5" />
            </span>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">Portfolio</h1>
              <p className="text-sm text-violet-200">{positions.length} open positions</p>
            </div>
          </div>
        </section>

        <div className="relative -mt-16 px-4 space-y-3">
          {/* PnL Summary Card */}
          <div className="overflow-hidden rounded-3xl bg-white shadow-xl shadow-slate-900/10 dark:bg-card">
            <div className="grid grid-cols-3 divide-x divide-slate-200 dark:divide-border">
              <div className="p-4 text-center">
                <p className="text-xs font-semibold text-muted-foreground">Unrealized</p>
                <p className="mt-1 text-lg font-bold text-emerald-500">{formatCurrency(totalUnrealized)}</p>
              </div>
              <div className="p-4 text-center">
                <p className="text-xs font-semibold text-muted-foreground">Realized</p>
                <p className="mt-1 text-lg font-bold text-emerald-500">{formatCurrency(totalRealized)}</p>
              </div>
              <div className="p-4 text-center">
                <p className="text-xs font-semibold text-muted-foreground">Total</p>
                <p className="mt-1 text-lg font-bold text-emerald-500">{formatCurrency(totalPnl)}</p>
              </div>
            </div>
          </div>

          {/* Position Cards */}
          <p className="px-1 pt-2 text-sm font-semibold text-slate-700 dark:text-slate-300">Open Positions</p>
          {positions.map((p) => {
            const isProfit = p.unrealized_pnl >= 0;
            const pnlPct = ((p.current_price - p.entry_price) / p.entry_price) * 100;
            return (
              <div key={p.id} className="overflow-hidden rounded-2xl bg-white shadow-lg shadow-slate-900/5 transition-transform active:scale-[0.99] dark:bg-card">
                <div className="flex items-center justify-between p-4">
                  <div className="flex items-center gap-3">
                    <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-100 text-sm font-bold text-violet-600 dark:bg-violet-500/10">
                      {p.symbol.split('/')[0].slice(0, 2)}
                    </span>
                    <div>
                      <p className="font-semibold">{p.symbol}</p>
                      <p className="text-xs text-muted-foreground uppercase">{p.side}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className={`flex items-center justify-end gap-0.5 font-bold ${isProfit ? 'text-emerald-500' : 'text-red-500'}`}>
                      {isProfit ? <ArrowUpRight className="h-4 w-4" /> : <ArrowDownRight className="h-4 w-4" />}
                      {formatCurrency(Math.abs(p.unrealized_pnl))}
                    </p>
                    <p className={`text-xs ${isProfit ? 'text-emerald-500' : 'text-red-500'}`}>
                      {isProfit ? '+' : ''}{pnlPct.toFixed(2)}%
                    </p>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-2 border-t border-slate-100 px-4 py-3 text-xs dark:border-border">
                  <div>
                    <p className="text-muted-foreground">Qty</p>
                    <p className="font-medium tabular-nums">{formatNumber(p.quantity)}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Entry</p>
                    <p className="font-medium tabular-nums">${formatNumber(p.entry_price)}</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Current</p>
                    <p className="font-medium tabular-nums">${formatNumber(p.current_price)}</p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Desktop */}
      <div className="hidden space-y-6 md:block">
        <h1 className="text-2xl font-bold">Portfolio</h1>
        <div className="grid gap-4 grid-cols-1 sm:grid-cols-3">
          <Card>
            <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Unrealized PnL</CardTitle></CardHeader>
            <CardContent><p className="text-2xl font-bold text-green-500">{formatCurrency(totalUnrealized)}</p></CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Realized PnL</CardTitle></CardHeader>
            <CardContent><p className="text-2xl font-bold text-green-500">{formatCurrency(totalRealized)}</p></CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Total PnL</CardTitle></CardHeader>
            <CardContent><p className="text-2xl font-bold text-green-500">{formatCurrency(totalPnl)}</p></CardContent>
          </Card>
        </div>
        <Card>
          <CardHeader><CardTitle>Open Positions</CardTitle></CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="pb-2">Symbol</th>
                    <th className="pb-2">Side</th>
                    <th className="pb-2">Qty</th>
                    <th className="pb-2">Entry</th>
                    <th className="pb-2">Current</th>
                    <th className="pb-2">Unrealized</th>
                    <th className="pb-2">Realized</th>
                  </tr>
                </thead>
                <tbody>
                  {positions.map((p) => (
                    <tr key={p.id} className="border-b">
                      <td className="py-3 font-medium">{p.symbol}</td>
                      <td className="py-3 uppercase">{p.side}</td>
                      <td className="py-3">{formatNumber(p.quantity)}</td>
                      <td className="py-3">${formatNumber(p.entry_price)}</td>
                      <td className="py-3">${formatNumber(p.current_price)}</td>
                      <td className="py-3 text-green-500">{formatCurrency(p.unrealized_pnl)}</td>
                      <td className="py-3 text-green-500">{formatCurrency(p.realized_pnl)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>
    </>
=======
import { useEffect, useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { TrendingUp, TrendingDown, Search, RefreshCw, DollarSign, BarChart3, Activity } from 'lucide-react';
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
  symbol: string;
  side: string;
  quantity: string;
  entry_price: string;
  current_price: string;
  value: string;
  unrealized_pnl: string;
  realized_pnl: string;
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
  if (isNaN(num)) return '—';
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
        // CoinGecko not available — market cap will show as "—"
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
        /* My Positions Table */
        <Card glass>
          <CardHeader>
            <CardTitle>My Open Positions</CardTitle>
          </CardHeader>
          <CardContent>
            {positions.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <Activity className="mb-2 h-8 w-8 text-muted-foreground/50" />
                <p className="text-sm text-muted-foreground">No open positions yet.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-left text-xs text-muted-foreground">
                      <th className="py-2 pr-4">Symbol</th>
                      <th className="py-2 pr-4">Side</th>
                      <th className="py-2 pr-4">Qty</th>
                      <th className="py-2 pr-4">Entry</th>
                      <th className="py-2 pr-4">Current</th>
                      <th className="py-2 pr-4">Value</th>
                      <th className="py-2 pr-4 text-right">PnL</th>
                    </tr>
                  </thead>
                  <tbody>
                    {positions.map((pos) => {
                      const pnl = parseFloat(pos.unrealized_pnl) + parseFloat(pos.realized_pnl);
                      const isProfit = pnl >= 0;
                      return (
                        <tr key={pos.id} className="border-b border-border/50">
                          <td className="py-2 pr-4 font-medium">{pos.symbol}</td>
                          <td className="py-2 pr-4">
                            <Badge variant={pos.side === 'BUY' ? 'success' : 'destructive'}>
                              {pos.side}
                            </Badge>
                          </td>
                          <td className="py-2 pr-4 tabular-nums">{pos.quantity}</td>
                          <td className="py-2 pr-4 tabular-nums">${formatPrice(pos.entry_price)}</td>
                          <td className="py-2 pr-4 tabular-nums">${formatPrice(pos.current_price)}</td>
                          <td className="py-2 pr-4 tabular-nums">${formatPrice(pos.value)}</td>
                          <td className={cn('py-2 pr-4 text-right font-medium tabular-nums', isProfit ? 'text-emerald-500' : 'text-red-500')}>
                            {isProfit ? '+' : ''}${pnl.toFixed(2)}
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
                              {d.marketCap > 0 ? `$${formatNumber(d.marketCap)}` : '—'}
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
>>>>>>> develop
  );
}
