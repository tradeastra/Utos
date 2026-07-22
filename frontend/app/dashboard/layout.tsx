'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { Sidebar } from '@/components/layout/sidebar';
import { BottomNav } from '@/components/layout/bottom-nav';
import { TopBar } from '@/components/layout/top-bar';
import { useAuthStore } from '@/stores/auth';

const pageTitles: Record<string, string> = {
  '/dashboard': 'Overview',
  '/dashboard/trading': 'Trading',
  '/dashboard/trade': 'Trade',
  '/dashboard/strategy-setting': 'Strategy Setting',
  '/dashboard/grid': 'Grid',
  '/dashboard/orders': 'Orders',
  '/dashboard/portfolio': 'Portfolio',
  '/dashboard/risk': 'Risk',
  '/dashboard/recovery': 'Recovery',
  '/dashboard/workers': 'Workers',
  '/dashboard/events': 'Events',
  '/dashboard/notifications': 'Notifications',
  '/dashboard/subscription': 'Subscription',
  '/dashboard/billing': 'Billing',
  '/dashboard/affiliate': 'Affiliate',
};

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const [checked, setChecked] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      router.replace('/login');
    } else {
      setChecked(true);
    }
  }, [isAuthenticated, router]);

  if (!checked) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-violet-500 border-t-transparent" />
      </div>
    );
  }

  const title = pageTitles[pathname] || 'UTOS';
  const isOverview = pathname === '/dashboard';

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed(!collapsed)} />

      <div className="flex flex-1 flex-col overflow-hidden">
        <div className={isOverview ? 'hidden md:block' : undefined}>
          <TopBar title={title} />
        </div>
        <main className="flex-1 overflow-y-auto pb-20 md:pb-0">
          <div className={isOverview ? 'mx-auto max-w-7xl md:px-6 md:py-6 lg:px-8' : 'mx-auto max-w-7xl px-4 py-6 md:px-6 lg:px-8'}>
            {children}
          </div>
        </main>
        <BottomNav />
      </div>
    </div>
  );
}
