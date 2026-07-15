'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { formatCurrency, formatPercent } from '@/lib/utils';
import type { PortfolioSummary, RiskStatus, WorkerHealth } from '@/types';

export default function DashboardOverview() {
  const [portfolio, setPortfolio] = useState<PortfolioSummary | null>(null);
  const [risk, setRisk] = useState<RiskStatus | null>(null);
  const [workers, setWorkers] = useState<WorkerHealth[]>([]);

  useEffect(() => {
    setPortfolio({
      total_value: 125000,
      total_pnl: 3450.75,
      total_pnl_pct: 2.84,
      total_exposure: 45000,
      open_positions: 8,
      positions: [],
    });
    setRisk({
      max_exposure_per_symbol: 20000,
      max_exposure_per_exchange: 100000,
      max_open_positions: 20,
      max_position_size: 5000,
      current_exposure: 45000,
      open_positions: 8,
      orders_checked: 1542,
      orders_allowed: 1538,
      orders_denied: 4,
    });
    setWorkers([
      { id: '1', name: 'GridEngine-1', status: 'running', last_heartbeat: new Date().toISOString(), error_count: 0 },
      { id: '2', name: 'ExecutionEngine-1', status: 'running', last_heartbeat: new Date().toISOString(), error_count: 0 },
      { id: '3', name: 'MarketHub-1', status: 'running', last_heartbeat: new Date().toISOString(), error_count: 0 },
    ]);
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Dashboard Overview</h1>
        <p className="text-muted-foreground">Trading performance and system status at a glance</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Value</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{portfolio ? formatCurrency(portfolio.total_value) : '—'}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total PnL</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-green-500">
              {portfolio ? formatCurrency(portfolio.total_pnl) : '—'}
            </p>
            <p className="text-sm text-green-500">
              {portfolio ? formatPercent(portfolio.total_pnl_pct) : ''}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Exposure</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{portfolio ? formatCurrency(portfolio.total_exposure) : '—'}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Open Positions</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{portfolio?.open_positions ?? '—'}</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Risk Status</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {risk ? (
              <>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Current Exposure</span>
                  <span className="font-medium">{formatCurrency(risk.current_exposure)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Open Positions</span>
                  <span className="font-medium">{risk.open_positions} / {risk.max_open_positions}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Orders Checked</span>
                  <span className="font-medium">{risk.orders_checked}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Orders Denied</span>
                  <span className="font-medium text-red-500">{risk.orders_denied}</span>
                </div>
              </>
            ) : (
              <p className="text-muted-foreground">Loading...</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Worker Health</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {workers.map((w) => (
              <div key={w.id} className="flex items-center justify-between">
                <span className="font-medium">{w.name}</span>
                <Badge variant={w.status === 'running' ? 'success' : 'destructive'}>
                  {w.status}
                </Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
