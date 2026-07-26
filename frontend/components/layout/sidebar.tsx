'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  ShoppingCart,
  Wallet,
  Shield,
  RefreshCw,
  Users,
  Radio,
  Bell,
  Receipt,
  UserPlus,
  Settings,
  LogOut,
  ChevronLeft,
  ChevronRight,
  X,
  Sliders,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuthStore } from '@/stores/auth';

const navItems = [
  { label: 'Overview', href: '/dashboard', icon: LayoutDashboard },
  { label: 'Strategy', href: '/dashboard/strategy-setting', icon: Sliders },
  { label: 'Orders', href: '/dashboard/orders', icon: ShoppingCart },
  { label: 'Portfolio', href: '/dashboard/portfolio', icon: Wallet },
  { label: 'Risk', href: '/dashboard/risk', icon: Shield },
  { label: 'Recovery', href: '/dashboard/recovery', icon: RefreshCw },
  { label: 'Workers', href: '/dashboard/workers', icon: Users },
  { label: 'Events', href: '/dashboard/events', icon: Radio },
  { label: 'Notifications', href: '/dashboard/notifications', icon: Bell },
];

const saasItems = [
  { label: 'Billing', href: '/dashboard/billing', icon: Receipt },
  { label: 'Affiliate', href: '/dashboard/affiliate', icon: UserPlus },
];

const settingsItems = [
  { label: 'Exchanges', href: '/settings/exchanges', icon: Settings },
  { label: 'Admin', href: '/dashboard/admin', icon: Shield },
];

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  mobile?: boolean;
}

export function Sidebar({ collapsed, onToggle, mobile = false }: SidebarProps) {
  const pathname = usePathname();
  const logout = useAuthStore((s) => s.logout);

  const isActive = (href: string) =>
    pathname === href || (href !== '/dashboard' && pathname.startsWith(href));

  const renderLink = (item: typeof navItems[number]) => {
    const Icon = item.icon;
    const active = isActive(item.href);
    return (
      <Link
        key={item.href}
        href={item.href}
        onClick={mobile ? onToggle : undefined}
        title={collapsed ? item.label : undefined}
        className={cn(
          'flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-all',
          collapsed && !mobile && 'justify-center',
          active
            ? 'bg-violet-500/10 text-violet-600 dark:text-violet-400 font-medium'
            : 'text-muted-foreground hover:bg-violet-500/5 hover:text-foreground',
        )}
      >
        <Icon className="h-[18px] w-[18px] shrink-0" />
        {(!collapsed || mobile) && <span>{item.label}</span>}
      </Link>
    );
  };

  return (
    <aside
      className={cn(
        'h-full flex-col border-r bg-card transition-all duration-300 ease-in-out',
        mobile
          ? 'flex w-72 animate-slide-in-left'
          : cn('hidden md:flex', collapsed ? 'w-16' : 'w-64'),
      )}
    >
      <div className="flex h-14 items-center justify-between border-b px-4">
        {mobile ? (
          <>
            <span className="text-lg font-bold tracking-tight">
              <span className="text-violet-500">U</span>TOS
            </span>
            <button
              onClick={onToggle}
              className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent"
              aria-label="Close menu"
            >
              <X className="h-5 w-5" />
            </button>
          </>
        ) : (
          <>
            {!collapsed && (
              <span className="text-lg font-bold tracking-tight">
                <span className="text-violet-500">U</span>TOS
              </span>
            )}
            {collapsed && (
              <span className="text-lg font-bold text-violet-500 mx-auto">U</span>
            )}
          </>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-2 no-scrollbar">
        {(!collapsed || mobile) && (
          <div className="mb-1 px-3 pt-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground/70">
            Strategy
          </div>
        )}
        <ul className="space-y-0.5">
          {navItems.map((item) => (
            <li key={item.href}>{renderLink(item)}</li>
          ))}
        </ul>

        {(!collapsed || mobile) && (
          <div className="mb-1 mt-4 px-3 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground/70">
            SaaS
          </div>
        )}
        {collapsed && !mobile && <div className="my-3 border-t border-border/50" />}
        <ul className="space-y-0.5">
          {saasItems.map((item) => (
            <li key={item.href}>{renderLink(item)}</li>
          ))}
        </ul>

        {(!collapsed || mobile) && (
          <div className="mb-1 mt-4 px-3 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground/70">
            Settings
          </div>
        )}
        {collapsed && !mobile && <div className="my-3 border-t border-border/50" />}
        <ul className="space-y-0.5">
          {settingsItems.map((item) => (
            <li key={item.href}>{renderLink(item)}</li>
          ))}
        </ul>
      </div>

      <div className="border-t p-2">
        <button
          onClick={() => {
            logout();
            window.location.href = '/login';
          }}
          title={collapsed ? 'Logout' : undefined}
          className={cn(
            'flex w-full items-center gap-3 rounded-xl px-3 py-2 text-sm text-muted-foreground transition-all hover:bg-red-500/10 hover:text-red-500',
            collapsed && !mobile && 'justify-center',
          )}
        >
          <LogOut className="h-[18px] w-[18px] shrink-0" />
          {(!collapsed || mobile) && <span>Logout</span>}
        </button>
      </div>

      {!mobile && (
        <div className="border-t p-2">
          <button
            onClick={onToggle}
            title={collapsed ? 'Expand' : 'Collapse'}
            className={cn(
              'flex w-full items-center gap-3 rounded-xl px-3 py-2 text-sm text-muted-foreground transition-all hover:bg-accent',
              collapsed && 'justify-center',
            )}
          >
            {collapsed ? (
              <ChevronRight className="h-[18px] w-[18px]" />
            ) : (
              <>
                <ChevronLeft className="h-[18px] w-[18px]" />
                <span>Collapse</span>
              </>
            )}
          </button>
        </div>
      )}
    </aside>
  );
}
