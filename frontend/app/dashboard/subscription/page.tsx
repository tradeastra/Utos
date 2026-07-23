'use client';

import { useCallback, useEffect, useState } from 'react';
import { api } from '@/services/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { formatCurrency } from '@/lib/utils';

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
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Subscription</h1>
        <p className="text-muted-foreground">Manage your plan and add-ons</p>
      </div>

      {msg && (
        <div className={`rounded-md p-3 text-sm ${msg.type === 'success' ? 'bg-green-500/10 text-green-600' : 'bg-red-500/10 text-red-600'}`}>
          {msg.text}
        </div>
      )}

      {/* Plans */}
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

      {/* Add-ons */}
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
  );
}
