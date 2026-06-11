import React, { useState } from "react";
import { Lock, User as UserIcon, Eye, EyeOff, UserPlus } from "lucide-react";

interface RegisterFormProps {
  onSubmit: (username: string, password: string, fullName: string) => Promise<void>;
  isLoading: boolean;
  errorMsg: string;
}

export function RegisterForm({ onSubmit, isLoading, errorMsg }: RegisterFormProps) {
  const [fullName, setFullName] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [validationError, setValidationError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError("");

    if (!fullName.trim() || !username.trim() || !password || !confirmPassword) {
      setValidationError("Vui lòng nhập đầy đủ thông tin.");
      return;
    }

    const usernameRegex = /^[a-zA-Z0-9_.]+$/;
    if (!usernameRegex.test(username)) {
      setValidationError("Tên đăng nhập chỉ gồm chữ cái, số, dấu gạch dưới (_) và dấu chấm (.)");
      return;
    }

    if (username.length < 3 || username.length > 30) {
      setValidationError("Tên đăng nhập phải từ 3 đến 30 ký tự.");
      return;
    }

    if (password.length < 8) {
      setValidationError("Mật khẩu phải chứa ít nhất 8 ký tự.");
      return;
    }

    if (password !== confirmPassword) {
      setValidationError("Mật khẩu xác nhận không khớp.");
      return;
    }

    try {
      await onSubmit(username.trim(), password, fullName.trim());
    } catch {
      // API error handled by parent component
    }
  };

  const activeError = validationError || errorMsg;

  return (
    <form className="auth-card-form" onSubmit={handleSubmit}>
      {activeError && <div className="auth-error-banner">{activeError}</div>}

      <div className="auth-input-group">
        <label htmlFor="reg-name">Họ và tên sinh viên</label>
        <div className="input-with-icon-wrapper">
          <UserIcon size={18} className="input-inner-icon" />
          <input
            id="reg-name"
            type="text"
            placeholder="Ví dụ: Nguyễn Văn A"
            value={fullName}
            onChange={(e) => {
              setFullName(e.target.value);
              setValidationError("");
            }}
            disabled={isLoading}
            required
            className="auth-form-input"
          />
        </div>
      </div>

      <div className="auth-input-group">
        <label htmlFor="reg-username">Tên đăng nhập (3-30 ký tự)</label>
        <div className="input-with-icon-wrapper">
          <UserIcon size={18} className="input-inner-icon" />
          <input
            id="reg-username"
            type="text"
            placeholder="ví dụ: nguyenvana"
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
        <label htmlFor="reg-password">Mật khẩu (tối thiểu 8 ký tự)</label>
        <div className="input-with-icon-wrapper">
          <Lock size={18} className="input-inner-icon" />
          <input
            id="reg-password"
            type={showPassword ? "text" : "password"}
            placeholder="Tạo mật khẩu bảo mật"
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

      <div className="auth-input-group">
        <label htmlFor="reg-confirm">Xác nhận mật khẩu</label>
        <div className="input-with-icon-wrapper">
          <Lock size={18} className="input-inner-icon" />
          <input
            id="reg-confirm"
            type={showPassword ? "text" : "password"}
            placeholder="Nhập lại mật khẩu"
            value={confirmPassword}
            onChange={(e) => {
              setConfirmPassword(e.target.value);
              setValidationError("");
            }}
            disabled={isLoading}
            required
            className="auth-form-input"
          />
        </div>
      </div>

      <button
        type="submit"
        disabled={isLoading}
        className="auth-submit-btn btn-primary"
        style={{ marginTop: "1rem" }}
      >
        {isLoading ? (
          <span className="btn-loading-wrapper">
            <span className="spinner-mini" /> Đang tạo tài khoản...
          </span>
        ) : (
          <>
            Đăng ký tài khoản <UserPlus size={18} />
          </>
        )}
      </button>
    </form>
  );
}
