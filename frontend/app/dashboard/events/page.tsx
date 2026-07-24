'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { timeAgo } from '@/lib/utils';
import { Radio, TrendingUp, ShoppingCart, CheckCircle2, Grid3x3, ShieldCheck, Heart, Bell } from 'lucide-react';

interface EventEntry {
  event_type: string;
  event_id: string;
  timestamp: string;
}

const EVENT_ICONS: Record<string, typeof Radio> = {
  'price.update': TrendingUp,
  'order.created': ShoppingCart,
  'order.filled': CheckCircle2,
  'grid.level.hit': Grid3x3,
  'risk.check.passed': ShieldCheck,
  'worker.heartbeat': Heart,
  'notification.sent': Bell,
};

const EVENT_COLORS: Record<string, string> = {
  'price.update': 'bg-blue-100 text-blue-600 dark:bg-blue-500/10',
  'order.created': 'bg-amber-100 text-amber-600 dark:bg-amber-500/10',
  'order.filled': 'bg-emerald-100 text-emerald-600 dark:bg-emerald-500/10',
  'grid.level.hit': 'bg-violet-100 text-violet-600 dark:bg-violet-500/10',
  'risk.check.passed': 'bg-green-100 text-green-600 dark:bg-green-500/10',
  'worker.heartbeat': 'bg-rose-100 text-rose-600 dark:bg-rose-500/10',
  'notification.sent': 'bg-cyan-100 text-cyan-600 dark:bg-cyan-500/10',
};

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
    <>
      {/* Mobile */}
      <div className="min-h-full bg-slate-50 pb-24 dark:bg-background md:hidden">
        <section className="relative overflow-hidden rounded-b-[2rem] bg-gradient-to-br from-violet-700 via-purple-600 to-fuchsia-600 px-5 pb-20 pt-[max(1.25rem,env(safe-area-inset-top))] text-white">
          <div className="absolute -right-14 top-4 h-44 w-44 rounded-full bg-fuchsia-400/20 blur-2xl" />
          <div className="relative flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-white/15 backdrop-blur-sm">
              <Radio className="h-5 w-5" />
            </span>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">Event Feed</h1>
              <p className="text-sm text-violet-200">{events.length} recent events</p>
            </div>
          </div>
        </section>
        <div className="relative -mt-12 px-4">
          <div className="overflow-hidden rounded-3xl bg-white shadow-xl shadow-slate-900/10 dark:bg-card">
            <div className="divide-y divide-slate-100 dark:divide-border">
              {events.map((e) => {
                const Icon = EVENT_ICONS[e.event_type] ?? Radio;
                const color = EVENT_COLORS[e.event_type] ?? 'bg-slate-100 text-slate-600 dark:bg-slate-500/10';
                return (
                  <div key={e.event_id} className="flex items-center gap-3 p-4 transition-transform active:scale-[0.99]">
                    <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${color}`}>
                      <Icon className="h-5 w-5" />
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-semibold">{e.event_type}</p>
                      <p className="text-xs text-muted-foreground">{e.event_id}</p>
                    </div>
                    <span className="shrink-0 text-xs text-muted-foreground">{timeAgo(e.timestamp)}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Desktop */}
      <div className="hidden space-y-6 md:block">
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
    </>
  );
}
