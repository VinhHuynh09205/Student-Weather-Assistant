import { useState, useRef, useEffect } from "react";
import { Calendar, ChevronLeft, ChevronRight } from "lucide-react";
import type { StudyDateMode } from "../../types/weather";

type DateSelectorProps = {
  mode: StudyDateMode;
  value: string;
  onModeChange: (mode: StudyDateMode) => void;
  onDateChange: (value: string) => void;
};

export function DateSelector({ mode, onDateChange, onModeChange, value }: DateSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  
  // Calculate range bounds relative to current date
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const maxDate = new Date(today);
  maxDate.setDate(today.getDate() + 8); // Capped at 8 days forecast

  // Parse current value or default to today for calendar view
  const initialDate = value ? new Date(value) : new Date();
  const [viewDate, setViewDate] = useState(initialDate);
  const calendarRef = useRef<HTMLDivElement>(null);

  // Close calendar popover on click outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (calendarRef.current && !calendarRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  // Sync viewDate when opening popover or when value changes
  useEffect(() => {
    if (isOpen && value) {
      const parsed = new Date(value);
      if (!isNaN(parsed.getTime())) {
        setViewDate(parsed);
      }
    }
  }, [isOpen, value]);

  const toggleCalendar = () => {
    setIsOpen(!isOpen);
  };

  const selectPreset = (newMode: StudyDateMode) => {
    onModeChange(newMode);
    setIsOpen(false);
  };

  const handleDayClick = (date: Date) => {
    const selected = new Date(date);
    selected.setHours(0, 0, 0, 0);
    
    if (selected >= today && selected <= maxDate) {
      const yyyy = selected.getFullYear();
      const mm = String(selected.getMonth() + 1).padStart(2, "0");
      const dd = String(selected.getDate()).padStart(2, "0");
      const formatted = `${yyyy}-${mm}-${dd}`;
      onDateChange(formatted);
      setIsOpen(false);
    }
  };

  const changeMonth = (offset: number) => {
    setViewDate(new Date(viewDate.getFullYear(), viewDate.getMonth() + offset, 1));
  };

  const getCustomLabel = () => {
    if (mode === "custom" && value) {
      return formatCustomDateLabel(value);
    }
    return "Chọn ngày";
  };

  // Generate calendar days
  const year = viewDate.getFullYear();
  const month = viewDate.getMonth();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const firstDayIndex = new Date(year, month, 1).getDay(); // Sunday = 0, Monday = 1, etc.
  
  // Shift firstDayIndex so Monday = 0, Sunday = 6
  const startOffset = firstDayIndex === 0 ? 6 : firstDayIndex - 1;

  const daysArray = [];
  // Previous month padding days
  const prevMonthDays = new Date(year, month, 0).getDate();
  for (let i = startOffset - 1; i >= 0; i--) {
    daysArray.push({
      day: prevMonthDays - i,
      isCurrentMonth: false,
      date: new Date(year, month - 1, prevMonthDays - i),
    });
  }

  // Current month days
  for (let i = 1; i <= daysInMonth; i++) {
    daysArray.push({
      day: i,
      isCurrentMonth: true,
      date: new Date(year, month, i),
    });
  }

  // Next month padding days to fill 42 cells (6 rows)
  const remainingCells = 42 - daysArray.length;
  for (let i = 1; i <= remainingCells; i++) {
    daysArray.push({
      day: i,
      isCurrentMonth: false,
      date: new Date(year, month + 1, i),
    });
  }

  // Navigation bounds
  const currentYearMonth = today.getFullYear() * 12 + today.getMonth();
  const viewYearMonth = viewDate.getFullYear() * 12 + viewDate.getMonth();
  const maxYearMonth = maxDate.getFullYear() * 12 + maxDate.getMonth();
  
  const canGoPrev = viewYearMonth > currentYearMonth;
  const canGoNext = viewYearMonth < maxYearMonth;

  return (
    <div className="date-selector" ref={calendarRef}>
      <span className="field-label">Ngày học</span>
      <div className="segmented-control schedule-date-options">
        <button
          className={mode === "today" ? "selected" : ""}
          type="button"
          onClick={() => selectPreset("today")}
        >
          Hôm nay
        </button>
        <button
          className={mode === "tomorrow" ? "selected" : ""}
          type="button"
          onClick={() => selectPreset("tomorrow")}
        >
          Ngày mai
        </button>
        <button
          className={mode === "custom" ? "selected custom-date-btn" : "custom-date-btn"}
          type="button"
          onClick={toggleCalendar}
        >
          <Calendar size={16} />
          <span>{getCustomLabel()}</span>
        </button>
      </div>

      <p className="field-note">Bạn có thể chọn ngày trong 8 ngày tới.</p>

      {isOpen && (
        <div className="calendar-popover glass-card">
          <header className="calendar-header">
            <button
              type="button"
              className="nav-btn"
              onClick={() => changeMonth(-1)}
              disabled={!canGoPrev}
            >
              <ChevronLeft size={18} />
            </button>
            <span className="calendar-title">
              Tháng {month + 1}, {year}
            </span>
            <button
              type="button"
              className="nav-btn"
              onClick={() => changeMonth(1)}
              disabled={!canGoNext}
            >
              <ChevronRight size={18} />
            </button>
          </header>

          <div className="calendar-weekdays">
            <span>T2</span>
            <span>T3</span>
            <span>T4</span>
            <span>T5</span>
            <span>T6</span>
            <span>T7</span>
            <span>CN</span>
          </div>

          <div className="calendar-grid">
            {daysArray.map((cell, idx) => {
              const cellDate = new Date(cell.date);
              cellDate.setHours(0, 0, 0, 0);
              
              const isDisabled = cellDate < today || cellDate > maxDate;
              const isSelected = mode === "custom" && value === formatDateString(cellDate);
              const isToday = formatDateString(cellDate) === formatDateString(new Date());

              let classNames = "calendar-day";
              if (!cell.isCurrentMonth) classNames += " other-month";
              if (isDisabled) classNames += " disabled";
              if (isSelected) classNames += " selected";
              if (isToday) classNames += " today";

              return (
                <button
                  key={`${cell.day}-${idx}`}
                  type="button"
                  className={classNames}
                  disabled={isDisabled}
                  onClick={() => handleDayClick(cell.date)}
                >
                  {cell.day}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

function formatDateString(date: Date): string {
  const yyyy = date.getFullYear();
  const mm = String(date.getMonth() + 1).padStart(2, "0");
  const dd = String(date.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

function formatCustomDateLabel(dateStr: string): string {
  if (!dateStr) return "Chọn ngày";
  const [year, month, day] = dateStr.split("-").map(Number);
  if (!year || !month || !day) return dateStr;
  const date = new Date(year, month - 1, day);
  
  const weekdays = [
    "Chủ Nhật",
    "Thứ Hai",
    "Thứ Ba",
    "Thứ Tư",
    "Thứ Năm",
    "Thứ Sáu",
    "Thứ Bảy"
  ];
  
  const weekday = weekdays[date.getDay()];
  const dd = String(day).padStart(2, "0");
  const mm = String(month).padStart(2, "0");
  
  return `${weekday}, ${dd}/${mm}`;
}
