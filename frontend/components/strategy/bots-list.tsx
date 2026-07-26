'use client';

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Bot, Pause, Play, Square, CheckCircle2, AlertCircle } from 'lucide-react';
import { api } from '@/services/api';

interface TradingInstance {
  id: string;
  status: string;
  symbol: string;
  total_investment: number;
  start_price: number | null;
  current_price: number | null;
  started_at: string | null;
  stopped_at: string | null;
  error_message: string | null;
}

const STATUS_COLORS: Record<string, 'success' | 'warning' | 'secondary' | 'destructive'> = {
  created: 'secondary',
  ready: 'warning',
  running: 'success',
  paused: 'warning',
  stopped: 'destructive',
  error: 'destructive',
};

interface BotsListProps {
  refreshKey?: number;
}

export function BotsList({ refreshKey }: BotsListProps) {
  const [instances, setInstances] = useState<TradingInstance[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Trailing profit state (kept from original TradingBots)
  const [trailingEnabled, setTrailingEnabled] = useState(false);
  const [triggerPct, setTriggerPct] = useState(2.0);
  const [trailPct, setTrailPct] = useState(1.5);
  const [maxProfitPct, setMaxProfitPct] = useState(0);
  const [trailingConfigured, setTrailingConfigured] = useState<Record<string, boolean>>({});
  const [trailingAccess, setTrailingAccess] = useState<{ has_access: boolean; via_tier: boolean; via_addon: boolean } | null>(null);
  const [purchasing, setPurchasing] = useState(false);

  const loadAll = useCallback(async () => {
    try {
      const [insts, addonCheck] = await Promise.all([
        api.listTradingInstances().catch(() => [] as TradingInstance[]),
        api.checkAddonAccess('trailing_profit').catch(() => null),
      ]);
      setInstances(insts || []);
      if (addonCheck) setTrailingAccess(addonCheck);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    loadAll();
    const interval = setInterval(loadAll, 5000);
    return () => clearInterval(interval);
  }, [loadAll, refreshKey]);

  async function handleAction(instanceId: string, action: 'prepare' | 'start' | 'pause' | 'resume' | 'stop') {
    setBusy(instanceId);
    setMsg(null);
    try {
      const fn = {
        prepare: api.prepareTradingInstance.bind(api),
        start: api.startTradingInstance.bind(api),
        pause: api.pauseTradingInstance.bind(api),
        resume: api.resumeTradingInstance.bind(api),
        stop: api.stopTradingInstance.bind(api),
      }[action];
      const res = await fn(instanceId);
      setMsg({ type: 'success', text: `Bot ${action}: status now ${res.status}` });
      await loadAll();
    } catch (err) {
      setMsg({ type: 'error', text: err instanceof Error ? err.message : `Failed to ${action}` });
    } finally {
      setBusy(null);
    }
  }

  async function handleConfigureTrailing(instanceId: string) {
    setBusy(instanceId);
    setMsg(null);
    try {
      await api.configureTrailingProfit(instanceId, triggerPct, trailPct, maxProfitPct);
      setTrailingConfigured((prev) => ({ ...prev, [instanceId]: true }));
      setMsg({ type: 'success', text: `Trailing profit configured: trigger ${triggerPct}%, trail ${trailPct}%` });
    } catch (err) {
      setMsg({ type: 'error', text: err instanceof Error ? err.message : 'Failed to configure trailing profit' });
    } finally {
      setBusy(null);
    }
  }

  async function handlePurchaseTrailing() {
    setPurchasing(true);
    setMsg(null);
    try {
      await api.purchaseAddon('trailing_profit', 30);
      setMsg({ type: 'success', text: 'Trailing Profit add-on purchased successfully!' });
      await loadAll();
    } catch (err) {
      setMsg({ type: 'error', text: err instanceof Error ? err.message : 'Failed to purchase add-on' });
    } finally {
      setPurchasing(false);
    }
  }

  const activeCount = instances.filter((i) => i.status === 'running').length;

  return (
    <div className="space-y-6">
      {msg && (
        <div className={`rounded-md p-3 text-sm ${msg.type === 'success' ? 'bg-green-500/10 text-green-600' : 'bg-red-500/10 text-red-600'}`}>
          {msg.text}
        </div>
      )}

      <div className="rounded-xl border border-violet-500/20 bg-violet-500/10 px-4 py-2.5 text-sm text-violet-600 dark:text-violet-400">
        {activeCount} active · {instances.length} total bot{instances.length !== 1 ? 's' : ''}
      </div>

      {/* Trailing Profit config (global) */}
      <Card glass>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-violet-500" />
            Trailing Profit
          </CardTitle>
          <CardDescription>
            {trailingAccess?.has_access
              ? 'Active — enable per bot below'
              : 'Add-on ($19/mo) or Starter+ plan required'}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {trailingAccess && !trailingAccess.has_access && (
            <div className="rounded-md bg-amber-500/10 p-3 border border-amber-500/20 flex items-center justify-between gap-3">
              <p className="text-sm text-amber-700 dark:text-amber-400">
                Get trailing profit for $19/month as an add-on, or upgrade to Starter+.
              </p>
              <Button onClick={handlePurchaseTrailing} disabled={purchasing} size="sm">
                {purchasing ? 'Processing...' : 'Buy $19/mo'}
              </Button>
            </div>
          )}
          {trailingAccess?.has_access && (
            <>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={trailingEnabled}
                  onChange={(e) => setTrailingEnabled(e.target.checked)}
                />
                <span className="text-sm font-medium">Enable trailing profit on bots</span>
              </label>
              {trailingEnabled && (
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                  <div>
                    <label className="text-sm font-medium">Trigger Profit (%)</label>
                    <Input type="number" step="0.1" value={triggerPct} onChange={(e) => setTriggerPct(Number(e.target.value))} />
                    <p className="text-xs text-muted-foreground mt-1">Start trailing when profit reaches this %</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium">Trail Distance (%)</label>
                    <Input type="number" step="0.1" value={trailPct} onChange={(e) => setTrailPct(Number(e.target.value))} />
                    <p className="text-xs text-muted-foreground mt-1">Sell if price drops this % below highest</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium">Max Profit Cap (%)</label>
                    <Input type="number" step="1" value={maxProfitPct} onChange={(e) => setMaxProfitPct(Number(e.target.value))} />
                    <p className="text-xs text-muted-foreground mt-1">0 = ride trend forever</p>
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Bots list */}
      <Card glass>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bot className="h-5 w-5 text-violet-500" />
            Trading Bots
          </CardTitle>
          <CardDescription>Lifecycle control for your bots</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {instances.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Bot className="mb-2 h-8 w-8 text-muted-foreground/50" />
              <p className="text-sm text-muted-foreground">
                No trading bots yet. Create one from the Setup tab.
              </p>
            </div>
          ) : (
            instances.map((inst) => (
              <div key={inst.id} className="rounded-md border p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="font-medium">{inst.symbol}</span>
                    <Badge variant={STATUS_COLORS[inst.status] || 'secondary'}>
                      {inst.status}
                    </Badge>
                    <span className="text-sm text-muted-foreground">
                      ${inst.total_investment}
                    </span>
                  </div>
                  <span className="text-xs text-muted-foreground font-mono hidden sm:inline">
                    {inst.id.slice(0, 8)}
                  </span>
                </div>

                <div className="text-sm text-muted-foreground">
                  {inst.current_price && (
                    <>Current: ${inst.current_price} </>
                  )}
                  {inst.start_price && (
                    <>| Start: ${inst.start_price}</>
                  )}
                  {inst.started_at && (
                    <> | Since: {new Date(inst.started_at).toLocaleDateString()}</>
                  )}
                </div>

                {inst.error_message && (
                  <div className="flex items-start gap-2 rounded-md bg-red-500/10 p-2 text-sm text-red-600">
                    <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
                    <span>{inst.error_message}</span>
                  </div>
                )}

                <div className="flex gap-2 flex-wrap">
                  {inst.status === 'created' && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleAction(inst.id, 'prepare')}
                      disabled={busy === inst.id}
                    >
                      Prepare
                    </Button>
                  )}
                  {inst.status === 'ready' && (
                    <Button
                      size="sm"
                      onClick={() => handleAction(inst.id, 'start')}
                      disabled={busy === inst.id}
                    >
                      <Play className="h-4 w-4" /> Start Bot
                    </Button>
                  )}
                  {inst.status === 'running' && (
                    <>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleAction(inst.id, 'pause')}
                        disabled={busy === inst.id}
                      >
                        <Pause className="h-4 w-4" /> Pause
                      </Button>
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => handleAction(inst.id, 'stop')}
                        disabled={busy === inst.id}
                      >
                        <Square className="h-4 w-4" /> Stop
                      </Button>
                    </>
                  )}
                  {inst.status === 'paused' && (
                    <>
                      <Button
                        size="sm"
                        onClick={() => handleAction(inst.id, 'resume')}
                        disabled={busy === inst.id}
                      >
                        <Play className="h-4 w-4" /> Resume
                      </Button>
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => handleAction(inst.id, 'stop')}
                        disabled={busy === inst.id}
                      >
                        <Square className="h-4 w-4" /> Stop
                      </Button>
                    </>
                  )}
                  {inst.status === 'stopped' && (
                    <Badge variant="secondary">Stopped — create a new bot to restart</Badge>
                  )}
                  {inst.status === 'error' && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleAction(inst.id, 'prepare')}
                      disabled={busy === inst.id}
                    >
                      Retry Prepare
                    </Button>
                  )}

                  {trailingEnabled && trailingAccess?.has_access && !trailingConfigured[inst.id] && inst.status === 'running' && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleConfigureTrailing(inst.id)}
                      disabled={busy === inst.id}
                    >
                      Enable Trailing
                    </Button>
                  )}
                  {trailingConfigured[inst.id] && (
                    <Badge variant="success">Trailing Active</Badge>
                  )}
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>

      {/* State machine legend */}
      <div className="rounded-lg bg-muted/40 p-3 text-xs text-muted-foreground">
        <strong className="text-foreground">Bot lifecycle:</strong>{' '}
        created → ready → running ⇄ paused → stopped
        <br />
        <span className="mt-1 inline-block">
          <Badge variant="secondary">created</Badge> must be <strong>Prepared</strong> first, then <strong>Started</strong>.
        </span>
      </div>
    </div>
  );
}
