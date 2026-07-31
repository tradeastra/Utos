'use client';

import { Radio } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';

export default function EventsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Events</h1>
        <p className="text-muted-foreground">Real-time system and trading events feed</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Event Stream</CardTitle>
          <CardDescription>Live feed of order fills, grid steps, and system events</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <Radio className="h-12 w-12 text-muted-foreground/40" />
            <p className="mt-4 text-sm text-muted-foreground">Event stream coming soon.</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
