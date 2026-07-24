'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Save, Send, Bell } from 'lucide-react';

export default function NotificationsPage() {
  const [telegramChatId, setTelegramChatId] = useState('');
  const [telegramConnected, setTelegramConnected] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const channels = [
    { name: 'Email', enabled: true, configured: true },
    { name: 'Telegram', enabled: telegramConnected, configured: telegramConnected },
    { name: 'Discord', enabled: false, configured: false },
    { name: 'Webhook', enabled: false, configured: false },
  ];

  async function handleSaveTelegram() {
    if (!telegramChatId.trim()) return;
    setTelegramConnected(true);
    setTestResult(null);
  }

  async function handleTestTelegram() {
    setTesting(true);
    setTestResult(null);
    try {
      // In production, this would call the backend to send a test message
      await new Promise((r) => setTimeout(r, 1000));
      setTestResult({ type: 'success', text: 'Test message sent to Telegram' });
    } catch {
      setTestResult({ type: 'error', text: 'Failed to send test message' });
    } finally {
      setTesting(false);
    }
  }

  return (
    <>
      {/* Mobile */}
      <div className="min-h-full bg-slate-50 pb-24 dark:bg-background md:hidden">
        <section className="relative overflow-hidden rounded-b-[2rem] bg-gradient-to-br from-violet-700 via-purple-600 to-fuchsia-600 px-5 pb-20 pt-[max(1.25rem,env(safe-area-inset-top))] text-white">
          <div className="absolute -right-14 top-4 h-44 w-44 rounded-full bg-fuchsia-400/20 blur-2xl" />
          <div className="relative flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-white/15 backdrop-blur-sm">
              <Bell className="h-5 w-5" />
            </span>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">Notifications</h1>
              <p className="text-sm text-violet-200">Channels & alerts</p>
            </div>
          </div>
        </section>

        <div className="relative -mt-12 px-4 space-y-3">
          {/* Channels Card */}
          <div className="overflow-hidden rounded-3xl bg-white shadow-xl shadow-slate-900/10 dark:bg-card">
            <div className="border-b border-slate-100 px-5 py-4 dark:border-border">
              <p className="text-sm font-semibold">Channels</p>
            </div>
            <div className="divide-y divide-slate-100 dark:divide-border">
              {channels.map((ch) => (
                <div key={ch.name} className="flex items-center justify-between p-4">
                  <div className="flex items-center gap-3">
                    <span className={`flex h-10 w-10 items-center justify-center rounded-xl ${ch.enabled ? 'bg-emerald-100 text-emerald-600 dark:bg-emerald-500/10' : 'bg-slate-100 text-muted-foreground dark:bg-muted'}`}>
                      <Bell className="h-5 w-5" />
                    </span>
                    <div>
                      <p className="text-sm font-semibold">{ch.name}</p>
                      {!ch.configured && <p className="text-xs text-amber-500">Not configured</p>}
                    </div>
                  </div>
                  <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${ch.enabled ? 'bg-emerald-100 text-emerald-600 dark:bg-emerald-500/10' : 'bg-slate-100 text-muted-foreground dark:bg-muted'}`}>
                    {ch.enabled ? 'enabled' : 'disabled'}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Telegram Setup */}
          <div className="overflow-hidden rounded-3xl bg-white shadow-xl shadow-slate-900/10 dark:bg-card">
            <div className="border-b border-slate-100 px-5 py-4 dark:border-border">
              <p className="text-sm font-semibold">Telegram Setup</p>
            </div>
            <div className="space-y-4 p-5">
              <div className="space-y-2">
                <label className="text-sm font-medium">Telegram Chat ID</label>
                <input
                  type="text"
                  value={telegramChatId}
                  onChange={(e) => setTelegramChatId(e.target.value)}
                  placeholder="e.g. 123456789"
                  className="w-full rounded-xl border border-border bg-background px-3 py-2.5 text-sm focus:border-violet-500 focus:outline-none"
                />
                <p className="text-xs text-muted-foreground">
                  Start a chat with your bot on Telegram, then forward the chat ID here.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  onClick={handleSaveTelegram}
                  disabled={!telegramChatId.trim()}
                  variant="default"
                  size="sm"
                >
                  <Save className="mr-1.5 h-4 w-4" />
                  Save
                </Button>
                <Button
                  onClick={handleTestTelegram}
                  disabled={!telegramConnected || testing}
                  variant="outline"
                  size="sm"
                >
                  <Send className="mr-1.5 h-4 w-4" />
                  {testing ? 'Sending...' : 'Send Test'}
                </Button>
              </div>
              {testResult && (
                <div className={`rounded-xl p-3 text-sm ${testResult.type === 'success' ? 'bg-emerald-500/10 text-emerald-600' : 'bg-red-500/10 text-red-600'}`}>
                  {testResult.text}
                </div>
              )}
            </div>
          </div>

          {/* Recent Notifications */}
          <div className="overflow-hidden rounded-3xl bg-white shadow-xl shadow-slate-900/10 dark:bg-card">
            <div className="border-b border-slate-100 px-5 py-4 dark:border-border">
              <p className="text-sm font-semibold">Recent Notifications</p>
            </div>
            <div className="divide-y divide-slate-100 dark:divide-border">
              <div className="p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Grid level filled — BTC/USDT #3</span>
                  <span className="rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-medium text-emerald-600 dark:bg-emerald-500/10">delivered</span>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">Buy order filled at $64,000</p>
              </div>
              <div className="p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Risk warning — exposure at 45%</span>
                  <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-medium text-amber-600 dark:bg-amber-500/10">delivered</span>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">Total exposure approaching limit</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Desktop */}
      <div className="hidden space-y-6 md:block">
        <h1 className="text-2xl font-bold">Notifications</h1>
        <Card>
          <CardHeader><CardTitle>Channels</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {channels.map((ch) => (
              <div key={ch.name} className="flex items-center justify-between rounded-md border p-3">
                <div className="flex items-center gap-3">
                  <span className="font-medium">{ch.name}</span>
                  {!ch.configured && <Badge variant="warning">not configured</Badge>}
                </div>
                <Badge variant={ch.enabled ? 'success' : 'secondary'}>
                  {ch.enabled ? 'enabled' : 'disabled'}
                </Badge>
              </div>
            ))}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Telegram Setup</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Telegram Chat ID</label>
              <input
                type="text"
                value={telegramChatId}
                onChange={(e) => setTelegramChatId(e.target.value)}
                placeholder="e.g. 123456789"
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm focus:border-violet-500 focus:outline-none"
              />
              <p className="text-xs text-muted-foreground">
                Start a chat with your bot on Telegram, then forward the chat ID here.
                You can get your chat ID by messaging @userinfobot on Telegram.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button onClick={handleSaveTelegram} disabled={!telegramChatId.trim()} variant="default" size="sm">
                <Save className="mr-1.5 h-4 w-4" /> Save
              </Button>
              <Button onClick={handleTestTelegram} disabled={!telegramConnected || testing} variant="outline" size="sm">
                <Send className="mr-1.5 h-4 w-4" /> {testing ? 'Sending...' : 'Send Test'}
              </Button>
            </div>
            {testResult && (
              <div className={`rounded-lg p-3 text-sm ${testResult.type === 'success' ? 'bg-emerald-500/10 text-emerald-600' : 'bg-red-500/10 text-red-600'}`}>
                {testResult.text}
              </div>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Recent Notifications</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            <div className="rounded-md border p-3 text-sm">
              <div className="flex items-center justify-between">
                <span className="font-medium">Grid level filled — BTC/USDT #3</span>
                <Badge variant="success">delivered</Badge>
              </div>
              <p className="mt-1 text-muted-foreground">Buy order filled at $64,000</p>
            </div>
            <div className="rounded-md border p-3 text-sm">
              <div className="flex items-center justify-between">
                <span className="font-medium">Risk warning — exposure at 45%</span>
                <Badge variant="warning">delivered</Badge>
              </div>
              <p className="mt-1 text-muted-foreground">Total exposure approaching limit</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </>
  );
}
