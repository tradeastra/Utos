'use client';

import { Bell } from 'lucide-react';
import { ThemeToggle } from '@/components/theme-toggle';

interface TopBarProps {
  title?: string;
}

export function TopBar({ title }: TopBarProps) {
  return (
    <header className="sticky top-0 z-40 flex h-14 items-center justify-between border-b border-border/50 bg-background/80 px-4 backdrop-blur-xl">
      <div className="flex items-center gap-3">
        <span className="text-lg font-bold tracking-tight md:hidden">
          <span className="text-violet-500">U</span>TOS
        </span>
        {title && (
          <h1 className="hidden text-base font-semibold text-foreground md:block">{title}</h1>
        )}
      </div>

      <div className="flex items-center gap-2">
        <button
          className="flex h-9 w-9 items-center justify-center rounded-xl border border-border bg-card text-muted-foreground transition-all hover:bg-accent active:scale-95"
          aria-label="Notifications"
        >
          <Bell className="h-4 w-4" />
        </button>
        <ThemeToggle />
      </div>
    </header>
  );
}
