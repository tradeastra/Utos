'use client';

<<<<<<< HEAD
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Activity, Cpu, Server, Bell, Heart } from 'lucide-react';

const workers = [
  { name: 'GridEngine-1', icon: Cpu, status: 'running', errors: 0 },
  { name: 'ExecutionEngine-1', icon: Server, status: 'running', errors: 0 },
  { name: 'MarketHub-1', icon: Activity, status: 'running', errors: 0 },
  { name: 'NotificationService-1', icon: Bell, status: 'running', errors: 0 },
  { name: 'HeartbeatMonitor-1', icon: Heart, status: 'running', errors: 0 },
];

export default function WorkersPage() {
  return (
    <>
      {/* Mobile */}
      <div className="min-h-full bg-slate-50 pb-24 dark:bg-background md:hidden">
        <section className="relative overflow-hidden rounded-b-[2rem] bg-gradient-to-br from-violet-700 via-purple-600 to-fuchsia-600 px-5 pb-20 pt-[max(1.25rem,env(safe-area-inset-top))] text-white">
          <div className="absolute -right-14 top-4 h-44 w-44 rounded-full bg-fuchsia-400/20 blur-2xl" />
          <div className="relative">
            <h1 className="text-2xl font-bold tracking-tight">Worker Health</h1>
            <p className="mt-1 text-sm text-violet-200">{workers.length} active workers</p>
          </div>
        </section>
        <div className="relative -mt-12 px-4 space-y-3">
          {workers.map((w) => {
            const Icon = w.icon;
            return (
              <div key={w.name} className="flex items-center gap-3 rounded-2xl bg-white p-4 shadow-lg shadow-slate-900/5 transition-transform active:scale-[0.98] dark:bg-card">
                <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-emerald-100 text-emerald-600 dark:bg-emerald-500/10">
                  <Icon className="h-6 w-6" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="font-semibold">{w.name}</p>
                  <p className="text-xs text-muted-foreground">{w.errors} errors</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-emerald-500" />
                  <span className="text-xs font-medium text-emerald-600 capitalize">{w.status}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Desktop */}
      <div className="hidden space-y-6 md:block">
        <h1 className="text-2xl font-bold">Worker Health</h1>
        <Card>
          <CardHeader><CardTitle>Active Workers</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {workers.map((w) => (
              <div key={w.name} className="flex items-center justify-between rounded-md border p-3">
                <span className="font-medium">{w.name}</span>
                <div className="flex items-center gap-3">
                  <span className="text-sm text-muted-foreground">{w.errors} errors</span>
                  <Badge variant="success">{w.status}</Badge>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </>
=======
import { Users } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';

export default function WorkersPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Workers</h1>
        <p className="text-muted-foreground">Monitor background worker processes</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Worker Status</CardTitle>
          <CardDescription>Active trading engine workers and their health</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <Users className="h-12 w-12 text-muted-foreground/40" />
            <p className="mt-4 text-sm text-muted-foreground">Worker monitoring coming soon.</p>
          </div>
        </CardContent>
      </Card>
    </div>
>>>>>>> develop
  );
}
