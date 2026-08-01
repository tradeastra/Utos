'use client';

import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';
import { Check } from 'lucide-react';
import { api } from '@/services/api';
import type { StrategyMode } from '@/types';

interface ModeConfig {
  mode: string;
  label: string;
  tp_range_min: number;
  tp_range_max: number;
  risk_level: string;
  description?: string | null;
  is_active?: boolean;
  sort_order?: number;
}

// Fallback if API fails — must stay in sync with backend DB seed
// (migration 0014 + DEFAULT_STRATEGY_MODES in strategy_mode_store.py).
const FALLBACK_MODES: ModeConfig[] = [
  {
    mode: 'A', label: 'Hyper', tp_range_min: 0.0, tp_range_max: 0.3,
    risk_level: 'Very Aggressive',
    description: null,
  },
  {
    mode: 'B', label: 'Aggressive', tp_range_min: 0.0, tp_range_max: 0.6,
    risk_level: 'Aggressive',
    description: null,
  },
  {
    mode: 'C', label: 'Balanced', tp_range_min: 0.0, tp_range_max: 0.9,
    risk_level: 'Balanced',
    description: null,
  },
];

const COLOR_MAP: Record<string, string> = {
  A: 'bg-red-500/10 border-red-500/30 text-red-600 dark:text-red-400',
  B: 'bg-amber-500/10 border-amber-500/30 text-amber-600 dark:text-amber-400',
  C: 'bg-green-500/10 border-green-500/30 text-green-600 dark:text-green-400',
};

interface StrategyModeProps {
  value: StrategyMode;
  onChange: (mode: StrategyMode) => void;
}

export function StrategyModeSelector({ value, onChange }: StrategyModeProps) {
  const [modes, setModes] = useState<ModeConfig[]>(FALLBACK_MODES);

  useEffect(() => {
    api.listStrategyModes()
      .then((data) => setModes(data as ModeConfig[]))
      .catch(() => {});
  }, []);

  return (
    <div className="grid gap-3 grid-cols-1 sm:grid-cols-3">
      {modes.map((sm) => (
        <button
          key={sm.mode}
          onClick={() => onChange(sm.mode as StrategyMode)}
          className={cn(
            'rounded-2xl border p-4 text-left transition-all active:scale-[0.98]',
            value === sm.mode ? `${COLOR_MAP[sm.mode] ?? COLOR_MAP.C} border-2` : 'border-border bg-card hover:bg-accent',
          )}
        >
          <div className="flex items-center justify-between">
            <span className="text-lg font-bold">{sm.mode}</span>
            {value === sm.mode && <Check className="h-4 w-4" />}
          </div>
          <p className="mt-1 text-sm font-medium">{sm.label}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            TP: {sm.tp_range_min}% – {sm.tp_range_max}%
          </p>
          <div className="mt-2">
            <span className={cn(
              'inline-block rounded-full px-2 py-0.5 text-xs font-medium',
              COLOR_MAP[sm.mode] ?? COLOR_MAP.C,
            )}>
              {sm.risk_level}
            </span>
          </div>
        </button>
      ))}
    </div>
  );
}

/** Get tp_range_max for a mode — used as baseline spacing before ATR fetch.
 *
 *  tp_range_max is the take-profit target per grid level and also the
 *  minimum spacing (ATR can only widen it, never narrow below TP target).
 */
export function getModeSpacing(mode: string, modes: ModeConfig[] | null): number {
  if (modes && modes.length > 0) {
    const found = modes.find((m) => m.mode === mode);
    if (found) return found.tp_range_max;
  }
  const fallback = FALLBACK_MODES.find((m) => m.mode === mode);
  return fallback?.tp_range_max ?? 0.6;
}

export type { ModeConfig };
