import { BookOpen, Cloud, CloudSun, Home, Settings } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import type { AppView } from "../../types/weather";
import { useRealtimeClock } from "../../hooks/useRealtimeClock";
import { formatClockTime, formatDateLabel } from "../../utils/timeHelpers";
import { useAuth } from "../../context/AuthContext";
import { SidebarAccountCard } from "./SidebarAccountCard";

const navItems: Array<{ id: AppView; label: string; Icon: LucideIcon }> = [
  { id: "home", label: "Trang chủ", Icon: Home },
  { id: "forecast", label: "Dự báo", Icon: Cloud },
  { id: "study", label: "Trợ lý đi học", Icon: BookOpen },
  { id: "settings", label: "Cài đặt", Icon: Settings },
];

type SidebarProps = {
  activeView: AppView;
  timeZone?: string;
  onNavigate: (view: AppView) => void;
  onOpenLogin: () => void;
};

export function Sidebar({ activeView, onNavigate, timeZone, onOpenLogin }: SidebarProps) {
  const now = useRealtimeClock(timeZone);
  const { currentUser, logout, isLoading } = useAuth();

  return (
    <aside className="sidebar">
      <div className="brand">
        <CloudSun size={34} />
        <div>
          <strong>
            Student
            <br />
            Weather
          </strong>
          <span>Trợ lý thời tiết sinh viên</span>
        </div>
      </div>

      <nav className="side-nav" aria-label="Điều hướng chính">
        {navItems.map(({ Icon, ...item }) => (
          <button
            className={`nav-item ${activeView === item.id ? "active" : ""}`}
            key={item.id}
            type="button"
            onClick={() => onNavigate(item.id)}
          >
            <Icon size={24} aria-hidden="true" />
            {item.label}
          </button>
        ))}
      </nav>

      <div className="sidebar-bottom-section">
        <div className="time-card" aria-label="Thời gian hiện tại">
          <strong>{formatClockTime(now, timeZone)}</strong>
          <span>{formatDateLabel(now, timeZone)}</span>
        </div>

        <SidebarAccountCard
          user={currentUser}
          isAuthenticated={!!currentUser}
          isLoading={isLoading}
          onLogin={onOpenLogin}
          onLogout={logout}
        />
      </div>
    </aside>
  );
}
