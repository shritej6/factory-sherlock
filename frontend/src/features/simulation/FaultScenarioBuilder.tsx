import { Button } from '@/components/ui/Button';
import { SelectField, TextField } from '@/components/ui/Field';
import type { FaultKind, FaultScenario, Machine } from '@/types/api';
import { FAULT_KINDS } from '@/types/constants';
import { titleCase } from '@/utils/format';

interface FaultScenarioBuilderProps {
  machines: Machine[];
  faults: FaultScenario[];
  onChange: (faults: FaultScenario[]) => void;
}

export function FaultScenarioBuilder({ machines, faults, onChange }: FaultScenarioBuilderProps) {
  function update(index: number, patch: Partial<FaultScenario>) {
    onChange(faults.map((fault, i) => (i === index ? { ...fault, ...patch } : fault)));
  }
  function add() {
    onChange([
      ...faults,
      { machine_code: machines[0]?.code ?? '', fault: 'TOOL_WEAR', start_batch_index: 4 },
    ]);
  }
  return (
    <fieldset className="flex flex-col gap-3">
      <legend className="text-xs font-medium text-ink-muted">Fault scenarios</legend>
      {faults.length === 0 && (
        <p className="text-sm text-ink-muted">No faults. The run will produce a healthy history.</p>
      )}
      {faults.map((fault, index) => (
        <div
          key={index}
          className="grid grid-cols-1 gap-2 rounded-panel border border-border p-3 md:grid-cols-[1fr_1fr_140px_auto] md:items-end"
        >
          <SelectField
            label={`Machine ${index + 1}`}
            value={fault.machine_code}
            onChange={(e) => update(index, { machine_code: e.target.value })}
            required
          >
            {machines.map((m) => (
              <option key={m.id} value={m.code}>
                {m.code}
              </option>
            ))}
          </SelectField>
          <SelectField
            label="Fault"
            value={fault.fault}
            onChange={(e) => update(index, { fault: e.target.value as FaultKind })}
          >
            {FAULT_KINDS.map((kind) => (
              <option key={kind} value={kind}>
                {titleCase(kind)}
              </option>
            ))}
          </SelectField>
          <TextField
            label="Start batch index"
            type="number"
            min={0}
            value={fault.start_batch_index}
            onChange={(e) => update(index, { start_batch_index: Number(e.target.value) })}
          />
          <Button
            size="sm"
            onClick={() => onChange(faults.filter((_, i) => i !== index))}
            aria-label={`Remove fault ${index + 1}`}
          >
            Remove
          </Button>
        </div>
      ))}
      <div>
        <Button size="sm" onClick={add} disabled={machines.length === 0}>
          Add fault
        </Button>
      </div>
    </fieldset>
  );
}
