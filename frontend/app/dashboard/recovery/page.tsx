'use client';

<<<<<<< HEAD
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { RefreshCw, CheckCircle2, Wifi, Database, RefreshCcw, Save } from 'lucide-react';

const steps = [
  { name: 'Connection Recovery', icon: Wifi, desc: 'Reconnect to exchange WebSocket' },
  { name: 'State Recovery', icon: Database, desc: 'Restore grid & order state from DB' },
  { name: 'Runtime Reconciliation', icon: RefreshCcw, desc: 'Sync local state with exchange' },
  { name: 'Persistence Checkpoint', icon: Save, desc: 'Save final state snapshot' },
];

export default function RecoveryPage() {
  return (
    <>
      {/* Mobile */}
      <div className="min-h-full bg-slate-50 pb-24 dark:bg-background md:hidden">
        <section className="relative overflow-hidden rounded-b-[2rem] bg-gradient-to-br from-violet-700 via-purple-600 to-fuchsia-600 px-5 pb-20 pt-[max(1.25rem,env(safe-area-inset-top))] text-white">
          <div className="absolute -right-14 top-4 h-44 w-44 rounded-full bg-fuchsia-400/20 blur-2xl" />
          <div className="relative flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-white/15 backdrop-blur-sm">
              <RefreshCw className="h-5 w-5" />
            </span>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">Recovery Status</h1>
              <p className="text-sm text-violet-200">4-Layer Recovery Pipeline</p>
            </div>
          </div>
        </section>
        <div className="relative -mt-12 px-4 space-y-3">
          {steps.map((s, i) => {
            const Icon = s.icon;
            return (
              <div key={s.name} className="flex items-center gap-3 rounded-2xl bg-white p-4 shadow-lg shadow-slate-900/5 dark:bg-card">
                <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-emerald-100 text-emerald-600 dark:bg-emerald-500/10">
                  <Icon className="h-6 w-6" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-medium text-muted-foreground">Step {i + 1}</p>
                  <p className="font-semibold">{s.name}</p>
                  <p className="text-xs text-muted-foreground">{s.desc}</p>
                </div>
                <CheckCircle2 className="h-6 w-6 shrink-0 text-emerald-500" />
              </div>
            );
          })}
        </div>
      </div>

      {/* Desktop */}
      <div className="hidden space-y-6 md:block">
        <h1 className="text-2xl font-bold">Recovery Status</h1>
        <Card>
          <CardHeader><CardTitle>4-Layer Recovery Pipeline</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {steps.map((s) => (
              <div key={s.name} className="flex items-center justify-between rounded-md border p-3">
                <span className="font-medium">{s.name}</span>
                <Badge variant="success">completed</Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </>
=======
import { RefreshCw } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';

export default function RecoveryPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Recovery</h1>
        <p className="text-muted-foreground">Recover and resume interrupted trading instances</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recovery Queue</CardTitle>
          <CardDescription>Instances that need manual or automatic recovery</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <RefreshCw className="h-12 w-12 text-muted-foreground/40" />
            <p className="mt-4 text-sm text-muted-foreground">No instances need recovery.</p>
          </div>
        </CardContent>
      </Card>
    </div>
>>>>>>> develop
  );
}
