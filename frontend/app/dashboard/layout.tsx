'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { Sidebar } from '@/components/layout/sidebar';
import { BottomNav } from '@/components/layout/bottom-nav';
import { TopBar } from '@/components/layout/top-bar';
import { useAuthStore } from '@/stores/auth';

const pageTitles: Record<string, string> = {
  '/dashboard': 'Overview',
  '/dashboard/strategy-setting': 'Strategy',
  '/dashboard/orders': 'Orders',
  '/dashboard/portfolio': 'Portfolio',
  '/dashboard/risk': 'Risk',
  '/dashboard/recovery': 'Recovery',
  '/dashboard/workers': 'Workers',
  '/dashboard/events': 'Events',
  '/dashboard/notifications': 'Notifications',
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
  const login = useAuthStore((s) => s.login);
  const [checked, setChecked] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    // Re-check token from localStorage on client (SSR may have false)
    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
    if (token && !isAuthenticated) {
      // Restore auth state from localStorage
      login(token, {
        id: '',
        email: '',
        full_name: null,
        is_active: true,
        is_verified: true,
        role: 'user',
        subscription_tier: 'free',
        created_at: new Date().toISOString(),
      });
      setChecked(true);
    } else if (!isAuthenticated && !token) {
      router.replace('/login');
    } else {
      setChecked(true);
    }
  }, [isAuthenticated, router, login]);

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
