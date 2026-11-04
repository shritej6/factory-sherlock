import { Navigate, Outlet, useLocation } from 'react-router';

import { Button } from '@/components/ui/Button';
import { ErrorState, LoadingState } from '@/components/ui/States';
import { useAuth } from '@/hooks/useAuth';

export function RequireAuth() {
  const { status, restoreError, retryRestore, logout } = useAuth();
  const location = useLocation();
  if (status === 'loading') return <LoadingState label="Restoring your session" />;
  if (status === 'error') {
    return (
      <main className="mx-auto max-w-md px-4 py-10">
        <ErrorState
          error={restoreError}
          title="Could not verify the session"
          onRetry={retryRestore}
        />
        <Button className="mt-3" variant="ghost" onClick={logout}>
          Sign in again
        </Button>
      </main>
    );
  }
  if (status === 'anonymous') return <Navigate to="/login" replace state={{ from: location }} />;
  return <Outlet />;
}
