'use client';

import { RefreshCw } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';

export default function RecoveryPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Recovery</h1>
        <p className="text-muted-foreground">Recover and resume interrupted trading instances</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recovery Queue</CardTitle>
          <CardDescription>Instances that need manual or automatic recovery</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <RefreshCw className="h-12 w-12 text-muted-foreground/40" />
            <p className="mt-4 text-sm text-muted-foreground">No instances need recovery.</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
