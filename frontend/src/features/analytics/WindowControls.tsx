import { TextField } from '@/components/ui/Field';

export interface TimeWindow {
  start: string;
  end: string;
}

interface WindowControlsProps {
  value: TimeWindow;
  onChange: (value: TimeWindow) => void;
}

export function WindowControls({ value, onChange }: WindowControlsProps) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      <TextField
        label="Window start"
        type="datetime-local"
        value={value.start}
        onChange={(e) => onChange({ ...value, start: e.target.value })}
      />
      <TextField
        label="Window end"
        type="datetime-local"
        value={value.end}
        onChange={(e) => onChange({ ...value, end: e.target.value })}
      />
    </div>
  );
}
