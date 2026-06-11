import type { PropsWithChildren } from "react";

import type { AppView } from "../../types/weather";
import { BottomNav } from "./BottomNav";
import { Sidebar } from "./Sidebar";

type AppLayoutProps = PropsWithChildren<{
  activeView: AppView;
  timeZone?: string;
  onNavigate: (view: AppView) => void;
  onOpenLogin: () => void;
}>;

export function AppLayout({ activeView, children, onNavigate, timeZone, onOpenLogin }: AppLayoutProps) {
  return (
    <div className="app-shell">
      <Sidebar activeView={activeView} timeZone={timeZone} onNavigate={onNavigate} onOpenLogin={onOpenLogin} />
      <main className="main-content">{children}</main>
      <BottomNav activeView={activeView} onNavigate={onNavigate} />
    </div>
  );
}
