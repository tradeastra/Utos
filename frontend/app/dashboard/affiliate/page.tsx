'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { formatCurrency } from '@/lib/utils';

export default function AffiliatePage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Affiliate Dashboard</h1>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Total Referrals</CardTitle></CardHeader>
          <CardContent><p className="text-2xl font-bold">12</p></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Active Referrals</CardTitle></CardHeader>
          <CardContent><p className="text-2xl font-bold">8</p></CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground">Total Earnings</CardTitle></CardHeader>
          <CardContent><p className="text-2xl font-bold text-green-500">{formatCurrency(118.80)}</p></CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle>Your Referral Link</CardTitle></CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Input value="https://utos.app/register?ref=UTOS-A1B2C3" readOnly />
            <Button>Copy</Button>
          </div>
          <p className="mt-2 text-sm text-muted-foreground">Commission rate: 10% per subscription payment</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Downline</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          {['user2@example.com', 'user3@example.com', 'user4@example.com'].map((email) => (
            <div key={email} className="flex items-center justify-between rounded-md border p-3 text-sm">
              <span className="font-medium">{email}</span>
              <Badge variant="success">active</Badge>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
