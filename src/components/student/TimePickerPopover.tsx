import { useEffect, useRef, useState } from "react";

type TimePickerPopoverProps = {
  value: string;
  onChange: (value: string) => void;
  onClose: () => void;
  align?: "left" | "right";
};

// Generate list of 30-minute intervals from 05:00 to 22:00
const quickTimeSlots: string[] = [];
for (let h = 5; h <= 22; h++) {
  const hr = String(h).padStart(2, "0");
  quickTimeSlots.push(`${hr}:00`);
  if (h < 22) {
    quickTimeSlots.push(`${hr}:30`);
  }
}

export function TimePickerPopover({ value, onChange, onClose, align = "left" }: TimePickerPopoverProps) {
  const popoverRef = useRef<HTMLDivElement>(null);
  
  // Parse initial values
  const [currentHour, currentMinute] = value.split(":");
  const [selectedHour, setSelectedHour] = useState(currentHour || "07");
  const [selectedMinute, setSelectedMinute] = useState(currentMinute || "30");

  // Handle click outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (popoverRef.current && !popoverRef.current.contains(event.target as Node)) {
        onClose();
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [onClose]);

  const handleQuickSelect = (time: string) => {
    onChange(time);
    onClose();
  };

  const handleCustomSubmit = () => {
    onChange(`${selectedHour}:${selectedMinute}`);
    onClose();
  };

  const hours = Array.from({ length: 24 }, (_, i) => String(i).padStart(2, "0"));
  
  // Build minutes list, ensuring the current value is included
  const minutes = ["00", "15", "30", "45"];
  if (currentMinute && !minutes.includes(currentMinute)) {
    minutes.push(currentMinute);
    minutes.sort();
  }

  return (
    <div className={`time-picker-popover glass-card align-${align}`} ref={popoverRef}>
      <div className="picker-section-title">Chọn giờ nhanh</div>
      <div className="quick-time-grid custom-scrollbar">
        {quickTimeSlots.map((time) => {
          const isActive = value === time;
          return (
            <button
              key={time}
              type="button"
              className={`quick-time-btn ${isActive ? "active" : ""}`}
              onClick={() => handleQuickSelect(time)}
            >
              {time}
            </button>
          );
        })}
      </div>

      <div className="picker-divider" />

      <div className="picker-section-title">Tùy chỉnh khác</div>
      <div className="custom-time-selectors">
        <div className="selector-group">
          <label>Giờ</label>
          <select
            value={selectedHour}
            onChange={(e) => setSelectedHour(e.target.value)}
            className="custom-select"
          >
            {hours.map((h) => (
              <option key={h} value={h}>
                {h}h
              </option>
            ))}
          </select>
        </div>

        <div className="selector-group">
          <label>Phút</label>
          <select
            value={selectedMinute}
            onChange={(e) => setSelectedMinute(e.target.value)}
            className="custom-select"
          >
            {minutes.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </div>

        <button type="button" className="custom-time-submit" onClick={handleCustomSubmit}>
          Xong
        </button>
      </div>
    </div>
  );
}
