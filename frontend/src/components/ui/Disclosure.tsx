import { useId, useState } from 'react';
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
  return (
    <>
      <Button
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
