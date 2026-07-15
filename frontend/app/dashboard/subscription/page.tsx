'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { formatCurrency } from '@/lib/utils';

const plans = [
  { tier: 'free', name: 'Free', price: 0, limits: '1 instance, 2 symbols', features: ['Basic Grid'] },
  { tier: 'starter', name: 'Starter', price: 29, limits: '3 instances, 10 symbols', features: ['Basic Grid', 'Profit Lock', 'Notifications'] },
  { tier: 'pro', name: 'Pro', price: 99, limits: '10 instances, 50 symbols', features: ['+ Automation', 'Advanced Risk', 'Priority Support'] },
  { tier: 'enterprise', name: 'Enterprise', price: 499, limits: '100 instances, 500 symbols', features: ['+ Custom Strategies', 'Dedicated Support', 'White Label'] },
];

export default function SubscriptionPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Subscription</h1>
        <p className="text-muted-foreground">Current plan: <Badge variant="success">Pro</Badge></p>
      </div>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
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
  );
}
