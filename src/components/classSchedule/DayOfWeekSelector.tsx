import { dayOfWeekOptions } from "../../utils/classScheduleFormatters";

type DayOfWeekSelectorProps = {
  value: number;
  onChange: (value: number) => void;
  error?: string;
};

export function DayOfWeekSelector({ value, onChange, error }: DayOfWeekSelectorProps) {
  return (
    <div className="class-form-group">
      <span className="class-field-label">Thứ trong tuần</span>
      <div className="class-day-chip-grid" role="radiogroup" aria-label="Chọn thứ học hằng tuần">
        {dayOfWeekOptions.map((day) => (
          <button
            className={value === day.value ? "selected" : ""}
            key={day.value}
            type="button"
            role="radio"
            aria-checked={value === day.value}
            onClick={() => onChange(day.value)}
          >
            <span>{day.shortLabel}</span>
            <strong>{day.label}</strong>
          </button>
        ))}
      </div>
      {error ? <p className="class-field-error">{error}</p> : null}
    </div>
  );
}
