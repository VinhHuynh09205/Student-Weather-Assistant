import { Check, ChevronDown, Clock3 } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import type { RefObject } from "react";

type TimeRangeInputProps = {
  startTime: string;
  endTime: string;
  startError?: string;
  endError?: string;
  onStartTimeChange: (value: string) => void;
  onEndTimeChange: (value: string) => void;
};

const hours = Array.from({ length: 24 }, (_, index) => String(index).padStart(2, "0"));
const minutes = Array.from({ length: 12 }, (_, index) => String(index * 5).padStart(2, "0"));

export function TimeRangeInput({
  startTime,
  endTime,
  startError,
  endError,
  onStartTimeChange,
  onEndTimeChange,
}: TimeRangeInputProps) {
  return (
    <div className="class-time-range-grid">
      <TimePickerField
        label="Giờ bắt đầu"
        value={startTime}
        error={startError}
        onChange={onStartTimeChange}
      />

      <TimePickerField
        label="Giờ kết thúc"
        value={endTime}
        error={endError}
        onChange={onEndTimeChange}
      />
    </div>
  );
}

function TimePickerField({
  error,
  label,
  onChange,
  value,
}: {
  error?: string;
  label: string;
  onChange: (value: string) => void;
  value: string;
}) {
  const [open, setOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  const parsed = useMemo(() => parseTimeValue(value), [value]);

  usePickerDismiss(open, rootRef, () => setOpen(false));

  useEffect(() => {
    if (!open) return undefined;

    const timeoutId = window.setTimeout(() => {
      panelRef.current?.scrollIntoView({ block: "nearest", inline: "nearest" });
    }, 0);

    return () => window.clearTimeout(timeoutId);
  }, [open]);

  const handleHourChange = (hour: string) => {
    onChange(`${hour}:${parsed.minute}`);
  };

  const handleMinuteChange = (minute: string) => {
    onChange(`${parsed.hour}:${minute}`);
    setOpen(false);
  };

  return (
    <div className="class-form-group class-picker-field" ref={rootRef}>
      <span className="class-field-label">{label}</span>
      <button
        className={`class-picker-trigger ${open ? "open" : ""}`}
        type="button"
        aria-label={`Chọn ${label.toLowerCase()}`}
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
      >
        <Clock3 size={18} aria-hidden="true" />
        <span>{parsed.display}</span>
        <ChevronDown className="class-picker-chevron" size={18} aria-hidden="true" />
      </button>

      {open ? (
        <div
          className="class-picker-panel class-time-picker-panel"
          ref={panelRef}
          role="dialog"
          aria-label={`Bảng chọn ${label.toLowerCase()}`}
        >
          <div className="class-time-picker-columns">
            <div className="class-picker-column">
              <span className="class-picker-column-title">Giờ</span>
              <div className="class-time-option-grid hours">
                {hours.map((hour) => (
                  <button
                    className={hour === parsed.hour ? "selected" : ""}
                    key={hour}
                    type="button"
                    onClick={() => handleHourChange(hour)}
                  >
                    {hour}
                  </button>
                ))}
              </div>
            </div>

            <div className="class-picker-column">
              <span className="class-picker-column-title">Phút</span>
              <div className="class-time-option-grid minutes">
                {minutes.map((minute) => (
                  <button
                    className={minute === parsed.minute ? "selected" : ""}
                    key={minute}
                    type="button"
                    onClick={() => handleMinuteChange(minute)}
                  >
                    {minute}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <button className="class-picker-done-button" type="button" onClick={() => setOpen(false)}>
            <Check size={16} aria-hidden="true" />
            Xong
          </button>
        </div>
      ) : null}

      {error ? <p className="class-field-error">{error}</p> : null}
    </div>
  );
}

function parseTimeValue(value: string) {
  const match = /^(\d{2}):(\d{2})$/.exec(value);
  const hour = match && Number(match[1]) >= 0 && Number(match[1]) <= 23 ? match[1] : "07";
  const minute = match && Number(match[2]) >= 0 && Number(match[2]) <= 59 ? match[2] : "00";
  return {
    display: `${hour}:${minute}`,
    hour,
    minute,
  };
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
