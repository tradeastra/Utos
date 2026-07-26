'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Zap, TrendingUp, TrendingDown, AlertTriangle } from 'lucide-react';
import { api } from '@/services/api';
import type { ForceBuyResult, ForceSellResult } from '@/types';

interface TradingInstance {
  id: string;
  status: string;
  symbol: string;
  total_investment: number;
  current_price: number | null;
}

export function ManualActions() {
  const [instances, setInstances] = useState<TradingInstance[]>([]);
  const [selectedInstanceId, setSelectedInstanceId] = useState<string>('');
  const [level, setLevel] = useState<string>('');
  const [price, setPrice] = useState<string>('');
  const [qty, setQty] = useState<string>('');
  const [result, setResult] = useState<ForceBuyResult | ForceSellResult | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let mounted = true;
    async function load() {
      try {
        const insts = await api.listTradingInstances();
        if (mounted) setInstances(insts || []);
      } catch {
        if (mounted) setInstances([]);
      }
    }
    load();
    const interval = setInterval(load, 5000);
    return () => { mounted = false; clearInterval(interval); };
  }, []);

  const selected = instances.find((i) => i.id === selectedInstanceId);
  // Only running bots can be force-buy/sold meaningfully
  const actionableInstances = instances;

  async function handleForceBuy() {
    if (!selectedInstanceId) return;
    setLoading(true);
    setResult(null);
    try {
      const r = await api.forceBuy(selectedInstanceId, {
        level: level ? Number(level) : undefined,
        price: price ? Number(price) : undefined,
        quantity: qty ? Number(qty) : undefined,
      });
      setResult(r as ForceBuyResult);
    } catch (err) {
      setResult({ message: err instanceof Error ? err.message : 'Force buy failed' } as ForceBuyResult);
    } finally {
      setLoading(false);
    }
  }

  async function handleForceSell() {
    if (!selectedInstanceId) return;
    setLoading(true);
    setResult(null);
    try {
      const r = await api.forceSell(selectedInstanceId, {
        level: level ? Number(level) : undefined,
        price: price ? Number(price) : undefined,
        quantity: qty ? Number(qty) : undefined,
      });
      setResult(r as ForceSellResult);
    } catch (err) {
      setResult({ message: err instanceof Error ? err.message : 'Force sell failed' } as ForceSellResult);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <Card glass>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Zap className="h-5 w-5 text-amber-500" />
            Force Buy / Force Sell
          </CardTitle>
          <CardDescription>
            Manually override the bot — bypass market signals to enter or exit a position
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Info banner */}
          <div className="rounded-xl bg-blue-500/10 p-3 text-xs text-blue-600 dark:text-blue-400">
            <strong>Force Buy</strong> — Manually initiate a buy at a specific level, bypassing market signals.
            After the buy fills, averaging continues automatically for subsequent levels.
            <br />
            <strong>Force Sell</strong> — Close an existing position (spot market: can only sell coins you hold).
            Sells all filled positions if no level is specified.
          </div>

          {/* Instance dropdown — replaces manual UUID input */}
          <div>
            <label className="mb-1 block text-sm font-medium">Trading Bot</label>
            {actionableInstances.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No trading bots available. Create one from the Setup tab first.
              </p>
            ) : (
              <select
                value={selectedInstanceId}
                onChange={(e) => {
                  setSelectedInstanceId(e.target.value);
                  setResult(null);
                }}
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:border-amber-500 focus:outline-none"
              >
                <option value="">— Select a bot —</option>
                {actionableInstances.map((inst) => (
                  <option key={inst.id} value={inst.id}>
                    {inst.symbol} · {inst.status} · ${inst.total_investment}
                    {inst.current_price ? ` · @ $${inst.current_price}` : ''}
                  </option>
                ))}
              </select>
            )}
            {selected && (
              <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                <Badge variant={selected.status === 'running' ? 'success' : 'secondary'}>
                  {selected.status}
                </Badge>
                <span>Symbol: <strong>{selected.symbol}</strong></span>
                <span>Investment: <strong>${selected.total_investment}</strong></span>
                {selected.current_price && (
                  <span>Current: <strong>${selected.current_price}</strong></span>
                )}
                <span className="font-mono">ID: {selected.id.slice(0, 8)}…</span>
              </div>
            )}
          </div>

          {/* Optional parameters */}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div>
              <label className="mb-1 block text-xs text-muted-foreground">Level (optional)</label>
              <Input
                type="number"
                value={level}
                onChange={(e) => setLevel(e.target.value)}
                placeholder="Auto"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-muted-foreground">Price (optional)</label>
              <Input
                type="number"
                step="0.01"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                placeholder="Market"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-muted-foreground">Qty (optional)</label>
              <Input
                type="number"
                step="0.001"
                value={qty}
                onChange={(e) => setQty(e.target.value)}
                placeholder="Default"
              />
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex gap-2">
            <Button
              onClick={handleForceBuy}
              disabled={!selectedInstanceId || loading}
              className="flex-1 bg-green-600 hover:bg-green-700"
            >
              <TrendingUp className="h-4 w-4" />
              {loading ? 'Processing...' : 'Force Buy'}
            </Button>
            <Button
              onClick={handleForceSell}
              disabled={!selectedInstanceId || loading}
              className="flex-1 bg-red-600 hover:bg-red-700"
            >
              <TrendingDown className="h-4 w-4" />
              {loading ? 'Processing...' : 'Force Sell'}
            </Button>
          </div>

          {/* Warning for non-running bots */}
          {selected && selected.status !== 'running' && (
            <div className="flex items-start gap-2 rounded-md bg-amber-500/10 p-3 text-xs text-amber-700 dark:text-amber-400">
              <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
              <span>
                This bot is <strong>{selected.status}</strong>, not running. Force actions may fail
                or have no effect. Consider starting the bot first from the Bots tab.
              </span>
            </div>
          )}

          {/* Result */}
          {loading && (
            <div className="flex items-center justify-center py-4">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-amber-500 border-t-transparent" />
            </div>
          )}

          {result && !loading && (
            <div className="rounded-lg bg-amber-500/5 p-4 text-sm">
              {'order_id' in result && (
                <>
                  <p className="font-semibold text-green-600">Buy executed</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Order: <span className="font-mono">{result.order_id}</span>
                    {' · '}Level {result.level} @ ${result.price} × {result.quantity}
                  </p>
                  {result.message && <p className="mt-1 text-xs">{result.message}</p>}
                </>
              )}
              {'order_ids' in result && (
                <>
                  <p className="font-semibold text-red-600">Sell executed</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {result.order_ids.length} order(s) · Levels: {result.levels_sold.join(', ')}
                    {' · '}Total: {result.total_quantity} @ ${result.price} = ${result.total_value}
                  </p>
                  {result.message && <p className="mt-1 text-xs">{result.message}</p>}
                </>
              )}
              {'message' in result && !('order_id' in result) && !('order_ids' in result) && (
                <p className="text-red-600">{(result as { message: string }).message}</p>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <div className="rounded-lg bg-muted/40 p-3 text-xs text-muted-foreground">
        <strong className="text-foreground">When to use:</strong> Use Force Buy when you want to
        enter a position immediately without waiting for the bot&apos;s grid signal. Use Force Sell
        to exit a position early (e.g. take profit manually, cut loss, or close all levels).
      </div>
    </div>
  );
}
