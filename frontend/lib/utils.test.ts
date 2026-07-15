import { describe, it, expect } from 'vitest';
import { formatCurrency, formatNumber, formatPercent, timeAgo, cn } from '@/lib/utils';

describe('cn', () => {
  it('merges class names', () => {
    expect(cn('px-2', 'py-2')).toBe('px-2 py-2');
  });

  it('deduplicates conflicting tailwind classes', () => {
    expect(cn('px-2', 'px-4')).toBe('px-4');
  });
});

describe('formatCurrency', () => {
  it('formats USD', () => {
    expect(formatCurrency(99.0)).toContain('99.00');
  });

  it('formats zero', () => {
    expect(formatCurrency(0)).toContain('0.00');
  });
});

describe('formatNumber', () => {
  it('formats with decimals', () => {
    expect(formatNumber(1234.5678, 2)).toBe('1,234.57');
  });

  it('formats integer', () => {
    expect(formatNumber(100, 0)).toBe('100');
  });
});

describe('formatPercent', () => {
  it('formats positive', () => {
    expect(formatPercent(2.84)).toBe('+2.84%');
  });

  it('formats negative', () => {
    expect(formatPercent(-1.5)).toBe('-1.50%');
  });
});

describe('timeAgo', () => {
  it('returns seconds ago', () => {
    const date = new Date(Date.now() - 5000).toISOString();
    expect(timeAgo(date)).toContain('s ago');
  });

  it('returns minutes ago', () => {
    const date = new Date(Date.now() - 120000).toISOString();
    expect(timeAgo(date)).toContain('m ago');
  });

  it('returns hours ago', () => {
    const date = new Date(Date.now() - 7200000).toISOString();
    expect(timeAgo(date)).toContain('h ago');
  });
});
