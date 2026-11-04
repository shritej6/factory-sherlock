import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import type { FormEvent } from 'react';

import { Button } from '@/components/ui/Button';
import { SelectField, TextField } from '@/components/ui/Field';
import { ErrorState, InlineNotice } from '@/components/ui/States';
import { invalidateProduction } from '@/hooks/invalidate';
import { useDefectTypes, useProducts } from '@/hooks/queries';
import { qualityApi } from '@/services/api';
import { describeError } from '@/utils/errors';

export function InspectionForm({ onDone }: { onDone: () => void }) {
  const queryClient = useQueryClient();
  const products = useProducts();
  const defectTypes = useDefectTypes();
  const [unitId, setUnitId] = useState('');
  const [specificationId, setSpecificationId] = useState('');
  const [measured, setMeasured] = useState('');
  const [codes, setCodes] = useState<string[]>([]);
  const [message, setMessage] = useState<{ tone: 'error' | 'success'; text: string } | null>(null);

  const record = useMutation({
    mutationFn: () =>
      qualityApi.recordInspection({
        unit_id: Number(unitId),
        specification_id: Number(specificationId),
        measured_value: measured,
        defect_type_codes: codes,
      }),
    onSuccess: (inspection) => {
      setMessage({
        tone: 'success',
        text: `Inspection ${inspection.id} recorded as ${inspection.result}.`,
      });
      setMeasured('');
      setCodes([]);
      invalidateProduction(queryClient);
    },
    onError: (cause) => setMessage({ tone: 'error', text: describeError(cause) }),
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);
    record.mutate();
  }

  function toggleCode(code: string) {
    setCodes((current) =>
      current.includes(code) ? current.filter((c) => c !== code) : [...current, code],
    );
  }

  const lookupError = products.error ?? defectTypes.error;
  if (lookupError) {
    return (
      <div className="mt-3">
        <ErrorState
          error={lookupError}
          title="Could not load specifications and defect types"
          onRetry={() => {
            void products.refetch();
            void defectTypes.refetch();
          }}
        />
      </div>
    );
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="panel mt-3 flex flex-col gap-3 p-4"
      aria-label="Record inspection"
    >
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <TextField
          label="Unit id"
          type="number"
          min={1}
          value={unitId}
          onChange={(e) => setUnitId(e.target.value)}
          required
          hint="Numeric id of the production unit."
        />
        <SelectField
          label="Specification"
          value={specificationId}
          onChange={(e) => setSpecificationId(e.target.value)}
          required
        >
          <option value="">Select a specification</option>
          {products.data?.map((product) => (
            <optgroup key={product.id} label={`${product.code} · ${product.name}`}>
              {product.specifications.map((spec) => (
                <option key={spec.id} value={spec.id}>
                  {spec.characteristic} {spec.target_value} ± {spec.tolerance} {spec.unit}
                </option>
              ))}
            </optgroup>
          ))}
        </SelectField>
        <TextField
          label="Measured value"
          type="number"
          step="0.001"
          value={measured}
          onChange={(e) => setMeasured(e.target.value)}
          required
          hint="Pass or fail is decided by the specification."
        />
      </div>
      <fieldset>
        <legend className="text-xs font-medium text-ink-muted">
          Additional defect codes (failing inspections only)
        </legend>
        <div className="mt-1.5 flex flex-wrap gap-3">
          {defectTypes.data?.map((defect) => (
            <label key={defect.code} className="inline-flex items-center gap-1.5 text-sm">
              <input
                type="checkbox"
                checked={codes.includes(defect.code)}
                onChange={() => toggleCode(defect.code)}
              />
              <span className="font-mono text-xs">{defect.code}</span>
            </label>
          ))}
        </div>
      </fieldset>
      {message && <InlineNotice tone={message.tone}>{message.text}</InlineNotice>}
      <div className="flex gap-2">
        <Button type="submit" variant="primary" busy={record.isPending}>
          Record inspection
        </Button>
        <Button onClick={onDone}>Close</Button>
      </div>
    </form>
  );
}
