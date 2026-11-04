import { useId } from 'react';
import type { ReactNode } from 'react';

interface PanelProps {
  title?: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  as?: 'section' | 'div' | 'article';
}

export function Panel({
  title,
  description,
  actions,
  children,
  className = '',
  as: Tag = 'section',
}: PanelProps) {
  const headingId = useId();
  return (
    <Tag className={`panel ${className}`} aria-labelledby={title ? headingId : undefined}>
      {(title || actions) && (
        <header className="flex flex-wrap items-start justify-between gap-3 border-b border-border px-4 py-3">
          <div>
            {title && (
              <h2 id={headingId} className="text-sm font-semibold text-ink">
                {title}
              </h2>
            )}
            {description && <p className="mt-0.5 text-xs text-ink-muted">{description}</p>}
          </div>
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </header>
      )}
      <div className="p-4">{children}</div>
    </Tag>
  );
}
