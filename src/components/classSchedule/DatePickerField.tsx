import { CalendarDays, ChevronDown, ChevronLeft, ChevronRight, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import type { RefObject } from "react";

type DatePickerFieldProps = {
  error?: string;
  label: string;
  onChange: (value: string) => void;
  value: string;
};

const weekdayLabels = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"];

export function DatePickerField({ error, label, onChange, value }: DatePickerFieldProps) {
  const [open, setOpen] = useState(false);
  const selectedDate = useMemo(() => parseDateValue(value), [value]);
  const [visibleMonth, setVisibleMonth] = useState(() => startOfMonth(selectedDate ?? new Date()));
  const panelRef = useRef<HTMLDivElement>(null);
  const rootRef = useRef<HTMLDivElement>(null);

  usePickerDismiss(open, rootRef, () => setOpen(false));

  useEffect(() => {
    if (!open) return undefined;

    const timeoutId = window.setTimeout(() => {
      panelRef.current?.scrollIntoView({ block: "nearest", inline: "nearest" });
    }, 0);

    return () => window.clearTimeout(timeoutId);
  }, [open]);

  useEffect(() => {
    if (selectedDate) {
      setVisibleMonth(startOfMonth(selectedDate));
    }
  }, [selectedDate]);

  const calendarDays = useMemo(() => buildCalendarDays(visibleMonth), [visibleMonth]);
  const displayValue = selectedDate ? formatDisplayDate(selectedDate) : "Chọn ngày";

  const handleSelectDate = (date: Date) => {
    onChange(formatDateValue(date));
    setOpen(false);
  };

  return (
    <div className="class-form-group class-picker-field" ref={rootRef}>
      <span className="class-field-label">{label}</span>
      <button
        className={`class-picker-trigger ${open ? "open" : ""} ${selectedDate ? "" : "empty"}`}
        type="button"
        aria-label={`Chọn ${label.toLowerCase()}`}
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
      >
        <CalendarDays size={18} aria-hidden="true" />
        <span>{displayValue}</span>
        <ChevronDown className="class-picker-chevron" size={18} aria-hidden="true" />
      </button>

      {open ? (
        <div
          className="class-picker-panel class-date-picker-panel"
          ref={panelRef}
          role="dialog"
          aria-label={`Bảng chọn ${label.toLowerCase()}`}
        >
          <div className="class-date-picker-header">
            <button
              type="button"
              aria-label="Tháng trước"
              onClick={() => setVisibleMonth(addMonths(visibleMonth, -1))}
            >
              <ChevronLeft size={16} aria-hidden="true" />
            </button>
            <strong>{formatMonthTitle(visibleMonth)}</strong>
            <button
              type="button"
              aria-label="Tháng sau"
              onClick={() => setVisibleMonth(addMonths(visibleMonth, 1))}
            >
              <ChevronRight size={16} aria-hidden="true" />
            </button>
          </div>

          <div className="class-calendar-grid class-calendar-weekdays" aria-hidden="true">
            {weekdayLabels.map((weekday) => (
              <span key={weekday}>{weekday}</span>
            ))}
          </div>

          <div className="class-calendar-grid" role="grid" aria-label={formatMonthTitle(visibleMonth)}>
            {calendarDays.map((date) => {
              const valueForDay = formatDateValue(date);
              const selected = value === valueForDay;
              const today = isSameDay(date, new Date());
              const outsideMonth = date.getMonth() !== visibleMonth.getMonth();

              return (
                <button
                  className={`${outsideMonth ? "outside" : ""} ${selected ? "selected" : ""} ${today ? "today" : ""}`}
                  key={valueForDay}
                  type="button"
                  role="gridcell"
                  aria-selected={selected}
                  onClick={() => handleSelectDate(date)}
                >
                  {date.getDate()}
                </button>
              );
            })}
          </div>

          <div className="class-picker-actions">
            <button type="button" onClick={() => handleSelectDate(new Date())}>
              Hôm nay
            </button>
            <button
              type="button"
              onClick={() => {
                onChange("");
                setOpen(false);
              }}
            >
              <X size={15} aria-hidden="true" />
              Xóa
            </button>
          </div>
        </div>
      ) : null}

      {error ? <p className="class-field-error">{error}</p> : null}
    </div>
  );
}

function parseDateValue(value: string): Date | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return null;

  const year = Number(match[1]);
  const month = Number(match[2]) - 1;
  const day = Number(match[3]);
  const date = new Date(year, month, day);

  if (date.getFullYear() !== year || date.getMonth() !== month || date.getDate() !== day) {
    return null;
  }

  return date;
}

function startOfMonth(date: Date) {
  return new Date(date.getFullYear(), date.getMonth(), 1);
}

function addMonths(date: Date, offset: number) {
  return new Date(date.getFullYear(), date.getMonth() + offset, 1);
}

function buildCalendarDays(month: Date) {
  const first = startOfMonth(month);
  const mondayOffset = (first.getDay() + 6) % 7;
  const start = new Date(first.getFullYear(), first.getMonth(), 1 - mondayOffset);

  return Array.from({ length: 42 }, (_, index) => {
    return new Date(start.getFullYear(), start.getMonth(), start.getDate() + index);
  });
}

function formatDateValue(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function formatDisplayDate(date: Date) {
  const day = String(date.getDate()).padStart(2, "0");
  const month = String(date.getMonth() + 1).padStart(2, "0");
  return `${day}/${month}/${date.getFullYear()}`;
}

function formatMonthTitle(date: Date) {
  return `Tháng ${date.getMonth() + 1}/${date.getFullYear()}`;
}

function isSameDay(left: Date, right: Date) {
  return (
    left.getFullYear() === right.getFullYear() &&
    left.getMonth() === right.getMonth() &&
    left.getDate() === right.getDate()
  );
}

function usePickerDismiss(
  open: boolean,
  rootRef: RefObject<HTMLElement | null>,
  onDismiss: () => void,
) {
  useEffect(() => {
    if (!open) return undefined;

    const handlePointerDown = (event: PointerEvent) => {
      if (rootRef.current?.contains(event.target as Node)) return;
      onDismiss();
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onDismiss();
      }
    };

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [onDismiss, open, rootRef]);
}
