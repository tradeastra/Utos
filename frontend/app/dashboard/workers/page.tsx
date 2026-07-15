'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

export default function WorkersPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Worker Health</h1>
      <Card>
        <CardHeader><CardTitle>Active Workers</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          {['GridEngine-1', 'ExecutionEngine-1', 'MarketHub-1', 'NotificationService-1', 'HeartbeatMonitor-1'].map((name) => (
            <div key={name} className="flex items-center justify-between rounded-md border p-3">
              <span className="font-medium">{name}</span>
              <div className="flex items-center gap-3">
                <span className="text-sm text-muted-foreground">0 errors</span>
                <Badge variant="success">running</Badge>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
