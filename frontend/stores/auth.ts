import { create } from 'zustand';
import type { User } from '@/types';

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (token: string, user: User) => void;
  logout: () => void;
  setUser: (user: User) => void;
}

const DEMO_MODE = false;

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: typeof window !== 'undefined'
    ? localStorage.getItem('access_token') || (DEMO_MODE ? 'demo-token' : null)
    : null,
  isAuthenticated: typeof window !== 'undefined'
    ? !!localStorage.getItem('access_token') || DEMO_MODE
    : false,
  login: (token, user) => {
    localStorage.setItem('access_token', token);
    set({ token, user, isAuthenticated: true });
  },
  logout: () => {
    localStorage.removeItem('access_token');
    set({ token: null, user: null, isAuthenticated: false });
  },
  setUser: (user) => set({ user }),
}));
