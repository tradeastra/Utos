'use client';

import { useCallback, useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Sliders, Bitcoin, Wallet, Activity, ArrowRight, RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/services/api';
import { StrategyModeSelector } from '@/components/settings/strategy-mode';
import { CoinGroupsSelector } from '@/components/settings/coin-groups';
import { MoneyManagementSection } from '@/components/settings/money-management';
import { TechnicalAnalysisSettings } from '@/components/settings/technical-analysis';
import type {
  CoinGroup,
  CoinSelectionLimit,
  MMCalculationResult,
  MMPreset,
  StrategyMode,
  TAConfig,
  TAIndicatorDescription,
} from '@/types';

// Persisted template — bridges Config tab to Bots creation flow.
// Backend persistence is not yet available; localStorage keeps the
// template so the wizard pre-fills from the user's last saved settings.
interface StrategyTemplate {
  mode: StrategyMode;
  coinGroupId: string;
  capital: number;
  presetType: string;
  taEnabled: boolean;
  taConfigs: TAConfig[];
  symbol: string;
  upperPrice: number;
  lowerPrice: number;
  gridCount: number;
  investmentPerGrid: number;
}

const STORAGE_KEY = 'utos.strategy-template.v1';

const DEFAULT_TEMPLATE: StrategyTemplate = {
  mode: 'B',
  coinGroupId: '',
  capital: 0,
  presetType: '',
  taEnabled: false,
  taConfigs: [],
  symbol: 'BTCUSDT',
  upperPrice: 50000,
  lowerPrice: 40000,
  gridCount: 10,
  investmentPerGrid: 10,
};

function loadTemplate(): StrategyTemplate {
  if (typeof window === 'undefined') return DEFAULT_TEMPLATE;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_TEMPLATE;
    return { ...DEFAULT_TEMPLATE, ...JSON.parse(raw) };
  } catch {
    return DEFAULT_TEMPLATE;
  }
}

function saveTemplate(t: StrategyTemplate) {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(t));
  } catch {
    // ignore quota errors
  }
}

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
}

interface TradingInstance {
  id: string;
  status: string;
  symbol: string;
  total_investment: number;
  start_price?: number | null;
  current_price?: number | null;
  started_at?: string | null;
  stopped_at?: string | null;
  error_message?: string | null;
}

const STEPS = [
  { key: 'mode', label: 'Strategy Mode', icon: Sliders },
  { key: 'coins', label: 'Coin Group', icon: Bitcoin },
  { key: 'mm', label: 'Money Management', icon: Wallet },
  { key: 'grid', label: 'Grid Profile', icon: RefreshCw },
  { key: 'ta', label: 'Technical Analysis', icon: Activity },
  { key: 'launch', label: 'Launch Bot', icon: ArrowRight },
] as const;

interface SetupWizardProps {
  onInstanceCreated?: (instance: TradingInstance) => void;
}

