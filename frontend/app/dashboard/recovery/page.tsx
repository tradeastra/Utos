'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

export default function RecoveryPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Recovery Status</h1>
      <Card>
        <CardHeader><CardTitle>4-Layer Recovery Pipeline</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between rounded-md border p-3">
            <span className="font-medium">1. Connection Recovery</span>
            <Badge variant="success">completed</Badge>
          </div>
          <div className="flex items-center justify-between rounded-md border p-3">
            <span className="font-medium">2. State Recovery</span>
            <Badge variant="success">completed</Badge>
          </div>
          <div className="flex items-center justify-between rounded-md border p-3">
            <span className="font-medium">3. Runtime Reconciliation</span>
            <Badge variant="success">completed</Badge>
          </div>
          <div className="flex items-center justify-between rounded-md border p-3">
            <span className="font-medium">4. Persistence Checkpoint</span>
            <Badge variant="success">completed</Badge>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
