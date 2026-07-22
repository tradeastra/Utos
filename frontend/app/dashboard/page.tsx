'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  ArrowRight,
  Bell,
  ChevronDown,
  ChevronRight,
  CircleHelp,
  Coins,
  Gift,
  Landmark,
  Link2,
  Menu,
  RefreshCw,
  Settings,
  WalletCards,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { formatCurrency, formatPercent } from '@/lib/utils';
import type { PortfolioSummary, RiskStatus, WorkerHealth } from '@/types';

const quickActions = [
  { label: 'API', icon: Link2, href: '/settings/exchanges', color: 'from-violet-500 to-fuchsia-500' },
  { label: 'Credit', icon: WalletCards, href: '/dashboard/billing', color: 'from-indigo-500 to-violet-500' },
  { label: 'Profit', icon: Gift, href: '/dashboard/portfolio', color: 'from-fuchsia-500 to-purple-500' },
  { label: 'FAQ', icon: CircleHelp, href: '/dashboard/notifications', color: 'from-purple-600 to-violet-500' },
];

const utilityLinks = [
  { label: 'Savings', detail: 'Grow your idle balance', icon: Coins, href: '/dashboard/portfolio', color: 'bg-amber-100 text-amber-600' },
  { label: 'Cashback', detail: 'View your earned rewards', icon: Gift, href: '/dashboard/affiliate', color: 'bg-orange-100 text-orange-500' },
  { label: 'Strategy Settings', detail: 'Configure your trading app', icon: Settings, href: '/dashboard/strategy-setting', color: 'bg-violet-100 text-violet-600' },
];

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
    <>
      <div className="min-h-full bg-slate-50 pb-6 dark:bg-background md:hidden">
        <section className="relative overflow-hidden rounded-b-[2rem] bg-gradient-to-br from-violet-700 via-purple-600 to-fuchsia-600 px-5 pb-24 pt-[max(1.25rem,env(safe-area-inset-top))] text-white">
          <div className="absolute -right-14 top-4 h-44 w-44 rounded-full bg-fuchsia-400/20 blur-2xl" />
          <div className="absolute -left-16 bottom-0 h-36 w-36 rounded-full bg-cyan-300/15 blur-2xl" />
          <div className="relative flex items-center justify-between">
            <div className="text-xl font-bold tracking-tight">UTOS<span className="font-medium text-violet-200">BOT</span></div>
            <div className="flex items-center gap-3">
              <button className="rounded-xl bg-white/10 p-2.5 backdrop-blur-sm" aria-label="Notifications"><Bell className="h-5 w-5" /></button>
              <button className="rounded-xl bg-white/10 p-2.5 backdrop-blur-sm" aria-label="Menu"><Menu className="h-5 w-5" /></button>
            </div>
          </div>
          <div className="relative mt-9 flex items-center gap-3 text-sm font-medium">
            <RefreshCw className="h-4 w-4" />
            <span>Exchange</span>
            <button className="flex items-center gap-2 rounded-full bg-white px-3 py-2 text-slate-800 shadow-lg shadow-purple-950/10">
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-amber-400 text-[10px] font-bold text-white">B</span>
              Binance <ChevronDown className="h-4 w-4" />
            </button>
          </div>
        </section>

        <div className="relative -mt-16 px-4">
          <div className="overflow-hidden rounded-3xl bg-white shadow-xl shadow-slate-900/10 dark:bg-card">
            <div className="grid grid-cols-2 divide-x divide-slate-200 dark:divide-border">
              <div className="p-4">
                <p className="text-xs font-semibold text-muted-foreground">USDT</p>
                <p className="mt-1 text-xl font-bold tracking-tight">{portfolio ? formatCurrency(portfolio.total_value) : '—'}</p>
                <p className="mt-1 flex items-center gap-1 text-xs text-emerald-500"><RefreshCw className="h-3 w-3" /> Available balance</p>
              </div>
              <div className="p-4">
                <p className="text-xs font-semibold text-muted-foreground">Coin Asset</p>
                <p className="mt-1 text-xl font-bold tracking-tight">{portfolio ? formatCurrency(portfolio.total_exposure) : '—'}</p>
                <p className="mt-1 text-xs text-muted-foreground">In active strategies</p>
              </div>
            </div>
            <Link href="/dashboard/portfolio" className="flex items-center justify-between border-t border-slate-100 px-4 py-3 text-sm dark:border-border">
              <span className="text-muted-foreground">My Trading Volume (D-1)</span>
              <span className="flex items-center gap-1 font-semibold">{portfolio ? formatCurrency(portfolio.total_pnl) : '—'} <ChevronRight className="h-4 w-4" /></span>
            </Link>
          </div>

          <div className="flex items-center justify-between px-1 py-5 text-sm">
            <span>Credit: <strong>{portfolio ? formatCurrency(portfolio.total_value) : '—'}</strong></span>
            <Link href="/dashboard/billing" className="flex items-center gap-1 font-semibold text-emerald-600">Recharge now <ArrowRight className="h-4 w-4" /></Link>
          </div>

          <div className="grid grid-cols-4 gap-2 pb-7">
            {quickActions.map((action) => {
              const Icon = action.icon;
              return <Link key={action.label} href={action.href} className="flex flex-col items-center gap-2 text-center text-xs font-semibold"><span className={`flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br ${action.color} text-white shadow-lg shadow-violet-500/20`}><Icon className="h-6 w-6" /></span>{action.label}</Link>;
            })}
          </div>

          <Link href="/dashboard/trading" className="flex items-center justify-between overflow-hidden rounded-2xl bg-gradient-to-r from-violet-700 via-purple-600 to-fuchsia-600 px-4 py-3 text-white shadow-lg shadow-violet-500/20">
            <div><p className="text-base font-bold">UTOS MOBILE TRADING</p><p className="text-xs text-violet-100">One app. All your automated trades.</p></div>
            <Landmark className="h-10 w-10 text-violet-200" />
          </Link>

          <div className="mt-5 space-y-3">
            {utilityLinks.map((item) => {
              const Icon = item.icon;
              return <Link key={item.label} href={item.href} className="flex items-center gap-4 rounded-2xl bg-white p-4 shadow-md shadow-slate-900/5 transition-transform active:scale-[0.98] dark:bg-card"><span className={`flex h-11 w-11 items-center justify-center rounded-2xl ${item.color}`}><Icon className="h-6 w-6" /></span><span className="min-w-0 flex-1"><span className="block font-semibold">{item.label}</span><span className="block truncate text-xs text-muted-foreground">{item.detail}</span></span><ChevronRight className="h-5 w-5 text-muted-foreground" /></Link>;
            })}
          </div>
        </div>
      </div>

      <div className="hidden space-y-6 md:block">
        <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
          <Card glass><CardContent className="p-5"><p className="text-sm font-medium text-muted-foreground">Total Value</p><p className="mt-1 text-2xl font-bold tracking-tight">{portfolio ? formatCurrency(portfolio.total_value) : '—'}</p></CardContent></Card>
          <Card glass><CardContent className="p-5"><p className="text-sm font-medium text-muted-foreground">Total PnL</p><p className="mt-1 text-2xl font-bold tracking-tight text-profit">{portfolio ? formatCurrency(portfolio.total_pnl) : '—'}</p><p className="text-sm text-profit">{portfolio ? formatPercent(portfolio.total_pnl_pct) : ''}</p></CardContent></Card>
          <Card glass><CardContent className="p-5"><p className="text-sm font-medium text-muted-foreground">Exposure</p><p className="mt-1 text-2xl font-bold tracking-tight">{portfolio ? formatCurrency(portfolio.total_exposure) : '—'}</p></CardContent></Card>
          <Card glass><CardContent className="p-5"><p className="text-sm font-medium text-muted-foreground">Open Positions</p><p className="mt-1 text-2xl font-bold tracking-tight">{portfolio?.open_positions ?? '—'}</p></CardContent></Card>
        </div>
        <div className="grid gap-4 grid-cols-1 lg:grid-cols-2">
          <Card><CardHeader><CardTitle>Risk Status</CardTitle></CardHeader><CardContent className="space-y-3">{risk ? <><div className="flex justify-between text-sm"><span className="text-muted-foreground">Current Exposure</span><span className="font-medium">{formatCurrency(risk.current_exposure)}</span></div><div className="flex justify-between text-sm"><span className="text-muted-foreground">Open Positions</span><span className="font-medium">{risk.open_positions} / {risk.max_open_positions}</span></div><div className="flex justify-between text-sm"><span className="text-muted-foreground">Orders Checked</span><span className="font-medium">{risk.orders_checked}</span></div><div className="flex justify-between text-sm"><span className="text-muted-foreground">Orders Denied</span><Badge variant="loss">{risk.orders_denied}</Badge></div></> : <p className="text-muted-foreground">Loading...</p>}</CardContent></Card>
          <Card><CardHeader><CardTitle>Worker Health</CardTitle></CardHeader><CardContent className="space-y-3">{workers.map((w) => <div key={w.id} className="flex items-center justify-between text-sm"><span className="font-medium">{w.name}</span><Badge variant={w.status === 'running' ? 'success' : 'destructive'}>{w.status}</Badge></div>)}</CardContent></Card>
        </div>
      </div>
    </>
  );
}
