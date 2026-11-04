import { useState } from 'react';
import type { FormEvent } from 'react';

import { Button } from '@/components/ui/Button';
import { TextField } from '@/components/ui/Field';

interface TraceSearchFormProps {
  label: string;
  hint: string;
  buttonLabel: string;
  busy: boolean;
  onSearch: (value: string) => void;
}

export function TraceSearchForm({
  label,
  hint,
  buttonLabel,
  busy,
  onSearch,
}: TraceSearchFormProps) {
  const [value, setValue] = useState('');
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (value.trim()) onSearch(value.trim());
  }
  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-wrap items-end gap-2"
      aria-label={buttonLabel}
    >
      <div className="min-w-56 flex-1">
        <TextField
          label={label}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          hint={hint}
          className="font-mono"
        />
      </div>
      <Button type="submit" variant="primary" busy={busy} disabled={!value.trim()}>
        {buttonLabel}
      </Button>
    </form>
  );
}
