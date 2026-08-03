'use client';

import { useCallback, useEffect, useState } from 'react';
import { api } from '@/services/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';

interface ExchangeAccount {
  id: string;
  exchange_name: string;
  is_testnet: boolean;
  is_active: boolean;
  connection_status: string;
}

interface Strategy {
  id: string;
  name: string;
  type: string;
  description: string | null;
  min_investment: number;
  max_investment: number | null;
}

interface GridProfile {
  id: string;
  name: string;
  upper_price: number;
  lower_price: number;
  grid_count: number;
  grid_spacing: number | null;
  investment_per_grid: number;
}

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

export function TradingBots() {
  const [accounts, setAccounts] = useState<ExchangeAccount[]>([]);
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [profiles, setProfiles] = useState<GridProfile[]>([]);
  const [instances, setInstances] = useState<TradingInstance[]>([]);

  const [selectedAccount, setSelectedAccount] = useState('');
  const [selectedStrategy, setSelectedStrategy] = useState('');
  const [selectedProfile, setSelectedProfile] = useState('');
  const [symbol, setSymbol] = useState('BTCUSDT');

  const [showProfileForm, setShowProfileForm] = useState(false);
  const [profileName, setProfileName] = useState('');
  const [upperPrice, setUpperPrice] = useState(50000);
  const [lowerPrice, setLowerPrice] = useState(40000);
  const [gridCount, setGridCount] = useState(10);
  const [investmentPerGrid, setInvestmentPerGrid] = useState(10);

  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const [trailingEnabled, setTrailingEnabled] = useState(false);
  const [triggerPct, setTriggerPct] = useState(2.0);
  const [trailPct, setTrailPct] = useState(1.5);
  const [maxProfitPct, setMaxProfitPct] = useState(0);
  const [trailingConfigured, setTrailingConfigured] = useState<Record<string, boolean>>({});

  const [trailingAccess, setTrailingAccess] = useState<{ has_access: boolean; via_tier: boolean; via_addon: boolean } | null>(null);
  const [purchasing, setPurchasing] = useState(false);

  const loadAll = useCallback(async () => {
    try {
      const [accs, strat, profs, insts, addonCheck] = await Promise.all([
        api.listExchangeAccounts().catch(() => []),
        api.listStrategies().catch(() => []),
        api.listGridProfiles().catch(() => []),
        api.listTradingInstances().catch(() => []),
        api.checkAddonAccess('trailing_profit').catch(() => null),
      ]);
      setAccounts(accs || []);
      setStrategies(strat || []);
      setProfiles(profs || []);
      setInstances(insts || []);
      if (addonCheck) setTrailingAccess(addonCheck);

      // Auto-pick the first active strategy (strategy selector is hidden
      // from the UI — all strategies run the same averaging engine, so the
      // choice is cosmetic. strategy_id is still required by the backend
      // as a foreign key, so we send the first available one.)
      if (strat && strat.length > 0) {
        setSelectedStrategy((prev) => prev || strat[0].id);
      }
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    loadAll();
    const interval = setInterval(loadAll, 5000);
    return () => clearInterval(interval);
  }, [loadAll]);

  async function handleCreateProfile() {
    setBusy(true);
    setMsg(null);
    try {
      await api.createGridProfile({
        name: profileName || `Grid ${upperPrice}-${lowerPrice}`,
        upper_price: upperPrice,
        lower_price: lowerPrice,
        grid_count: gridCount,
        investment_per_grid: investmentPerGrid,
      });
      setMsg({ type: 'success', text: 'Grid profile created!' });
      setShowProfileForm(false);
      await loadAll();
    } catch (err) {
      setMsg({ type: 'error', text: err instanceof Error ? err.message : 'Failed' });
    } finally {
      setBusy(false);
    }
  }

  async function handleCreateInstance() {
    setBusy(true);
    setMsg(null);
    try {
      const instance = await api.createTradingInstance({
        exchange_account_id: selectedAccount,
        strategy_id: selectedStrategy,
        grid_profile_id: selectedProfile,
        symbol: symbol.toUpperCase(),
      });
      setMsg({ type: 'success', text: `Trading bot created (status: ${instance.status})` });
      await loadAll();
    } catch (err) {
      setMsg({ type: 'error', text: err instanceof Error ? err.message : 'Failed' });
    } finally {
      setBusy(false);
    }
  }

  async function handleConfigureTrailing(instanceId: string) {
    setBusy(true);
    setMsg(null);
    try {
      await api.configureTrailingProfit(instanceId, triggerPct, trailPct, maxProfitPct);
      setTrailingConfigured((prev) => ({ ...prev, [instanceId]: true }));
      setMsg({ type: 'success', text: `Trailing profit configured: trigger ${triggerPct}%, trail ${trailPct}%, max ${maxProfitPct > 0 ? maxProfitPct + '%' : 'no cap'}` });
    } catch (err) {
      setMsg({ type: 'error', text: err instanceof Error ? err.message : 'Failed to configure trailing profit' });
    } finally {
      setBusy(false);
    }
  }

  async function handlePurchaseTrailing() {
    setPurchasing(true);
    setMsg(null);
    try {
      await api.purchaseAddon('trailing_profit', 30);
      setMsg({ type: 'success', text: 'Trailing Profit add-on purchased successfully! You can now enable it on your bots.' });
      await loadAll();
    } catch (err) {
      setMsg({ type: 'error', text: err instanceof Error ? err.message : 'Failed to purchase add-on' });
    } finally {
      setPurchasing(false);
    }
  }

  async function handleAction(instanceId: string, action: 'prepare' | 'start' | 'pause' | 'resume' | 'stop') {
    setBusy(true);
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
      setBusy(false);
    }
  }

  async function handleDelete(instanceId: string, symbol: string) {
    if (!confirm(`Delete bot for ${symbol}? This cannot be undone.`)) return;
    setBusy(true);
    setMsg(null);
    try {
      await api.deleteTradingInstance(instanceId);
      setMsg({ type: 'success', text: `Bot for ${symbol} deleted` });
      await loadAll();
    } catch (err) {
      setMsg({ type: 'error', text: err instanceof Error ? err.message : 'Failed to delete bot' });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      {msg && (
        <div className={`rounded-md p-3 text-sm ${msg.type === 'success' ? 'bg-green-500/10 text-green-600' : 'bg-red-500/10 text-red-600'}`}>
          {msg.text}
        </div>
      )}

      {/* Step 1: Exchange Account */}
      <Card>
        <CardHeader>
          <CardTitle>1. Select Exchange Account</CardTitle>
          <CardDescription>Choose your saved exchange account</CardDescription>
        </CardHeader>
        <CardContent>
          {accounts.length === 0 ? (
            <p className="text-sm text-muted-foreground">No exchange accounts found. Add one in Settings → Exchanges first.</p>
          ) : (
            <div className="space-y-2">
              {accounts.map((acc) => (
                <label key={acc.id} className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="radio"
                    name="account"
                    value={acc.id}
                    checked={selectedAccount === acc.id}
                    onChange={(e) => setSelectedAccount(e.target.value)}
                  />
                  <span className="font-medium capitalize">{acc.exchange_name}</span>
                  {acc.is_testnet && <Badge variant="warning">testnet</Badge>}
                  <Badge variant={acc.is_active ? 'success' : 'secondary'}>{acc.connection_status}</Badge>
                </label>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Step 2: Strategy — auto-selected (all strategies run the same engine) */}
      <Card>
        <CardHeader>
          <CardTitle>2. Strategy</CardTitle>
          <CardDescription>Auto-selected</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            {strategies.length === 0
              ? 'Loading…'
              : 'Strategy configured automatically.'}
          </p>
        </CardContent>
      </Card>

      {/* Step 3: Grid Profile */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>3. Grid Profile</CardTitle>
              <CardDescription>Configure grid trading parameters</CardDescription>
            </div>
            <Button variant="outline" size="sm" onClick={() => setShowProfileForm(!showProfileForm)}>
              {showProfileForm ? 'Cancel' : 'New Profile'}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {showProfileForm && (
            <div className="rounded-md border p-4 space-y-3">
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <div>
                  <label className="text-sm font-medium">Profile Name</label>
                  <Input value={profileName} onChange={(e) => setProfileName(e.target.value)} placeholder="My Grid" />
                </div>
                <div>
                  <label className="text-sm font-medium">Symbol</label>
                  <Input value={symbol} onChange={(e) => setSymbol(e.target.value)} placeholder="BTCUSDT" />
                </div>
                <div>
                  <label className="text-sm font-medium">Upper Price</label>
                  <Input type="number" value={upperPrice} onChange={(e) => setUpperPrice(Number(e.target.value))} />
                </div>
                <div>
                  <label className="text-sm font-medium">Lower Price</label>
                  <Input type="number" value={lowerPrice} onChange={(e) => setLowerPrice(Number(e.target.value))} />
                </div>
                <div>
                  <label className="text-sm font-medium">Grid Count</label>
                  <Input type="number" value={gridCount} onChange={(e) => setGridCount(Number(e.target.value))} />
                </div>
                <div>
                  <label className="text-sm font-medium">Investment Per Grid (USDT)</label>
                  <Input type="number" value={investmentPerGrid} onChange={(e) => setInvestmentPerGrid(Number(e.target.value))} />
                </div>
              </div>
              <Button onClick={handleCreateProfile} disabled={busy} size="sm">Create Profile</Button>
            </div>
          )}

          {profiles.length === 0 && !showProfileForm ? (
            <p className="text-sm text-muted-foreground">No grid profiles yet. Click &ldquo;New Profile&rdquo; to create one.</p>
          ) : (
            <div className="space-y-2">
              {profiles.map((p) => (
                <label key={p.id} className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="radio"
                    name="profile"
                    value={p.id}
                    checked={selectedProfile === p.id}
                    onChange={(e) => setSelectedProfile(e.target.value)}
                  />
                  <div className="flex-1">
                    <span className="font-medium">{p.name}</span>
                    <span className="text-sm text-muted-foreground ml-2">
                      {p.lower_price} - {p.upper_price} | {p.grid_count} grids | {p.investment_per_grid}/grid
                    </span>
                  </div>
                </label>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Step 4: Launch */}
      <Card>
        <CardHeader>
          <CardTitle>4. Launch Trading Bot</CardTitle>
          <CardDescription>Create and start your auto trading bot</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label className="text-sm font-medium">Symbol</label>
              <Input value={symbol} onChange={(e) => setSymbol(e.target.value)} placeholder="BTCUSDT" />
            </div>
            <div>
              <label className="text-sm font-medium">Grid Layers / Steps</label>
              <Input
                type="number"
                value={selectedProfile ? (profiles.find(p => p.id === selectedProfile)?.grid_count ?? 0) : 0}
                disabled
              />
              <p className="text-xs text-muted-foreground mt-1">
                {selectedProfile
                  ? `${profiles.find(p => p.id === selectedProfile)?.grid_count ?? 0} layers × ${profiles.find(p => p.id === selectedProfile)?.investment_per_grid ?? 0} USDT/layer = ${((profiles.find(p => p.id === selectedProfile)?.grid_count ?? 0) * (profiles.find(p => p.id === selectedProfile)?.investment_per_grid ?? 0)).toFixed(2)} USDT total`
                  : 'Select a grid profile first'}
              </p>
            </div>
          </div>
          <Button
            onClick={handleCreateInstance}
            disabled={busy || !selectedAccount || !selectedStrategy || !selectedProfile}
          >
            {busy ? 'Creating...' : 'Create Trading Bot'}
          </Button>
        </CardContent>
      </Card>

      {/* Trailing Profit */}
      <Card>
        <CardHeader>
          <CardTitle>5. Trailing Profit (Add-on)</CardTitle>
          <CardDescription>Lock in profit automatically as price rises — available as add-on or with Starter+ plan</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className={`rounded-lg border p-4 ${(!trailingAccess || !trailingAccess.has_access) ? 'border-primary' : 'border-muted'}`}>
              <div className="flex items-center justify-between mb-2">
                <h4 className="font-semibold">Basic Grid</h4>
                {!trailingAccess?.has_access && <Badge>Current</Badge>}
              </div>
              <p className="text-2xl font-bold">$0</p>
              <p className="text-xs text-muted-foreground mt-1">Included in Free plan</p>
              <ul className="mt-3 space-y-1 text-sm text-muted-foreground">
                <li>- Fixed grid buy/sell levels</li>
                <li>- Manual take profit per grid</li>
                <li>- No trailing profit</li>
              </ul>
            </div>
            <div className={`rounded-lg border p-4 ${(trailingAccess?.has_access) ? 'border-primary' : 'border-muted'}`}>
              <div className="flex items-center justify-between mb-2">
                <h4 className="font-semibold">Grid + Trailing Profit</h4>
                {trailingAccess?.has_access && <Badge variant="success">Active</Badge>}
              </div>
              <p className="text-2xl font-bold">$19<span className="text-sm font-normal text-muted-foreground">/mo</span></p>
              <p className="text-xs text-muted-foreground mt-1">
                {trailingAccess?.via_tier ? 'Included in your plan' : 'Add-on purchase'}
              </p>
              <ul className="mt-3 space-y-1 text-sm text-muted-foreground">
                <li>- Everything in Basic Grid</li>
                <li>- Auto trailing profit on buy fill</li>
                <li>- Configurable trigger &amp; trail %</li>
                <li>- Max profit cap for uptrend safety</li>
              </ul>
            </div>
          </div>

          {trailingAccess && !trailingAccess.has_access && (
            <div className="rounded-md bg-amber-500/10 p-4 border border-amber-500/20">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-amber-700">Trailing Profit not activated</p>
                  <p className="text-sm text-amber-600 mt-1">
                    Get trailing profit for $19/month as an add-on, or upgrade to Starter+ plan.
                  </p>
                </div>
                <Button onClick={handlePurchaseTrailing} disabled={purchasing}>
                  {purchasing ? 'Processing...' : 'Buy Add-on $19/mo'}
                </Button>
              </div>
            </div>
          )}

          {trailingAccess?.has_access && (
            <div className="space-y-3">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={trailingEnabled}
                  onChange={(e) => setTrailingEnabled(e.target.checked)}
                />
                <span className="text-sm font-medium">Enable trailing profit on new bots</span>
              </label>
              {trailingEnabled && (
                <>
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                    <div>
                      <label className="text-sm font-medium">Trigger Profit (%)</label>
                      <Input type="number" step="0.1" value={triggerPct} onChange={(e) => setTriggerPct(Number(e.target.value))} placeholder="2.0" />
                      <p className="text-xs text-muted-foreground mt-1">Start trailing when profit reaches this %</p>
                    </div>
                    <div>
                      <label className="text-sm font-medium">Trail Distance (%)</label>
                      <Input type="number" step="0.1" value={trailPct} onChange={(e) => setTrailPct(Number(e.target.value))} placeholder="1.5" />
                      <p className="text-xs text-muted-foreground mt-1">Sell if price drops this % below highest</p>
                    </div>
                    <div>
                      <label className="text-sm font-medium">Max Profit Cap (%)</label>
                      <Input type="number" step="1" value={maxProfitPct} onChange={(e) => setMaxProfitPct(Number(e.target.value))} placeholder="0" />
                      <p className="text-xs text-muted-foreground mt-1">Auto-sell at this profit. 0 = ride trend forever</p>
                    </div>
                  </div>
                  <div className="rounded-md bg-blue-500/10 p-3 text-sm text-blue-600">
                    <strong>How it works:</strong> When a buy order fills, profit lock starts monitoring.
                    Once profit hits {triggerPct}%, a trailing lock is set at {trailPct}% below the highest price.
                    If price keeps rising, the lock trails upward. When price drops below the lock, a sell order is placed automatically.
                    {maxProfitPct > 0 && ` If profit reaches ${maxProfitPct}%, it auto-sells immediately regardless of trailing.`}
                  </div>
                </>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Active Bots */}
      <Card>
        <CardHeader>
          <CardTitle>Trading Bots</CardTitle>
          <CardDescription>Your active and historical trading instances</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {instances.length === 0 ? (
            <p className="text-sm text-muted-foreground">No trading bots yet.</p>
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
                      Investment: ${inst.total_investment}
                    </span>
                  </div>
                </div>

                {inst.current_price && (
                  <div className="text-sm text-muted-foreground">
                    Current Price: ${inst.current_price}
                    {inst.start_price && ` | Start: $${inst.start_price}`}
                  </div>
                )}

                {inst.error_message && (
                  <div className="text-sm text-red-600">Error: {inst.error_message}</div>
                )}

                <div className="flex gap-2 flex-wrap">
                  {inst.status === 'created' && (
                    <Button size="sm" variant="outline" onClick={() => handleAction(inst.id, 'prepare')} disabled={busy}>
                      Prepare
                    </Button>
                  )}
                  {inst.status === 'ready' && (
                    <Button size="sm" onClick={() => handleAction(inst.id, 'start')} disabled={busy}>
                      Start Bot
                    </Button>
                  )}
                  {inst.status === 'running' && (
                    <>
                      <Button size="sm" variant="outline" onClick={() => handleAction(inst.id, 'pause')} disabled={busy}>
                        Pause
                      </Button>
                      <Button size="sm" variant="destructive" onClick={() => handleAction(inst.id, 'stop')} disabled={busy}>
                        Stop
                      </Button>
                    </>
                  )}
                  {inst.status === 'paused' && (
                    <>
                      <Button size="sm" onClick={() => handleAction(inst.id, 'resume')} disabled={busy}>
                        Resume
                      </Button>
                      <Button size="sm" variant="destructive" onClick={() => handleAction(inst.id, 'stop')} disabled={busy}>
                        Stop
                      </Button>
                    </>
                  )}
                  {trailingEnabled && trailingAccess?.has_access && !trailingConfigured[inst.id] && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleConfigureTrailing(inst.id)}
                      disabled={busy}
                    >
                      Enable Trailing Profit
                    </Button>
                  )}
                  {trailingConfigured[inst.id] && (
                    <Badge variant="success">Trailing Active</Badge>
                  )}
                  {inst.status !== 'running' && inst.status !== 'paused' && (
                    <Button
                      size="sm"
                      variant="ghost"
                      className="text-red-500 hover:bg-red-500/10"
                      onClick={() => handleDelete(inst.id, inst.symbol)}
                      disabled={busy}
                    >
                      Delete
                    </Button>
                  )}
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
