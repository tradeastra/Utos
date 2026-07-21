'use client';

import { Activity } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { TAConfig, TAIndicatorDescription } from '@/types';

interface TechnicalAnalysisSettingsProps {
  indicators: TAIndicatorDescription[];
  configs: TAConfig[];
  enabled: boolean;
  onEnabledChange: (enabled: boolean) => void;
  onConfigsChange: (configs: TAConfig[]) => void;
}

export function TechnicalAnalysisSettings({
  indicators,
  configs,
  enabled,
  onEnabledChange,
  onConfigsChange,
}: TechnicalAnalysisSettingsProps) {

  function updateIndicator(index: number, updates: Partial<TAConfig>) {
    const next = configs.map((c, i) => (i === index ? { ...c, ...updates } : c));
    onConfigsChange(next);
  }

  function addIndicator() {
    const defaultInd = indicators[0] || { indicator: 'rsi', default_params: {} };
    onConfigsChange([
      ...configs,
      {
        indicator: defaultInd.indicator,
        time_frame: '1h',
        operator: 'and',
        params: defaultInd.default_params as Record<string, number | string>,
        enabled: true,
        priority: configs.length,
        description: null,
      },
    ]);
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between rounded-xl border border-border/50 bg-card p-3">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-violet-500" />
          <div>
            <div className="text-sm font-medium">Technical Analysis Gate</div>
            <div className="text-xs text-muted-foreground">Filter buy orders by indicators</div>
          </div>
        </div>
        <button
          onClick={() => onEnabledChange(!enabled)}
          className={cn(
            'relative h-6 w-11 rounded-full transition-colors',
            enabled ? 'bg-violet-600' : 'bg-muted',
          )}
        >
          <span className={cn(
            'absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform',
            enabled ? 'translate-x-5' : 'translate-x-0.5',
          )} />
        </button>
      </div>

      {enabled && (
        <div className="space-y-3 rounded-xl border border-border/50 bg-card p-3">
          {configs.length === 1 && (
            <div className="text-xs text-muted-foreground">
              Operator for single indicator is ignored.
            </div>
          )}
          {configs.map((cfg, idx) => (
            <div key={idx} className="grid gap-2 rounded-lg border border-border/30 bg-background p-2 sm:grid-cols-4">
              <select
                value={cfg.indicator}
                onChange={(e) => {
                  const ind = indicators.find((i) => i.indicator === e.target.value);
                  updateIndicator(idx, {
                    indicator: e.target.value,
                    params: (ind?.default_params ?? {}) as Record<string, number | string>,
                  });
                }}
                className="rounded-lg border border-border bg-background px-2 py-1.5 text-sm focus:border-violet-500 focus:outline-none"
              >
                {indicators.map((i) => (
                  <option key={i.indicator} value={i.indicator}>{i.label}</option>
                ))}
              </select>
              <select
                value={cfg.time_frame}
                onChange={(e) => updateIndicator(idx, { time_frame: e.target.value })}
                className="rounded-lg border border-border bg-background px-2 py-1.5 text-sm focus:border-violet-500 focus:outline-none"
              >
                {['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w'].map((tf) => (
                  <option key={tf} value={tf}>{tf}</option>
                ))}
              </select>
              <select
                value={cfg.operator}
                onChange={(e) => updateIndicator(idx, { operator: e.target.value })}
                className="rounded-lg border border-border bg-background px-2 py-1.5 text-sm focus:border-violet-500 focus:outline-none"
              >
                <option value="and">AND</option>
                <option value="or">OR</option>
              </select>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => onConfigsChange(configs.filter((_, i) => i !== idx))}
                  className="text-xs text-red-500 hover:text-red-600"
                >
                  Remove
                </button>
              </div>
            </div>
          ))}

          <button
            onClick={addIndicator}
            className="w-full rounded-lg border border-dashed border-violet-500/30 py-2 text-xs font-medium text-violet-500 hover:bg-violet-500/5"
          >
            + Add Indicator
          </button>
        </div>
      )}
    </div>
  );
}
