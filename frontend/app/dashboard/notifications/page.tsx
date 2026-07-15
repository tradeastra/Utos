'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

export default function NotificationsPage() {
  const channels = [
    { name: 'Email', enabled: true, configured: true },
    { name: 'Telegram', enabled: true, configured: true },
    { name: 'Discord', enabled: false, configured: false },
    { name: 'Webhook', enabled: false, configured: false },
  ];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Notifications</h1>
      <Card>
        <CardHeader><CardTitle>Channels</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          {channels.map((ch) => (
            <div key={ch.name} className="flex items-center justify-between rounded-md border p-3">
              <div className="flex items-center gap-3">
                <span className="font-medium">{ch.name}</span>
                {!ch.configured && <Badge variant="warning">not configured</Badge>}
              </div>
              <Badge variant={ch.enabled ? 'success' : 'secondary'}>
                {ch.enabled ? 'enabled' : 'disabled'}
              </Badge>
            </div>
          ))}
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>Recent Notifications</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          <div className="rounded-md border p-3 text-sm">
            <div className="flex items-center justify-between">
              <span className="font-medium">Grid level filled — BTC/USDT #3</span>
              <Badge variant="success">delivered</Badge>
            </div>
            <p className="mt-1 text-muted-foreground">Buy order filled at $64,000</p>
          </div>
          <div className="rounded-md border p-3 text-sm">
            <div className="flex items-center justify-between">
              <span className="font-medium">Risk warning — exposure at 45%</span>
              <Badge variant="warning">delivered</Badge>
            </div>
            <p className="mt-1 text-muted-foreground">Total exposure approaching limit</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
