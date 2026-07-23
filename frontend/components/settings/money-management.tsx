'use client';

import { useState } from 'react';
import { Wallet, Calculator } from 'lucide-react';
import { cn } from '@/lib/utils';
import { api } from '@/services/api';
import type { MMCalculationResult, MMPreset } from '@/types';

interface MoneyManagementProps {
  presets: MMPreset[];
  capital: number;
  selectedPreset: string;
  selectedCoinGroup?: string;
  onCapitalChange: (capital: number) => void;
  onPresetChange: (preset: string) => void;
  onCalculation?: (result: MMCalculationResult) => void;
}

export function MoneyManagementSection({
  presets,
  capital,
  selectedPreset,
  selectedCoinGroup,
  onCapitalChange,
  onPresetChange,
  onCalculation,
}: MoneyManagementProps) {
  const [calculating, setCalculating] = useState(false);
  const [calcResult, setCalcResult] = useState<MMCalculationResult | null>(null);

  const selected = presets.find((p) => p.preset_type === selectedPreset);
  const canShowPresets = capital > 0 && !!selectedCoinGroup;
  const eligiblePresets = presets.filter((p) => capital >= Number(p.min_capital));
  const ineligiblePresets = presets.filter((p) => capital < Number(p.min_capital));

  async function handleCalculate() {
    if (!selected || !capital) return;
    setCalculating(true);
    try {
      const result = await api.calculateMM(selected.preset_type, capital, selectedCoinGroup);
      setCalcResult(result);
      onCalculation?.(result);
    } catch {
      setCalcResult(null);
    } finally {
      setCalculating(false);
    }
  }

  return (
    <div className="space-y-4">
      {/* Capital Input */}
      <div>
        <label className="mb-1 flex items-center gap-2 text-sm font-medium">
          <Wallet className="h-4 w-4 text-violet-500" />
          Total Capital
        </label>
        <div className="relative">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-muted-foreground">$</span>
          <input
            type="number"
            value={capital || ''}
            onChange={(e) => onCapitalChange(Number(e.target.value))}
            placeholder="Enter capital"
            className="w-full rounded-lg border border-border bg-background py-2 pl-8 pr-3 text-sm focus:border-violet-500 focus:outline-none"
          />
        </div>
      </div>

      {/* MM Preset — only visible after capital is entered and coins are selected */}
      {canShowPresets && (
        <div className="space-y-3">
          <label className="text-sm font-medium">Money Management Preset</label>
          {eligiblePresets.length === 0 && (
            <div className="rounded-lg bg-amber-500/10 p-3 text-sm text-amber-600 dark:text-amber-400">
              Capital is below the minimum required for all presets. Increase your capital to continue.
            </div>
          )}
          <div className="grid gap-2 grid-cols-2 sm:grid-cols-4">
            {eligiblePresets.map((p) => (
              <button
                key={p.preset_type}
                onClick={() => onPresetChange(p.preset_type)}
                className={cn(
                  'rounded-xl border p-3 text-left transition-all active:scale-[0.98]',
                  selectedPreset === p.preset_type ? 'border-2 border-violet-500 bg-violet-500/10' : 'border-border bg-card hover:bg-accent',
                )}
              >
                <div className="font-semibold">{p.name}</div>
                <div className="text-xs text-muted-foreground">{p.steps} steps</div>
                <div className="text-xs text-muted-foreground">Min: ${Number(p.min_capital).toLocaleString()}</div>
              </button>
            ))}
            {ineligiblePresets.map((p) => (
              <div
                key={p.preset_type}
                className="rounded-xl border border-dashed border-border bg-muted/50 p-3 text-left opacity-50"
              >
                <div className="font-semibold">{p.name}</div>
                <div className="text-xs text-muted-foreground">{p.steps} steps</div>
                <div className="text-xs text-muted-foreground">Min: ${Number(p.min_capital).toLocaleString()}</div>
              </div>
            ))}
          </div>

          {/* Calculate Button */}
          {selectedPreset && (
            <button
              disabled={!selected || !capital || calculating}
              onClick={handleCalculate}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-violet-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-violet-700 disabled:opacity-50"
            >
              <Calculator className="h-4 w-4" />
              {calculating ? 'Calculating...' : 'Calculate Allocation'}
            </button>
          )}
        </div>
      )}

      {/* Hint when prerequisites are not met */}
      {!canShowPresets && (
        <div className="rounded-lg bg-muted/50 p-3 text-sm text-muted-foreground">
          {capital <= 0 && !selectedCoinGroup
            ? 'Enter your total capital and select coins to see available MM presets.'
            : capital <= 0
              ? 'Enter your total capital to see available MM presets.'
              : 'Select coins to see available MM presets.'}
        </div>
      )}

      {/* Calculation Output */}
      {calcResult && (
        <div className="grid gap-3 rounded-xl border border-violet-500/20 bg-violet-500/10 p-4 sm:grid-cols-3">
          <div>
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Per Buy</div>
            <div className="text-lg font-semibold tabular-nums">${Number(calcResult.buy_amount).toFixed(2)}</div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Max Coins</div>
            <div className="text-lg font-semibold tabular-nums">{calcResult.max_coins}</div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Steps</div>
            <div className="text-lg font-semibold tabular-nums">{calcResult.steps}</div>
          </div>
        </div>
      )}
    </div>
  );
}
