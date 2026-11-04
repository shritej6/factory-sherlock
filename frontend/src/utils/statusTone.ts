export type Tone = 'idle' | 'running' | 'warning' | 'stopped' | 'fault' | 'info';

const STATUS_TONES: Record<string, Tone> = {
  IDLE: 'idle',
  RUNNING: 'running',
  WARNING: 'warning',
  STOPPED: 'stopped',
  FAULT: 'fault',
  PLANNED: 'idle',
  RELEASED: 'info',
  IN_PROGRESS: 'warning',
  COMPLETED: 'running',
  CANCELLED: 'fault',
  QUARANTINED: 'fault',
  AVAILABLE: 'running',
  CONSUMED: 'idle',
  PASS: 'running',
  FAIL: 'fault',
  OPEN: 'info',
  IN_REVIEW: 'warning',
  CLOSED: 'idle',
  INFO: 'info',
  CRITICAL: 'fault',
};

export function toneFor(status: string): Tone {
  return STATUS_TONES[status] ?? 'idle';
}
