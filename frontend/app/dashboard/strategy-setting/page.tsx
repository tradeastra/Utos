'use client';

<<<<<<< HEAD
import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Save, Pause, Play, Sliders, Bitcoin, Wallet, Activity } from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/services/api';
import { StrategyModeSelector } from '@/components/settings/strategy-mode';
import { CoinVolumeList } from '@/components/settings/coin-volume-list';
import { MoneyManagementSection } from '@/components/settings/money-management';
import { TechnicalAnalysisSettings } from '@/components/settings/technical-analysis';
import type {
  CoinSelectionLimit,
  MMPreset,
  StrategyMode,
  TAConfig,
  TAIndicatorDescription,
} from '@/types';
=======
import { useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { TabNav } from '@/components/ui/tab-nav';
import { SetupWizard } from '@/components/strategy/setup-wizard';
import { BotsList } from '@/components/strategy/bots-list';
import { PositionsTab } from '@/components/strategy/positions-tab';
import { ManualActions } from '@/components/strategy/manual-actions';
>>>>>>> develop

const validTabs = ['setup', 'bots', 'positions', 'actions'] as const;
type TabKey = typeof validTabs[number];

const TAB_LABELS: Record<TabKey, string> = {
  setup: 'Setup',
  bots: 'Bots',
  positions: 'Positions',
  actions: 'Manual Actions',
};

export default function StrategySettingPage() {
<<<<<<< HEAD
  const [mode, setMode] = useState<StrategyMode>('B');
  const [limits, setLimits] = useState<CoinSelectionLimit | null>(null);
  const [presets, setPresets] = useState<MMPreset[]>([]);
  const [capital, setCapital] = useState<number>(0);
  const [selectedPreset, setSelectedPreset] = useState<string>('');
  const [selectedCoins, setSelectedCoins] = useState<string[]>([]);
  const [indicators, setIndicators] = useState<TAIndicatorDescription[]>([]);
  const [taConfigs, setTaConfigs] = useState<TAConfig[]>([]);
  const [taEnabled, setTaEnabled] = useState(false);
  const [instances, setInstances] = useState<SettingInstance[]>([]);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [updateMsg, setUpdateMsg] = useState<{ type: 'success' | 'info'; text: string } | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        const [lim, prs, inds, insts] = await Promise.all([
          api.getCoinSelectionLimits(),
          api.getMMPresets(),
          api.getTAIndicators(),
          api.getTradingInstances().catch(() => [] as Record<string, unknown>[]),
        ]);
        setLimits(lim);
        setPresets(prs);
        setIndicators(inds);
        setInstances((insts as Record<string, unknown>[]).map((i) => ({
          id: String(i.id),
          status: String(i.status),
          symbol: String(i.symbol),
        })));
        if (prs.length > 0) setSelectedPreset(prs[0].preset_type);
      } catch {
        // ignore
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const activeCount = instances.filter((i) => i.status === 'running').length;
  const hasRunning = activeCount > 0;

  async function handleUpdate() {
    setUpdating(true);
    setUpdateMsg(null);
    try {
      if (instances.length > 0) {
        await Promise.all(
          instances.map((inst) =>
            api.updateTAConfigs(inst.id, taConfigs.map((c) => ({
              indicator: c.indicator,
              time_frame: c.time_frame,
              operator: c.operator,
              params: c.params,
              enabled: c.enabled && taEnabled,
              priority: c.priority,
              description: c.description ?? undefined,
            }))),
          ),
        );
        setUpdateMsg({
          type: 'success',
          text: `TA configs saved to ${instances.length} instance${instances.length !== 1 ? 's' : ''}. Strategy mode, coin selection, and MM preset are saved locally until backend persistence is added.`,
        });
      } else {
        setUpdateMsg({
          type: 'info',
          text: 'No trading instances found. Create one in the Trading page first, then Update will push TA configs to it.',
        });
      }
    } catch {
      setUpdateMsg({ type: 'info', text: 'Failed to save. Ensure the backend is running and you have trading instances.' });
    } finally {
      setUpdating(false);
    }
  }

  async function handlePauseResume() {
    try {
      await Promise.all(
        instances.map(async (inst) => {
          if (hasRunning) {
            await api.pauseTradingInstance(inst.id);
          } else {
            await api.resumeTradingInstance(inst.id);
          }
        }),
      );
      setInstances(instances.map((i) => ({ ...i, status: hasRunning ? 'paused' : 'running' })));
    } catch {
      // Ignore
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-violet-500 border-t-transparent" />
      </div>
    );
  }
=======
  const searchParams = useSearchParams();
  const paramTab = searchParams.get('tab') as TabKey | null;
  const [activeTab, setActiveTab] = useState<TabKey>(
    paramTab && validTabs.includes(paramTab) ? paramTab : 'setup'
  );
  const [botsRefreshKey, setBotsRefreshKey] = useState(0);
>>>>>>> develop

  return (
    <div className="space-y-6">
      {/* Header */}
<<<<<<< HEAD
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-bold tracking-tight">Strategy Settings</h2>
          <p className="text-sm text-muted-foreground">Configure strategy, coins, MM and TA</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            disabled={updating || instances.length === 0}
            onClick={handlePauseResume}
            className={cn(
              'flex items-center gap-1.5 rounded-lg px-4 py-2 text-sm font-medium text-white transition disabled:opacity-50',
              hasRunning ? 'bg-amber-600 hover:bg-amber-700' : 'bg-emerald-600 hover:bg-emerald-700',
            )}
          >
            {hasRunning ? <><Pause className="h-4 w-4" /> Pause All</> : <><Play className="h-4 w-4" /> Resume All</>}
          </button>
          <button
            disabled={updating}
            onClick={handleUpdate}
            className="flex items-center gap-1.5 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-violet-700 disabled:opacity-50"
          >
            <Save className="h-4 w-4" />
            {updating ? 'Saving...' : 'Update'}
          </button>
        </div>
=======
      <div>
        <h2 className="text-xl font-bold tracking-tight">Strategy</h2>
        <p className="text-sm text-muted-foreground">
          Configure your bot, manage running instances, and monitor positions
        </p>
>>>>>>> develop
      </div>

      <TabNav
        tabs={validTabs.map((key) => ({ key, label: TAB_LABELS[key] }))}
        active={activeTab}
        onChange={(key) => setActiveTab(key as TabKey)}
      />

<<<<<<< HEAD
      {/* Update feedback */}
      {updateMsg && (
        <div className={`rounded-lg p-3 text-sm ${updateMsg.type === 'success' ? 'bg-green-500/10 text-green-600 dark:text-green-400' : 'bg-amber-500/10 text-amber-600 dark:text-amber-400'}`}>
          {updateMsg.text}
        </div>
      )}

      {/* Strategy Mode */}
      <Card glass>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sliders className="h-5 w-5 text-violet-500" />
            Strategy Mode
          </CardTitle>
        </CardHeader>
        <CardContent>
          <StrategyModeSelector value={mode} onChange={setMode} />
        </CardContent>
      </Card>

      {/* Coin Selection */}
      <Card glass>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bitcoin className="h-5 w-5 text-violet-500" />
            Coin Selection
          </CardTitle>
        </CardHeader>
        <CardContent>
          <CoinVolumeList
            exchange="binance"
            selectedCoins={selectedCoins}
            onChange={setSelectedCoins}
            maxSelection={limits?.max_coin_selection ?? 2}
          />
        </CardContent>
      </Card>

      {/* Money Management */}
      <Card glass>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Wallet className="h-5 w-5 text-violet-500" />
            Money Management
          </CardTitle>
        </CardHeader>
        <CardContent>
          <MoneyManagementSection
            presets={presets}
            capital={capital}
            selectedPreset={selectedPreset}
            selectedCoinGroup={selectedCoins.length > 0 ? `${selectedCoins.length} coins` : undefined}
            onCapitalChange={(c) => setCapital(c > 0 ? c : 0)}
            onPresetChange={setSelectedPreset}
          />
        </CardContent>
      </Card>
=======
      {activeTab === 'setup' && (
        <SetupWizard onInstanceCreated={() => setBotsRefreshKey((k) => k + 1)} />
      )}

      {activeTab === 'bots' && (
        <BotsList refreshKey={botsRefreshKey} />
      )}

      {activeTab === 'positions' && (
        <PositionsTab />
      )}
>>>>>>> develop

      {activeTab === 'actions' && (
        <ManualActions />
      )}
    </div>
  );
}
