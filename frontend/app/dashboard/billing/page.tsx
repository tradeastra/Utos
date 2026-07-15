'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { formatCurrency, timeAgo } from '@/lib/utils';

const invoices = [
  { id: 'inv-1', amount: 99, currency: 'USD', plan: 'pro', status: 'paid', provider: 'manual', created_at: new Date(Date.now() - 86400000).toISOString(), paid_at: new Date(Date.now() - 86000000).toISOString() },
  { id: 'inv-2', amount: 99, currency: 'USD', plan: 'pro', status: 'paid', provider: 'stripe', created_at: new Date(Date.now() - 172800000).toISOString(), paid_at: new Date(Date.now() - 172000000).toISOString() },
  { id: 'inv-3', amount: 99, currency: 'USD', plan: 'pro', status: 'pending', provider: null, created_at: new Date().toISOString(), paid_at: null },
];

export default function BillingPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Billing</h1>
      <Card>
        <CardHeader><CardTitle>Invoice History</CardTitle></CardHeader>
        <CardContent>
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
        </CardContent>
      </Card>
    </div>
  );
}
