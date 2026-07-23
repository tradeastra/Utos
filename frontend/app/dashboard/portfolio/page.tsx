'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatCurrency, formatNumber, formatPercent } from '@/lib/utils';
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

  return (
    <div className="space-y-6">
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
          <CardContent><p className="text-2xl font-bold text-green-500">{formatCurrency(totalUnrealized + totalRealized)}</p></CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle>Open Positions</CardTitle></CardHeader>
        <CardContent>
          {/* Mobile: card list */}
          <div className="space-y-2 md:hidden">
            {positions.map((p) => (
              <div key={p.id} className="rounded-lg border p-3 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-medium">{p.symbol}</span>
                  <span className="text-xs uppercase text-muted-foreground">{p.side}</span>
                </div>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                  <span className="text-muted-foreground">Qty: <span className="text-foreground">{formatNumber(p.quantity)}</span></span>
                  <span className="text-muted-foreground">Entry: <span className="text-foreground">${formatNumber(p.entry_price)}</span></span>
                  <span className="text-muted-foreground">Current: <span className="text-foreground">${formatNumber(p.current_price)}</span></span>
                  <span className="text-muted-foreground">Unrealized: <span className="text-green-500">{formatCurrency(p.unrealized_pnl)}</span></span>
                </div>
              </div>
            ))}
          </div>
          {/* Desktop: table */}
          <div className="hidden overflow-x-auto md:block">
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
  );
}
