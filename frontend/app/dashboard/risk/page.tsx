'use client';

import { Shield, AlertTriangle, Activity } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';

export default function RiskPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Risk Management</h1>
        <p className="text-muted-foreground">Monitor and configure risk parameters</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="p-5">
            <div className="flex items-center gap-2 text-muted-foreground">
              <AlertTriangle className="h-4 w-4" />
              <span className="text-xs uppercase tracking-wider">Max Drawdown</span>
            </div>
            <div className="mt-2 text-2xl font-bold">â€”</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Shield className="h-4 w-4" />
              <span className="text-xs uppercase tracking-wider">Risk Score</span>
            </div>
            <div className="mt-2 text-2xl font-bold">â€”</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Activity className="h-4 w-4" />
              <span className="text-xs uppercase tracking-wider">Exposure</span>
            </div>
            <div className="mt-2 text-2xl font-bold">â€”</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Risk Rules</CardTitle>
          <CardDescription>Configure stop-loss, max position size, and drawdown limits</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <Shield className="h-12 w-12 text-muted-foreground/40" />
            <p className="mt-4 text-sm text-muted-foreground">Risk management dashboard coming soon.</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
