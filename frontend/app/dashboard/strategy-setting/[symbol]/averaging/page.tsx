'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowLeft, RotateCcw, Edit3, Save, Layers } from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/services/api';
import { AveragingTable, type AveragingStepData } from '@/components/trade/averaging-table';

export default function AveragingConfigPage() {
  const params = useParams();
  const router = useRouter();
  const symbol = decodeURIComponent(params.symbol as string);

  const [instanceId, setInstanceId] = useState<string>('');
  const [steps, setSteps] = useState<AveragingStepData[]>([]);
  const [originalSteps, setOriginalSteps] = useState<AveragingStepData[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [changingAll, setChangingAll] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const instances = await api.getTradingInstances().catch(() => [] as Record<string, unknown>[]);
        const instList = instances as Record<string, unknown>[];
        const found = instList.find((i) => String(i.symbol).toUpperCase() === symbol.toUpperCase());
        if (found) {
          const id = String(found.id);
          setInstanceId(id);
          const config = await api.getAveragingConfig(id);
          const stepData = config as AveragingStepData[];
          setSteps(stepData);
          setOriginalSteps(stepData);
        }
      } catch {
        // API not available
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [symbol]);

  async function handleSave() {
    if (!instanceId) return;
    setSaving(true);
    setMessage(null);
    try {
      const result = await api.updateAveragingConfig(instanceId, steps.map((s) => ({
        step_number: s.step_number,
        drop_rate: Number(s.drop_rate),
        multiple_buy_amount: Number(s.multiple_buy_amount),
        take_profit: Number(s.take_profit),
        description: s.description ?? undefined,
      })));
      setSteps(result as AveragingStepData[]);
      setOriginalSteps(result as AveragingStepData[]);
      setMessage({ type: 'success', text: 'Averaging config saved successfully' });
    } catch {
      setMessage({ type: 'error', text: 'Failed to save averaging config' });
    } finally {
      setSaving(false);
    }
  }

  async function handleReset() {
    if (!instanceId) return;
    setResetting(true);
    setMessage(null);
    try {
      const result = await api.resetAveragingConfig(instanceId);
      setSteps(result as AveragingStepData[]);
      setOriginalSteps(result as AveragingStepData[]);
      setMessage({ type: 'success', text: 'Averaging config reset to default' });
    } catch {
      setMessage({ type: 'error', text: 'Failed to reset averaging config' });
    } finally {
      setResetting(false);
    }
  }

  async function handleChangeAll() {
    if (!instanceId) return;
    setChangingAll(true);
    setMessage(null);
    try {
      const template = await api.getAveragingTemplate();
      const newSteps = template.drop_rates.map((dr, i) => ({
        step_number: i + 1,
        drop_rate: String(dr),
        multiple_buy_amount: String(template.multipliers[i] ?? 1),
        take_profit: String(template.take_profits[i] ?? 0),
        description: null,
      }));
      const result = await api.updateAveragingConfig(instanceId, newSteps.map((s) => ({
        step_number: s.step_number,
        drop_rate: Number(s.drop_rate),
        multiple_buy_amount: Number(s.multiple_buy_amount),
        take_profit: Number(s.take_profit),
        description: undefined,
      })));
      setSteps(result as AveragingStepData[]);
      setOriginalSteps(result as AveragingStepData[]);
      setMessage({ type: 'success', text: 'All steps updated from template' });
    } catch {
      setMessage({ type: 'error', text: 'Failed to change all steps' });
    } finally {
      setChangingAll(false);
    }
  }

  const hasChanges = JSON.stringify(steps) !== JSON.stringify(originalSteps);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-violet-500 border-t-transparent" />
      </div>
    );
  }

  if (!instanceId) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <Layers className="mb-2 h-8 w-8 text-muted-foreground/50" />
        <p className="text-sm text-muted-foreground">No trading instance found for {symbol}</p>
        <button
          onClick={() => router.push('/dashboard/strategy-setting?tab=positions')}
          className="mt-4 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-700"
        >
          Back to Strategy
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => router.push(`/dashboard/strategy-setting/${symbol}`)}
          className="rounded-lg p-2 hover:bg-muted"
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div className="flex-1">
          <h2 className="text-xl font-bold tracking-tight">{symbol} — Averaging Config</h2>
          <p className="text-xs text-muted-foreground">{steps.length} steps · Editable per step</p>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex flex-wrap gap-2">
        <button
          disabled={resetting}
          onClick={handleReset}
          className="flex items-center gap-1.5 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-red-700 disabled:opacity-50"
        >
          <RotateCcw className="h-4 w-4" />
          {resetting ? 'Resetting...' : 'RESET AVG'}
        </button>
        <button
          disabled={changingAll}
          onClick={handleChangeAll}
          className="flex items-center gap-1.5 rounded-lg bg-amber-500 px-4 py-2 text-sm font-medium text-white transition hover:bg-amber-600 disabled:opacity-50"
        >
          <Edit3 className="h-4 w-4" />
          {changingAll ? 'Updating...' : 'CHANGE ALL'}
        </button>
        <button
          disabled={!hasChanges || saving}
          onClick={handleSave}
          className={cn(
            'flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium text-white transition disabled:opacity-50',
            hasChanges ? 'bg-violet-600 hover:bg-violet-700' : 'bg-muted',
          )}
        >
          <Save className="h-4 w-4" />
          {saving ? 'Saving...' : 'SAVE'}
        </button>
      </div>

      {/* Message */}
      {message && (
        <div className={cn(
          'rounded-lg p-3 text-sm',
          message.type === 'success' ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400' : 'bg-red-500/10 text-red-600 dark:text-red-400',
        )}>
          {message.text}
        </div>
      )}

      {/* Unsaved indicator */}
      {hasChanges && (
        <div className="rounded-lg bg-amber-500/10 px-3 py-1.5 text-xs text-amber-600 dark:text-amber-400">
          You have unsaved changes. Click SAVE to persist.
        </div>
      )}

      {/* Averaging Table */}
      <Card glass>
        <CardHeader>
          <CardTitle>Averaging Steps</CardTitle>
        </CardHeader>
        <CardContent>
          <AveragingTable steps={steps} onChange={setSteps} />
        </CardContent>
      </Card>
    </div>
  );
}
