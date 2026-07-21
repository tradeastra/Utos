'use client';

import { cn } from '@/lib/utils';
import { ArrowUp, ArrowDown, Minus } from 'lucide-react';

export interface CoinRowData {
  id: string;
  symbol: string;
  status: 'running' | 'paused' | 'stopped' | 'error' | 'created' | 'ready';
  exchange: string;
  qty: number;
  currentPrice: number;
  change24h: number;
  avgPrice: number | null;
  step: number | null;
  totalSteps: number | null;
  profit: number | null;
  profitPct: number | null;
  isAveraging: boolean;
}

interface CoinRowProps {
  data: CoinRowData;
  onClick?: (symbol: string) => void;
}

const STATUS_DOT: Record<string, string> = {
  running: 'bg-emerald-500',
  paused: 'bg-amber-500',
  stopped: 'bg-red-500',
  error: 'bg-red-500',
  created: 'bg-blue-500',
  ready: 'bg-cyan-500',
};

function formatPrice(price: number): string {
  if (price >= 1000) return price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  if (price >= 1) return price.toFixed(4);
  if (price >= 0.01) return price.toFixed(6);
  return price.toFixed(8);
}

function formatProfit(profit: number | null): string {
  if (profit === null) return '—';
  const sign = profit >= 0 ? '+' : '';
  return `${sign}$${profit.toFixed(2)}`;
}

export function CoinRow({ data, onClick }: CoinRowProps) {
  const change = data.change24h;
  const isProfit = (data.profit ?? 0) >= 0;
  const hasPosition = data.qty > 0;

  return (
    <div
      onClick={() => onClick?.(data.symbol)}
      className={cn(
        'flex items-center gap-3 rounded-xl border border-border/50 bg-card px-3 py-3 transition-all',
        'hover:border-violet-500/30 hover:bg-violet-500/5 cursor-pointer',
        'md:grid md:grid-cols-12 md:gap-2',
      )}
    >
      {/* Status + Symbol */}
      <div className="flex items-center gap-2 md:col-span-3">
        <span className={cn('h-2 w-2 shrink-0 rounded-full', STATUS_DOT[data.status] ?? 'bg-muted')} />
        <div className="min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="truncate text-sm font-semibold">{data.symbol}</span>
            {data.isAveraging && (
              <span className="rounded bg-violet-500/10 px-1 py-0.5 text-[9px] font-medium text-violet-500">AVG</span>
            )}
          </div>
          <span className="text-[10px] text-muted-foreground">{data.exchange}</span>
        </div>
      </div>

      {/* Qty — desktop only */}
      <div className="hidden md:col-span-2 md:block">
        <span className="text-sm tabular-nums">{data.qty > 0 ? data.qty.toFixed(6) : '—'}</span>
      </div>

      {/* Price */}
      <div className="flex-1 md:col-span-2">
        <div className="text-sm font-medium tabular-nums">${formatPrice(data.currentPrice)}</div>
        <div className={cn(
          'flex items-center gap-0.5 text-[10px]',
          change > 0 ? 'text-emerald-500' : change < 0 ? 'text-red-500' : 'text-muted-foreground',
        )}>
          {change > 0 ? <ArrowUp className="h-3 w-3" /> : change < 0 ? <ArrowDown className="h-3 w-3" /> : <Minus className="h-3 w-3" />}
          {Math.abs(change).toFixed(2)}%
        </div>
      </div>

      {/* AVG — desktop only */}
      <div className="hidden md:col-span-2 md:block">
        {data.avgPrice ? (
          <div>
            <div className="text-sm tabular-nums">${formatPrice(data.avgPrice)}</div>
            <div className="text-[10px] text-muted-foreground">
              Step {data.step ?? '—'}/{data.totalSteps ?? '—'}
            </div>
          </div>
        ) : (
          <span className="text-sm text-muted-foreground">—</span>
        )}
      </div>

      {/* Profit */}
      <div className="text-right md:col-span-3">
        <div className={cn(
          'text-sm font-semibold tabular-nums',
          !hasPosition && 'text-muted-foreground',
          hasPosition && isProfit && 'text-emerald-500',
          hasPosition && !isProfit && 'text-red-500',
        )}>
          {formatProfit(data.profit)}
        </div>
        {hasPosition && data.profitPct !== null && (
          <div className={cn('text-[10px]', isProfit ? 'text-emerald-500' : 'text-red-500')}>
            {isProfit ? '+' : ''}{data.profitPct.toFixed(2)}%
          </div>
        )}
      </div>
    </div>
  );
}
