'use client';

import { cn } from '@/lib/utils';

export type FilterType = 'all' | 'profit' | 'loss' | 'active' | 'paused';

interface FilterChip {
  label: string;
  value: FilterType;
  icon?: string;
}

const CHIPS: FilterChip[] = [
  { label: 'All', value: 'all' },
  { label: 'Active', value: 'active' },
  { label: 'Paused', value: 'paused' },
  { label: 'Profit', value: 'profit' },
  { label: 'Loss', value: 'loss' },
];

interface FilterChipsProps {
  active: FilterType;
  onChange: (filter: FilterType) => void;
  counts?: Partial<Record<FilterType, number>>;
}

export function FilterChips({ active, onChange, counts }: FilterChipsProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {CHIPS.map((chip) => {
        const isActive = active === chip.value;
        const count = counts?.[chip.value];
        return (
          <button
            key={chip.value}
            onClick={() => onChange(chip.value)}
            className={cn(
              'rounded-full px-3 py-1.5 text-xs font-medium transition-all',
              isActive
                ? 'bg-violet-600 text-white shadow-md shadow-violet-600/20'
                : 'bg-muted text-muted-foreground hover:bg-muted/80',
            )}
          >
            {chip.label}
            {count !== undefined && count > 0 && (
              <span className={cn('ml-1.5 rounded-full px-1.5 py-0.5 text-[10px]', isActive ? 'bg-white/20' : 'bg-background/50')}>
                {count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
