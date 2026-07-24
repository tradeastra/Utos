'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Shield, AlertTriangle, CheckCircle2, XCircle } from 'lucide-react';

export default function RiskPage() {
  return (
    <>
      {/* Mobile */}
      <div className="min-h-full bg-slate-50 pb-24 dark:bg-background md:hidden">
        <section className="relative overflow-hidden rounded-b-[2rem] bg-gradient-to-br from-violet-700 via-purple-600 to-fuchsia-600 px-5 pb-20 pt-[max(1.25rem,env(safe-area-inset-top))] text-white">
          <div className="absolute -right-14 top-4 h-44 w-44 rounded-full bg-fuchsia-400/20 blur-2xl" />
          <div className="relative flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-white/15 backdrop-blur-sm">
              <Shield className="h-5 w-5" />
            </span>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">Risk Management</h1>
              <p className="text-sm text-violet-200">Exposure & order limits</p>
            </div>
          </div>
        </section>
        <div className="relative -mt-12 px-4 space-y-3">
          {/* Exposure Card */}
          <div className="overflow-hidden rounded-3xl bg-white shadow-xl shadow-slate-900/10 dark:bg-card">
            <div className="border-b border-slate-100 px-5 py-4 dark:border-border">
              <p className="text-sm font-semibold">Exposure Limits</p>
            </div>
            <div className="space-y-3 p-5">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Max per Symbol</span>
                <span className="text-sm font-bold">$20,000</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Max per Exchange</span>
                <span className="text-sm font-bold">$100,000</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Current Exposure</span>
                <span className="text-sm font-bold">$45,000</span>
              </div>
              <div className="pt-2">
                <div className="mb-1 flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">Utilization</span>
                  <span className="font-semibold text-amber-600">45%</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-muted">
                  <div className="h-full rounded-full bg-gradient-to-r from-amber-400 to-amber-600" style={{ width: '45%' }} />
                </div>
              </div>
            </div>
          </div>

          {/* Position Limits Card */}
          <div className="overflow-hidden rounded-3xl bg-white shadow-xl shadow-slate-900/10 dark:bg-card">
            <div className="border-b border-slate-100 px-5 py-4 dark:border-border">
              <p className="text-sm font-semibold">Position Limits</p>
            </div>
            <div className="space-y-3 p-5">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Max Open Positions</span>
                <span className="text-sm font-bold">20</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Current Open</span>
                <span className="text-sm font-bold">8</span>
              </div>
              <div className="pt-2">
                <div className="mb-1 flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">Position Usage</span>
                  <span className="font-semibold text-emerald-600">40%</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-muted">
                  <div className="h-full rounded-full bg-gradient-to-r from-emerald-400 to-emerald-600" style={{ width: '40%' }} />
                </div>
              </div>
            </div>
          </div>

          {/* Order Gatekeeper Card */}
          <div className="overflow-hidden rounded-3xl bg-white shadow-xl shadow-slate-900/10 dark:bg-card">
            <div className="border-b border-slate-100 px-5 py-4 dark:border-border">
              <p className="text-sm font-semibold">Order Gatekeeper</p>
            </div>
            <div className="divide-y divide-slate-100 dark:divide-border">
              <div className="flex items-center gap-3 p-4">
                <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-100 text-blue-600 dark:bg-blue-500/10">
                  <CheckCircle2 className="h-5 w-5" />
                </span>
                <span className="flex-1 text-sm text-muted-foreground">Orders Checked</span>
                <span className="text-sm font-bold">1,542</span>
              </div>
              <div className="flex items-center gap-3 p-4">
                <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-100 text-emerald-600 dark:bg-emerald-500/10">
                  <CheckCircle2 className="h-5 w-5" />
                </span>
                <span className="flex-1 text-sm text-muted-foreground">Orders Allowed</span>
                <span className="text-sm font-bold text-emerald-600">1,538</span>
              </div>
              <div className="flex items-center gap-3 p-4">
                <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-red-100 text-red-600 dark:bg-red-500/10">
                  <XCircle className="h-5 w-5" />
                </span>
                <span className="flex-1 text-sm text-muted-foreground">Orders Denied</span>
                <span className="text-sm font-bold text-red-500">4</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Desktop */}
      <div className="hidden space-y-6 md:block">
        <h1 className="text-2xl font-bold">Risk Management</h1>
        <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
          <Card>
            <CardHeader><CardTitle>Exposure Limits</CardTitle></CardHeader>
            <CardContent className="space-y-2">
              <div className="flex justify-between"><span className="text-muted-foreground">Max per Symbol</span><span className="font-medium">$20,000</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Max per Exchange</span><span className="font-medium">$100,000</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Current Exposure</span><span className="font-medium">$45,000</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Utilization</span><Badge variant="warning">45%</Badge></div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Position Limits</CardTitle></CardHeader>
            <CardContent className="space-y-2">
              <div className="flex justify-between"><span className="text-muted-foreground">Max Open Positions</span><span className="font-medium">20</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Current Open</span><span className="font-medium">8</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Max Position Size</span><span className="font-medium">$5,000</span></div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>Order Gatekeeper</CardTitle></CardHeader>
            <CardContent className="space-y-2">
              <div className="flex justify-between"><span className="text-muted-foreground">Orders Checked</span><span className="font-medium">1,542</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Orders Allowed</span><span className="font-medium text-green-500">1,538</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">Orders Denied</span><span className="font-medium text-red-500">4</span></div>
            </CardContent>
          </Card>
        </div>
      </div>
    </>
  );
}
