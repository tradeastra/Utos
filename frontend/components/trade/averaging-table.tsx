'use client';

import { useState } from 'react';
import { cn } from '@/lib/utils';

export interface AveragingStepData {
  step_number: number;
  drop_rate: string;
  multiple_buy_amount: string;
  take_profit: string;
  description: string | null;
}

interface AveragingTableProps {
  steps: AveragingStepData[];
  onChange: (steps: AveragingStepData[]) => void;
}

export function AveragingTable({ steps, onChange }: AveragingTableProps) {
  const [editing, setEditing] = useState<Set<number>>(new Set());

  function updateField(stepNum: number, field: keyof AveragingStepData, value: string) {
    onChange(steps.map((s) => (s.step_number === stepNum ? { ...s, [field]: value } : s)));
  }

  function toggleEdit(stepNum: number) {
    const next = new Set(editing);
    if (next.has(stepNum)) next.delete(stepNum);
    else next.add(stepNum);
    setEditing(next);
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-border/50">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border/50 bg-muted/50 text-[10px] uppercase tracking-wider text-muted-foreground">
            <th className="px-3 py-2 text-left font-medium">Step</th>
            <th className="px-3 py-2 text-right font-medium">Drop Rate %</th>
            <th className="px-3 py-2 text-right font-medium">Multiplier</th>
            <th className="px-3 py-2 text-right font-medium">Take Profit %</th>
            <th className="px-3 py-2 text-center font-medium">Edit</th>
          </tr>
        </thead>
        <tbody>
          {steps.map((step, idx) => {
            const isEditing = editing.has(step.step_number);
            return (
              <tr
                key={step.step_number}
                className={cn(
                  'border-b border-border/30 transition-colors',
                  idx % 2 === 0 ? 'bg-card' : 'bg-card/50',
                  isEditing && 'bg-violet-500/5',
                )}
              >
                <td className="px-3 py-2 font-medium tabular-nums">{step.step_number}</td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {isEditing ? (
                    <input
                      type="number"
                      step="0.01"
                      value={step.drop_rate}
                      onChange={(e) => updateField(step.step_number, 'drop_rate', e.target.value)}
                      className="w-20 rounded border border-border bg-background px-2 py-1 text-right text-sm focus:border-violet-500 focus:outline-none"
                    />
                  ) : (
                    step.drop_rate
                  )}
                </td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {isEditing ? (
                    <input
                      type="number"
                      step="0.1"
                      value={step.multiple_buy_amount}
                      onChange={(e) => updateField(step.step_number, 'multiple_buy_amount', e.target.value)}
                      className="w-20 rounded border border-border bg-background px-2 py-1 text-right text-sm focus:border-violet-500 focus:outline-none"
                    />
                  ) : (
                    step.multiple_buy_amount
                  )}
                </td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {isEditing ? (
                    <input
                      type="number"
                      step="0.01"
                      value={step.take_profit}
                      onChange={(e) => updateField(step.step_number, 'take_profit', e.target.value)}
                      className="w-20 rounded border border-border bg-background px-2 py-1 text-right text-sm focus:border-violet-500 focus:outline-none"
                    />
                  ) : (
                    step.take_profit
                  )}
                </td>
                <td className="px-3 py-2 text-center">
                  <button
                    onClick={() => toggleEdit(step.step_number)}
                    className={cn(
                      'rounded px-2 py-0.5 text-[10px] font-medium transition',
                      isEditing ? 'bg-violet-600 text-white' : 'bg-muted text-muted-foreground hover:bg-muted/80',
                    )}
                  >
                    {isEditing ? 'Done' : 'Edit'}
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
