import { useEffect, useRef } from 'react';
import type { ReactNode } from 'react';

interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: ReactNode;
}

/** Sets the document title and moves focus to the heading whenever a new page is shown. */
export function PageHeader({ title, description, actions }: PageHeaderProps) {
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    document.title = `${title} | Factory Sherlock`;
    heading.current?.focus({ preventScroll: false });
  }, [title]);
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1
          ref={heading}
          tabIndex={-1}
          className="text-xl font-semibold tracking-tight text-ink outline-none"
        >
          {title}
        </h1>
        {description && <p className="mt-1 max-w-3xl text-sm text-ink-muted">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}