export function SetupWizard({ onInstanceCreated }: SetupWizardProps) {
  const [template, setTemplate] = useState<StrategyTemplate>(DEFAULT_TEMPLATE);
  const [hydrated, setHydrated] = useState(false);

  const [limits, setLimits] = useState<CoinSelectionLimit | null>(null);
  const [coinGroups, setCoinGroups] = useState<CoinGroup[]>([]);
  const [presets, setPresets] = useState<MMPreset[]>([]);
  const [indicators, setIndicators] = useState<TAIndicatorDescription[]>([]);
  const [mmResult, setMMResult] = useState<MMCalculationResult | null>(null);

  const [accounts, setAccounts] = useState<ExchangeAccount[]>([]);
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [selectedAccount, setSelectedAccount] = useState('');
  const [selectedStrategy, setSelectedStrategy] = useState('');

  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ type: 'success' | 'error' | 'info'; text: string } | null>(null);

  // Hydrate template from localStorage on mount
  useEffect(() => {
    setTemplate(loadTemplate());
    setHydrated(true);
  }, []);

  // Persist template whenever it changes (after hydration)
  useEffect(() => {
    if (hydrated) saveTemplate(template);
  }, [template, hydrated]);

  // Load reference data
  const loadReference = useCallback(async () => {
    try {
      const [lim, groups, prs, inds, accs, strat] = await Promise.all([
        api.getCoinSelectionLimits().catch(() => null),
        api.getCoinGroups().catch(() => [] as CoinGroup[]),
        api.getMMPresets().catch(() => [] as MMPreset[]),
        api.getTAIndicators().catch(() => [] as TAIndicatorDescription[]),
        api.listExchangeAccounts().catch(() => [] as ExchangeAccount[]),
        api.listStrategies().catch(() => [] as Strategy[]),
      ]);
      setLimits(lim);
      setCoinGroups(groups || []);
      setPresets(prs || []);
      setIndicators(inds || []);
      setAccounts(accs || []);
      setStrategies(strat || []);

      // Auto-select first preset if template has none
      setTemplate((t) => {
        if (t.presetType && prs?.some((p) => p.preset_type === t.presetType)) return t;
        const first = prs?.[0];
        return first ? { ...t, presetType: first.preset_type } : t;
      });

      // Auto-select first coin group if template has none
      setTemplate((t) => {
        if (t.coinGroupId && groups?.some((g) => g.id === t.coinGroupId)) return t;
        const first = groups?.[0];
        return first ? { ...t, coinGroupId: first.id } : t;
      });
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    loadReference();
  }, [loadReference]);

  // Recompute MM when relevant inputs change (lazy — only if user already calculated once)
  async function recalculateMM() {
    const selected = presets.find((p) => p.preset_type === template.presetType);
    if (!selected || !template.capital) return;
    const group = coinGroups.find((g) => g.id === template.coinGroupId);
    if (!group?.name) {
      setMMResult(null);
      return;
    }
    try {
      const result = await api.calculateMM(
        selected.preset_type,
        template.capital,
        group.name,
      );
      setMMResult(result);
    } catch {
      setMMResult(null);
    }
  }

  // Auto-recompute MM when capital, preset, or coin group changes (only if user already calculated once)
  useEffect(() => {
    if (mmResult) recalculateMM();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [template.capital, template.presetType, template.coinGroupId]);

  function patchTemplate(p: Partial<StrategyTemplate>) {
    setTemplate((t) => ({ ...t, ...p }));
  }

  async function handleCreateGridProfile(): Promise<string | null> {
    try {
      const profile = await api.createGridProfile({
        name: `${template.symbol} ${template.lowerPrice}-${template.upperPrice}`,
        upper_price: template.upperPrice,
        lower_price: template.lowerPrice,
        grid_count: template.gridCount,
        investment_per_grid: template.investmentPerGrid,
      });
      return profile.id;
    } catch (err) {
      setMsg({ type: 'error', text: err instanceof Error ? err.message : 'Failed to create grid profile' });
      return null;
    }
  }

  async function handleLaunch() {
    if (!selectedAccount) {
      setMsg({ type: 'error', text: 'Select an exchange account in the Launch section below.' });
      if (typeof window !== 'undefined') {
        document.getElementById('setup-launch')?.scrollIntoView({ behavior: 'smooth' });
      }
      return;
    }
    if (!selectedStrategy) {
      setMsg({ type: 'error', text: 'Select a strategy in the Launch section below.' });
      if (typeof window !== 'undefined') {
        document.getElementById('setup-launch')?.scrollIntoView({ behavior: 'smooth' });
      }
      return;
    }
    setBusy(true);
    setMsg(null);
    try {
      // Reuse existing grid profile if matching, else create new.
      // For simplicity we always create a fresh profile from template.
      const gridProfileId = await handleCreateGridProfile();
      if (!gridProfileId) return;

      const instance = await api.createTradingInstance({
        exchange_account_id: selectedAccount,
        strategy_id: selectedStrategy,
        grid_profile_id: gridProfileId,
        symbol: template.symbol.toUpperCase(),
      });

      // Push TA configs to the new instance if enabled
      if (template.taEnabled && template.taConfigs.length > 0) {
        try {
          await api.updateTAConfigs(instance.id, template.taConfigs.map((c) => ({
            indicator: c.indicator,
            time_frame: c.time_frame,
            operator: c.operator,
            params: c.params,
            enabled: c.enabled && template.taEnabled,
            priority: c.priority,
            description: c.description ?? undefined,
          })));
        } catch {
          // Non-fatal — bot can still run without TA gate
        }
      }

      setMsg({
        type: 'success',
        text: `Trading bot created for ${template.symbol.toUpperCase()} (status: ${instance.status}). Go to the Bots list to Prepare & Start.`,
      });
      onInstanceCreated?.(instance);
    } catch (err) {
      setMsg({ type: 'error', text: err instanceof Error ? err.message : 'Failed to create bot' });
    } finally {
      setBusy(false);
    }
  }

  const filteredPresets = presets.filter((p) => {
    // MM30 only allowed for Top 3 / Top 5 (per business rule in INTERFACE_REFERENCE)
    if (p.preset_type === 'mm30') {
      const group = coinGroups.find((g) => g.id === template.coinGroupId);
      if (!group) return true;
      const name = group.name.toLowerCase();
      return name.includes('top 3') || name.includes('top 5') || group.max_coins <= 5;
    }
    return true;
  });

  const selectedCoinGroup = coinGroups.find((g) => g.id === template.coinGroupId);
  const selectedCoinGroupName = selectedCoinGroup?.name;

  if (!hydrated) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-violet-500 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Section quick-nav (anchor scroll, not page switch) */}
      <div className="sticky top-0 z-10 -mx-4 flex items-center gap-1 overflow-x-auto bg-background/80 px-4 py-2 backdrop-blur md:mx-0 md:rounded-lg md:border md:border-border">
        {STEPS.map((s) => {
          const Icon = s.icon;
          return (
            <a
              key={s.key}
              href={`#setup-${s.key}`}
              className="flex shrink-0 items-center gap-2 rounded-full bg-slate-100 px-3 py-1.5 text-xs font-medium text-muted-foreground transition hover:bg-violet-500/10 hover:text-violet-600 dark:bg-muted"
            >
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-muted-foreground/20">
                <Icon className="h-3 w-3" />
              </span>
              <span className="hidden sm:inline">{s.label}</span>
            </a>
          );
        })}
      </div>

      {msg && (
        <div className={cn(
          'rounded-lg p-3 text-sm',
          msg.type === 'success' ? 'bg-green-500/10 text-green-600 dark:text-green-400'
            : msg.type === 'error' ? 'bg-red-500/10 text-red-600 dark:text-red-400'
              : 'bg-amber-500/10 text-amber-600 dark:text-amber-400',
        )}>
          {msg.text}
        </div>
      )}

      {/* Section 1: Strategy Mode */}
      <Card glass id="setup-mode" className="scroll-mt-20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sliders className="h-5 w-5 text-violet-500" />
            Strategy Mode
          </CardTitle>
          <CardDescription>Risk profile & daily range for the bot</CardDescription>
        </CardHeader>
        <CardContent>
          <StrategyModeSelector
            value={template.mode}
            onChange={(mode) => patchTemplate({ mode })}
          />
          <p className="mt-3 text-xs text-muted-foreground">
            *Result may vary due to market fluctuations.
          </p>
        </CardContent>
      </Card>

      {/* Section 2: Coin Group */}
      <Card glass id="setup-coins" className="scroll-mt-20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bitcoin className="h-5 w-5 text-violet-500" />
            Coin Group
          </CardTitle>
          <CardDescription>
            {limits
              ? `${limits.max_coin_selection >= 999 ? 'Unlimited' : limits.max_coin_selection} coins max — ${limits.tier} tier`
              : 'Choose which coins the bot can trade'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {coinGroups.length === 0 ? (
            <p className="text-sm text-muted-foreground">No coin groups available. Contact admin or check backend connection.</p>
          ) : (
            <CoinGroupsSelector
              groups={coinGroups.map((g) => ({
                id: g.id,
                name: g.name,
                description: g.description,
                count: g.coins.length,
              }))}
              selected={template.coinGroupId}
              onChange={(id) => patchTemplate({ coinGroupId: id })}
              limit={limits?.max_coin_selection}
            />
          )}
          {template.coinGroupId && (
            <div className="mt-3 rounded-md bg-muted/40 p-3 text-xs text-muted-foreground">
              {(() => {
                const g = coinGroups.find((x) => x.id === template.coinGroupId);
                if (!g) return null;
                return (
                  <>
                    <strong className="text-foreground">{g.name}</strong>: {g.coins.slice(0, 8).join(', ')}
                    {g.coins.length > 8 && ` … (+${g.coins.length - 8} more)`}
                  </>
                );
              })()}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Section 3: Money Management */}
      <Card glass id="setup-mm" className="scroll-mt-20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Wallet className="h-5 w-5 text-violet-500" />
            Money Management
          </CardTitle>
          <CardDescription>Capital allocation & buy amount per grid</CardDescription>
        </CardHeader>
        <CardContent>
          <MoneyManagementSection
            presets={filteredPresets}
            capital={template.capital}
            selectedPreset={template.presetType}
            coinGroupName={selectedCoinGroupName}
            onCapitalChange={(c) => patchTemplate({ capital: c > 0 ? c : 0 })}
            onPresetChange={(presetType) => patchTemplate({ presetType })}
            onCalculation={(result) => setMMResult(result)}
          />
          {mmResult && (
            <div className="mt-4 rounded-lg bg-blue-500/10 p-3 text-xs text-blue-600 dark:text-blue-400">
              <strong>Allocation preview:</strong> {mmResult.max_coins} coins × {mmResult.steps} layers × ${Number(mmResult.buy_amount).toFixed(2)}/layer
              {' → '}≈ ${(mmResult.max_coins * mmResult.steps * Number(mmResult.buy_amount)).toFixed(2)} max deployed.
              {' '}Min 24h volume filter: ${Number(mmResult.min_volume_filter).toLocaleString()}.
            </div>
          )}
          <p className="mt-3 text-xs text-muted-foreground">
            Tip: MM30 is restricted to small coin groups (Top 3 / Top 5). Each coin receives {`steps`} DCA layers, so capital must cover coins × layers × $15 min per layer.
          </p>
        </CardContent>
      </Card>

      {/* Section 4: Grid Profile */}
      <Card glass id="setup-grid" className="scroll-mt-20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <RefreshCw className="h-5 w-5 text-violet-500" />
            Grid Profile
          </CardTitle>
          <CardDescription>Price range & grid density for the bot</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label className="text-sm font-medium">Symbol</label>
              <Input
                value={template.symbol}
                onChange={(e) => patchTemplate({ symbol: e.target.value.toUpperCase() })}
                placeholder="BTCUSDT"
              />
            </div>
            <div>
              <label className="text-sm font-medium">Investment Per Grid (USDT)</label>
              <Input
                type="number"
                value={template.investmentPerGrid}
                onChange={(e) => patchTemplate({ investmentPerGrid: Number(e.target.value) })}
              />
            </div>
            <div>
              <label className="text-sm font-medium">Upper Price</label>
              <Input
                type="number"
                value={template.upperPrice}
                onChange={(e) => patchTemplate({ upperPrice: Number(e.target.value) })}
              />
            </div>
            <div>
              <label className="text-sm font-medium">Lower Price</label>
              <Input
                type="number"
                value={template.lowerPrice}
                onChange={(e) => patchTemplate({ lowerPrice: Number(e.target.value) })}
              />
            </div>
            <div className="sm:col-span-2">
              <label className="text-sm font-medium">Grid Count (layers)</label>
              <Input
                type="number"
                value={template.gridCount}
                onChange={(e) => patchTemplate({ gridCount: Number(e.target.value) })}
              />
              <p className="mt-1 text-xs text-muted-foreground">
                {template.gridCount} layers × ${template.investmentPerGrid}/layer
                {' = '}
                <strong>${(template.gridCount * template.investmentPerGrid).toFixed(2)}</strong> total grid capital.
              </p>
            </div>
          </div>
          {template.upperPrice <= template.lowerPrice && (
            <div className="rounded-md bg-red-500/10 p-3 text-xs text-red-600">
              Upper price must be greater than lower price.
            </div>
          )}
        </CardContent>
      </Card>

      {/* Section 5: Technical Analysis */}
      <Card glass id="setup-ta" className="scroll-mt-20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-violet-500" />
            Technical Analysis (Optional)
          </CardTitle>
          <CardDescription>Gate buy orders with indicator conditions</CardDescription>
        </CardHeader>
        <CardContent>
          <TechnicalAnalysisSettings
            indicators={indicators}
            configs={template.taConfigs}
            enabled={template.taEnabled}
            onEnabledChange={(taEnabled) => patchTemplate({ taEnabled })}
            onConfigsChange={(taConfigs) => patchTemplate({ taConfigs })}
          />
          <p className="mt-3 text-xs text-muted-foreground">
            When enabled, TA configs will be pushed to the bot automatically on launch.
          </p>
        </CardContent>
      </Card>

      {/* Section 6: Launch — Exchange + Strategy + Create */}
      <div id="setup-launch" className="scroll-mt-20 space-y-6">
        <Card glass>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ArrowRight className="h-5 w-5 text-violet-500" />
              Select Exchange Account
            </CardTitle>
            <CardDescription>Choose your saved exchange account</CardDescription>
          </CardHeader>
          <CardContent>
            {accounts.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                No exchange accounts found. Add one in Settings → Exchanges first.
              </p>
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

        <Card glass>
          <CardHeader>
            <CardTitle>Select Strategy Algorithm</CardTitle>
            <CardDescription>Trading strategy implementation</CardDescription>
          </CardHeader>
          <CardContent>
            {strategies.length === 0 ? (
              <p className="text-sm text-muted-foreground">Loading strategies...</p>
            ) : (
              <div className="space-y-2">
                {strategies.map((s) => (
                  <label key={s.id} className="flex items-start gap-3 cursor-pointer">
                    <input
                      type="radio"
                      name="strategy"
                      value={s.id}
                      checked={selectedStrategy === s.id}
                      onChange={(e) => setSelectedStrategy(e.target.value)}
                    />
                    <div>
                      <span className="font-medium">{s.name}</span>
                      {s.description && <p className="text-sm text-muted-foreground">{s.description}</p>}
                    </div>
                  </label>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card glass>
          <CardHeader>
            <CardTitle>Launch Summary</CardTitle>
            <CardDescription>Review before creating the bot</CardDescription>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-1 gap-2 text-sm sm:grid-cols-2">
              <div className="flex justify-between rounded-md bg-muted/40 px-3 py-2">
                <dt className="text-muted-foreground">Strategy Mode</dt>
                <dd className="font-medium">{template.mode}</dd>
              </div>
              <div className="flex justify-between rounded-md bg-muted/40 px-3 py-2">
                <dt className="text-muted-foreground">Coin Group</dt>
                <dd className="font-medium">
                  {coinGroups.find((g) => g.id === template.coinGroupId)?.name ?? '—'}
                </dd>
              </div>
              <div className="flex justify-between rounded-md bg-muted/40 px-3 py-2">
                <dt className="text-muted-foreground">Capital</dt>
                <dd className="font-medium">${template.capital || '—'}</dd>
              </div>
              <div className="flex justify-between rounded-md bg-muted/40 px-3 py-2">
                <dt className="text-muted-foreground">MM Preset</dt>
                <dd className="font-medium">
                  {presets.find((p) => p.preset_type === template.presetType)?.name ?? '—'}
                </dd>
              </div>
              <div className="flex justify-between rounded-md bg-muted/40 px-3 py-2">
                <dt className="text-muted-foreground">Symbol</dt>
                <dd className="font-medium">{template.symbol.toUpperCase()}</dd>
              </div>
              <div className="flex justify-between rounded-md bg-muted/40 px-3 py-2">
                <dt className="text-muted-foreground">Grid Range</dt>
                <dd className="font-medium">${template.lowerPrice} – ${template.upperPrice}</dd>
              </div>
              <div className="flex justify-between rounded-md bg-muted/40 px-3 py-2">
                <dt className="text-muted-foreground">Grid Layers</dt>
                <dd className="font-medium">{template.gridCount} × ${template.investmentPerGrid}</dd>
              </div>
              <div className="flex justify-between rounded-md bg-muted/40 px-3 py-2">
                <dt className="text-muted-foreground">TA Gate</dt>
                <dd className="font-medium">
                  {template.taEnabled ? `On (${template.taConfigs.length} rule${template.taConfigs.length !== 1 ? 's' : ''})` : 'Off'}
                </dd>
              </div>
            </dl>
            <Button
              onClick={handleLaunch}
              disabled={busy || !selectedAccount || !selectedStrategy || template.upperPrice <= template.lowerPrice}
              className="mt-4 w-full"
            >
              {busy ? 'Creating...' : 'Create Trading Bot'}
            </Button>
            <p className="mt-2 text-center text-xs text-muted-foreground">
              After creation, the bot will be in <Badge variant="secondary">created</Badge> status.
              Use the Bots list to Prepare → Start it.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
