'use client';

import { useEffect, useState, useCallback } from 'react';
import { Coins, Search, Lock, Check } from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/services/api';
import type { TickerItem } from '@/types';

interface CoinVolumeListProps {
  exchange: string;
  selectedCoins: string[];
  onChange: (coins: string[]) => void;
  maxSelection: number;
}

function formatVolume(vol: string): string {
  const n = Number(vol);
  if (isNaN(n)) return vol;
  if (n >= 1e9) return `${(n / 1e9).toFixed(2)}B`;
  if (n >= 1e6) return `${(n / 1e6).toFixed(2)}M`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(2)}K`;
  return n.toFixed(2);
}

function formatPrice(price: string): string {
  const n = Number(price);
  if (isNaN(n)) return price;
  if (n >= 1000) return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
  if (n >= 1) return n.toFixed(4);
  return n.toFixed(6);
}

export function CoinVolumeList({
  exchange,
  selectedCoins,
  onChange,
  maxSelection,
}: CoinVolumeListProps) {
  const [tickers, setTickers] = useState<TickerItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');

  const loadTickers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getMarketTickers(exchange, 200);
      setTickers(data.map((d: Record<string, string>) => ({
        symbol: d.symbol,
        last: d.last_price ?? d.last ?? '',
        volume: d.quote_volume ?? d.volume ?? '',
        quote_volume: d.quote_volume ?? null,
      })));
    } catch {
      setError(`Failed to load tickers from ${exchange}`);
      setTickers([]);
    } finally {
      setLoading(false);
    }
  }, [exchange]);

  useEffect(() => {
    loadTickers();
  }, [loadTickers]);

  const filtered = tickers.filter((t) =>
    t.symbol.toLowerCase().includes(search.toLowerCase())
  );

  const atLimit = selectedCoins.length >= maxSelection;

  function toggleCoin(symbol: string) {
    if (selectedCoins.includes(symbol)) {
      onChange(selectedCoins.filter((s) => s !== symbol));
    } else {
      if (atLimit) return;
      onChange([...selectedCoins, symbol]);
    }
  }

  function selectTopN(n: number) {
    const limit = Math.min(n, maxSelection);
    onChange(tickers.slice(0, limit).map((t) => t.symbol));
  }

  function clearAll() {
    onChange([]);
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium">
          <Coins className="h-4 w-4 text-violet-500" />
          Coin Selection
        </div>
        <div className="text-xs text-muted-foreground">
          <span className={cn('font-medium', atLimit && 'text-amber-500')}>
            {selectedCoins.length}
          </span>
          {' / '}
          {maxSelection >= 999 ? 'Unlimited' : maxSelection} coins
        </div>
      </div>

      {maxSelection < 999 && (
        <div className="flex items-center gap-2 rounded-xl bg-violet-500/5 p-3 text-sm">
          <Lock className="h-4 w-4 text-violet-500" />
          <span className="text-muted-foreground">
            Your plan allows selecting up to{' '}
            <span className="font-medium text-violet-500">{maxSelection}</span> coins.
          </span>
        </div>
      )}

      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative flex-1 sm:max-w-xs">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search coin..."
            className="w-full rounded-lg border border-border bg-background py-2 pl-9 pr-3 text-sm focus:border-violet-500 focus:outline-none"
          />
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => selectTopN(Math.min(5, maxSelection))}
            disabled={loading}
            className="rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-medium transition hover:bg-accent disabled:opacity-50"
          >
            Top 5
          </button>
          <button
            onClick={() => selectTopN(Math.min(10, maxSelection))}
            disabled={loading}
            className="rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-medium transition hover:bg-accent disabled:opacity-50"
          >
            Top 10
          </button>
          <button
            onClick={() => selectTopN(Math.min(20, maxSelection))}
            disabled={loading}
            className="rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-medium transition hover:bg-accent disabled:opacity-50"
          >
            Top 20
          </button>
          {selectedCoins.length > 0 && (
            <button
              onClick={clearAll}
              className="rounded-lg border border-border bg-card px-3 py-1.5 text-xs font-medium text-muted-foreground transition hover:bg-accent hover:text-foreground"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-8">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-violet-500 border-t-transparent" />
        </div>
      ) : error ? (
        <div className="rounded-xl bg-amber-500/10 p-4 text-sm text-amber-600 dark:text-amber-400">
          {error}
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-xl bg-muted/50 p-4 text-sm text-muted-foreground">
          No coins found.
        </div>
      ) : (
        <div className="max-h-80 space-y-1 overflow-y-auto rounded-xl border border-border p-2">
          {filtered.map((ticker, idx) => {
            const isSelected = selectedCoins.includes(ticker.symbol);
            const disabled = !isSelected && atLimit;
            return (
              <button
                key={ticker.symbol}
                onClick={() => toggleCoin(ticker.symbol)}
                disabled={disabled}
                className={cn(
                  'flex w-full items-center justify-between rounded-lg px-3 py-2 text-left transition',
                  isSelected
                    ? 'bg-violet-500/10 border border-violet-500/30'
                    : 'hover:bg-accent border border-transparent',
                  disabled && 'cursor-not-allowed opacity-40',
                )}
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-6 w-6 items-center justify-center rounded-full bg-muted text-[10px] font-bold text-muted-foreground">
                    {idx + 1}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold">{ticker.symbol}</span>
                      {isSelected && (
                        <Check className="h-3.5 w-3.5 text-violet-500" />
                      )}
                    </div>
                    <span className="text-xs text-muted-foreground">
                      ${formatPrice(ticker.last)}
                    </span>
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-xs font-medium text-muted-foreground">
                    Vol: {formatVolume(ticker.volume)}
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      )}

      {selectedCoins.length > 0 && (
        <div className="rounded-xl border border-border bg-card p-3">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground">
              Selected ({selectedCoins.length})
            </span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {selectedCoins.map((coin) => (
              <span
                key={coin}
                className="inline-flex items-center gap-1 rounded-full bg-violet-500/10 px-2.5 py-1 text-xs font-medium text-violet-600 dark:text-violet-400"
              >
                {coin}
                <button
                  onClick={() => toggleCoin(coin)}
                  className="ml-0.5 text-violet-400 hover:text-violet-600"
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
