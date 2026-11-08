import { useEffect, useState } from 'react';

import { useMachines } from '@/hooks/queries';
import { useAuth } from '@/hooks/useAuth';
import type { Machine } from '@/types/api';
import { titleCase } from '@/utils/format';
import { toneFor } from '@/utils/statusTone';
import type { Tone } from '@/utils/statusTone';

const LAMP_CLASSES: Record<Tone, string> = {
  idle: 'bg-status-idle',
  running: 'bg-status-running',
  warning: 'bg-status-warning',
  stopped: 'bg-status-stopped',
  fault: 'bg-status-fault',
  info: 'bg-status-info',
};

const TEXT_CLASSES: Record<Tone, string> = {
  idle: 'text-status-idle',
  running: 'text-status-running',
  warning: 'text-status-warning',
  stopped: 'text-status-stopped',
  fault: 'text-status-fault',
  info: 'text-status-info',
};

function MachineLamp({ machine }: { machine: Machine }) {
  const tone = toneFor(machine.status);
  return (
    <li className="flex items-center gap-1.5 font-mono text-xs whitespace-nowrap">
      <span aria-hidden="true" className={`inline-block h-2 w-2 ${LAMP_CLASSES[tone]}`} />
      <span className="text-ink">{machine.code}</span>
      <span className={TEXT_CLASSES[tone]}>{machine.status}</span>
    </li>
  );
}

/** Wall-clock time in the band, so screenshots and recordings carry the moment they were taken. */
function Clock() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(id);
  }, []);
  return (
    <time dateTime={now.toISOString()} className="font-mono text-xs text-ink tabular-nums">
      {now.toLocaleTimeString('en-GB', { hour12: false })}
    </time>
  );
}

/** The band across the top of every screen: product name, live machine states, clock, operator. */
export function StatusBand() {
  const { user, logout } = useAuth();
  const machines = useMachines();
  return (
    <header className="flex flex-wrap items-stretch border-b-2 border-border-strong bg-surface">
      <div className="flex items-baseline gap-3 border-r border-border px-4 py-2">
        <p className="font-display text-base leading-none font-bold tracking-wider text-ink uppercase">
          Factory Sherlock
        </p>
        <p className="hidden text-[11px] text-ink-muted sm:block">Production intelligence</p>
      </div>
      <ul
        aria-label="Machine states"
        className="flex flex-1 flex-wrap items-center gap-x-5 gap-y-1 px-4 py-2"
      >
        {machines.data?.map((machine) => (
          <MachineLamp key={machine.id} machine={machine} />
        ))}
        {machines.isError && (
          <li className="text-xs text-status-fault">Machine states unavailable</li>
        )}
      </ul>
      <div className="flex items-center gap-4 border-l border-border px-4 py-2 text-xs">
        <Clock />
        {user && (
          <p className="whitespace-nowrap">
            <span className="font-medium text-ink">{user.username}</span>{' '}
            <span className="text-ink-muted">{titleCase(user.role)}</span>
          </p>
        )}
        <button
          type="button"
          onClick={logout}
          className="key px-2.5 py-1 font-display text-xs font-semibold tracking-wide text-ink-muted uppercase hover:text-ink"
        >
          Sign out
        </button>
      </div>
    </header>
  );
}
