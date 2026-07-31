'use client';

import { Users } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';

export default function WorkersPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Workers</h1>
        <p className="text-muted-foreground">Monitor background worker processes</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Worker Status</CardTitle>
          <CardDescription>Active trading engine workers and their health</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <Users className="h-12 w-12 text-muted-foreground/40" />
            <p className="mt-4 text-sm text-muted-foreground">Worker monitoring coming soon.</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
