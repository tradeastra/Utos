'use client';

import { Menu, Bell } from 'lucide-react';
import { ThemeToggle } from '@/components/theme-toggle';

interface TopBarProps {
  onMenuClick?: () => void;
  title?: string;
}

export function TopBar({ onMenuClick, title }: TopBarProps) {
  return (
    <header className="sticky top-0 z-40 flex h-14 items-center justify-between border-b border-border/50 bg-background/80 px-4 backdrop-blur-xl">
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuClick}
          className="flex h-9 w-9 items-center justify-center rounded-xl text-muted-foreground transition-colors hover:bg-accent md:hidden"
          aria-label="Menu"
        >
          <Menu className="h-5 w-5" />
        </button>
        {title && (
          <h1 className="text-sm font-semibold text-foreground md:text-base">{title}</h1>
        )}
        <span className="text-lg font-bold tracking-tight md:hidden">
          <span className="text-violet-500">U</span>TOS
        </span>
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
