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
  coinGroupName?: string;
  onCapitalChange: (capital: number) => void;
  onPresetChange: (preset: string) => void;
  onCalculation?: (result: MMCalculationResult) => void;
}

export function MoneyManagementSection({
  presets,
  capital,
  selectedPreset,
  coinGroupName,
  onCapitalChange,
  onPresetChange,
  onCalculation,
}: MoneyManagementProps) {
  const [calculating, setCalculating] = useState(false);
  const [calcResult, setCalcResult] = useState<MMCalculationResult | null>(null);
  const [calcError, setCalcError] = useState<string | null>(null);

  const selected = presets.find((p) => p.preset_type === selectedPreset);

  async function handleCalculate() {
    if (!selected || !capital) return;
    if (!coinGroupName) {
      setCalcError('Select a coin group first — max coins is derived from the coin group.');
      return;
    }
    setCalculating(true);
    setCalcError(null);
    try {
      const result = await api.calculateMM(selected.preset_type, capital, coinGroupName);
      setCalcResult(result);
      onCalculation?.(result);
    } catch (err) {
      setCalcResult(null);
      const message = err instanceof Error ? err.message : 'Calculation failed';
      setCalcError(message);
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

      {/* MM Preset */}
      <div>
        <label className="mb-1 text-sm font-medium">Money Management Preset</label>
        <div className="grid gap-2 grid-cols-2 sm:grid-cols-4">
          {presets.map((p) => (
            <button
              key={p.preset_type}
              onClick={() => onPresetChange(p.preset_type)}
              className={cn(
                'rounded-xl border p-3 text-left transition-all active:scale-[0.98]',
                selectedPreset === p.preset_type ? 'border-2 border-violet-500 bg-violet-500/10' : 'border-border bg-card hover:bg-accent',
              )}
            >
              <div className="font-semibold">{p.name}</div>
              <div className="text-[10px] text-muted-foreground">{p.description}</div>
              {p.min_capital && (
                <div className="mt-1 text-[10px] font-medium text-violet-600 dark:text-violet-400">
                  Min ${Number(p.min_capital).toLocaleString()}
                </div>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Calculate Button */}
      <button
        disabled={!selected || !capital || !coinGroupName || calculating}
        onClick={handleCalculate}
        className="flex w-full items-center justify-center gap-2 rounded-lg bg-violet-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-violet-700 disabled:opacity-50"
      >
        <Calculator className="h-4 w-4" />
        {calculating ? 'Calculating...' : 'Calculate Allocation'}
      </button>

      {!coinGroupName && (
        <p className="text-xs text-amber-600 dark:text-amber-400">
          Select a coin group above to enable allocation calculation.
        </p>
      )}

      {selected && capital > 0 && Number(selected.min_capital) > 0 && capital < Number(selected.min_capital) && (
        <p className="text-xs text-amber-600 dark:text-amber-400">
          Capital is below the {selected.name} minimum of ${Number(selected.min_capital).toLocaleString()}.
        </p>
      )}

      {calcError && (
        <div className="rounded-lg bg-red-500/10 p-3 text-xs text-red-600 dark:text-red-400">
          {calcError}
        </div>
      )}

      {/* Calculation Output */}
      {calcResult && (
        <div className="grid gap-3 rounded-xl border border-violet-500/20 bg-violet-500/10 p-4 sm:grid-cols-3">
          <div>
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Per Layer</div>
            <div className="text-lg font-semibold tabular-nums">${Number(calcResult.buy_amount).toFixed(2)}</div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Coins (from group)</div>
            <div className="text-lg font-semibold tabular-nums">{calcResult.max_coins}</div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Layers / coin</div>
            <div className="text-lg font-semibold tabular-nums">{calcResult.steps}</div>
          </div>
        </div>
      )}
    </div>
  );
}
