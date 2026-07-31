'use client';

import { cn } from '@/lib/utils';

export interface TabItem {
  key: string;
  label: string;
}

interface TabNavProps {
  tabs: TabItem[];
  active: string;
  onChange: (key: string) => void;
}

export function TabNav({ tabs, active, onChange }: TabNavProps) {
  return (
    <>
      {/* Mobile: pill tabs */}
      <div className="flex gap-2 overflow-x-auto pb-1 md:hidden">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => onChange(tab.key)}
            className={cn(
              'shrink-0 rounded-full px-4 py-2 text-sm font-medium transition-colors',
              active === tab.key
                ? 'bg-violet-600 text-white'
                : 'bg-slate-100 text-muted-foreground dark:bg-muted',
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Desktop: underline tabs */}
      <div className="hidden gap-6 border-b border-border md:flex">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => onChange(tab.key)}
            className={cn(
              'relative pb-3 pt-2 text-sm font-medium transition-colors',
              active === tab.key
                ? 'text-violet-600 dark:text-violet-400'
                : 'text-muted-foreground hover:text-foreground',
            )}
          >
            {tab.label}
            {active === tab.key && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5 rounded-full bg-violet-600" />
            )}
          </button>
        ))}
      </div>
    </>
  );
}
