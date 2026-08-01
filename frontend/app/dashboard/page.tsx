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
import { api } from '@/services/api';

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

interface PortfolioSummary {
  total_value: string;
  total_investment: string;
  total_pnl: string;
  pnl_percentage: string;
}

interface TradingInstanceSummary {
  id: string;
  status: string;
  symbol: string;
  total_investment: number;
}

export default function DashboardOverview() {
  const [portfolio, setPortfolio] = useState<PortfolioSummary | null>(null);
  const [instances, setInstances] = useState<TradingInstanceSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    async function load() {
      try {
        const [pf, insts] = await Promise.all([
          api.getPortfolio().catch(() => null),
          api.listTradingInstances().catch(() => [] as TradingInstanceSummary[]),
        ]);
        if (!mounted) return;
        if (pf) {
          const summary = (pf as Record<string, unknown>).summary as Record<string, string> | undefined;
          setPortfolio({
            total_value: summary?.total_value ?? '0',
            total_investment: summary?.total_investment ?? '0',
            total_pnl: summary?.total_pnl ?? '0',
            pnl_percentage: summary?.pnl_percentage ?? '0',
          });
        }
        setInstances((insts as TradingInstanceSummary[]) ?? []);
      } catch {
        // ignore — values stay null / empty
      } finally {
        if (mounted) setLoading(false);
      }
    }
    load();
    return () => { mounted = false; };
  }, []);

  const totalValue = portfolio ? parseFloat(portfolio.total_value) : null;
  const totalPnl = portfolio ? parseFloat(portfolio.total_pnl) : null;
  const totalPnlPct = portfolio ? parseFloat(portfolio.pnl_percentage) : null;
  const totalInvestment = portfolio ? parseFloat(portfolio.total_investment) : null;
  const activeBots = instances.filter((i) => i.status === 'running').length;

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
                <p className="mt-1 text-xl font-bold tracking-tight">{totalValue !== null ? formatCurrency(totalValue) : (loading ? '…' : '—')}</p>
                <p className="mt-1 flex items-center gap-1 text-xs text-emerald-500"><RefreshCw className="h-3 w-3" /> Available balance</p>
              </div>
              <div className="p-4">
                <p className="text-xs font-semibold text-muted-foreground">Coin Asset</p>
                <p className="mt-1 text-xl font-bold tracking-tight">{totalInvestment !== null ? formatCurrency(totalInvestment) : (loading ? '…' : '—')}</p>
                <p className="mt-1 text-xs text-muted-foreground">In active strategies</p>
              </div>
            </div>
            <Link href="/dashboard/portfolio" className="flex items-center justify-between border-t border-slate-100 px-4 py-3 text-sm dark:border-border">
              <span className="text-muted-foreground">Total PnL</span>
              <span className="flex items-center gap-1 font-semibold">{totalPnl !== null ? formatCurrency(totalPnl) : (loading ? '…' : '—')} <ChevronRight className="h-4 w-4" /></span>
            </Link>
          </div>

          <div className="flex items-center justify-between px-1 py-5 text-sm">
            <span>Active bots: <strong>{activeBots}</strong></span>
            <Link href="/dashboard/strategy-setting?tab=bots" className="flex items-center gap-1 font-semibold text-emerald-600">Manage bots <ArrowRight className="h-4 w-4" /></Link>
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
          <Card glass><CardContent className="p-5"><p className="text-sm font-medium text-muted-foreground">Total Value</p><p className="mt-1 text-2xl font-bold tracking-tight">{totalValue !== null ? formatCurrency(totalValue) : (loading ? '…' : '—')}</p></CardContent></Card>
          <Card glass><CardContent className="p-5"><p className="text-sm font-medium text-muted-foreground">Total PnL</p><p className="mt-1 text-2xl font-bold tracking-tight text-profit">{totalPnl !== null ? formatCurrency(totalPnl) : (loading ? '…' : '—')}</p><p className="text-sm text-profit">{totalPnlPct !== null ? formatPercent(totalPnlPct) : ''}</p></CardContent></Card>
          <Card glass><CardContent className="p-5"><p className="text-sm font-medium text-muted-foreground">Investment</p><p className="mt-1 text-2xl font-bold tracking-tight">{totalInvestment !== null ? formatCurrency(totalInvestment) : (loading ? '…' : '—')}</p></CardContent></Card>
          <Card glass><CardContent className="p-5"><p className="text-sm font-medium text-muted-foreground">Active Bots</p><p className="mt-1 text-2xl font-bold tracking-tight">{activeBots}</p></CardContent></Card>
        </div>
        <div className="grid gap-4 grid-cols-1 lg:grid-cols-2">
          <Card>
            <CardHeader><CardTitle>Recent Bots</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              {loading ? (
                <p className="text-muted-foreground">Loading…</p>
              ) : instances.length === 0 ? (
                <p className="text-muted-foreground">No bots yet. Create one from Strategy Settings.</p>
              ) : (
                instances.slice(0, 5).map((inst) => (
                  <div key={inst.id} className="flex items-center justify-between text-sm">
                    <span className="font-medium">{inst.symbol}</span>
                    <Badge variant={inst.status === 'running' ? 'success' : 'secondary'}>{inst.status}</Badge>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Quick Links</CardTitle></CardHeader>
            <CardContent className="space-y-2">
              <Link href="/dashboard/portfolio" className="flex items-center justify-between text-sm hover:text-violet-600">
                <span>Portfolio</span><ChevronRight className="h-4 w-4" />
              </Link>
              <Link href="/dashboard/orders" className="flex items-center justify-between text-sm hover:text-violet-600">
                <span>Orders</span><ChevronRight className="h-4 w-4" />
              </Link>
              <Link href="/dashboard/strategy-setting" className="flex items-center justify-between text-sm hover:text-violet-600">
                <span>Strategy Settings</span><ChevronRight className="h-4 w-4" />
              </Link>
            </CardContent>
          </Card>
        </div>
      </div>
    </>
  );
}
