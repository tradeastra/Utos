'use client';

<<<<<<< HEAD
=======
import { useState } from 'react';
>>>>>>> develop
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { formatCurrency, timeAgo } from '@/lib/utils';
import { Receipt, CreditCard, CheckCircle2, Clock } from 'lucide-react';
<<<<<<< HEAD
=======
import { SubscriptionPlans } from '@/components/billing/subscription-plans';
import { TabNav } from '@/components/ui/tab-nav';
import { useSearchParams } from 'next/navigation';
>>>>>>> develop

const invoices = [
  { id: 'inv-1', amount: 99, currency: 'USD', plan: 'pro', status: 'paid', provider: 'manual', created_at: new Date(Date.now() - 86400000).toISOString(), paid_at: new Date(Date.now() - 86000000).toISOString() },
  { id: 'inv-2', amount: 99, currency: 'USD', plan: 'pro', status: 'paid', provider: 'stripe', created_at: new Date(Date.now() - 172800000).toISOString(), paid_at: new Date(Date.now() - 172000000).toISOString() },
  { id: 'inv-3', amount: 99, currency: 'USD', plan: 'pro', status: 'pending', provider: null, created_at: new Date().toISOString(), paid_at: null },
];

export default function BillingPage() {
<<<<<<< HEAD
=======
  const searchParams = useSearchParams();
  const [activeTab, setActiveTab] = useState(searchParams.get('tab') === 'plans' ? 'plans' : 'invoices');

  if (activeTab === 'plans') {
    return (
      <>
        <div className="hidden md:block space-y-6">
          <div>
            <h1 className="text-2xl font-bold">Billing</h1>
            <p className="text-muted-foreground">Manage plan, add-ons & invoices</p>
          </div>
          <TabNav
            tabs={[
              { key: 'plans', label: 'Plans' },
              { key: 'invoices', label: 'Invoices' },
            ]}
            active={activeTab}
            onChange={setActiveTab}
          />
        </div>
        <SubscriptionPlans />
      </>
    );
  }

>>>>>>> develop
  return (
    <>
      {/* Mobile */}
      <div className="min-h-full bg-slate-50 pb-24 dark:bg-background md:hidden">
        <section className="relative overflow-hidden rounded-b-[2rem] bg-gradient-to-br from-violet-700 via-purple-600 to-fuchsia-600 px-5 pb-20 pt-[max(1.25rem,env(safe-area-inset-top))] text-white">
          <div className="absolute -right-14 top-4 h-44 w-44 rounded-full bg-fuchsia-400/20 blur-2xl" />
          <div className="relative flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-white/15 backdrop-blur-sm">
              <Receipt className="h-5 w-5" />
            </span>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">Billing</h1>
              <p className="text-sm text-violet-200">{invoices.length} invoices</p>
            </div>
          </div>
        </section>

        <div className="relative -mt-12 px-4 space-y-3">
<<<<<<< HEAD
=======
          <div className="md:hidden">
            <TabNav
              tabs={[
                { key: 'plans', label: 'Plans' },
                { key: 'invoices', label: 'Invoices' },
              ]}
              active={activeTab}
              onChange={setActiveTab}
            />
          </div>
>>>>>>> develop
          {invoices.map((inv) => {
            const isPaid = inv.status === 'paid';
            return (
              <div key={inv.id} className="overflow-hidden rounded-2xl bg-white shadow-lg shadow-slate-900/5 transition-transform active:scale-[0.99] dark:bg-card">
                <div className="flex items-center justify-between p-4">
                  <div className="flex items-center gap-3">
                    <span className={`flex h-10 w-10 items-center justify-center rounded-xl ${isPaid ? 'bg-emerald-100 text-emerald-600 dark:bg-emerald-500/10' : 'bg-amber-100 text-amber-600 dark:bg-amber-500/10'}`}>
                      {isPaid ? <CheckCircle2 className="h-5 w-5" /> : <Clock className="h-5 w-5" />}
                    </span>
                    <div>
                      <p className="font-semibold">{inv.id}</p>
                      <p className="text-xs text-muted-foreground uppercase">{inv.plan} plan</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="font-bold">{formatCurrency(inv.amount, inv.currency)}</p>
                    <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${isPaid ? 'bg-emerald-100 text-emerald-600 dark:bg-emerald-500/10' : 'bg-amber-100 text-amber-600 dark:bg-amber-500/10'}`}>
                      {inv.status}
                    </span>
                  </div>
                </div>
                <div className="flex items-center justify-between border-t border-slate-100 px-4 py-2.5 text-xs text-muted-foreground dark:border-border">
                  <span className="flex items-center gap-1">
                    <CreditCard className="h-3.5 w-3.5" />
                    {inv.provider || '—'}
                  </span>
                  <span>{timeAgo(inv.created_at)}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Desktop */}
      <div className="hidden space-y-6 md:block">
<<<<<<< HEAD
        <h1 className="text-2xl font-bold">Billing</h1>
=======
        <div>
          <h1 className="text-2xl font-bold">Billing</h1>
          <p className="text-muted-foreground">Manage plan, add-ons & invoices</p>
        </div>
        <TabNav
          tabs={[
            { key: 'plans', label: 'Plans' },
            { key: 'invoices', label: 'Invoices' },
          ]}
          active={activeTab}
          onChange={setActiveTab}
        />
>>>>>>> develop
        <Card>
          <CardHeader><CardTitle>Invoice History</CardTitle></CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="pb-2">Invoice</th>
                    <th className="pb-2">Amount</th>
                    <th className="pb-2">Plan</th>
                    <th className="pb-2">Provider</th>
                    <th className="pb-2">Status</th>
                    <th className="pb-2">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {invoices.map((inv) => (
                    <tr key={inv.id} className="border-b">
                      <td className="py-3 font-medium">{inv.id}</td>
                      <td className="py-3">{formatCurrency(inv.amount, inv.currency)}</td>
                      <td className="py-3 uppercase">{inv.plan}</td>
                      <td className="py-3">{inv.provider || '—'}</td>
                      <td className="py-3">
                        <Badge variant={inv.status === 'paid' ? 'success' : 'warning'}>{inv.status}</Badge>
                      </td>
                      <td className="py-3 text-muted-foreground">{timeAgo(inv.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>
    </>
  );
}
