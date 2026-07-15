'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { formatNumber } from '@/lib/utils';
import type { GridLevel } from '@/types';

const statusColors: Record<string, 'default' | 'secondary' | 'success' | 'destructive' | 'warning'> = {
  waiting: 'secondary',
  open: 'default',
  filled: 'success',
  cancelled: 'destructive',
  tp_hit: 'warning',
};

export default function GridPage() {
  const [levels, setLevels] = useState<GridLevel[]>([]);
  const [currentPrice, setCurrentPrice] = useState(0);

  useEffect(() => {
    const price = 65000;
    setCurrentPrice(price);
    const grid: GridLevel[] = [];
    for (let i = 0; i < 10; i++) {
      const levelPrice = price * (1 + (i - 5) * 0.01);
      const statuses: GridLevel['status'][] = ['waiting', 'open', 'filled', 'tp_hit', 'waiting', 'open', 'filled', 'cancelled', 'waiting', 'open'];
      grid.push({
        index: i,
        price: levelPrice,
        side: i < 5 ? 'buy' : 'sell',
        status: statuses[i],
        quantity: 0.1,
        order_id: statuses[i] === 'open' || statuses[i] === 'filled' ? `ord-${i}` : null,
      });
    }
    setLevels(grid);
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Grid Visualization</h1>
        <p className="text-muted-foreground">Live grid levels for BTC/USDT</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Current Price: ${formatNumber(currentPrice)}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {levels.map((level) => (
              <div
                key={level.index}
                className="flex items-center justify-between rounded-md border p-3"
              >
                <div className="flex items-center gap-4">
                  <span className="text-sm text-muted-foreground">#{level.index}</span>
                  <Badge variant={level.side === 'buy' ? 'success' : 'destructive'}>
                    {level.side.toUpperCase()}
                  </Badge>
                  <span className="font-medium">${formatNumber(level.price)}</span>
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-sm text-muted-foreground">{level.quantity} BTC</span>
                  <Badge variant={statusColors[level.status] || 'secondary'}>
                    {level.status}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
