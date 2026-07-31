'use client';

<<<<<<< HEAD
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { formatCurrency } from '@/lib/utils';
import { UserPlus, Users, DollarSign, Copy, ChevronRight } from 'lucide-react';

const downline = ['user2@example.com', 'user3@example.com', 'user4@example.com'];

export default function AffiliatePage() {
  return (
    <>
      {/* Mobile */}
      <div className="min-h-full bg-slate-50 pb-24 dark:bg-background md:hidden">
        <section className="relative overflow-hidden rounded-b-[2rem] bg-gradient-to-br from-violet-700 via-purple-600 to-fuchsia-600 px-5 pb-24 pt-[max(1.25rem,env(safe-area-inset-top))] text-white">
          <div className="absolute -right-14 top-4 h-44 w-44 rounded-full bg-fuchsia-400/20 blur-2xl" />
          <div className="relative flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-white/15 backdrop-blur-sm">
              <UserPlus className="h-5 w-5" />
            </span>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">Affiliate</h1>
              <p className="text-sm text-violet-200">Earn 10% commission</p>
            </div>
          </div>
        </section>

        <div className="relative -mt-16 px-4 space-y-3">
          {/* Stats Card */}
          <div className="overflow-hidden rounded-3xl bg-white shadow-xl shadow-slate-900/10 dark:bg-card">
            <div className="grid grid-cols-3 divide-x divide-slate-200 dark:divide-border">
              <div className="p-4 text-center">
                <span className="mx-auto flex h-10 w-10 items-center justify-center rounded-xl bg-violet-100 text-violet-600 dark:bg-violet-500/10">
                  <Users className="h-5 w-5" />
                </span>
                <p className="mt-2 text-lg font-bold">12</p>
                <p className="text-xs text-muted-foreground">Total</p>
              </div>
              <div className="p-4 text-center">
                <span className="mx-auto flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-100 text-emerald-600 dark:bg-emerald-500/10">
                  <Users className="h-5 w-5" />
                </span>
                <p className="mt-2 text-lg font-bold">8</p>
                <p className="text-xs text-muted-foreground">Active</p>
              </div>
              <div className="p-4 text-center">
                <span className="mx-auto flex h-10 w-10 items-center justify-center rounded-xl bg-amber-100 text-amber-600 dark:bg-amber-500/10">
                  <DollarSign className="h-5 w-5" />
                </span>
                <p className="mt-2 text-lg font-bold text-emerald-500">{formatCurrency(118.80)}</p>
                <p className="text-xs text-muted-foreground">Earnings</p>
              </div>
            </div>
          </div>

          {/* Referral Link */}
          <div className="overflow-hidden rounded-3xl bg-white shadow-xl shadow-slate-900/10 dark:bg-card">
            <div className="border-b border-slate-100 px-5 py-4 dark:border-border">
              <p className="text-sm font-semibold">Your Referral Link</p>
            </div>
            <div className="space-y-3 p-5">
              <div className="flex items-center gap-2 rounded-xl bg-slate-50 p-3 dark:bg-muted/50">
                <Input value="https://utos.app/register?ref=UTOS-A1B2C3" readOnly className="border-0 bg-transparent" />
                <Button size="sm" className="shrink-0">
                  <Copy className="mr-1.5 h-4 w-4" />
                  Copy
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">Commission rate: 10% per subscription payment</p>
            </div>
          </div>

          {/* Downline */}
          <p className="px-1 pt-2 text-sm font-semibold text-slate-700 dark:text-slate-300">Downline</p>
          <div className="overflow-hidden rounded-3xl bg-white shadow-xl shadow-slate-900/10 dark:bg-card">
            <div className="divide-y divide-slate-100 dark:divide-border">
              {downline.map((email) => (
                <div key={email} className="flex items-center gap-3 p-4">
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-violet-100 text-sm font-bold text-violet-600 dark:bg-violet-500/10">
                    {email[0].toUpperCase()}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold">{email}</p>
                  </div>
                  <span className="rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-medium text-emerald-600 dark:bg-emerald-500/10">
                    active
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Desktop */}
      <div className="hidden space-y-6 md:block">
        <h1 className="text-2xl font-bold">Affiliate Dashboard</h1>
        <div className="grid gap-4 grid-cols-1 sm:grid-cols-3">
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
            <div className="flex flex-col gap-2 sm:flex-row">
              <Input value="https://utos.app/register?ref=UTOS-A1B2C3" readOnly />
              <Button>Copy</Button>
            </div>
            <p className="mt-2 text-sm text-muted-foreground">Commission rate: 10% per subscription payment</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Downline</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {downline.map((email) => (
              <div key={email} className="flex items-center justify-between rounded-md border p-3 text-sm">
                <span className="font-medium">{email}</span>
                <Badge variant="success">active</Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </>
=======
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
>>>>>>> develop
  );
}
