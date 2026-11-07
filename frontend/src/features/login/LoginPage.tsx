import { useState } from 'react';
import type { FormEvent } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router';

import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/Field';
import { ErrorNotice } from '@/components/ui/States';
import { useAuth } from '@/hooks/useAuth';
import { ApiError } from '@/services/http';

interface LocationState {
  from?: { pathname: string };
}

/** A 429 carries the wait in details.retry_after_seconds; every other failure shows its message. */
function loginFailureText(error: unknown): string | undefined {
  if (!(error instanceof ApiError) || error.status !== 429) return undefined;
  const seconds = error.details.retry_after_seconds;
  return typeof seconds === 'number'
    ? `Too many attempts. Try again in ${seconds} seconds.`
    : undefined;
}

export function LoginPage() {
  const { status, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<unknown>(null);
  const [submitting, setSubmitting] = useState(false);

  const redirectTo = (location.state as LocationState | null)?.from?.pathname ?? '/';

  if (status === 'authenticated') return <Navigate to={redirectTo} replace />;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(username.trim(), password);
      navigate(redirectTo, { replace: true });
    } catch (cause) {
      setError(cause);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-10">
      <div className="panel w-full max-w-sm p-6">
        <h1 className="text-lg font-semibold tracking-tight text-ink">Factory Sherlock</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Sign in to the production intelligence console.
        </p>
        <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4" noValidate>
          <TextField
            label="Username"
            name="username"
            autoComplete="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            required
          />
          <TextField
            label="Password"
            name="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
          {error !== null && <ErrorNotice error={error}>{loginFailureText(error)}</ErrorNotice>}
          <Button
            type="submit"
            variant="primary"
            busy={submitting}
            disabled={!username || !password}
          >
            Sign in
          </Button>
        </form>
        <p className="mt-4 text-xs text-ink-faint">
          Demo accounts: admin, engineer, operator, viewer. Ask the administrator for the password.
        </p>
      </div>
    </main>
  );
}
