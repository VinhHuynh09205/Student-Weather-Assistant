import { BookOpen, Cloud, Home, Settings } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import type { AppView } from "../../types/weather";
import { useAutoHideBottomNav } from "../../hooks/useAutoHideBottomNav";

const navItems: Array<{ id: AppView; label: string; Icon: LucideIcon }> = [
  { id: "home", label: "Home", Icon: Home },
  { id: "forecast", label: "Dự báo", Icon: Cloud },
  { id: "study", label: "Trợ lý", Icon: BookOpen },
  { id: "settings", label: "Cài đặt", Icon: Settings },
];

type BottomNavProps = {
  activeView: AppView;
  onNavigate: (view: AppView) => void;
};

export function BottomNav({ activeView, onNavigate }: BottomNavProps) {
  const isHidden = useAutoHideBottomNav();

  return (
    <nav className={`bottom-nav ${isHidden ? "hidden" : "visible"}`} aria-label="Điều hướng mobile">
      {navItems.map(({ Icon, ...item }) => (
        <button
          className={activeView === item.id ? "active" : ""}
          key={item.id}
          type="button"
          onClick={() => onNavigate(item.id)}
        >
          <Icon size={18} aria-hidden="true" />
          <span>{item.label}</span>
        </button>
      ))}
    </nav>
  );
}
