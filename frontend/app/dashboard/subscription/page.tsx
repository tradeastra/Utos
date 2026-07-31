<<<<<<< HEAD
'use client';

import { useCallback, useEffect, useState } from 'react';
import { api } from '@/services/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { formatCurrency } from '@/lib/utils';
import { CreditCard, Check, Sparkles, Zap } from 'lucide-react';

const plans = [
  { tier: 'free', name: 'Free', price: 0, limits: '1 instance, 2 symbols', features: ['Basic Grid'] },
  { tier: 'starter', name: 'Starter', price: 29, limits: '3 instances, 10 symbols', features: ['Basic Grid', 'Profit Lock', 'Trailing Profit', 'Notifications'] },
  { tier: 'pro', name: 'Pro', price: 99, limits: '10 instances, 50 symbols', features: ['+ Automation', 'Advanced Risk', 'Priority Support'] },
  { tier: 'enterprise', name: 'Enterprise', price: 499, limits: '100 instances, 500 symbols', features: ['+ Custom Strategies', 'Dedicated Support', 'White Label'] },
];

interface AddOnInfo {
  key: string;
  name: string;
  description: string;
  price: number;
  is_purchased: boolean;
  is_active: boolean;
}

export default function SubscriptionPage() {
  const [addons, setAddons] = useState<AddOnInfo[]>([]);
  const [purchasing, setPurchasing] = useState<string | null>(null);
  const [msg, setMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const loadAddons = useCallback(async () => {
    try {
      const list = await api.listAddons();
      setAddons(list || []);
    } catch {
      setAddons([]);
    }
  }, []);

  useEffect(() => {
    loadAddons();
  }, [loadAddons]);

  async function handlePurchase(addonKey: string) {
    setPurchasing(addonKey);
    setMsg(null);
    try {
      await api.purchaseAddon(addonKey, 30);
      setMsg({ type: 'success', text: 'Add-on purchased successfully!' });
      await loadAddons();
    } catch (err) {
      setMsg({ type: 'error', text: err instanceof Error ? err.message : 'Failed to purchase add-on' });
    } finally {
      setPurchasing(null);
    }
  }

  return (
    <>
      {/* Mobile */}
      <div className="min-h-full bg-slate-50 pb-24 dark:bg-background md:hidden">
        <section className="relative overflow-hidden rounded-b-[2rem] bg-gradient-to-br from-violet-700 via-purple-600 to-fuchsia-600 px-5 pb-20 pt-[max(1.25rem,env(safe-area-inset-top))] text-white">
          <div className="absolute -right-14 top-4 h-44 w-44 rounded-full bg-fuchsia-400/20 blur-2xl" />
          <div className="relative flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-white/15 backdrop-blur-sm">
              <CreditCard className="h-5 w-5" />
            </span>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">Subscription</h1>
              <p className="text-sm text-violet-200">Manage plan & add-ons</p>
            </div>
          </div>
        </section>

        <div className="relative -mt-12 px-4 space-y-3">
          {msg && (
            <div className={`rounded-2xl p-3 text-sm ${msg.type === 'success' ? 'bg-emerald-500/10 text-emerald-600' : 'bg-red-500/10 text-red-600'}`}>
              {msg.text}
            </div>
          )}

          {/* Plans */}
          <p className="px-1 pt-2 text-sm font-semibold text-slate-700 dark:text-slate-300">Plans</p>
          <div className="overflow-x-auto pb-1">
            <div className="flex gap-3" style={{ width: 'max-content' }}>
              {plans.map((plan) => {
                const isCurrent = plan.tier === 'pro';
                return (
                  <div
                    key={plan.tier}
                    className={`w-64 shrink-0 overflow-hidden rounded-3xl bg-white shadow-lg shadow-slate-900/5 dark:bg-card ${isCurrent ? 'ring-2 ring-violet-500' : ''}`}
                  >
                    <div className={`p-5 ${isCurrent ? 'bg-gradient-to-br from-violet-600 to-fuchsia-600 text-white' : ''}`}>
                      <div className="flex items-center justify-between">
                        <p className="font-bold">{plan.name}</p>
                        {isCurrent && (
                          <span className="rounded-full bg-white/20 px-2.5 py-1 text-xs font-medium">Current</span>
                        )}
                      </div>
                      <p className={`mt-2 text-2xl font-bold ${isCurrent ? '' : 'text-slate-900 dark:text-white'}`}>
                        {formatCurrency(plan.price)}
                        <span className={`text-sm font-normal ${isCurrent ? 'text-violet-200' : 'text-muted-foreground'}`}>/mo</span>
                      </p>
                      <p className={`mt-1 text-xs ${isCurrent ? 'text-violet-200' : 'text-muted-foreground'}`}>{plan.limits}</p>
                    </div>
                    <div className="space-y-2 p-5">
                      {plan.features.map((f) => (
                        <div key={f} className="flex items-center gap-2 text-sm">
                          <Check className="h-4 w-4 shrink-0 text-emerald-500" />
                          <span className="text-muted-foreground">{f}</span>
                        </div>
                      ))}
                      <Button
                        variant={isCurrent ? 'secondary' : 'default'}
                        className="mt-3 w-full"
                        disabled={isCurrent}
                      >
                        {isCurrent ? 'Current Plan' : `Upgrade`}
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Add-ons */}
          <p className="px-1 pt-3 text-sm font-semibold text-slate-700 dark:text-slate-300">Add-ons</p>
          <p className="px-1 text-xs text-muted-foreground">Enhance your plan with additional features</p>
          {addons.length === 0 ? (
            <div className="rounded-3xl bg-white p-6 text-center text-sm text-muted-foreground shadow-lg shadow-slate-900/5 dark:bg-card">
              Loading add-ons...
            </div>
          ) : (
            <div className="space-y-2">
              {addons.map((addon) => (
                <div key={addon.key} className={`overflow-hidden rounded-2xl bg-white shadow-lg shadow-slate-900/5 transition-transform active:scale-[0.99] dark:bg-card ${addon.is_active ? 'ring-2 ring-violet-500' : ''}`}>
                  <div className="flex items-center justify-between p-4">
                    <div className="flex items-center gap-3">
                      <span className={`flex h-10 w-10 items-center justify-center rounded-xl ${addon.is_active ? 'bg-violet-100 text-violet-600 dark:bg-violet-500/10' : 'bg-amber-100 text-amber-600 dark:bg-amber-500/10'}`}>
                        <Sparkles className="h-5 w-5" />
                      </span>
                      <div>
                        <p className="font-semibold">{addon.name}</p>
                        <p className="text-xs text-muted-foreground">{formatCurrency(addon.price)}/mo</p>
                      </div>
                    </div>
                    {addon.is_active && (
                      <span className="rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-medium text-emerald-600 dark:bg-emerald-500/10">
                        Active
                      </span>
                    )}
                  </div>
                  <p className="px-4 pb-3 text-xs text-muted-foreground">{addon.description}</p>
                  {!addon.is_active && (
                    <div className="border-t border-slate-100 p-3 dark:border-border">
                      <Button
                        className="w-full"
                        disabled={purchasing === addon.key}
                        onClick={() => handlePurchase(addon.key)}
                      >
                        {purchasing === addon.key ? 'Processing...' : `Buy ${formatCurrency(addon.price)}/mo`}
                      </Button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Desktop */}
      <div className="hidden space-y-6 md:block">
        <div>
          <h1 className="text-2xl font-bold">Subscription</h1>
          <p className="text-muted-foreground">Manage your plan and add-ons</p>
        </div>

        {msg && (
          <div className={`rounded-md p-3 text-sm ${msg.type === 'success' ? 'bg-green-500/10 text-green-600' : 'bg-red-500/10 text-red-600'}`}>
            {msg.text}
          </div>
        )}

        <div>
          <h2 className="text-lg font-semibold mb-3">Plans</h2>
          <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
            {plans.map((plan) => (
              <Card key={plan.tier} className={plan.tier === 'pro' ? 'border-primary' : ''}>
                <CardHeader>
                  <CardTitle>{plan.name}</CardTitle>
                  <p className="text-2xl font-bold">{formatCurrency(plan.price)}<span className="text-sm font-normal text-muted-foreground">/mo</span></p>
                </CardHeader>
                <CardContent className="space-y-3">
                  <p className="text-sm text-muted-foreground">{plan.limits}</p>
                  <ul className="space-y-1 text-sm">
                    {plan.features.map((f) => (
                      <li key={f} className="text-muted-foreground">• {f}</li>
                    ))}
                  </ul>
                  <Button
                    variant={plan.tier === 'pro' ? 'secondary' : 'default'}
                    className="w-full"
                    disabled={plan.tier === 'pro'}
                  >
                    {plan.tier === 'pro' ? 'Current Plan' : `Upgrade to ${plan.name}`}
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        <div>
          <h2 className="text-lg font-semibold mb-3">Add-ons</h2>
          <p className="text-sm text-muted-foreground mb-4">Enhance your plan with additional features</p>
          <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
            {addons.length === 0 ? (
              <Card className="md:col-span-2 lg:col-span-3">
                <CardContent className="py-8 text-center text-sm text-muted-foreground">
                  Loading add-ons...
                </CardContent>
              </Card>
            ) : (
              addons.map((addon) => (
                <Card key={addon.key} className={addon.is_active ? 'border-primary' : ''}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-lg">{addon.name}</CardTitle>
                      {addon.is_active && <Badge variant="success">Active</Badge>}
                    </div>
                    <p className="text-2xl font-bold">{formatCurrency(addon.price)}<span className="text-sm font-normal text-muted-foreground">/mo</span></p>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <p className="text-sm text-muted-foreground">{addon.description}</p>
                    <Button
                      className="w-full"
                      variant={addon.is_active ? 'secondary' : 'default'}
                      disabled={addon.is_active || purchasing === addon.key}
                      onClick={() => handlePurchase(addon.key)}
                    >
                      {addon.is_active
                        ? 'Active'
                        : purchasing === addon.key
                          ? 'Processing...'
                          : `Buy ${formatCurrency(addon.price)}/mo`}
                    </Button>
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        </div>
      </div>
    </>
  );
=======
import { redirect } from 'next/navigation';

export default function SubscriptionPage() {
  redirect('/dashboard/billing?tab=plans');
>>>>>>> develop
}
