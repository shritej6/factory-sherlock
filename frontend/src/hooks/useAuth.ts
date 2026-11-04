import { createContext, useContext } from 'react';

import type { User } from '@/types/api';
import type { Capability } from '@/utils/permissions';

/** `error` means a stored token exists but the server could not confirm it (network or 5xx). */
export type AuthStatus = 'loading' | 'anonymous' | 'authenticated' | 'error';

export interface AuthContextValue {
  status: AuthStatus;
  user: User | null;
  /** Set while status is `error`. */
  restoreError: unknown;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  retryRestore: () => void;
  can: (capability: Capability) => boolean;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used inside AuthProvider');
  return context;
}
