import React from "react";
import { LogIn, LogOut, User as UserIcon } from "lucide-react";
import type { User } from "../../types/weather";

interface SidebarAccountCardProps {
  user: User | null;
  isAuthenticated: boolean;
  isLoading?: boolean;
  onLogin: () => void;
  onLogout: () => void;
}

export function SidebarAccountCard({
  user,
  isAuthenticated,
  isLoading = false,
  onLogin,
  onLogout,
}: SidebarAccountCardProps) {
  if (isLoading) {
    return (
      <div className="sidebar-account-card loading-state">
        <span className="spinner-mini" aria-hidden="true" />
        <span>Đang tải tài khoản...</span>
      </div>
    );
  }

  if (!isAuthenticated || !user) {
    return (
      <div className="sidebar-account-card unauthenticated">
        <div className="account-card-header">
          <div className="icon-glow-badge">
            <UserIcon size={16} />
          </div>
          <div className="header-text">
            <strong>Đăng nhập</strong>
            <span>Đồng bộ lịch học và vị trí</span>
          </div>
        </div>
        <button type="button" className="account-login-btn premium-btn" onClick={onLogin}>
          Đăng nhập ngay <LogIn size={13} style={{ marginLeft: "2px" }} />
        </button>
      </div>
    );
  }

  return (
    <div className="sidebar-account-card authenticated">
      <img
        src={user.avatar_url || "https://www.gravatar.com/avatar/00000000000000000000000000000000?d=mp&f=y"}
        alt="Avatar"
        className="user-profile-avatar"
      />
      <div className="user-profile-info" style={{ overflow: "hidden", minWidth: 0, flex: 1 }}>
        <span
          className="user-profile-name"
          title={user.full_name || "Sinh viên"}
          style={{ textOverflow: "ellipsis", overflow: "hidden", whiteSpace: "nowrap", display: "block" }}
        >
          {user.full_name || "Sinh viên"}
        </span>
        <span
          className="user-profile-email"
          title={user.auth_provider === "local" ? (user.username || "") : (user.email || "")}
          style={{ textOverflow: "ellipsis", overflow: "hidden", whiteSpace: "nowrap", display: "block" }}
        >
          {user.auth_provider === "local" ? user.username : (user.email || "Facebook Account")}
        </span>
      </div>
      <button type="button" className="user-logout-btn" onClick={onLogout} title="Đăng xuất">
        <LogOut size={16} />
      </button>
    </div>
  );
}
