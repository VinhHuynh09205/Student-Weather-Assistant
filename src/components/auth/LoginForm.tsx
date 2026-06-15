import React, { useState } from "react";
import { User, Lock, Eye, EyeOff, ArrowRight } from "lucide-react";

interface LoginFormProps {
  onSubmit: (username: string, password: string, rememberMe: boolean) => Promise<void>;
  isLoading: boolean;
  errorMsg: string;
}

export function LoginForm({ onSubmit, isLoading, errorMsg }: LoginFormProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [validationError, setValidationError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError("");

    if (!username.trim() || !password) {
      setValidationError("Vui lòng điền đầy đủ Tên đăng nhập và Mật khẩu.");
      return;
    }

    try {
      await onSubmit(username.trim(), password, rememberMe);
    } catch {
      // Parent component handles specific network/API errors
    }
  };

  const activeError = validationError || errorMsg;

  return (
    <form className="auth-card-form" onSubmit={handleSubmit}>
      {activeError && <div className="auth-error-banner">{activeError}</div>}

      <div className="auth-input-group">
        <label htmlFor="login-username">Tên đăng nhập</label>
        <div className="input-with-icon-wrapper">
          <User size={18} className="input-inner-icon" />
          <input
            id="login-username"
            type="text"
            placeholder="ví dụ: vinhstudent"
            value={username}
            onChange={(e) => {
              setUsername(e.target.value);
              setValidationError("");
            }}
            disabled={isLoading}
            required
            className="auth-form-input"
          />
        </div>
      </div>

      <div className="auth-input-group">
        <label htmlFor="login-password">Mật khẩu</label>
        <div className="input-with-icon-wrapper">
          <Lock size={18} className="input-inner-icon" />
          <input
            id="login-password"
            type={showPassword ? "text" : "password"}
            placeholder="Mật khẩu của bạn"
            value={password}
            onChange={(e) => {
              setPassword(e.target.value);
              setValidationError("");
            }}
            disabled={isLoading}
            required
            className="auth-form-input"
          />
          <button
            type="button"
            className="password-toggle-btn"
            onClick={() => setShowPassword(!showPassword)}
            title={showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
          >
            {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        </div>
      </div>

      <div className="form-options-row">
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={rememberMe}
            onChange={(e) => setRememberMe(e.target.checked)}
            disabled={isLoading}
          />
          <span>Ghi nhớ tôi</span>
        </label>
        <button
          type="button"
          className="forgot-pass-link"
          onClick={() => alert("Chức năng khôi phục mật khẩu đang được phát triển.")}
          disabled={isLoading}
        >
          Quên mật khẩu?
        </button>
      </div>

      <button
        type="submit"
        disabled={isLoading}
        className="auth-submit-btn btn-primary"
      >
        {isLoading ? (
          <span className="btn-loading-wrapper">
            <span className="spinner-mini" /> Đang đăng nhập...
          </span>
        ) : (
          <>
            Đăng nhập <ArrowRight size={18} />
          </>
        )}
      </button>
    </form>
  );
}
