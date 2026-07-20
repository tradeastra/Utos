'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Home, CandlestickChart, Settings } from 'lucide-react';
import { cn } from '@/lib/utils';

const tabs = [
  { label: 'Home', href: '/dashboard', icon: Home },
  { label: 'Trade', href: '/dashboard/trading', icon: CandlestickChart },
  { label: 'Settings', href: '/settings/exchanges', icon: Settings },
];

export function BottomNav() {
  const pathname = usePathname();

  const isActive = (href: string) =>
    pathname === href || (href !== '/dashboard' && pathname.startsWith(href));

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 flex h-16 items-center justify-around border-t border-white/10 bg-white/80 backdrop-blur-xl dark:bg-black/60 md:hidden">
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const active = isActive(tab.href);
        return (
          <Link
            key={tab.href}
            href={tab.href}
            className={cn(
              'flex flex-1 flex-col items-center justify-center gap-0.5 py-2 transition-colors',
              active ? 'text-violet-500' : 'text-muted-foreground',
            )}
          >
            <div className="relative">
              <Icon className="h-5 w-5" />
              {active && (
                <span className="absolute -bottom-1 left-1/2 h-1 w-1 -translate-x-1/2 rounded-full bg-violet-500" />
              )}
            </div>
            <span className="text-[10px] font-medium">{tab.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
