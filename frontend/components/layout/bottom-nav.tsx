'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Home,
  CandlestickChart,
  Grid3x3,
  Wallet,
  MoreHorizontal,
  ShoppingCart,
  Shield,
  RefreshCw,
  Users,
  Radio,
  Bell,
  CreditCard,
  Receipt,
  UserPlus,
  Settings,
  X,
  Sliders,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const mainTabs = [
  { label: 'Home', href: '/dashboard', icon: Home },
  { label: 'Trade', href: '/dashboard/trade', icon: CandlestickChart },
  { label: 'Grid', href: '/dashboard/trading', icon: Grid3x3 },
  { label: 'Portfolio', href: '/dashboard/portfolio', icon: Wallet },
];

const moreItems = [
  { label: 'Orders', href: '/dashboard/orders', icon: ShoppingCart },
  { label: 'Moonbot', href: '/dashboard/moonbot-setting', icon: Sliders },
  { label: 'Risk', href: '/dashboard/risk', icon: Shield },
  { label: 'Recovery', href: '/dashboard/recovery', icon: RefreshCw },
  { label: 'Workers', href: '/dashboard/workers', icon: Users },
  { label: 'Events', href: '/dashboard/events', icon: Radio },
  { label: 'Notifications', href: '/dashboard/notifications', icon: Bell },
  { label: 'Subscription', href: '/dashboard/subscription', icon: CreditCard },
  { label: 'Billing', href: '/dashboard/billing', icon: Receipt },
  { label: 'Affiliate', href: '/dashboard/affiliate', icon: UserPlus },
  { label: 'Exchanges', href: '/settings/exchanges', icon: Settings },
];

export function BottomNav() {
  const pathname = usePathname();
  const [moreOpen, setMoreOpen] = useState(false);

  const isActive = (href: string) =>
    pathname === href || (href !== '/dashboard' && pathname.startsWith(href));

  const moreActive = moreItems.some((item) => isActive(item.href));

  return (
    <>
      <nav className="fixed bottom-0 left-0 right-0 z-40 flex items-center justify-around border-t border-border/50 bg-background/80 backdrop-blur-xl md:hidden pb-[env(safe-area-inset-bottom)]">
        {mainTabs.map((tab) => {
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

        <button
          onClick={() => setMoreOpen(true)}
          className={cn(
            'flex flex-1 flex-col items-center justify-center gap-0.5 py-2 transition-colors',
            moreActive ? 'text-violet-500' : 'text-muted-foreground',
          )}
        >
          <div className="relative">
            <MoreHorizontal className="h-5 w-5" />
            {moreActive && (
              <span className="absolute -bottom-1 left-1/2 h-1 w-1 -translate-x-1/2 rounded-full bg-violet-500" />
            )}
          </div>
          <span className="text-[10px] font-medium">More</span>
        </button>
      </nav>

      {moreOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div
            className="absolute inset-0 bg-black/50 backdrop-blur-sm animate-fade-in"
            onClick={() => setMoreOpen(false)}
          />
          <div className="absolute bottom-0 left-0 right-0 rounded-t-3xl border-t border-border bg-card p-4 animate-slide-up pb-[calc(env(safe-area-inset-bottom)+1rem)]">
            <div className="mx-auto mb-4 h-1 w-10 rounded-full bg-border" />
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-semibold">More</h3>
              <button
                onClick={() => setMoreOpen(false)}
                className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground hover:bg-accent"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="grid grid-cols-4 gap-3">
              {moreItems.map((item) => {
                const Icon = item.icon;
                const active = isActive(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setMoreOpen(false)}
                    className={cn(
                      'flex flex-col items-center gap-1.5 rounded-2xl p-3 transition-colors',
                      active
                        ? 'bg-violet-500/10 text-violet-500'
                        : 'text-muted-foreground hover:bg-accent',
                    )}
                  >
                    <Icon className="h-6 w-6" />
                    <span className="text-[10px] font-medium text-center leading-tight">{item.label}</span>
                  </Link>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
