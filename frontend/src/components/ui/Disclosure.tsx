import { useEffect, useId, useRef, useState } from 'react';
import type { ReactNode } from 'react';

import { Button } from './Button';

interface DisclosureProps {
  label: string;
  closeLabel?: string;
  children: (close: () => void) => ReactNode;
  variant?: 'primary' | 'secondary';
}

/** A button that reveals an inline form; used for create actions on list screens. */
export function Disclosure({
  label,
  closeLabel = 'Cancel',
  children,
  variant = 'primary',
}: DisclosureProps) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const toggle = useRef<HTMLButtonElement>(null);
  const wasOpen = useRef(false);

  // The form's own Cancel or submit removes the element that had focus, so focus returns here.
  useEffect(() => {
    if (wasOpen.current && !open) toggle.current?.focus();
    wasOpen.current = open;
  }, [open]);

  return (
    <>
      <Button
        ref={toggle}
        variant={open ? 'secondary' : variant}
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((v) => !v)}
      >
        {open ? closeLabel : label}
      </Button>
      {open && (
        <div id={id} className="basis-full">
          {children(() => setOpen(false))}
        </div>
      )}
    </>
  );
}
