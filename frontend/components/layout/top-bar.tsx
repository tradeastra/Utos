'use client';

import { useEffect, useState } from 'react';
import { Bell, ChevronDown } from 'lucide-react';
import { ThemeToggle } from '@/components/theme-toggle';
import { api } from '@/services/api';
import { cn } from '@/lib/utils';

interface TopBarProps {
  title?: string;
}

interface ExchangeAccount {
  id: string;
  exchange_name: string;
  label?: string | null;
  is_testnet: boolean;
}

export function TopBar({ title }: TopBarProps) {
  const [exchanges, setExchanges] = useState<ExchangeAccount[]>([]);
  const [selectedId, setSelectedId] = useState<string>('');
  const [open, setOpen] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const data = await api.listExchangeAccounts();
        const list = data as unknown as ExchangeAccount[];
        setExchanges(list);
        const saved = localStorage.getItem('selected_exchange_id');
        if (saved && list.some((e) => e.id === saved)) {
          setSelectedId(saved);
        } else if (list.length > 0) {
          setSelectedId(list[0].id);
          localStorage.setItem('selected_exchange_id', list[0].id);
        }
      } catch {
        // No exchange accounts
      }
    }
    load();
  }, []);

  const selected = exchanges.find((e) => e.id === selectedId);

  function handleSelect(id: string) {
    setSelectedId(id);
    localStorage.setItem('selected_exchange_id', id);
    setOpen(false);
    window.dispatchEvent(new CustomEvent('exchange-changed', { detail: id }));
  }

  return (
    <header className="sticky top-0 z-40 flex h-14 items-center justify-between border-b border-border/50 bg-background/80 px-4 backdrop-blur-xl">
      <div className="flex items-center gap-3">
        <span className="text-lg font-bold tracking-tight md:hidden">
          <span className="text-violet-500">U</span>TOS
        </span>
        {title && (
          <h1 className="hidden text-base font-semibold text-foreground md:block">{title}</h1>
        )}

        {/* Exchange Selector */}
        {exchanges.length > 0 && (
          <div className="relative ml-2">
            <button
              onClick={() => setOpen(!open)}
              className="flex items-center gap-1.5 rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs font-medium transition hover:bg-accent"
            >
              <span className="capitalize">{selected?.exchange_name || 'Select'}</span>
              {selected?.is_testnet && (
                <span className="rounded bg-amber-500/20 px-1 py-0.5 text-[10px] text-amber-600">testnet</span>
              )}
              <ChevronDown className="h-3 w-3 text-muted-foreground" />
            </button>
            {open && (
              <>
                <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
                <div className="absolute left-0 top-full z-50 mt-1 w-48 rounded-lg border border-border bg-popover p-1 shadow-lg">
                  {exchanges.map((ex) => (
                    <button
                      key={ex.id}
                      onClick={() => handleSelect(ex.id)}
                      className={cn(
                        'flex w-full items-center justify-between rounded-md px-2 py-1.5 text-xs transition hover:bg-accent',
                        ex.id === selectedId && 'bg-violet-500/10 text-violet-600',
                      )}
                    >
                      <span className="capitalize">{ex.exchange_name}</span>
                      {ex.is_testnet && (
                        <span className="rounded bg-amber-500/20 px-1 py-0.5 text-[10px] text-amber-600">testnet</span>
                      )}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
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
