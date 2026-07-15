'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { formatNumber, timeAgo } from '@/lib/utils';
import type { Order } from '@/types';

export default function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([]);

  useEffect(() => {
    setOrders([
      { id: 'o1', user_id: 'u1', symbol: 'BTC/USDT', side: 'buy', type: 'limit', quantity: 0.1, price: 64000, status: 'filled', filled_quantity: 0.1, avg_fill_price: 63995, created_at: new Date(Date.now() - 60000).toISOString(), updated_at: new Date().toISOString() },
      { id: 'o2', user_id: 'u1', symbol: 'BTC/USDT', side: 'sell', type: 'limit', quantity: 0.1, price: 66000, status: 'open', filled_quantity: 0, avg_fill_price: null, created_at: new Date(Date.now() - 30000).toISOString(), updated_at: new Date().toISOString() },
      { id: 'o3', user_id: 'u1', symbol: 'ETH/USDT', side: 'buy', type: 'limit', quantity: 1.0, price: 3200, status: 'filled', filled_quantity: 1.0, avg_fill_price: 3198, created_at: new Date(Date.now() - 120000).toISOString(), updated_at: new Date().toISOString() },
      { id: 'o4', user_id: 'u1', symbol: 'SOL/USDT', side: 'buy', type: 'limit', quantity: 10, price: 140, status: 'cancelled', filled_quantity: 0, avg_fill_price: null, created_at: new Date(Date.now() - 300000).toISOString(), updated_at: new Date().toISOString() },
    ]);
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Orders Feed</h1>
      <Card>
        <CardHeader><CardTitle>Recent Orders</CardTitle></CardHeader>
        <CardContent>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="pb-2">Symbol</th>
                <th className="pb-2">Side</th>
                <th className="pb-2">Type</th>
                <th className="pb-2">Qty</th>
                <th className="pb-2">Price</th>
                <th className="pb-2">Status</th>
                <th className="pb-2">Time</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((o) => (
                <tr key={o.id} className="border-b">
                  <td className="py-3 font-medium">{o.symbol}</td>
                  <td className="py-3">
                    <Badge variant={o.side === 'buy' ? 'success' : 'destructive'}>{o.side}</Badge>
                  </td>
                  <td className="py-3">{o.type}</td>
                  <td className="py-3">{formatNumber(o.quantity)}</td>
                  <td className="py-3">${formatNumber(o.price)}</td>
                  <td className="py-3">
                    <Badge variant={o.status === 'filled' ? 'success' : o.status === 'open' ? 'default' : 'destructive'}>
                      {o.status}
                    </Badge>
                  </td>
                  <td className="py-3 text-muted-foreground">{timeAgo(o.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
