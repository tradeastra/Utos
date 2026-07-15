'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { timeAgo } from '@/lib/utils';

interface EventEntry {
  event_type: string;
  event_id: string;
  timestamp: string;
}

export default function EventsPage() {
  const [events, setEvents] = useState<EventEntry[]>([]);

  useEffect(() => {
    const types = ['price.update', 'order.created', 'order.filled', 'grid.level.hit', 'risk.check.passed', 'worker.heartbeat', 'notification.sent'];
    const mock: EventEntry[] = types.map((t, i) => ({
      event_type: t,
      event_id: `evt-${i}`,
      timestamp: new Date(Date.now() - i * 15000).toISOString(),
    }));
    setEvents(mock);
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">EventBus Live Feed</h1>
      <Card>
        <CardHeader><CardTitle>Recent Events</CardTitle></CardHeader>
        <CardContent className="space-y-1">
          {events.map((e) => (
            <div key={e.event_id} className="flex items-center justify-between rounded-md border p-2 text-sm">
              <div className="flex items-center gap-3">
                <Badge variant="secondary">{e.event_type}</Badge>
                <span className="text-muted-foreground">{e.event_id}</span>
              </div>
              <span className="text-muted-foreground">{timeAgo(e.timestamp)}</span>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
