'use client';

import { UserPlus, Gift, Users } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';

export default function AffiliatePage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Affiliate Program</h1>
        <p className="text-muted-foreground">Earn rewards by referring new users</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="p-5">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Users className="h-4 w-4" />
              <span className="text-xs uppercase tracking-wider">Referrals</span>
            </div>
            <div className="mt-2 text-2xl font-bold">0</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Gift className="h-4 w-4" />
              <span className="text-xs uppercase tracking-wider">Rewards Earned</span>
            </div>
            <div className="mt-2 text-2xl font-bold">$0.00</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <div className="flex items-center gap-2 text-muted-foreground">
              <UserPlus className="h-4 w-4" />
              <span className="text-xs uppercase tracking-wider">Active Referrals</span>
            </div>
            <div className="mt-2 text-2xl font-bold">0</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Your Referral Link</CardTitle>
          <CardDescription>Share this link to earn commission on referrals</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <UserPlus className="h-12 w-12 text-muted-foreground/40" />
            <p className="mt-4 text-sm text-muted-foreground">Affiliate program coming soon.</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
