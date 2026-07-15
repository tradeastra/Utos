'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

export default function ExchangesPage() {
  const accounts = [
    { id: '1', exchange_name: 'Binance', is_active: true, is_testnet: false },
    { id: '2', exchange_name: 'OKX', is_active: true, is_testnet: true },
    { id: '3', exchange_name: 'Bybit', is_active: false, is_testnet: false },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Exchange Accounts</h1>
        <Button>Add Exchange</Button>
      </div>
      <Card>
        <CardHeader><CardTitle>Connected Exchanges</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          {accounts.map((acc) => (
            <div key={acc.id} className="flex items-center justify-between rounded-md border p-3">
              <div className="flex items-center gap-3">
                <span className="font-medium">{acc.exchange_name}</span>
                {acc.is_testnet && <Badge variant="warning">testnet</Badge>}
              </div>
              <Badge variant={acc.is_active ? 'success' : 'secondary'}>
                {acc.is_active ? 'active' : 'inactive'}
              </Badge>
            </div>
          ))}
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>Add New Exchange</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Exchange</label>
            <Input placeholder="e.g. Binance, OKX, Bybit" />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">API Key</label>
            <Input type="password" placeholder="Your API key" />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">API Secret</label>
            <Input type="password" placeholder="Your API secret" />
          </div>
          <Button className="w-full">Connect</Button>
        </CardContent>
      </Card>
    </div>
  );
}
