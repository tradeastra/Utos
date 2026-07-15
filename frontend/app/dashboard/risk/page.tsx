'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

export default function RiskPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Risk Management</h1>
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Exposure Limits</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            <div className="flex justify-between"><span className="text-muted-foreground">Max per Symbol</span><span className="font-medium">$20,000</span></div>
            <div className="flex justify-between"><span className="text-muted-foreground">Max per Exchange</span><span className="font-medium">$100,000</span></div>
            <div className="flex justify-between"><span className="text-muted-foreground">Current Exposure</span><span className="font-medium">$45,000</span></div>
            <div className="flex justify-between"><span className="text-muted-foreground">Utilization</span><Badge variant="warning">45%</Badge></div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Position Limits</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            <div className="flex justify-between"><span className="text-muted-foreground">Max Open Positions</span><span className="font-medium">20</span></div>
            <div className="flex justify-between"><span className="text-muted-foreground">Current Open</span><span className="font-medium">8</span></div>
            <div className="flex justify-between"><span className="text-muted-foreground">Max Position Size</span><span className="font-medium">$5,000</span></div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Order Gatekeeper</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            <div className="flex justify-between"><span className="text-muted-foreground">Orders Checked</span><span className="font-medium">1,542</span></div>
            <div className="flex justify-between"><span className="text-muted-foreground">Orders Allowed</span><span className="font-medium text-green-500">1,538</span></div>
            <div className="flex justify-between"><span className="text-muted-foreground">Orders Denied</span><span className="font-medium text-red-500">4</span></div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
