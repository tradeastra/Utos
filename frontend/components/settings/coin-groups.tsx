'use client';

import { cn } from '@/lib/utils';
import { Coins } from 'lucide-react';

interface CoinGroup {
  id: string;
  name: string;
  description: string | null;
  count?: number;
}

interface CoinGroupsProps {
  groups: CoinGroup[];
  selected: string;
  onChange: (id: string) => void;
  limit?: number;
}

export function CoinGroupsSelector({ groups, selected, onChange, limit }: CoinGroupsProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium">
          <Coins className="h-4 w-4 text-violet-500" />
          Select Coin Group
        </div>
        {limit !== undefined && (
          <div className="text-xs text-muted-foreground">
            Max {limit} coins
          </div>
        )}
      </div>
      <div className="grid gap-2 grid-cols-1 sm:grid-cols-2">
        {groups.map((g) => {
          const isSelected = selected === g.id;
          return (
            <button
              key={g.id}
              onClick={() => onChange(g.id)}
              className={cn(
                'rounded-xl border p-3 text-left transition-all active:scale-[0.98]',
                isSelected ? 'border-2 border-violet-500 bg-violet-500/10' : 'border-border bg-card hover:bg-accent',
              )}
            >
              <div className="flex items-center justify-between">
                <span className="font-semibold">{g.name}</span>
                {g.count !== undefined && (
                  <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium">
                    {g.count} coins
                  </span>
                )}
              </div>
              {g.description && (
                <p className="mt-1 text-xs text-muted-foreground">{g.description}</p>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
