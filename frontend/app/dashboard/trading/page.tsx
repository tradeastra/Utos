'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { TradingInstance } from '@/types';

export default function TradingPage() {
  const [instances, setInstances] = useState<TradingInstance[]>([]);

  useEffect(() => {
    setInstances([
      { id: '1', user_id: 'u1', exchange_account_id: 'e1', symbol: 'BTC/USDT', status: 'running', strategy: 'grid', created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
      { id: '2', user_id: 'u1', exchange_account_id: 'e1', symbol: 'ETH/USDT', status: 'running', strategy: 'grid', created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
      { id: '3', user_id: 'u1', exchange_account_id: 'e2', symbol: 'SOL/USDT', status: 'paused', strategy: 'grid', created_at: new Date().toISOString(), updated_at: new Date().toISOString() },
    ]);
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Trading Instances</h1>
      <Card>
        <CardHeader><CardTitle>Active Instances</CardTitle></CardHeader>
        <CardContent>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="pb-2">Symbol</th>
                <th className="pb-2">Strategy</th>
                <th className="pb-2">Status</th>
                <th className="pb-2">Exchange</th>
              </tr>
            </thead>
            <tbody>
              {instances.map((inst) => (
                <tr key={inst.id} className="border-b">
                  <td className="py-3 font-medium">{inst.symbol}</td>
                  <td className="py-3">{inst.strategy}</td>
                  <td className="py-3">
                    <Badge variant={inst.status === 'running' ? 'success' : 'warning'}>
                      {inst.status}
                    </Badge>
                  </td>
                  <td className="py-3 text-muted-foreground">{inst.exchange_account_id}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
