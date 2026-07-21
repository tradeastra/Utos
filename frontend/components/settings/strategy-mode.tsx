'use client';

import { cn } from '@/lib/utils';
import { Check } from 'lucide-react';
import type { StrategyMode } from '@/types';

const MODES: { mode: StrategyMode; label: string; dailyRange: string; riskLevel: string; color: string }[] = [
  { mode: 'A', label: 'Super Bearish', dailyRange: '0.5% – 1.5%', riskLevel: 'Low', color: 'bg-blue-500/10 border-blue-500/30 text-blue-600 dark:text-blue-400' },
  { mode: 'B', label: 'Conventional', dailyRange: '1.0% – 3.0%', riskLevel: 'Medium', color: 'bg-green-500/10 border-green-500/30 text-green-600 dark:text-green-400' },
  { mode: 'C', label: 'Aggressive', dailyRange: '2.0% – 5.0%', riskLevel: 'High', color: 'bg-amber-500/10 border-amber-500/30 text-amber-600 dark:text-amber-400' },
  { mode: 'D', label: 'Very Aggressive', dailyRange: '3.0% – 8.0%', riskLevel: 'Very High', color: 'bg-orange-500/10 border-orange-500/30 text-orange-600 dark:text-orange-400' },
  { mode: 'U', label: 'Ultimate', dailyRange: '5.0% – 15.0%', riskLevel: 'Extreme', color: 'bg-violet-500/10 border-violet-500/30 text-violet-600 dark:text-violet-400' },
];

interface StrategyModeProps {
  value: StrategyMode;
  onChange: (mode: StrategyMode) => void;
}

export function StrategyModeSelector({ value, onChange }: StrategyModeProps) {
  return (
    <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-5">
      {MODES.map((sm) => (
        <button
          key={sm.mode}
          onClick={() => onChange(sm.mode)}
          className={cn(
            'rounded-2xl border p-4 text-left transition-all active:scale-[0.98]',
            value === sm.mode ? `${sm.color} border-2` : 'border-border bg-card hover:bg-accent',
          )}
        >
          <div className="flex items-center justify-between">
            <span className="text-lg font-bold">{sm.mode}</span>
            {value === sm.mode && <Check className="h-4 w-4" />}
          </div>
          <p className="mt-1 text-sm font-medium">{sm.label}</p>
          <p className="mt-1 text-xs text-muted-foreground">{sm.dailyRange}</p>
          <div className="mt-2">
            <span className="text-xs font-medium opacity-80">Risk: {sm.riskLevel}</span>
          </div>
        </button>
      ))}
    </div>
  );
}
