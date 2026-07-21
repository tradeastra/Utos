'use client';

import { useState } from 'react';
import { Zap } from 'lucide-react';
import { api } from '@/services/api';
import { cn } from '@/lib/utils';

interface ForceActionsProps {
  instanceId: string;
}

export function ForceActions({ instanceId }: ForceActionsProps) {
  const [level, setLevel] = useState('');
  const [price, setPrice] = useState('');
  const [qty, setQty] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ type: 'buy' | 'sell'; message: string } | null>(null);

  async function handleForceBuy() {
    setLoading(true);
    setResult(null);
    try {
      const res = await api.forceBuy(instanceId, {
        level: level ? Number(level) : undefined,
        price: price ? Number(price) : undefined,
        quantity: qty ? Number(qty) : undefined,
      });
      setResult({ type: 'buy', message: `Level ${res.level} · $${res.price} · Qty: ${res.quantity}` });
    } catch {
      setResult({ type: 'buy', message: 'Force buy failed' });
    } finally {
      setLoading(false);
    }
  }

  async function handleForceSell() {
    setLoading(true);
    setResult(null);
    try {
      const res = await api.forceSell(instanceId, {
        level: level ? Number(level) : undefined,
        price: price ? Number(price) : undefined,
        quantity: qty ? Number(qty) : undefined,
      });
      setResult({ type: 'sell', message: `Levels: ${res.levels_sold.join(', ')} · Qty: ${res.total_quantity} · $${res.total_value}` });
    } catch {
      setResult({ type: 'sell', message: 'Force sell failed' });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Zap className="h-4 w-4 text-amber-500" />
        <span className="text-sm font-semibold">Force Actions</span>
      </div>

      <div className="grid grid-cols-3 gap-2">
        <div>
          <label className="mb-1 block text-[10px] text-muted-foreground">Level</label>
          <input
            type="number"
            value={level}
            onChange={(e) => setLevel(e.target.value)}
            placeholder="Auto"
            className="w-full rounded-lg border border-border bg-background px-2 py-1.5 text-sm focus:border-amber-500 focus:outline-none"
          />
        </div>
        <div>
          <label className="mb-1 block text-[10px] text-muted-foreground">Price</label>
          <input
            type="number"
            step="0.01"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            placeholder="Market"
            className="w-full rounded-lg border border-border bg-background px-2 py-1.5 text-sm focus:border-amber-500 focus:outline-none"
          />
        </div>
        <div>
          <label className="mb-1 block text-[10px] text-muted-foreground">Qty</label>
          <input
            type="number"
            step="0.001"
            value={qty}
            onChange={(e) => setQty(e.target.value)}
            placeholder="Default"
            className="w-full rounded-lg border border-border bg-background px-2 py-1.5 text-sm focus:border-amber-500 focus:outline-none"
          />
        </div>
      </div>

      <div className="flex gap-2">
        <button
          disabled={loading}
          onClick={handleForceBuy}
          className="flex-1 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-green-700 disabled:opacity-50"
        >
          Force Buy
        </button>
        <button
          disabled={loading}
          onClick={handleForceSell}
          className="flex-1 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-red-700 disabled:opacity-50"
        >
          Force Sell
        </button>
      </div>

      {loading && (
        <div className="flex justify-center py-2">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-amber-500 border-t-transparent" />
        </div>
      )}

      {result && (
        <div className={cn(
          'rounded-lg p-3 text-xs',
          result.type === 'buy' ? 'bg-green-500/10 text-green-600 dark:text-green-400' : 'bg-red-500/10 text-red-600 dark:text-red-400',
        )}>
          {result.message}
        </div>
      )}
    </div>
  );
}
