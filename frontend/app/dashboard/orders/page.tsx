'use client';

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { formatNumber, timeAgo } from '@/lib/utils';
import { api } from '@/services/api';
import { Search, X, Loader2 } from 'lucide-react';

interface OrderData {
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
  trading_instance_id: string;
}

const STATUS_VARIANTS: Record<string, 'success' | 'default' | 'destructive' | 'warning'> = {
  filled: 'success',
  open: 'default',
  pending: 'default',
  partially_filled: 'warning',
  cancelled: 'destructive',
  rejected: 'destructive',
  expired: 'destructive',
};

export default function OrdersPage() {
  const [orders, setOrders] = useState<OrderData[]>([]);
  const [loading, setLoading] = useState(true);
  const [symbolFilter, setSymbolFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [cancelling, setCancelling] = useState<string | null>(null);

  const fetchOrders = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (symbolFilter) params.set('symbol', symbolFilter);
      if (statusFilter) params.set('status', statusFilter);
      const qs = params.toString();
      const data = await api.get(`/api/v1/orders${qs ? `?${qs}` : ''}`);
      setOrders(data as OrderData[]);
    } catch {
      setOrders([]);
    } finally {
      setLoading(false);
    }
  }, [symbolFilter, statusFilter]);

  useEffect(() => {
    fetchOrders();
  }, [fetchOrders]);

  async function handleCancel(orderId: string) {
    setCancelling(orderId);
    try {
      await api.delete(`/api/v1/orders/${orderId}`);
      setOrders(orders.map((o) => o.id === orderId ? { ...o, status: 'cancelled' } : o));
    } catch {
      // Ignore
    } finally {
      setCancelling(null);
    }
  }

  return (
    <>
      {/* Mobile */}
      <div className="min-h-full bg-slate-50 pb-24 dark:bg-background md:hidden">
        <section className="relative overflow-hidden rounded-b-[2rem] bg-gradient-to-br from-violet-700 via-purple-600 to-fuchsia-600 px-5 pb-20 pt-[max(1.25rem,env(safe-area-inset-top))] text-white">
          <div className="absolute -right-14 top-4 h-44 w-44 rounded-full bg-fuchsia-400/20 blur-2xl" />
          <div className="relative">
            <h1 className="text-2xl font-bold tracking-tight">Orders Feed</h1>
            <p className="mt-1 text-sm text-violet-200">{orders.length} recent orders</p>
          </div>
        </section>

        <div className="relative -mt-12 px-4 space-y-3">
          {/* Search & Filter */}
          <div className="overflow-hidden rounded-3xl bg-white shadow-xl shadow-slate-900/10 dark:bg-card">
            <div className="p-4 space-y-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <input
                  type="text"
                  value={symbolFilter}
                  onChange={(e) => setSymbolFilter(e.target.value)}
                  placeholder="Search symbol..."
                  className="w-full rounded-xl border border-border bg-background py-2.5 pl-9 pr-3 text-sm focus:border-violet-500 focus:outline-none"
                />
              </div>
              <div className="flex gap-2 overflow-x-auto pb-1">
                {['', 'pending', 'open', 'partially_filled', 'filled', 'cancelled', 'rejected'].map((s) => (
                  <button
                    key={s}
                    onClick={() => setStatusFilter(s)}
                    className={`shrink-0 rounded-full px-3 py-1.5 text-xs font-medium transition ${
                      statusFilter === s
                        ? 'bg-violet-600 text-white'
                        : 'bg-slate-100 text-muted-foreground dark:bg-muted'
                    }`}
                  >
                    {s === '' ? 'All' : s.replace('_', ' ')}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Orders List */}
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-violet-500" />
            </div>
          ) : orders.length === 0 ? (
            <div className="rounded-3xl bg-white p-8 text-center text-sm text-muted-foreground shadow-lg shadow-slate-900/5 dark:bg-card">
              No orders found.
            </div>
          ) : (
            <div className="space-y-2">
              {orders.map((o) => (
                <div key={o.id} className="overflow-hidden rounded-2xl bg-white shadow-lg shadow-slate-900/5 transition-transform active:scale-[0.99] dark:bg-card">
                  <div className="flex items-center justify-between p-4 pb-2">
                    <div className="flex items-center gap-2">
                      <span className={`flex h-8 w-8 items-center justify-center rounded-lg text-xs font-bold ${
                        o.side === 'buy'
                          ? 'bg-emerald-100 text-emerald-600 dark:bg-emerald-500/10'
                          : 'bg-red-100 text-red-600 dark:bg-red-500/10'
                      }`}>
                        {o.side === 'buy' ? 'B' : 'S'}
                      </span>
                      <span className="font-semibold">{o.symbol}</span>
                    </div>
                    <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                      o.status === 'filled' ? 'bg-emerald-100 text-emerald-600 dark:bg-emerald-500/10' :
                      o.status === 'cancelled' || o.status === 'rejected' ? 'bg-red-100 text-red-600 dark:bg-red-500/10' :
                      o.status === 'partially_filled' ? 'bg-amber-100 text-amber-600 dark:bg-amber-500/10' :
                      'bg-slate-100 text-muted-foreground dark:bg-muted'
                    }`}>
                      {o.status.replace('_', ' ')}
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-2 px-4 pb-3 text-xs">
                    <div>
                      <p className="text-muted-foreground">Type</p>
                      <p className="font-medium">{o.order_type}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Qty</p>
                      <p className="font-medium tabular-nums">{formatNumber(Number(o.quantity))}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Price</p>
                      <p className="font-medium tabular-nums">{o.price ? `$${formatNumber(Number(o.price))}` : '—'}</p>
                    </div>
                  </div>
                  <div className="flex items-center justify-between border-t border-slate-100 px-4 py-2.5 dark:border-border">
                    <span className="text-xs text-muted-foreground">{timeAgo(o.created_at)}</span>
                    {(o.status === 'pending' || o.status === 'open' || o.status === 'partially_filled') && (
                      <button
                        onClick={() => handleCancel(o.id)}
                        disabled={cancelling === o.id}
                        className="rounded-lg px-3 py-1 text-xs font-medium text-red-500 transition active:scale-95 disabled:opacity-50"
                      >
                        {cancelling === o.id ? 'Cancelling...' : 'Cancel'}
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Desktop */}
      <div className="hidden space-y-6 md:block">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Orders Feed</h1>
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <input
                type="text"
                value={symbolFilter}
                onChange={(e) => setSymbolFilter(e.target.value)}
                placeholder="Symbol..."
                className="w-32 rounded-lg border border-border bg-background py-1.5 pl-8 pr-3 text-sm focus:border-violet-500 focus:outline-none"
              />
            </div>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="rounded-lg border border-border bg-background px-3 py-1.5 text-sm focus:border-violet-500 focus:outline-none"
            >
              <option value="">All Status</option>
              <option value="pending">Pending</option>
              <option value="open">Open</option>
              <option value="partially_filled">Partially Filled</option>
              <option value="filled">Filled</option>
              <option value="cancelled">Cancelled</option>
              <option value="rejected">Rejected</option>
            </select>
            {(symbolFilter || statusFilter) && (
              <button
                onClick={() => { setSymbolFilter(''); setStatusFilter(''); }}
                className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>
        <Card>
          <CardHeader><CardTitle>Recent Orders ({orders.length})</CardTitle></CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-6 w-6 animate-spin text-violet-500" />
              </div>
            ) : orders.length === 0 ? (
              <div className="py-12 text-center text-sm text-muted-foreground">
                No orders found.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left text-muted-foreground">
                      <th className="pb-2">Symbol</th>
                      <th className="pb-2">Side</th>
                      <th className="pb-2">Type</th>
                      <th className="pb-2">Qty</th>
                      <th className="pb-2">Price</th>
                      <th className="pb-2">Filled</th>
                      <th className="pb-2">Status</th>
                      <th className="pb-2">Time</th>
                      <th className="pb-2"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {orders.map((o) => (
                      <tr key={o.id} className="border-b hover:bg-muted/30">
                        <td className="py-3 font-medium">{o.symbol}</td>
                        <td className="py-3">
                          <Badge variant={o.side === 'buy' ? 'success' : 'destructive'}>{o.side}</Badge>
                        </td>
                        <td className="py-3">{o.order_type}</td>
                        <td className="py-3 tabular-nums">{formatNumber(Number(o.quantity))}</td>
                        <td className="py-3 tabular-nums">{o.price ? `$${formatNumber(Number(o.price))}` : '—'}</td>
                        <td className="py-3 tabular-nums">
                          {Number(o.filled_quantity) > 0 ? `${formatNumber(Number(o.filled_quantity))}` : '—'}
                          {o.average_fill_price && Number(o.filled_quantity) > 0 && (
                            <span className="ml-1 text-xs text-muted-foreground">@ ${formatNumber(Number(o.average_fill_price))}</span>
                          )}
                        </td>
                        <td className="py-3">
                          <Badge variant={STATUS_VARIANTS[o.status] ?? 'default'}>
                            {o.status.replace('_', ' ')}
                          </Badge>
                        </td>
                        <td className="py-3 text-muted-foreground">{timeAgo(o.created_at)}</td>
                        <td className="py-3">
                          {(o.status === 'pending' || o.status === 'open' || o.status === 'partially_filled') && (
                            <button
                              onClick={() => handleCancel(o.id)}
                              disabled={cancelling === o.id}
                              className="rounded-lg px-2 py-1 text-xs font-medium text-red-500 hover:bg-red-500/10 disabled:opacity-50"
                            >
                              {cancelling === o.id ? '...' : 'Cancel'}
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  );
}
