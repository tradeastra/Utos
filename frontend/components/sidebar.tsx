'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  CandlestickChart,
  Grid3x3,
  ShoppingCart,
  Wallet,
  Shield,
  RefreshCw,
  Users,
  Radio,
  Bell,
  CreditCard,
  Receipt,
  UserPlus,
  Settings,
  LogOut,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuthStore } from '@/stores/auth';

const navItems = [
  { label: 'Overview', href: '/dashboard', icon: LayoutDashboard },
  { label: 'Trading', href: '/dashboard/trading', icon: CandlestickChart },
  { label: 'Grid', href: '/dashboard/grid', icon: Grid3x3 },
  { label: 'Orders', href: '/dashboard/orders', icon: ShoppingCart },
  { label: 'Portfolio', href: '/dashboard/portfolio', icon: Wallet },
  { label: 'Risk', href: '/dashboard/risk', icon: Shield },
  { label: 'Recovery', href: '/dashboard/recovery', icon: RefreshCw },
  { label: 'Workers', href: '/dashboard/workers', icon: Users },
  { label: 'Events', href: '/dashboard/events', icon: Radio },
  { label: 'Notifications', href: '/dashboard/notifications', icon: Bell },
];

const saasItems = [
  { label: 'Subscription', href: '/dashboard/subscription', icon: CreditCard },
  { label: 'Billing', href: '/dashboard/billing', icon: Receipt },
  { label: 'Affiliate', href: '/dashboard/affiliate', icon: UserPlus },
];

const settingsItems = [
  { label: 'Exchanges', href: '/settings/exchanges', icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const logout = useAuthStore((s) => s.logout);

  const isActive = (href: string) =>
    pathname === href || (href !== '/dashboard' && pathname.startsWith(href));

  return (
    <aside className="flex h-screen w-60 flex-col border-r bg-card">
      <div className="flex h-14 items-center border-b px-6">
        <span className="text-lg font-bold">UTOS</span>
      </div>

      <nav className="flex-1 overflow-y-auto p-3">
        <div className="mb-2 px-3 text-xs font-semibold uppercase text-muted-foreground">
          Trading
        </div>
        <ul className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={cn(
                    'flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors',
                    isActive(item.href)
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>

        <div className="mb-2 mt-6 px-3 text-xs font-semibold uppercase text-muted-foreground">
          SaaS
        </div>
        <ul className="space-y-1">
          {saasItems.map((item) => {
            const Icon = item.icon;
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={cn(
                    'flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors',
                    isActive(item.href)
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>

        <div className="mb-2 mt-6 px-3 text-xs font-semibold uppercase text-muted-foreground">
          Settings
        </div>
        <ul className="space-y-1">
          {settingsItems.map((item) => {
            const Icon = item.icon;
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={cn(
                    'flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors',
                    isActive(item.href)
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      <div className="border-t p-3">
        <button
          onClick={() => {
            logout();
            window.location.href = '/login';
          }}
          className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
        >
          <LogOut className="h-4 w-4" />
          Logout
        </button>
      </div>
    </aside>
  );
}
