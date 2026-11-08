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

/** Every variant but ghost is a raised key; primary is the amber key. */
const VARIANT_CLASSES: Record<Variant, string> = {
  primary: 'key border-accent bg-accent text-on-accent hover:bg-accent-strong',
  secondary: 'key text-ink hover:border-ink-faint',
  danger: 'key text-status-fault hover:bg-status-fault-soft',
  ghost: 'border border-transparent bg-transparent text-accent hover:bg-accent-soft',
};

const SIZE_CLASSES: Record<Size, string> = {
  sm: 'h-7 px-2.5 text-[13px]',
  md: 'h-9 px-3.5 text-sm',
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
      className={`inline-flex items-center justify-center gap-2 font-display font-semibold tracking-wide transition-colors motion-reduce:transition-none disabled:cursor-not-allowed disabled:opacity-60 ${VARIANT_CLASSES[variant]} ${SIZE_CLASSES[size]} ${className}`}
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
