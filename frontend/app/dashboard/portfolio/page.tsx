'use client';

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
  );
}
