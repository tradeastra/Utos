'use client';

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { api } from '@/services/api';
import { timeAgo } from '@/lib/utils';

interface TestResult {
  exchange: string;
  is_testnet: boolean;
  connected: boolean;
  latency_ms: number | null;
  price_symbol: string | null;
  price: string | null;
  error: string | null;
}

interface SavedAccount {
  id: string;
  exchange_name: string;
  is_testnet: boolean;
  is_active: boolean;
  connection_status: string;
  created_at: string;
}

interface BalanceItem {
  currency: string;
  available: string;
  locked: string;
  total: string;
}

interface OrderItem {
  order_id: string;
  symbol: string;
  side: string;
  order_type: string;
  quantity: string;
  price: string | null;
  status: string;
  created_at: string | null;
}

export default function ExchangesPage() {
  const [supportedExchanges, setSupportedExchanges] = useState<string[]>([]);
  const [selectedExchange, setSelectedExchange] = useState('');
  const [isTestnet, setIsTestnet] = useState(true);
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState<TestResult | null>(null);
  const [testedAt, setTestedAt] = useState<Date | null>(null);
  const [apiKey, setApiKey] = useState('');
  const [apiSecret, setApiSecret] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [accounts, setAccounts] = useState<SavedAccount[]>([]);
  const [balances, setBalances] = useState<Record<string, BalanceItem[]>>({});
  const [orders, setOrders] = useState<Record<string, OrderItem[]>>({});
  const [loadingBalance, setLoadingBalance] = useState<string | null>(null);
  const [loadingOrders, setLoadingOrders] = useState<string | null>(null);

  const loadAccounts = useCallback(async () => {
    try {
      const list = await api.listExchangeAccounts();
      setAccounts(list || []);
    } catch {
      setAccounts([]);
    }
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const res = await api.listSupportedExchanges();
        const exchanges = res.exchanges || [];
        setSupportedExchanges(exchanges);
        if (exchanges.length > 0 && !selectedExchange) {
          setSelectedExchange(exchanges[0]);
        }
      } catch {
        setSupportedExchanges([]);
      }
    })();
    loadAccounts();
  }, [loadAccounts, selectedExchange]);

  async function handleTestConnection() {
    if (!selectedExchange) return;
    setTesting(true);
    setResult(null);
    try {
      const res = await api.testExchangeConnection(selectedExchange);
      setResult(res);
      setTestedAt(new Date());
    } catch (err) {
      setResult({
        exchange: selectedExchange,
        is_testnet: isTestnet,
        connected: false,
        latency_ms: null,
        price_symbol: null,
        price: null,
        error: err instanceof Error ? err.message : 'Unknown error',
      });
      setTestedAt(new Date());
    } finally {
      setTesting(false);
    }
  }

  async function handleSaveKeys() {
    if (!selectedExchange) return;
    setSaving(true);
    setSaveMsg(null);
    try {
      await api.saveExchangeAccount({
        exchange_name: selectedExchange,
        api_key: apiKey,
        api_secret: apiSecret,
        is_testnet: isTestnet,
      });
      setSaveMsg({ type: 'success', text: 'API keys saved successfully!' });
      setApiKey('');
      setApiSecret('');
      await loadAccounts();
    } catch (err) {
      setSaveMsg({
        type: 'error',
        text: err instanceof Error ? err.message : 'Failed to save API keys',
      });
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteAccount(id: string) {
    try {
      await api.deleteExchangeAccount(id);
      await loadAccounts();
    } catch {
      // ignore
    }
  }

  async function handleFetchBalance(accountId: string) {
    setLoadingBalance(accountId);
    try {
      const res = await api.getExchangeAccountBalance(accountId);
      setBalances((prev) => ({ ...prev, [accountId]: res.balances || [] }));
    } catch (err) {
      setBalances((prev) => ({ ...prev, [accountId]: [] }));
    } finally {
      setLoadingBalance(null);
    }
  }

  async function handleFetchOrders(accountId: string) {
    setLoadingOrders(accountId);
    try {
      const res = await api.getExchangeAccountOrders(accountId);
      setOrders((prev) => ({ ...prev, [accountId]: res.open_orders || [] }));
    } catch (err) {
      setOrders((prev) => ({ ...prev, [accountId]: [] }));
    } finally {
      setLoadingOrders(null);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Exchange Accounts</h1>
        <p className="text-muted-foreground">Test and manage exchange connections</p>
      </div>

      {/* Exchange Selector + Connection Test */}
      <Card>
        <CardHeader>
          <CardTitle>Exchange Connection</CardTitle>
          <CardDescription>
            Select an exchange to test connectivity. No API keys required for public market data.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Exchange Selector */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Exchange</label>
            <select
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              value={selectedExchange}
              onChange={(e) => {
                setSelectedExchange(e.target.value);
                setResult(null);
                setTestedAt(null);
              }}
            >
              {supportedExchanges.length === 0 && (
                <option value="" disabled>Loading exchanges...</option>
              )}
              {supportedExchanges.map((ex) => (
                <option key={ex} value={ex}>
                  {ex.charAt(0).toUpperCase() + ex.slice(1)}
                </option>
              ))}
            </select>
          </div>

          {/* Testnet Toggle */}
          <div className="flex items-center gap-3">
            <label className="text-sm font-medium">Testnet Mode</label>
            <button
              type="button"
              role="switch"
              aria-checked={isTestnet}
              onClick={() => setIsTestnet(!isTestnet)}
              className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors ${
                isTestnet ? 'bg-primary' : 'bg-input'
              }`}
            >
              <span
                className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-background shadow-lg ring-0 transition-transform ${
                  isTestnet ? 'translate-x-5' : 'translate-x-0'
                }`}
              />
            </button>
          </div>

          <div className="flex items-center gap-3">
            {isTestnet && <Badge variant="warning">testnet</Badge>}
            {result?.connected && <Badge variant="success">connected</Badge>}
            {result && !result.connected && <Badge variant="destructive">failed</Badge>}
            {!result && <Badge variant="secondary">not tested</Badge>}
          </div>

          {result && (
            <div className="rounded-md border p-4 space-y-2">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Exchange</span>
                <span className="font-medium capitalize">{result.exchange}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Testnet</span>
                <span className="font-medium">{result.is_testnet ? 'Yes' : 'No'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Connected</span>
                <span className={`font-medium ${result.connected ? 'text-green-500' : 'text-red-500'}`}>
                  {result.connected ? 'Yes' : 'No'}
                </span>
              </div>
              {result.latency_ms !== null && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Latency</span>
                  <span className="font-medium">{result.latency_ms} ms</span>
                </div>
              )}
              {result.price_symbol && result.price && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">{result.price_symbol} Price</span>
                  <span className="font-medium">${result.price}</span>
                </div>
              )}
              {result.error && (
                <div className="rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950 dark:text-red-200">
                  Error: {result.error}
                </div>
              )}
              {testedAt && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Last Test</span>
                  <span className="text-sm text-muted-foreground">{timeAgo(testedAt)}</span>
                </div>
              )}
            </div>
          )}

          <Button onClick={handleTestConnection} disabled={testing || !selectedExchange} className="w-full">
            {testing ? 'Testing...' : 'Test Connection'}
          </Button>
        </CardContent>
      </Card>

      {/* Saved Exchange Accounts */}
      {accounts.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Saved Accounts</CardTitle>
            <CardDescription>Your registered exchange API keys</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {accounts.map((acc) => (
              <div key={acc.id} className="rounded-md border p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="font-medium capitalize">{acc.exchange_name}</span>
                    {acc.is_testnet && <Badge variant="warning">testnet</Badge>}
                    <Badge variant={acc.is_active ? 'success' : 'secondary'}>
                      {acc.connection_status}
                    </Badge>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleFetchBalance(acc.id)}
                      disabled={loadingBalance === acc.id}
                    >
                      {loadingBalance === acc.id ? 'Loading...' : 'Balance'}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleFetchOrders(acc.id)}
                      disabled={loadingOrders === acc.id}
                    >
                      {loadingOrders === acc.id ? 'Loading...' : 'Orders'}
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => handleDeleteAccount(acc.id)}
                    >
                      Delete
                    </Button>
                  </div>
                </div>

                {/* Balance Display */}
                {balances[acc.id] && (
                  <div className="rounded-md bg-muted/50 p-3">
                    <p className="text-sm font-medium mb-2">Balances</p>
                    {balances[acc.id].length === 0 ? (
                      <p className="text-sm text-muted-foreground">No balances found</p>
                    ) : (
                      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                        {balances[acc.id].map((b) => (
                          <div key={b.currency} className="flex justify-between text-sm">
                            <span className="font-medium">{b.currency}</span>
                            <span className="text-muted-foreground">{b.total}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Open Orders Display */}
                {orders[acc.id] && (
                  <div className="rounded-md bg-muted/50 p-3">
                    <p className="text-sm font-medium mb-2">Open Orders</p>
                    {orders[acc.id].length === 0 ? (
                      <p className="text-sm text-muted-foreground">No open orders</p>
                    ) : (
                      <div className="space-y-1">
                        {orders[acc.id].map((o) => (
                          <div key={o.order_id} className="flex items-center justify-between text-sm border-b pb-1">
                            <span className="font-medium">{o.symbol}</span>
                            <Badge variant={o.side === 'BUY' ? 'success' : 'destructive'}>
                              {o.side}
                            </Badge>
                            <span className="text-muted-foreground">{o.quantity} @ {o.price || 'MARKET'}</span>
                            <Badge variant="secondary">{o.status}</Badge>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Add API Keys (for authenticated trading) */}
      <Card>
        <CardHeader>
          <CardTitle>Add API Keys (Optional)</CardTitle>
          <CardDescription>
            Add API keys for {selectedExchange || 'the selected exchange'} for authenticated trading (order placement, balance checks).
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">API Key</label>
            <Input
              type="password"
              placeholder={`Your ${selectedExchange || 'exchange'} API key`}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">API Secret</label>
            <Input
              type="password"
              placeholder={`Your ${selectedExchange || 'exchange'} API secret`}
              value={apiSecret}
              onChange={(e) => setApiSecret(e.target.value)}
            />
          </div>
          {saveMsg && (
            <div
              className={`rounded-md p-3 text-sm ${
                saveMsg.type === 'success'
                  ? 'bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-200'
                  : 'bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-200'
              }`}
            >
              {saveMsg.text}
            </div>
          )}
          <Button onClick={handleSaveKeys} disabled={saving || !apiKey || !apiSecret || !selectedExchange} className="w-full">
            {saving ? 'Saving...' : 'Save & Authenticate'}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
