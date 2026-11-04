import { useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';

import { authApi } from '@/services/api';
import { ApiError, tokenStore, UNAUTHORIZED_EVENT } from '@/services/http';
import type { User } from '@/types/api';
import { describeError } from '@/utils/errors';
import { can } from '@/utils/permissions';

import { AuthContext } from './useAuth';
import type { AuthContextValue, AuthStatus } from './useAuth';

function isRejectedToken(error: unknown): boolean {
  return error instanceof ApiError && (error.status === 401 || error.status === 403);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<AuthStatus>(() =>
    tokenStore.get() ? 'loading' : 'anonymous',
  );
  const [user, setUser] = useState<User | null>(null);
  const [restoreError, setRestoreError] = useState<unknown>(null);

  const logout = useCallback(() => {
    tokenStore.clear();
    queryClient.clear();
    setUser(null);
    setRestoreError(null);
    setStatus('anonymous');
  }, [queryClient]);

  useEffect(() => {
    if (status !== 'loading') return;
    let cancelled = false;
    authApi
      .me()
      .then((me) => {
        if (cancelled) return;
        setUser(me);
        setStatus('authenticated');
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        if (isRejectedToken(error)) {
          logout();
          return;
        }
        setRestoreError(error);
        setStatus('error');
      });
    return () => {
      cancelled = true;
    };
  }, [status, logout]);

  useEffect(() => {
    window.addEventListener(UNAUTHORIZED_EVENT, logout);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, logout);
  }, [logout]);

  const login = useCallback(
    async (username: string, password: string) => {
      const token = await authApi.login({ username, password });
      queryClient.clear();
      tokenStore.set(token.access_token);
      try {
        const me = await authApi.me();
        setUser(me);
        setRestoreError(null);
        setStatus('authenticated');
      } catch (error) {
        tokenStore.clear();
        throw new Error(describeError(error));
      }
    },
    [queryClient],
  );

  const retryRestore = useCallback(() => {
    setRestoreError(null);
    setStatus('loading');
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      restoreError,
      login,
      logout,
      retryRestore,
      can: (capability) => can(user?.role, capability),
    }),
    [status, user, restoreError, login, logout, retryRestore],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/** Test helper: provides a fixed auth value without touching the network. */
export function StaticAuthProvider({
  value,
  children,
}: {
  value: Partial<AuthContextValue> & { user: User | null };
  children: ReactNode;
}) {
  const merged: AuthContextValue = {
    status: value.user ? 'authenticated' : 'anonymous',
    restoreError: null,
    login: async () => {},
    logout: () => {},
    retryRestore: () => {},
    can: (capability) => can(value.user?.role, capability),
    ...value,
  };
  return <AuthContext.Provider value={merged}>{children}</AuthContext.Provider>;
}
