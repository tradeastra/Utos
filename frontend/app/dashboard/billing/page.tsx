'use client';

import { useEffect, useState } from 'react';
import { SubscriptionPlans } from '@/components/billing/subscription-plans';
import { TabNav } from '@/components/ui/tab-nav';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CheckCircle2, Clock, CreditCard, Receipt } from 'lucide-react';
import { api } from '@/services/api';

interface Invoice {
  id: string;
  amount: number;
  currency: string;
  plan: string;
  status: string;
  provider: string | null;
  created_at: string;
  paid_at: string | null;
}

function formatCurrency(amount: number, currency: string) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(amount);
}

function timeAgo(dateStr: string) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const days = Math.floor(diff / 86400000);
  if (days > 0) return days + 'd ago';
  const hours = Math.floor(diff / 3600000);
  if (hours > 0) return hours + 'h ago';
  return 'just now';
}

export default function BillingPage() {
  const [activeTab, setActiveTab] = useState<string>('plans');
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    async function load() {
      try {
        const data = await api.getInvoices();
        if (mounted) setInvoices((data as Invoice[]) ?? []);
      } catch {
        // Backend not available — show empty state, not fake data
        if (mounted) setInvoices([]);
      } finally {
        if (mounted) setLoading(false);
      }
    }
    load();
    return () => { mounted = false; };
  }, []);

  if (activeTab === 'plans') {
    return (
      <>
        <div className='md:hidden'>
          <TabNav
            tabs={[{ key: 'plans', label: 'Plans' }, { key: 'invoices', label: 'Invoices' }]}
            active={activeTab}
            onChange={setActiveTab}
          />
        </div>
        <SubscriptionPlans />
      </>
    );
  }

  return (
    <>
      <div className='min-h-full bg-slate-50 pb-24 dark:bg-background md:hidden'>
        <section className='relative overflow-hidden rounded-b-[2rem] bg-gradient-to-br from-violet-700 via-purple-600 to-fuchsia-600 px-5 pb-20 pt-[max(1.25rem,env(safe-area-inset-top))] text-white'>
          <div className='absolute -right-14 top-4 h-44 w-44 rounded-full bg-fuchsia-400/20 blur-2xl' />
          <div className='relative flex items-center gap-3'>
            <span className='flex h-10 w-10 items-center justify-center rounded-2xl bg-white/15 backdrop-blur-sm'>
              <Receipt className='h-5 w-5' />
            </span>
            <div>
              <h1 className='text-2xl font-bold tracking-tight'>Billing</h1>
              <p className='text-sm text-violet-200'>{invoices.length} invoices</p>
            </div>
          </div>
        </section>
        <div className='relative -mt-12 px-4 space-y-3'>
          <div className='md:hidden'>
            <TabNav
              tabs={[{ key: 'plans', label: 'Plans' }, { key: 'invoices', label: 'Invoices' }]}
              active={activeTab}
              onChange={setActiveTab}
            />
          </div>
          {loading ? (
            <div className='rounded-2xl bg-white p-8 text-center text-sm text-muted-foreground shadow-lg shadow-slate-900/5 dark:bg-card'>
              Loading invoices…
            </div>
          ) : invoices.length === 0 ? (
            <div className='rounded-2xl bg-white p-8 text-center text-sm text-muted-foreground shadow-lg shadow-slate-900/5 dark:bg-card'>
              No invoices yet.
            </div>
          ) : (
            invoices.map((inv) => {
              const isPaid = inv.status === 'paid';
              return (
                <div key={inv.id} className='overflow-hidden rounded-2xl bg-white shadow-lg shadow-slate-900/5 transition-transform active:scale-[0.99] dark:bg-card'>
                  <div className='flex items-center justify-between p-4'>
                    <div className='flex items-center gap-3'>
                      <span className={'flex h-10 w-10 items-center justify-center rounded-xl ' + (isPaid ? 'bg-emerald-100 text-emerald-600 dark:bg-emerald-500/10' : 'bg-amber-100 text-amber-600 dark:bg-amber-500/10')}>
                        {isPaid ? <CheckCircle2 className='h-5 w-5' /> : <Clock className='h-5 w-5' />}
                      </span>
                      <div>
                        <p className='font-semibold'>{inv.id}</p>
                        <p className='text-xs text-muted-foreground uppercase'>{inv.plan} plan</p>
                      </div>
                    </div>
                    <div className='text-right'>
                      <p className='font-bold'>{formatCurrency(inv.amount, inv.currency)}</p>
                      <span className={'rounded-full px-2.5 py-1 text-xs font-medium ' + (isPaid ? 'bg-emerald-100 text-emerald-600 dark:bg-emerald-500/10' : 'bg-amber-100 text-amber-600 dark:bg-amber-500/10')}>
                        {inv.status}
                      </span>
                    </div>
                  </div>
                  <div className='flex items-center justify-between border-t border-slate-100 px-4 py-2.5 text-xs text-muted-foreground dark:border-border'>
                    <span className='flex items-center gap-1'>
                      <CreditCard className='h-3.5 w-3.5' />
                      {inv.provider || '—'}
                    </span>
                    <span>{timeAgo(inv.created_at)}</span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
      <div className='hidden space-y-6 md:block'>
        <div>
          <h1 className='text-2xl font-bold'>Billing</h1>
          <p className='text-muted-foreground'>Manage plan, add-ons & invoices</p>
        </div>
        <TabNav
          tabs={[{ key: 'plans', label: 'Plans' }, { key: 'invoices', label: 'Invoices' }]}
          active={activeTab}
          onChange={setActiveTab}
        />
        <Card>
          <CardHeader><CardTitle>Invoice History</CardTitle></CardHeader>
          <CardContent>
            {loading ? (
              <p className='text-sm text-muted-foreground'>Loading invoices…</p>
            ) : invoices.length === 0 ? (
              <p className='text-sm text-muted-foreground'>No invoices yet.</p>
            ) : (
              <div className='overflow-x-auto'>
                <table className='w-full text-sm'>
                  <thead>
                    <tr className='border-b text-left text-muted-foreground'>
                      <th className='pb-2'>Invoice</th>
                      <th className='pb-2'>Amount</th>
                      <th className='pb-2'>Plan</th>
                      <th className='pb-2'>Provider</th>
                      <th className='pb-2'>Status</th>
                      <th className='pb-2'>Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {invoices.map((inv) => (
                      <tr key={inv.id} className='border-b'>
                        <td className='py-3 font-medium'>{inv.id}</td>
                        <td className='py-3'>{formatCurrency(inv.amount, inv.currency)}</td>
                        <td className='py-3 uppercase'>{inv.plan}</td>
                        <td className='py-3'>{inv.provider || '—'}</td>
                        <td className='py-3'>
                          <Badge variant={inv.status === 'paid' ? 'success' : 'warning'}>{inv.status}</Badge>
                        </td>
                        <td className='py-3 text-muted-foreground'>{timeAgo(inv.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  );
}
