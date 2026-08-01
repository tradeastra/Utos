'use client';

import { useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { TabNav } from '@/components/ui/tab-nav';
import { SetupWizard } from '@/components/strategy/setup-wizard';
import { BotsList } from '@/components/strategy/bots-list';
import { ManualActions } from '@/components/strategy/manual-actions';

const validTabs = ['setup', 'bots', 'actions'] as const;
type TabKey = typeof validTabs[number];

const TAB_LABELS: Record<TabKey, string> = {
  setup: 'Setup',
  bots: 'Bots',
  actions: 'Manual Actions',
};

export default function StrategySettingPage() {
  const searchParams = useSearchParams();
  const paramTab = searchParams.get('tab') as TabKey | null;
  const [activeTab, setActiveTab] = useState<TabKey>(
    paramTab && validTabs.includes(paramTab) ? paramTab : 'setup'
  );
  const [botsRefreshKey, setBotsRefreshKey] = useState(0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold tracking-tight">Strategy</h2>
        <p className="text-sm text-muted-foreground">
          Configure your bot, manage running instances, and execute manual actions
        </p>
      </div>

      <TabNav
        tabs={validTabs.map((key) => ({ key, label: TAB_LABELS[key] }))}
        active={activeTab}
        onChange={(key) => setActiveTab(key as TabKey)}
      />

      {activeTab === 'setup' && (
        <SetupWizard onInstanceCreated={() => setBotsRefreshKey((k) => k + 1)} />
      )}

      {activeTab === 'bots' && (
        <BotsList refreshKey={botsRefreshKey} />
      )}

      {activeTab === 'actions' && (
        <ManualActions />
      )}
    </div>
  );
}
