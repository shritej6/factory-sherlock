import type { ButtonHTMLAttributes, Ref } from 'react';

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost';
type Size = 'sm' | 'md';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  busy?: boolean;
  /** Lets a parent return focus to the button after an inline form it opened is closed. */
  ref?: Ref<HTMLButtonElement>;
}

const VARIANT_CLASSES: Record<Variant, string> = {
  primary: 'bg-accent text-on-accent border-accent hover:bg-accent-strong',
  secondary: 'bg-surface text-ink border-border-strong hover:bg-surface-muted',
  danger: 'bg-surface text-status-fault border-status-fault hover:bg-status-fault-soft',
  ghost: 'bg-transparent text-accent border-transparent hover:bg-accent-soft',
};

const SIZE_CLASSES: Record<Size, string> = {
  sm: 'px-2.5 py-1 text-xs',
  md: 'px-3.5 py-2 text-sm',
};

export function Button({
  variant = 'secondary',
  size = 'md',
  busy = false,
  className = '',
  children,
  disabled,
  type = 'button',
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled || busy}
      aria-busy={busy || undefined}
      className={`inline-flex items-center justify-center gap-2 rounded-panel border font-medium transition-colors motion-reduce:transition-none disabled:cursor-not-allowed disabled:opacity-60 ${VARIANT_CLASSES[variant]} ${SIZE_CLASSES[size]} ${className}`}
      {...rest}
    >
      {children}
      {busy && (
        <span className="sr-only" role="status">
          Working
        </span>
      )}
    </button>
  );
}
