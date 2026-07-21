'use client';

import { cn } from '@/lib/utils';

interface MetricCardProps {
  label: string;
  value: string | number;
  sublabel?: string;
  variant?: 'default' | 'profit' | 'loss' | 'warning' | 'violet';
  icon?: React.ReactNode;
}

const VARIANT_STYLES: Record<string, string> = {
  default: 'text-foreground',
  profit: 'text-emerald-500',
  loss: 'text-red-500',
  warning: 'text-amber-500',
  violet: 'text-violet-500',
};

export function MetricCard({ label, value, sublabel, variant = 'default', icon }: MetricCardProps) {
  return (
    <div className="rounded-xl border border-border/50 bg-card p-3">
      <div className="flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
        {icon}
        {label}
      </div>
      <div className={cn('mt-1 text-lg font-bold tabular-nums', VARIANT_STYLES[variant])}>
        {value}
      </div>
      {sublabel && (
        <div className="text-[10px] text-muted-foreground">{sublabel}</div>
      )}
    </div>
  );
}
