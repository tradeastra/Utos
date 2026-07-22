'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Save, Send } from 'lucide-react';

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
    <div className="space-y-6">
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

      {/* Telegram Setup */}
      <Card>
        <CardHeader>
          <CardTitle>Telegram Setup</CardTitle>
        </CardHeader>
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
  );
}
