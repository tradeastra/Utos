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
    <div className="space-y-6">
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
  );
}
